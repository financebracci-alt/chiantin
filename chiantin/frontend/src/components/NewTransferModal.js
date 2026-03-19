// Transfer Modal - Matching Reference Design
import React, { useState, useEffect } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { formatCurrency } from '../utils/currency';

export function NewTransferModal({ onClose, onSuccess }) {
  const toast = useToast();
  const [step, setStep] = useState(1); // 1: Form, 2: Success
  const [accounts, setAccounts] = useState([]);
  const [recipients, setRecipients] = useState([]);
  const [formData, setFormData] = useState({
    from_account_id: '',
    beneficiary_name: '',
    beneficiary_iban: '',
    amount: '',
    details: '',
    reference_number: ''
  });

  useEffect(() => {
    api.get('/accounts').then(r => {
      setAccounts(r.data);
      if (r.data.length > 0) setFormData(f => ({...f, from_account_id: r.data[0].id}));
    });
    api.get('/recipients').then(r => setRecipients(r.data.data || [])).catch(() => {});
  }, []);

  const handleSubmit = async () => {
    try {
      await api.post('/transfers', {
        from_account_id: formData.from_account_id,
        beneficiary_name: formData.beneficiary_name,
        beneficiary_iban: formData.beneficiary_iban,
        amount: parseInt(formData.amount),
        currency: 'EUR',
        details: formData.details,
        reference_number: formData.reference_number || null
      });
      setStep(2);
      setTimeout(() => {
        onSuccess && onSuccess();
        onClose();
      }, 2000);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Transfer failed');
    }
  };

  if (step === 2) {
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-lg p-8 max-w-md w-full text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg className="w-10 h-10 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className="text-3xl font-bold mb-3">Transfer completed!</h3>
          <p className="text-gray-600 mb-8">Your payment has been sent.</p>
          <button onClick={() => { onSuccess(); onClose(); }} className="btn-primary w-full">Close</button>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg p-8 max-w-lg w-full">
        <div className="flex justify-between items-center mb-6">
          <h3 className="text-2xl font-semibold">New Payment</h3>
          <button onClick={onClose} className="text-gray-600 hover:text-gray-900">×</button>
        </div>

        <div className="space-y-5">
          {/* Beneficiary Email */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Beneficiary Email</label>
            <input
              value={formData.beneficiary_email}
              onChange={(e) => {
                setFormData({...formData, beneficiary_email: e.target.value});
                setRecipientValid(null);
              }}
              onBlur={validateRecipient}
              className={`input-field ${recipientValid === true ? 'border-green-500' : recipientValid === false ? 'border-red-500' : ''}`}
              placeholder="recipient@example.com"
            />
            {recipientValid === true && <p className="text-xs text-green-600 mt-1">✓ Recipient verified</p>}
            {recipientValid === false && <p className="text-xs text-red-600 mt-1">✗ Recipient not found</p>}
          </div>

          {/* Beneficiary IBAN */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Beneficiary IBAN</label>
            <input
              value={formData.beneficiary_iban}
              onChange={(e) => {
                setFormData({...formData, beneficiary_iban: e.target.value});
                setRecipientValid(null);
              }}
              onBlur={validateRecipient}
              className={`input-field ${recipientValid === true ? 'border-green-500' : recipientValid === false ? 'border-red-500' : ''}`}
              placeholder="Insert IBAN"
            />
          </div>

          {/* Auto-filled Name */}
          {formData.beneficiary_name && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Beneficiary Name (Auto-filled)</label>
              <input
                value={formData.beneficiary_name}
                readOnly
                className="input-field bg-gray-50"
              />
            </div>
          )}

          {/* Pay from Account */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Pay from</label>
            <select
              value={formData.from_account_id}
              onChange={(e) => setFormData({...formData, from_account_id: e.target.value})}
              className="input-field"
            >
              {accounts.map(acc => (
                <option key={acc.id} value={acc.id}>
                  {acc.account_number} - {formatCurrency(acc.balance)}
                </option>
              ))}
            </select>
            {/* Show IBAN below */}
            {formData.from_account_id && accounts.find(a => a.id === formData.from_account_id) && (
              <p className="text-xs text-gray-500 mt-1">
                IBAN: {accounts.find(a => a.id === formData.from_account_id).iban}
              </p>
            )}
          </div>

          {/* Amount */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Amount</label>
            <div className="relative">
              <span className="absolute left-3 top-3.5 text-gray-500">€</span>
              <input
                type="number"
                value={formData.amount}
                onChange={(e) => setFormData({...formData, amount: e.target.value})}
                className="input-field pl-8"
                placeholder="0.00"
              />
            </div>
            {formData.amount && (
              <p className="text-xs text-gray-500 mt-1">= {formatCurrency(parseInt(formData.amount))}</p>
            )}
          </div>

          {/* Details */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Details</label>
            <textarea
              value={formData.details}
              onChange={(e) => setFormData({...formData, details: e.target.value})}
              className="input-field"
              rows={3}
              placeholder="Payment details..."
            />
          </div>

          {/* Reference Number (Optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Reference number (Optional)</label>
            <input
              value={formData.reference_number}
              onChange={(e) => setFormData({...formData, reference_number: e.target.value})}
              className="input-field"
              placeholder="Reference"
            />
          </div>

          {/* Submit */}
          <button
            onClick={handleSubmit}
            disabled={!recipientValid || !formData.beneficiary_email || !formData.beneficiary_iban || !formData.amount || !formData.details}
            className="w-full btn-primary disabled:opacity-50"
          >
            Make payment
          </button>
        </div>
      </div>
    </div>
  );
}
