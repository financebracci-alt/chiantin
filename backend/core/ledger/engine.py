"""Ledger posting engine with double-entry invariants.

Critical rules enforced:
1. Double-entry: debits = credits per currency in every transaction
2. Append-only: entries never updated/deleted after posting
3. Reversals create new mirrored entries, mark original as REVERSED
4. Idempotency: same external_id = same result (no duplicate postings)
5. Balances always derived from entries (never stored directly)
"""

from typing import List, Optional, Tuple
from datetime import datetime
from .models import (
    LedgerAccount,
    LedgerTransaction,
    LedgerEntry,
    TransactionStatus,
    EntryDirection,
    AccountType
)


class LedgerError(Exception):
    """Base exception for ledger operations."""
    pass


class InvariantViolation(LedgerError):
    """Raised when double-entry or other ledger invariant is violated."""
    pass


class LedgerEngine:
    """Core ledger posting engine (in-memory for POC, will use MongoDB in app)."""
    
    def __init__(self):
        # In-memory stores for POC
        self.accounts: dict[str, LedgerAccount] = {}
        self.transactions: dict[str, LedgerTransaction] = {}
        self.entries: List[LedgerEntry] = []
        self.idempotency_store: dict[str, str] = {}  # external_id -> txn_id
    
    def create_account(
        self,
        account_type: AccountType,
        user_id: Optional[str] = None,
        currency: str = "EUR"
    ) -> LedgerAccount:
        """Create a new ledger account."""
        account = LedgerAccount(
            account_type=account_type,
            user_id=user_id,
            currency=currency
        )
        self.accounts[account.id] = account
        return account
    
    def get_account(self, account_id: str) -> Optional[LedgerAccount]:
        """Get account by ID."""
        return self.accounts.get(account_id)
    
    def get_balance(self, account_id: str) -> int:
        """Calculate derived balance for an account.
        
        Balance = sum(credits) - sum(debits) for this account.
        This is the ONLY way to get balance (never stored directly).
        """
        balance = 0
        for entry in self.entries:
            if entry.account_id == account_id:
                if entry.direction == EntryDirection.CREDIT:
                    balance += entry.amount
                else:  # DEBIT
                    balance -= entry.amount
        return balance
    
    def _validate_entries_balance(
        self,
        entries: List[LedgerEntry]
    ) -> None:
        """Validate double-entry invariant: debits = credits per currency."""
        by_currency: dict[str, Tuple[int, int]] = {}  # currency -> (total_debits, total_credits)
        
        for entry in entries:
            if entry.currency not in by_currency:
                by_currency[entry.currency] = (0, 0)
            
            debits, credits = by_currency[entry.currency]
            if entry.direction == EntryDirection.DEBIT:
                debits += entry.amount
            else:
                credits += entry.amount
            by_currency[entry.currency] = (debits, credits)
        
        # Check balance for each currency
        for currency, (debits, credits) in by_currency.items():
            if debits != credits:
                raise InvariantViolation(
                    f"Unbalanced transaction for {currency}: "
                    f"debits={debits}, credits={credits}"
                )
    
    def post_transaction(
        self,
        transaction_type: str,
        entries: List[Tuple[str, int, EntryDirection]],  # (account_id, amount, direction)
        external_id: Optional[str] = None,
        reason: Optional[str] = None,
        performed_by: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> LedgerTransaction:
        """Post a transaction with entries (atomic operation).
        
        Args:
            transaction_type: TOP_UP, WITHDRAW, FEE, TRANSFER, etc.
            entries: List of (account_id, amount, direction) tuples
            external_id: Idempotency key (optional)
            reason: Human-readable reason (required for admin ops)
            performed_by: User/admin ID who initiated
            metadata: Additional data
        
        Returns:
            Posted LedgerTransaction
        
        Raises:
            InvariantViolation: If entries don't balance
            LedgerError: If account doesn't exist or idempotency conflict
        """
        # Check idempotency
        if external_id:
            if external_id in self.idempotency_store:
                existing_txn_id = self.idempotency_store[external_id]
                return self.transactions[existing_txn_id]
        
        # Create transaction
        txn = LedgerTransaction(
            transaction_type=transaction_type,
            status=TransactionStatus.POSTED,
            external_id=external_id,
            reason=reason,
            performed_by=performed_by,
            metadata=metadata or {}
        )
        
        # Create entries
        ledger_entries = []
        for account_id, amount, direction in entries:
            # Validate account exists
            if account_id not in self.accounts:
                raise LedgerError(f"Account {account_id} does not exist")
            
            account = self.accounts[account_id]
            entry = LedgerEntry(
                transaction_id=txn.id,
                account_id=account_id,
                amount=amount,
                direction=direction,
                currency=account.currency
            )
            ledger_entries.append(entry)
        
        # Validate double-entry balance
        self._validate_entries_balance(ledger_entries)
        
        # Commit (in POC this is just appending; in real app use MongoDB transaction)
        self.transactions[txn.id] = txn
        self.entries.extend(ledger_entries)
        
        if external_id:
            self.idempotency_store[external_id] = txn.id
        
        return txn
    
    def reverse_transaction(
        self,
        original_txn_id: str,
        external_id: Optional[str] = None,
        reason: Optional[str] = None,
        performed_by: Optional[str] = None
    ) -> LedgerTransaction:
        """Reverse a posted transaction by creating mirror entries.
        
        Creates a new transaction with reversed entries (swap debit/credit).
        Marks original as REVERSED.
        """
        # Check idempotency first
        if external_id and external_id in self.idempotency_store:
            existing_txn_id = self.idempotency_store[external_id]
            return self.transactions[existing_txn_id]
        
        # Get original transaction
        original_txn = self.transactions.get(original_txn_id)
        if not original_txn:
            raise LedgerError(f"Transaction {original_txn_id} not found")
        
        if original_txn.status == TransactionStatus.REVERSED:
            raise LedgerError(f"Transaction {original_txn_id} already reversed")
        
        # Get original entries
        original_entries = [
            e for e in self.entries if e.transaction_id == original_txn_id
        ]
        
        # Create reversal transaction
        reversal_txn = LedgerTransaction(
            transaction_type="REVERSAL",
            status=TransactionStatus.POSTED,
            external_id=external_id,
            reverses_txn_id=original_txn_id,
            reason=reason or f"Reversal of {original_txn_id}",
            performed_by=performed_by,
            metadata={"original_txn_type": original_txn.transaction_type}
        )
        
        # Create mirror entries (swap direction)
        reversal_entries = []
        for orig_entry in original_entries:
            reversed_direction = (
                EntryDirection.CREDIT if orig_entry.direction == EntryDirection.DEBIT
                else EntryDirection.DEBIT
            )
            reversal_entry = LedgerEntry(
                transaction_id=reversal_txn.id,
                account_id=orig_entry.account_id,
                amount=orig_entry.amount,
                direction=reversed_direction,
                currency=orig_entry.currency
            )
            reversal_entries.append(reversal_entry)
        
        # Validate balance (should always balance since it's a mirror)
        self._validate_entries_balance(reversal_entries)
        
        # Commit
        self.transactions[reversal_txn.id] = reversal_txn
        self.entries.extend(reversal_entries)
        
        # Mark original as reversed (this is the ONLY update allowed on transactions)
        original_txn.status = TransactionStatus.REVERSED
        original_txn.reversed_by_txn_id = reversal_txn.id
        
        if external_id:
            self.idempotency_store[external_id] = reversal_txn.id
        
        return reversal_txn
    
    # Convenience methods for common operations
    
    def top_up(
        self,
        user_account_id: str,
        amount: int,
        external_id: Optional[str] = None,
        reason: str = "Sandbox top-up",
        performed_by: Optional[str] = None
    ) -> LedgerTransaction:
        """Add funds to user account (from sandbox funding).
        
        Entries:
        - CREDIT user_account (increase balance)
        - DEBIT sandbox_funding (source of funds)
        """
        # Find or create sandbox funding account
        funding_account = None
        for acc in self.accounts.values():
            if acc.account_type == AccountType.SANDBOX_FUNDING:
                funding_account = acc
                break
        
        if not funding_account:
            funding_account = self.create_account(AccountType.SANDBOX_FUNDING)
        
        return self.post_transaction(
            transaction_type="TOP_UP",
            entries=[
                (user_account_id, amount, EntryDirection.CREDIT),
                (funding_account.id, amount, EntryDirection.DEBIT)
            ],
            external_id=external_id,
            reason=reason,
            performed_by=performed_by
        )
    
    def withdraw(
        self,
        user_account_id: str,
        amount: int,
        external_id: Optional[str] = None,
        reason: str = "Sandbox withdrawal",
        performed_by: Optional[str] = None
    ) -> LedgerTransaction:
        """Remove funds from user account.
        
        Entries:
        - DEBIT user_account (decrease balance)
        - CREDIT sandbox_funding (destination of funds)
        """
        funding_account = None
        for acc in self.accounts.values():
            if acc.account_type == AccountType.SANDBOX_FUNDING:
                funding_account = acc
                break
        
        if not funding_account:
            funding_account = self.create_account(AccountType.SANDBOX_FUNDING)
        
        return self.post_transaction(
            transaction_type="WITHDRAW",
            entries=[
                (user_account_id, amount, EntryDirection.DEBIT),
                (funding_account.id, amount, EntryDirection.CREDIT)
            ],
            external_id=external_id,
            reason=reason,
            performed_by=performed_by
        )
    
    def charge_fee(
        self,
        user_account_id: str,
        amount: int,
        external_id: Optional[str] = None,
        reason: str = "Service fee",
        performed_by: Optional[str] = None
    ) -> LedgerTransaction:
        """Charge fee to user account.
        
        Entries:
        - DEBIT user_account (decrease balance)
        - CREDIT fees_account (collect fee)
        """
        fees_account = None
        for acc in self.accounts.values():
            if acc.account_type == AccountType.FEES:
                fees_account = acc
                break
        
        if not fees_account:
            fees_account = self.create_account(AccountType.FEES)
        
        return self.post_transaction(
            transaction_type="FEE",
            entries=[
                (user_account_id, amount, EntryDirection.DEBIT),
                (fees_account.id, amount, EntryDirection.CREDIT)
            ],
            external_id=external_id,
            reason=reason,
            performed_by=performed_by
        )
    
    def internal_transfer(
        self,
        from_account_id: str,
        to_account_id: str,
        amount: int,
        external_id: Optional[str] = None,
        reason: str = "Internal transfer",
        performed_by: Optional[str] = None
    ) -> LedgerTransaction:
        """Transfer between two accounts.
        
        Entries:
        - DEBIT from_account (decrease sender balance)
        - CREDIT to_account (increase recipient balance)
        """
        return self.post_transaction(
            transaction_type="TRANSFER",
            entries=[
                (from_account_id, amount, EntryDirection.DEBIT),
                (to_account_id, amount, EntryDirection.CREDIT)
            ],
            external_id=external_id,
            reason=reason,
            performed_by=performed_by
        )