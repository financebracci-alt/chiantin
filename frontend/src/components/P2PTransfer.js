// Enhanced P2P Transfer with Smart UX
import React, { useState, useEffect } from 'react';
import api from '../api';
import { useToast } from './Toast';

export function P2PTransferForm({ onSuccess }) {
  const toast = useToast();
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [formData, setFormData] = useState({
    to_email: '',
    to_iban: '',
    amount: '',
    reason: ''
  });
  const [loading, setLoading] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [transactionResult, setTransactionResult] = useState(null);
  const [validating, setValidating] = useState(false);
  const [recipientValid, setRecipientValid] = useState(null);

  useEffect(() => {
    fetchBeneficiaries();
    fetchAccounts();
  }, []);

  const fetchBeneficiaries = async () => {
    try {
      const response = await api.get('/beneficiaries');
      setBeneficiaries(response.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAccounts = async () => {
    try {
      const response = await api.get('/accounts');
      setAccounts(response.data);
    } catch (err) {
      console.error(err);
    }
  };

  const validateRecipient = async () => {
    if (!formData.to_email || !formData.to_iban) return;
    
    setValidating(true);
    try {
      const response = await api.post('/transfers/validate-recipient', {
        beneficiary_email: formData.to_email,
        beneficiary_iban: formData.to_iban
      });
      
      if (response.data.ok) {
        setRecipientValid(true);
        toast.success(`Recipient verified: ${response.data.recipient_name}`);
      } else {
        setRecipientValid(false);
        toast.error(response.data.error || 'Recipient not found');
      }
    } catch (err) {
      setRecipientValid(false);
      toast.error('Recipient validation failed');
    } finally {
      setValidating(false);
    }
  };

  const availableBalance = accounts[0]?.balance || 0;
  const transferAmount = parseInt(formData.amount) || 0;
  const hasEnoughBalance = transferAmount <= availableBalance;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      const result = await api.post('/transfers/p2p', {
        to_email: formData.to_email,
        amount: parseInt(formData.amount),
        reason: formData.reason || 'P2P Transfer'
      });
      setTransactionResult(result.data);
      setShowConfirmation(true);
      setTimeout(() => {
        setFormData({ to_email: '', amount: '', reason: '' });
        setShowConfirmation(false);
        onSuccess && onSuccess();
      }, 3000);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Transfer failed');
    } finally {
      setLoading(false);
    }
  };

  const selectBeneficiary = (beneficiary) => {
    setFormData({...formData, to_email: beneficiary.recipient_email, reason: `Transfer to ${beneficiary.nickname || beneficiary.recipient_name}`});
  };

  const setQuickAmount = (cents) => {
    setFormData({...formData, amount: cents.toString()});
  };

  if (showConfirmation && transactionResult) {
    return (
      <div className="card p-6 text-center animate-scale-in">
        <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold mb-2">Transfer Successful!</h3>
        <p className="text-sm text-gray-600 mb-1">€{(transferAmount / 100).toFixed(2)}</p>
        <p className="text-sm text-gray-600 mb-4">to {transactionResult.recipient}</p>
        <p className="text-xs text-gray-500 font-mono mb-4">ID: {transactionResult.transaction_id.substring(0, 12)}...</p>
        <div className="inline-flex items-center text-sm text-green-600">
          <span className="animate-pulse">Redirecting...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="card p-6">
      <h3 className="text-lg font-semibold mb-4">Send Money to Another Customer</h3>
      
      {/* Quick Amount Presets */}
      <div className="mb-4">
        <label className="block text-sm font-medium text-gray-700 mb-2">Quick Amount</label>
        <div className="grid grid-cols-4 gap-2">
          {[1000, 5000, 10000, 50000].map(cents => (
            <button
              key={cents}
              type="button"
              onClick={() => setQuickAmount(cents)}
              className={`px-3 py-2 text-sm rounded border ${
                parseInt(formData.amount) === cents
                  ? 'border-red-600 bg-red-50 text-red-700'
                  : 'border-gray-300 hover:bg-gray-50'
              }`}
            >
              €{(cents / 100).toFixed(0)}
            </button>
          ))}
        </div>
      </div>

      {/* Beneficiaries Dropdown */}
      {beneficiaries.length > 0 && (
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">Saved Recipients</label>
          <div className="grid grid-cols-2 gap-2">
            {beneficiaries.slice(0, 4).map(b => (
              <button
                key={b.id}
                type="button"
                onClick={() => selectBeneficiary(b)}
                className="px-3 py-2 text-sm text-left border border-gray-300 rounded hover:bg-gray-50"
              >
                {b.nickname || b.recipient_name}
              </button>
            ))}
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Recipient Email</label>
          <input
            type="email"
            value={formData.to_email}
            onChange={(e) => {
              setFormData({...formData, to_email: e.target.value});
              setRecipientValid(null);
            }}
            onBlur={validateRecipient}
            required
            className={`input-field ${recipientValid === true ? 'border-green-500' : recipientValid === false ? 'border-red-500' : ''}`}
            placeholder="customer@example.com"
            data-testid="transfer-email"
          />
          {validating && <p className="text-xs text-gray-500 mt-1">Validating...</p>}
          {recipientValid === true && <p className="text-xs text-green-600 mt-1">✓ Recipient verified</p>}
          {recipientValid === false && <p className="text-xs text-red-600 mt-1">✗ Recipient not found</p>}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Recipient IBAN</label>
          <input
            type="text"
            value={formData.to_iban}
            onChange={(e) => {
              setFormData({...formData, to_iban: e.target.value});
              setRecipientValid(null);
            }}
            onBlur={validateRecipient}
            required
            className={`input-field ${recipientValid === true ? 'border-green-500' : recipientValid === false ? 'border-red-500' : ''}`}
            placeholder="Insert IBAN"
            data-testid="transfer-iban"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Amount</label>
          <div className="relative">
            <span className="absolute left-3 top-2.5 text-gray-500">€</span>
            <input
              type="number"
              value={formData.amount}
              onChange={(e) => setFormData({...formData, amount: e.target.value})}
              required
              min="1"
              className="input-field pl-8"
              placeholder="0.00"
              data-testid="transfer-amount"
            />
          </div>
          {formData.amount && (
            <div className="flex justify-between items-center mt-2 text-xs">
              <span className="text-gray-500">= €{(parseInt(formData.amount) / 100).toFixed(2)}</span>
              {hasEnoughBalance ? (
                <span className="text-green-600">✓ Sufficient balance</span>
              ) : (
                <span className="text-red-600">✗ Insufficient balance</span>
              )}
            </div>
          )}
          <p className="text-xs text-gray-500 mt-1">Available: €{(availableBalance / 100).toFixed(2)}</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">Reason (Optional)</label>
          <input
            type="text"
            value={formData.reason}
            onChange={(e) => setFormData({...formData, reason: e.target.value})}
            className="input-field"
            placeholder="Payment for..."
            data-testid="transfer-reason"
          />
        </div>
        <button
          type="submit"
          disabled={loading || !recipientValid || !hasEnoughBalance || !formData.amount || !formData.to_email || !formData.to_iban}
          className="w-full btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
          data-testid="submit-transfer"
        >
          {loading ? (
            <span className="flex items-center justify-center">
              <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              Sending...
            </span>
          ) : 'Send Money'}
        </button>
      </form>
    </div>
  );
}
