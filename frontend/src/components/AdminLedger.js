// Enhanced Admin Ledger Tools - Professional Banking
import React, { useState } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { formatEuroAmount } from '../utils/currency';

const TRANSACTION_DISPLAY_TYPES = [
  { value: 'SEPA Transfer', label: 'SEPA Transfer' },
  { value: 'Wire Transfer', label: 'Wire Transfer' },
  { value: 'Internal Transfer', label: 'Internal Transfer' },
  { value: 'Salary Payment', label: 'Salary Payment' },
  { value: 'Refund', label: 'Refund' },
  { value: 'Bank Transfer', label: 'Bank Transfer' },
  { value: 'Cash Deposit', label: 'Cash Deposit' },
  { value: 'Interest Payment', label: 'Interest Payment' },
  { value: 'Bonus', label: 'Bonus' },
  { value: 'Account Correction', label: 'Account Correction' },
  { value: 'Other', label: 'Other' }
];

export function EnhancedLedgerTools({ account, onSuccess }) {
  const toast = useToast();
  const [activeOperation, setActiveOperation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Professional credit form data
  const [creditForm, setCreditForm] = useState({
    amount: '',
    display_type: 'Bank Transfer',
    sender_name: '',
    sender_iban: '',
    sender_bic: '',
    reference: '',
    description: '',
    admin_note: ''
  });

  // Professional debit form data
  const [debitForm, setDebitForm] = useState({
    amount: '',
    display_type: 'Withdrawal',
    recipient_name: '',
    recipient_iban: '',
    reference: '',
    description: '',
    admin_note: ''
  });

  // Simple form data for fee and transfer
  const [simpleForm, setSimpleForm] = useState({
    amount: '',
    reason: '',
    toAccountId: ''
  });

  const handleProfessionalCredit = async () => {
    if (!creditForm.amount) {
      setError('Amount is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Convert euros to cents for the API
      const amountInCents = Math.round(parseFloat(creditForm.amount) * 100);
      
      await api.post(`/admin/accounts/${account.id}/topup`, {
        amount_cents: amountInCents,  // Fixed: Backend expects amount_cents
        display_type: creditForm.display_type,
        sender_name: creditForm.sender_name || null,
        sender_iban: creditForm.sender_iban || null,
        sender_bic: creditForm.sender_bic || null,
        reference: creditForm.reference || null,
        description: creditForm.description || null,
        admin_note: creditForm.admin_note || null
      });
      
      toast.success(`${formatEuroAmount(parseFloat(creditForm.amount))} credited to account`);
      setCreditForm({
        amount: '',
        display_type: 'Bank Transfer',
        sender_name: '',
        sender_iban: '',
        sender_bic: '',
        reference: '',
        description: '',
        admin_note: ''
      });
      setActiveOperation(null);
      onSuccess && onSuccess();
    } catch (err) {
      // Handle validation errors (detail can be array) and other errors
      const errorDetail = err.response?.data?.detail;
      const errorMsg = Array.isArray(errorDetail) 
        ? errorDetail.map(e => e.msg).join(', ') 
        : (errorDetail || 'Credit operation failed');
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleProfessionalDebit = async () => {
    if (!debitForm.amount) {
      setError('Amount is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Convert euros to cents for the API
      const amountInCents = Math.round(parseFloat(debitForm.amount) * 100);
      
      await api.post(`/admin/accounts/${account.id}/withdraw`, {
        amount_cents: amountInCents,  // Fixed: Backend expects amount_cents
        display_type: debitForm.display_type,
        recipient_name: debitForm.recipient_name || null,
        recipient_iban: debitForm.recipient_iban || null,
        reference: debitForm.reference || null,
        description: debitForm.description || null,
        admin_note: debitForm.admin_note || null
      });
      
      toast.success(`${formatEuroAmount(parseFloat(debitForm.amount))} debited from account`);
      setDebitForm({
        amount: '',
        display_type: 'Withdrawal',
        recipient_name: '',
        recipient_iban: '',
        reference: '',
        description: '',
        admin_note: ''
      });
      setActiveOperation(null);
      onSuccess && onSuccess();
    } catch (err) {
      // Handle validation errors (detail can be array) and other errors
      const errorDetail = err.response?.data?.detail;
      const errorMsg = Array.isArray(errorDetail) 
        ? errorDetail.map(e => e.msg).join(', ') 
        : (errorDetail || 'Debit operation failed');
      toast.error(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleChargeFee = async () => {
    if (!simpleForm.amount || !simpleForm.reason) {
      setError('Please fill all fields');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Convert euros to cents for the API
      const amountInCents = Math.round(parseFloat(simpleForm.amount) * 100);
      
      await api.post('/admin/ledger/charge-fee', {
        account_id: account.id,
        amount: amountInCents,
        reason: simpleForm.reason
      });
      toast.success(`${formatEuroAmount(parseFloat(simpleForm.amount))} fee charged`);
      setSimpleForm({ amount: '', reason: '', toAccountId: '' });
      setActiveOperation(null);
      onSuccess && onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Fee charge failed');
    } finally {
      setLoading(false);
    }
  };

  const handleInternalTransfer = async () => {
    if (!simpleForm.amount || !simpleForm.reason || !simpleForm.toAccountId) {
      setError('Please fill all fields');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Convert euros to cents for the API
      const amountInCents = Math.round(parseFloat(simpleForm.amount) * 100);
      
      await api.post('/admin/ledger/internal-transfer', {
        from_account_id: account.id,
        to_account_id: simpleForm.toAccountId,
        amount: amountInCents,
        reason: simpleForm.reason
      });
      toast.success(`${formatEuroAmount(parseFloat(simpleForm.amount))} transferred`);
      setSimpleForm({ amount: '', reason: '', toAccountId: '' });
      setActiveOperation(null);
      onSuccess && onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Transfer failed');
    } finally {
      setLoading(false);
    }
  };

  const formatAmountFromEuro = (euros) => formatEuroAmount(parseFloat(euros || 0));

  const resetAndClose = () => {
    setActiveOperation(null);
    setCreditForm({
      amount: '',
      display_type: 'Bank Transfer',
      sender_name: '',
      sender_iban: '',
      sender_bic: '',
      reference: '',
      description: '',
      admin_note: ''
    });
    setDebitForm({
      amount: '',
      display_type: 'Withdrawal',
      recipient_name: '',
      recipient_iban: '',
      reference: '',
      description: '',
      admin_note: ''
    });
    setSimpleForm({ amount: '', reason: '', toAccountId: '' });
    setError('');
  };

  return (
    <div className="space-y-4">
      <h4 className="font-medium text-gray-900">Ledger Operations</h4>
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded p-3 text-sm">
          {error}
        </div>
      )}

      {/* Operation Buttons */}
      {!activeOperation ? (
        <div className="grid grid-cols-2 gap-3">
          <button
            onClick={() => setActiveOperation('credit')}
            className="px-4 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 text-sm font-medium"
            data-testid="topup-btn"
          >
            + Credit Account
          </button>
          <button
            onClick={() => setActiveOperation('debit')}
            className="px-4 py-3 bg-red-600 text-white rounded-md hover:bg-red-700 text-sm font-medium"
            data-testid="withdraw-btn"
          >
            - Debit Account
          </button>
          <button
            onClick={() => setActiveOperation('fee')}
            className="px-4 py-3 bg-orange-600 text-white rounded-md hover:bg-orange-700 text-sm font-medium"
            data-testid="fee-btn"
          >
            Fee Charge
          </button>
          <button
            onClick={() => setActiveOperation('transfer')}
            className="px-4 py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 text-sm font-medium"
            data-testid="transfer-btn"
          >
            Internal Transfer
          </button>
        </div>
      ) : activeOperation === 'credit' ? (
        /* Professional Credit Form */
        <div className="border rounded-lg p-4 space-y-4 bg-green-50">
          <div className="flex justify-between items-center border-b pb-2">
            <h5 className="font-semibold text-green-800">Credit Account (Professional)</h5>
            <button onClick={resetAndClose} className="text-sm text-gray-600 hover:text-gray-900">
              Cancel
            </button>
          </div>

          <p className="text-xs text-green-700 bg-green-100 p-2 rounded">
            💡 Configure how this transaction will appear to the customer - like a real bank transfer.
          </p>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Amount (€) *</label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-gray-500">€</span>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={creditForm.amount}
                  onChange={(e) => setCreditForm({ ...creditForm, amount: e.target.value })}
                  placeholder="e.g., 100.00"
                  className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-md"
                  data-testid="credit-amount"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Transaction Type *</label>
              <select
                value={creditForm.display_type}
                onChange={(e) => setCreditForm({ ...creditForm, display_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="credit-type"
              >
                {TRANSACTION_DISPLAY_TYPES.map(t => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="border-t pt-4">
            <p className="text-xs font-medium text-gray-500 mb-2 uppercase">Customer Will See:</p>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sender Name</label>
              <input
                type="text"
                value={creditForm.sender_name}
                onChange={(e) => setCreditForm({ ...creditForm, sender_name: e.target.value })}
                placeholder="e.g., Deutsche Bank AG"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="credit-sender-name"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sender IBAN</label>
              <input
                type="text"
                value={creditForm.sender_iban}
                onChange={(e) => setCreditForm({ ...creditForm, sender_iban: e.target.value })}
                placeholder="e.g., DE89370400440532013000"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="credit-sender-iban"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Sender BIC</label>
              <input
                type="text"
                value={creditForm.sender_bic}
                onChange={(e) => setCreditForm({ ...creditForm, sender_bic: e.target.value })}
                placeholder="e.g., DEUTDEDB"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reference</label>
              <input
                type="text"
                value={creditForm.reference}
                onChange={(e) => setCreditForm({ ...creditForm, reference: e.target.value })}
                placeholder="e.g., TRF2024011500123"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="credit-reference"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description (shown to customer)</label>
            <input
              type="text"
              value={creditForm.description}
              onChange={(e) => setCreditForm({ ...creditForm, description: e.target.value })}
              placeholder="e.g., Salary Payment January 2024"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              data-testid="credit-description"
            />
          </div>

          <div className="border-t pt-4">
            <label className="block text-sm font-medium text-gray-500 mb-1">Admin Note (internal only)</label>
            <textarea
              value={creditForm.admin_note}
              onChange={(e) => setCreditForm({ ...creditForm, admin_note: e.target.value })}
              rows={2}
              placeholder="Internal notes - not shown to customer"
              className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50"
            />
          </div>

          <button
            onClick={handleProfessionalCredit}
            disabled={loading || !creditForm.amount}
            className="w-full py-3 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 font-medium"
            data-testid="submit-credit"
          >
            {loading ? 'Processing...' : `Credit ${creditForm.amount ? formatAmountFromEuro(creditForm.amount) : '€0.00'}`}
          </button>
        </div>
      ) : activeOperation === 'debit' ? (
        /* Professional Debit Form */
        <div className="border rounded-lg p-4 space-y-4 bg-red-50">
          <div className="flex justify-between items-center border-b pb-2">
            <h5 className="font-semibold text-red-800">Debit Account (Professional)</h5>
            <button onClick={resetAndClose} className="text-sm text-gray-600 hover:text-gray-900">
              Cancel
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Amount (€) *</label>
              <div className="relative">
                <span className="absolute left-3 top-2 text-gray-500">€</span>
                <input
                  type="number"
                  step="0.01"
                  min="0.01"
                  value={debitForm.amount}
                  onChange={(e) => setDebitForm({ ...debitForm, amount: e.target.value })}
                  placeholder="e.g., 100.00"
                  className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-md"
                  data-testid="debit-amount"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Transaction Type</label>
              <input
                type="text"
                value={debitForm.display_type}
                onChange={(e) => setDebitForm({ ...debitForm, display_type: e.target.value })}
                placeholder="e.g., Withdrawal, Payment"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Recipient Name</label>
              <input
                type="text"
                value={debitForm.recipient_name}
                onChange={(e) => setDebitForm({ ...debitForm, recipient_name: e.target.value })}
                placeholder="e.g., Amazon EU"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Reference</label>
              <input
                type="text"
                value={debitForm.reference}
                onChange={(e) => setDebitForm({ ...debitForm, reference: e.target.value })}
                placeholder="e.g., INV-2024-001"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
              />
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
            <input
              type="text"
              value={debitForm.description}
              onChange={(e) => setDebitForm({ ...debitForm, description: e.target.value })}
              placeholder="e.g., Monthly subscription"
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
            />
          </div>

          <button
            onClick={handleProfessionalDebit}
            disabled={loading || !debitForm.amount}
            className="w-full py-3 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 font-medium"
            data-testid="submit-debit"
          >
            {loading ? 'Processing...' : `Debit ${debitForm.amount ? formatAmountFromEuro(debitForm.amount) : '€0.00'}`}
          </button>
        </div>
      ) : (
        /* Simple Form for Fee and Transfer */
        <div className="border rounded-lg p-4 space-y-4">
          <div className="flex justify-between items-center">
            <h5 className="font-medium capitalize">{activeOperation === 'fee' ? 'Charge Fee' : 'Internal Transfer'}</h5>
            <button onClick={resetAndClose} className="text-sm text-gray-600 hover:text-gray-900">
              Cancel
            </button>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Amount (€) *</label>
            <div className="relative">
              <span className="absolute left-3 top-2 text-gray-500">€</span>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={simpleForm.amount}
                onChange={(e) => setSimpleForm({ ...simpleForm, amount: e.target.value })}
                placeholder="e.g., 100.00"
                className="w-full pl-8 pr-3 py-2 border border-gray-300 rounded-md"
                data-testid="amount-input"
              />
            </div>
          </div>

          {activeOperation === 'transfer' && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">To Account ID *</label>
              <input
                type="text"
                value={simpleForm.toAccountId}
                onChange={(e) => setSimpleForm({ ...simpleForm, toAccountId: e.target.value })}
                placeholder="Target account ID"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="to-account-input"
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Reason *</label>
            <textarea
              value={simpleForm.reason}
              onChange={(e) => setSimpleForm({ ...simpleForm, reason: e.target.value })}
              rows={3}
              placeholder="Enter reason..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md"
              data-testid="reason-input"
            />
          </div>

          <button
            onClick={() => {
              if (activeOperation === 'fee') handleChargeFee();
              else if (activeOperation === 'transfer') handleInternalTransfer();
            }}
            disabled={loading}
            className="w-full py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
            data-testid="submit-operation"
          >
            {loading ? 'Processing...' : `Submit`}
          </button>
        </div>
      )}
    </div>
  );
}

export function TransactionReversal({ transaction, onSuccess }) {
  const toast = useToast();
  const [reason, setReason] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleReverse = async () => {
    if (!reason) {
      setError('Please provide a reason for reversal');
      return;
    }

    if (!window.confirm('Are you sure you want to reverse this transaction?')) {
      return;
    }

    setLoading(true);
    setError('');

    try {
      await api.post('/admin/ledger/reverse', {
        transaction_id: transaction.id,
        reason
      });
      toast.success('Transaction reversed successfully!');
      onSuccess && onSuccess();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Reversal failed');
    } finally {
      setLoading(false);
    }
  };

  if (transaction.status === 'REVERSED') {
    return (
      <div className="bg-purple-50 border border-purple-200 rounded p-4">
        <p className="text-sm text-purple-800">This transaction has been reversed</p>
      </div>
    );
  }

  return (
    <div className="border-t pt-4 space-y-4">
      <h4 className="font-medium text-red-600">Reverse Transaction</h4>
      
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded p-3 text-sm">{error}</div>
      )}

      <textarea
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        rows={3}
        placeholder="Reason for reversal..."
        className="w-full px-3 py-2 border border-gray-300 rounded-md"
      />

      <button
        onClick={handleReverse}
        disabled={loading || !reason}
        className="w-full py-2 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50"
      >
        {loading ? 'Processing...' : 'Confirm Reversal'}
      </button>
    </div>
  );
}
