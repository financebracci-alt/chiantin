"""Statement generation service using WeasyPrint (lazy imported)."""

from motor.motor_asyncio import AsyncIOMotorDatabase
from datetime import datetime, timedelta
from typing import Optional
from io import BytesIO
import calendar
import logging

from services.ledger_service import LedgerEngine
from utils.common import serialize_doc

logger = logging.getLogger(__name__)

# Lazy import flag for WeasyPrint
_weasyprint_available = None
_HTML = None


def _get_weasyprint():
    """Lazily import WeasyPrint only when needed."""
    global _weasyprint_available, _HTML
    
    if _weasyprint_available is None:
        try:
            from weasyprint import HTML
            _HTML = HTML
            _weasyprint_available = True
            logger.info("WeasyPrint loaded successfully")
        except ImportError as e:
            _weasyprint_available = False
            _HTML = None
            logger.warning(f"WeasyPrint not available: {e}. PDF generation will be disabled.")
        except Exception as e:
            _weasyprint_available = False
            _HTML = None
            logger.warning(f"WeasyPrint failed to load: {e}. PDF generation will be disabled.")
    
    return _HTML


class StatementService:
    def __init__(self, db: AsyncIOMotorDatabase, ledger_engine: LedgerEngine):
        self.db = db
        self.ledger = ledger_engine
    
    async def generate_monthly_statement(
        self,
        user_id: str,
        account_id: str,
        year: int,
        month: int
    ) -> bytes:
        """Generate monthly statement PDF for an account."""
        # Check if WeasyPrint is available
        HTML = _get_weasyprint()
        if HTML is None:
            raise ValueError("PDF generation is not available. WeasyPrint dependency not installed.")
        
        # Get account
        account = await self.db.bank_accounts.find_one({"_id": account_id})
        if not account or account["user_id"] != user_id:
            raise ValueError("Account not found or access denied")
        
        # Get user
        user = await self.db.users.find_one({"_id": user_id})
        
        # Get date range
        start_date = datetime(year, month, 1)
        last_day = calendar.monthrange(year, month)[1]
        end_date = datetime(year, month, last_day, 23, 59, 59)
        
        # Get transactions for the month
        txn_cursor = self.db.ledger_transactions.find({
            "created_at": {"$gte": start_date, "$lte": end_date}
        }).sort("created_at", 1)
        
        transactions = []
        async for doc in txn_cursor:
            # Check if this transaction affects this account
            entry = await self.db.ledger_entries.find_one({
                "transaction_id": str(doc["_id"]),
                "account_id": account["ledger_account_id"]
            })
            if entry:
                transactions.append({
                    "id": str(doc["_id"]),
                    "date": doc["created_at"].strftime("%Y-%m-%d %H:%M"),
                    "type": doc["transaction_type"],
                    "reason": doc.get("reason", ""),
                    "amount": entry["amount"],
                    "direction": entry["direction"],
                    "status": doc["status"]
                })
        
        # Get opening and closing balance
        opening_balance = await self._get_balance_at_date(
            account["ledger_account_id"],
            start_date
        )
        closing_balance = await self.ledger.get_balance(account["ledger_account_id"])
        
        # Generate HTML
        html_content = self._generate_statement_html(
            user=user,
            account=account,
            transactions=transactions,
            opening_balance=opening_balance,
            closing_balance=closing_balance,
            period=f"{calendar.month_name[month]} {year}"
        )
        
        # Convert to PDF
        pdf_bytes = HTML(string=html_content).write_pdf()
        return pdf_bytes
    
    async def _get_balance_at_date(self, account_id: str, cutoff_date: datetime) -> int:
        """Calculate balance at a specific date."""
        pipeline = [
            {
                "$match": {
                    "account_id": account_id,
                    "created_at": {"$lt": cutoff_date}
                }
            },
            {
                "$group": {
                    "_id": None,
                    "credits": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$direction", "CREDIT"]},
                                "$amount",
                                0
                            ]
                        }
                    },
                    "debits": {
                        "$sum": {
                            "$cond": [
                                {"$eq": ["$direction", "DEBIT"]},
                                "$amount",
                                0
                            ]
                        }
                    }
                }
            }
        ]
        
        result = await self.db.ledger_entries.aggregate(pipeline).to_list(1)
        
        if not result:
            return 0
        
        return result[0]["credits"] - result[0]["debits"]
    
    def _generate_statement_html(
        self,
        user: dict,
        account: dict,
        transactions: list,
        opening_balance: int,
        closing_balance: int,
        period: str
    ) -> str:
        """Generate HTML for statement."""
        def format_amount(cents):
            return f"€{cents / 100:.2f}"
        
        transactions_html = ""
        for txn in transactions:
            amount_class = "text-green-600" if txn["direction"] == "CREDIT" else "text-red-600"
            sign = "+" if txn["direction"] == "CREDIT" else "-"
            transactions_html += f"""
            <tr>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{txn['date']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{txn['type']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">{txn['reason']}</td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb; text-align: right; color: {'#0B7D5A' if txn['direction'] == 'CREDIT' else '#DC2626'};">
                    {sign}{format_amount(txn['amount'])}
                </td>
                <td style="padding: 12px; border-bottom: 1px solid #e5e7eb;">
                    <span style="background: {'#D1FAE5' if txn['status'] == 'POSTED' else '#E5E7EB'}; color: {'#065F46' if txn['status'] == 'POSTED' else '#374151'}; padding: 4px 8px; border-radius: 4px; font-size: 12px;">
                        {txn['status']}
                    </span>
                </td>
            </tr>
            """
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Account Statement - {period}</title>
            <style>
                @page {{ size: A4; margin: 2cm; }}
                body {{ font-family: 'Inter', 'Arial', sans-serif; font-size: 10pt; color: #1F2937; }}
                h1 {{ font-family: 'Space Grotesk', sans-serif; color: #dc3545; margin: 0 0 20px 0; }}
                .header {{ margin-bottom: 30px; padding-bottom: 20px; border-bottom: 2px solid #dc3545; }}
                .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 30px; }}
                .info-item {{ }}
                .info-label {{ font-size: 9pt; color: #6B7280; margin-bottom: 4px; }}
                .info-value {{ font-weight: 600; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                th {{ background: #F3F4F6; padding: 12px; text-align: left; font-weight: 600; border-bottom: 2px solid #D1D5DB; }}
                .summary {{ margin-top: 30px; padding-top: 20px; border-top: 2px solid #E5E7EB; }}
                .balance-row {{ display: flex; justify-content: space-between; padding: 8px 0; }}
                .balance-label {{ font-weight: 500; }}
                .balance-amount {{ font-weight: 700; font-family: 'IBM Plex Mono', monospace; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Chiantin</h1>
                <p style="color: #6B7280; margin: 0;">Account Statement</p>
            </div>
            
            <div class="info-grid">
                <div class="info-item">
                    <div class="info-label">Account Holder</div>
                    <div class="info-value">{user.get('first_name', '')} {user.get('last_name', '')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Statement Period</div>
                    <div class="info-value">{period}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">Account Number</div>
                    <div class="info-value" style="font-family: 'IBM Plex Mono', monospace;">{account.get('account_number', '')}</div>
                </div>
                <div class="info-item">
                    <div class="info-label">IBAN</div>
                    <div class="info-value" style="font-family: 'IBM Plex Mono', monospace;">{account.get('iban', '')}</div>
                </div>
            </div>
            
            <h2 style="font-size: 12pt; margin-top: 30px; margin-bottom: 15px;">Transactions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Type</th>
                        <th>Description</th>
                        <th style="text-align: right;">Amount</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>
                    {transactions_html if transactions else '<tr><td colspan="5" style="padding: 20px; text-align: center; color: #9CA3AF;">No transactions in this period</td></tr>'}
                </tbody>
            </table>
            
            <div class="summary">
                <div class="balance-row">
                    <span class="balance-label">Opening Balance:</span>
                    <span class="balance-amount">{format_amount(opening_balance)}</span>
                </div>
                <div class="balance-row">
                    <span class="balance-label">Closing Balance:</span>
                    <span class="balance-amount" style="font-size: 14pt; color: #0B7D5A;">{format_amount(closing_balance)}</span>
                </div>
            </div>
            
            <div style="margin-top: 50px; padding-top: 20px; border-top: 1px solid #E5E7EB; font-size: 8pt; color: #9CA3AF;">
                <p>This statement is generated electronically and does not require a signature.</p>
                <p>Generated on: {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}</p>
            </div>
        </body>
        </html>
        """
        
        return html
