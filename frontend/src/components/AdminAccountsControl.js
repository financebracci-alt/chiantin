// Admin Accounts Control - Top-Up/Withdraw
import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { useBalanceVisibility, formatBalance } from '../hooks/useBalanceVisibility';
import BalanceToggle from './BalanceToggle';
import { formatCurrency } from '../utils/currency';
import { CopyButton, ActionButton, EmptyState, ClearFiltersButton } from './AdminUIComponents';

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
  const [submitting, setSubmitting] = useState(false); // Prevent double-click
  
  // Search and pagination state
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(1);
  const [limit, setLimit] = useState(50);
  const [pagination, setPagination] = useState({
    total_accounts: 0,
    total_pages: 1,
    has_next: false,
    has_prev: false
  });

  const fetchAccounts = useCallback(async () => {
    setLoading(true);
    try {
      // Build query params for search and pagination
      const params = new URLSearchParams();
      if (searchQuery.trim()) {
        params.append('search', searchQuery.trim());
      }
      params.append('page', page.toString());
      params.append('limit', limit.toString());
      
      const response = await api.get(`/admin/accounts-with-users?${params.toString()}`);
      
      // Handle new paginated response format
      if (response.data.accounts) {
        setAccounts(response.data.accounts);
        setPagination(response.data.pagination);
      } else {
        // Fallback for old format (array)
        setAccounts(response.data);
        setPagination({ total_accounts: response.data.length, total_pages: 1, has_next: false, has_prev: false });
      }
    } catch (err) {
      console.error('Failed to load accounts:', err);
      toast.error('Failed to load accounts');
    } finally {
      setLoading(false);
    }
  }, [toast, searchQuery, page, limit]);

  useEffect(() => {
    fetchAccounts();
  }, [fetchAccounts]);

  // Reset to page 1 when search changes
  useEffect(() => {
    setPage(1);
  }, [searchQuery, limit]);

  const handleSubmit = async () => {
    if (!formData.amount || !formData.reason) {
      toast.error('Fill all fields');
      return;
    }
    if (submitting) return; // Prevent double-click

    setSubmitting(true);
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
    } finally {
      setSubmitting(false);
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
      
      {/* Search Bar and Controls */}
      <div className="mb-6 flex flex-wrap items-center gap-4">
        {/* Search Input */}
        <div className="flex-1 min-w-[300px] relative">
          <input
            type="text"
            placeholder="Search by name, email, IBAN, or account number..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input-field w-full pr-8"
            data-testid="accounts-search-input"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              title="Clear search"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
        </div>
        
        {/* Active Filter Indicator */}
        {searchQuery && (
          <div className="flex items-center gap-2">
            <span className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full">
              <span className="font-medium">Search:</span>
              <span>"{searchQuery}"</span>
            </span>
            <ClearFiltersButton onClick={() => setSearchQuery('')} hasActiveFilters={true} />
          </div>
        )}
        
        {/* Results Count */}
        <div className="text-sm text-gray-600">
          Showing {accounts.length} of {pagination.total_accounts} accounts
        </div>
        
        {/* Per Page Selector */}
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600">Show:</span>
          <select
            value={limit}
            onChange={(e) => setLimit(Number(e.target.value))}
            className="input-field py-1 px-2 w-20"
            data-testid="accounts-limit-select"
          >
            <option value={20}>20</option>
            <option value={50}>50</option>
            <option value={100}>100</option>
          </select>
          <span className="text-sm text-gray-600">per page</span>
        </div>
      </div>
      
      {/* Pagination Controls - Top */}
      {!searchQuery.trim() && pagination.total_pages > 1 && (
        <div className="mb-4 flex items-center justify-end gap-2">
          <button
            onClick={() => setPage(1)}
            disabled={page === 1}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            First
          </button>
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={!pagination.has_prev}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-sm">
            Page {page} of {pagination.total_pages}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={!pagination.has_next}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Next
          </button>
          <button
            onClick={() => setPage(pagination.total_pages)}
            disabled={page === pagination.total_pages}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Last
          </button>
        </div>
      )}
      
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
              {accounts.length === 0 ? (
                <tr>
                  <td colSpan="5" className="text-center py-8 text-gray-500">
                    {searchQuery ? 'No accounts found matching your search' : 'No accounts found'}
                  </td>
                </tr>
              ) : (
                accounts.map(acc => (
                  <tr key={acc.id} data-testid={`account-row-${acc.id}`}>
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
                ))
              )}
            </tbody>
          </table>
        </div>
      )}
      
      {/* Pagination Controls - Bottom */}
      {!searchQuery.trim() && pagination.total_pages > 1 && (
        <div className="mt-4 flex items-center justify-end gap-2">
          <button
            onClick={() => setPage(1)}
            disabled={page === 1}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            First
          </button>
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={!pagination.has_prev}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Previous
          </button>
          <span className="px-3 py-1 text-sm">
            Page {page} of {pagination.total_pages}
          </span>
          <button
            onClick={() => setPage(p => p + 1)}
            disabled={!pagination.has_next}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Next
          </button>
          <button
            onClick={() => setPage(pagination.total_pages)}
            disabled={page === pagination.total_pages}
            className="px-3 py-1 text-sm border rounded disabled:opacity-50 disabled:cursor-not-allowed hover:bg-gray-50"
          >
            Last
          </button>
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
