// Admin Accounts Control - Top-Up/Withdraw
import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { useBalanceVisibility, formatBalance } from '../hooks/useBalanceVisibility';
import BalanceToggle from './BalanceToggle';

export function AdminAccountsControl() {
  const toast = useToast();
  const { isBalanceVisible, toggleBalanceVisibility } = useBalanceVisibility();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [showIbanModal, setShowIbanModal] = useState(false);
  const [operation, setOperation] = useState('topup');
  const [formData, setFormData] = useState({ amount: '', reason: '' });
  const [ibanFormData, setIbanFormData] = useState({ iban: '', bic: '' });

  const fetchAccounts = useCallback(async () => {
    try {
      // Use the optimized endpoint that returns all accounts with user info in one request
      const response = await api.get('/admin/accounts-with-users');
      setAccounts(response.data);
    } catch (err) {
      console.error('Failed to load accounts:', err);
      toast.error('Failed to load accounts');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  const handleSubmit = async () => {
    if (!formData.amount || !formData.reason) {
      toast.error('Fill all fields');
      return;
    }

    try {
      const amountInCents = Math.round(parseFloat(formData.amount) * 100);
      const endpoint = operation === 'topup' ? 'topup' : 'withdraw';
      await api.post(`/admin/accounts/${selectedAccount.id}/${endpoint}?amount=${amountInCents}&reason=${encodeURIComponent(formData.reason)}`);
      toast.success(`${operation === 'topup' ? 'Top-up' : 'Withdrawal'} successful!`);
      setShowModal(false);
      setFormData({ amount: '', reason: '' });
      fetchAccounts();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed');
    }
  };

  const handleEditIban = (acc) => {
    setSelectedAccount(acc);
    setIbanFormData({ iban: acc.iban || '', bic: acc.bic || '' });
    setShowIbanModal(true);
  };

  const handleIbanSubmit = async () => {
    if (!ibanFormData.iban || !ibanFormData.bic) {
      toast.error('IBAN and BIC are required');
      return;
    }

    try {
      await api.patch(`/admin/users/${selectedAccount.userId}/account-iban`, {
        iban: ibanFormData.iban,
        bic: ibanFormData.bic
      });
      toast.success('IBAN and BIC updated successfully!');
      setShowIbanModal(false);
      setIbanFormData({ iban: '', bic: '' });
      fetchAccounts();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update IBAN');
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Account Control</h2>
      {loading ? (
        <div className="skeleton-card h-64"></div>
      ) : (
        <div className="table-wrapper">
          <table className="table-main">
            <thead>
              <tr>
                <th>User</th>
                <th>Account</th>
                <th>
                  <div className="flex items-center gap-2">
                    Balance
                    <BalanceToggle 
                      isVisible={isBalanceVisible} 
                      onToggle={toggleBalanceVisibility} 
                      size="small"
                    />
                  </div>
                </th>
                <th>IBAN / BIC</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {accounts.map(acc => (
                <tr key={acc.id}>
                  <td>
                    <div className="font-medium">{acc.userName}</div>
                    <div className="text-xs text-gray-600">{acc.userEmail}</div>
                  </td>
                  <td>{acc.account_number}</td>
                  <td className="font-semibold">{formatBalance(acc.balance, isBalanceVisible)}</td>
                  <td>
                    <div className="font-mono text-xs">{acc.iban || 'Not set'}</div>
                    <div className="font-mono text-xs text-gray-500">{acc.bic || ''}</div>
                  </td>
                  <td>
                    <button onClick={() => { setSelectedAccount(acc); setOperation('topup'); setShowModal(true); }} className="btn-text text-xs mr-2">Top Up</button>
                    <button onClick={() => { setSelectedAccount(acc); setOperation('withdraw'); setShowModal(true); }} className="btn-text text-xs mr-2">Withdraw</button>
                    <button onClick={() => handleEditIban(acc)} className="btn-text text-xs text-blue-600">Edit IBAN</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">{operation === 'topup' ? 'Top Up Account' : 'Withdraw from Account'}</h3>
            <div className="mb-4">
              <p className="text-sm text-gray-600">Account: {selectedAccount.iban || selectedAccount.account_number}</p>
              <p className="text-sm text-gray-600">Current: {formatBalance(selectedAccount.balance, isBalanceVisible)}</p>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">Amount (€)</label>
                <input 
                  type="number" 
                  step="0.01"
                  value={formData.amount} 
                  onChange={(e) => setFormData({...formData, amount: e.target.value})} 
                  className="input-field" 
                  placeholder="100.00" 
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Reason</label>
                <input type="text" value={formData.reason} onChange={(e) => setFormData({...formData, reason: e.target.value})} className="input-field" />
              </div>
              <div className="flex space-x-3">
                <button onClick={() => setShowModal(false)} className="flex-1 btn-secondary">Cancel</button>
                <button onClick={handleSubmit} className="flex-1 btn-primary">Confirm</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Edit IBAN Modal */}
      {showIbanModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <h3 className="text-lg font-semibold mb-4">Edit IBAN / BIC</h3>
            <div className="mb-4">
              <p className="text-sm text-gray-600">User: {selectedAccount.userName}</p>
              <p className="text-sm text-gray-600">Email: {selectedAccount.userEmail}</p>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-2">IBAN</label>
                <input 
                  type="text" 
                  value={ibanFormData.iban} 
                  onChange={(e) => setIbanFormData({...ibanFormData, iban: e.target.value.toUpperCase()})} 
                  className="input-field font-mono" 
                  placeholder="IT60X0542811101000000123456" 
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">BIC / SWIFT</label>
                <input 
                  type="text" 
                  value={ibanFormData.bic} 
                  onChange={(e) => setIbanFormData({...ibanFormData, bic: e.target.value.toUpperCase()})} 
                  className="input-field font-mono" 
                  placeholder="ATLASLT21" 
                />
              </div>
              <div className="flex space-x-3">
                <button onClick={() => setShowIbanModal(false)} className="flex-1 btn-secondary">Cancel</button>
                <button onClick={handleIbanSubmit} className="flex-1 btn-primary">Save Changes</button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
