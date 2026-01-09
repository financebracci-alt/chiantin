// Transaction Components
import React, { useState, useEffect } from 'react';
import api from '../api';

export function TransactionsList({ accountId, isAdmin = false }) {
  const [transactions, setTransactions] = useState([]);
  const [filteredTransactions, setFilteredTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedTxn, setSelectedTxn] = useState(null);
  const [showDetails, setShowDetails] = useState(false);
  const [filters, setFilters] = useState({
    type: 'all',
    status: 'all',
    dateFrom: '',
    dateTo: '',
    search: ''
  });

  useEffect(() => {
    if (accountId) {
      fetchTransactions();
    }
  }, [accountId]);

  useEffect(() => {
    applyFilters();
  }, [transactions, filters]);

  const fetchTransactions = async () => {
    try {
      const response = await api.get(`/accounts/${accountId}/transactions`);
      setTransactions(response.data);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  const applyFilters = () => {
    let filtered = [...transactions];

    // Type filter
    if (filters.type !== 'all') {
      filtered = filtered.filter(t => t.transaction_type === filters.type);
    }

    // Status filter
    if (filters.status !== 'all') {
      filtered = filtered.filter(t => t.status === filters.status);
    }

    // Date range filter
    if (filters.dateFrom) {
      const fromDate = new Date(filters.dateFrom);
      filtered = filtered.filter(t => new Date(t.created_at) >= fromDate);
    }
    if (filters.dateTo) {
      const toDate = new Date(filters.dateTo);
      toDate.setHours(23, 59, 59);
      filtered = filtered.filter(t => new Date(t.created_at) <= toDate);
    }

    // Search filter
    if (filters.search) {
      const search = filters.search.toLowerCase();
      filtered = filtered.filter(t => 
        t.id.toLowerCase().includes(search) ||
        (t.reason && t.reason.toLowerCase().includes(search)) ||
        (t.external_id && t.external_id.toLowerCase().includes(search))
      );
    }

    setFilteredTransactions(filtered);
  };

  const exportToCSV = () => {
    const headers = ['ID', 'Type', 'Status', 'Date', 'Reason', 'External ID'];
    const rows = filteredTransactions.map(txn => [
      txn.id,
      txn.transaction_type,
      txn.status,
      new Date(txn.created_at).toISOString(),
      txn.reason || '',
      txn.external_id || ''
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map(row => row.map(cell => `"${cell}"`).join(','))
    ].join('\\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transactions_${accountId}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const formatAmount = (cents) => {
    return `€${(cents / 100).toFixed(2)}`;
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString();
  };

  const getTypeColor = (type) => {
    const colors = {
      TOP_UP: 'text-green-600',
      WITHDRAW: 'text-red-600',
      FEE: 'text-orange-600',
      TRANSFER: 'text-blue-600',
      REVERSAL: 'text-purple-600'
    };
    return colors[type] || 'text-gray-600';
  };

  if (loading) {
    return <div className="text-center py-8">Loading transactions...</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className="text-lg font-semibold">Transaction History</h3>
        {filteredTransactions.length > 0 && (
          <button
            onClick={exportToCSV}
            className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50 text-sm"
            data-testid="export-csv"
          >
            Export CSV
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
            <select
              value={filters.type}
              onChange={(e) => setFilters({ ...filters, type: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              data-testid="filter-type"
            >
              <option value="all">All Types</option>
              <option value="TOP_UP">Top Up</option>
              <option value="WITHDRAW">Withdraw</option>
              <option value="FEE">Fee</option>
              <option value="TRANSFER">Transfer</option>
              <option value="REVERSAL">Reversal</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              data-testid="filter-status"
            >
              <option value="all">All Status</option>
              <option value="POSTED">Posted</option>
              <option value="REVERSED">Reversed</option>
              <option value="PENDING">Pending</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">From Date</label>
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              data-testid="filter-date-from"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">To Date</label>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              data-testid="filter-date-to"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Search</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              placeholder="ID or reason..."
              className="w-full px-3 py-2 border border-gray-300 rounded-md text-sm"
              data-testid="filter-search"
            />
          </div>
        </div>
        {(filters.type !== 'all' || filters.status !== 'all' || filters.dateFrom || filters.dateTo || filters.search) && (
          <button
            onClick={() => setFilters({ type: 'all', status: 'all', dateFrom: '', dateTo: '', search: '' })}
            className="mt-3 text-sm text-blue-600 hover:text-blue-700"
            data-testid="clear-filters"
          >
            Clear all filters
          </button>
        )}
      </div>
      
      {filteredTransactions.length === 0 ? (
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <p className="text-gray-600">
            {transactions.length === 0 ? 'No transactions yet' : 'No transactions match your filters'}
          </p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow divide-y">
          {transactions.map((txn) => (
            <div
              key={txn.id}
              onClick={() => {
                setSelectedTxn(txn);
                setShowDetails(true);
              }}
              className="p-4 hover:bg-gray-50 cursor-pointer"
              data-testid={`transaction-${txn.id}`}
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className={`font-medium ${getTypeColor(txn.transaction_type)}`}>
                      {txn.transaction_type.replace('_', ' ')}
                    </span>
                    <span className={`text-xs px-2 py-1 rounded ${
                      txn.status === 'POSTED' 
                        ? 'bg-green-100 text-green-800'
                        : txn.status === 'REVERSED'
                        ? 'bg-purple-100 text-purple-800'
                        : 'bg-gray-100 text-gray-800'
                    }`}>
                      {txn.status}
                    </span>
                  </div>
                  {txn.reason && (
                    <p className="text-sm text-gray-600 mt-1">{txn.reason}</p>
                  )}
                  <p className="text-xs text-gray-500 mt-1">
                    {formatDate(txn.created_at)}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setSelectedTxn(txn);
                    setShowDetails(true);
                  }}
                  className="text-sm text-blue-600 hover:text-blue-700"
                  data-testid={`view-details-${txn.id}`}
                >
                  View Details →
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Transaction Details Modal */}
      {showDetails && selectedTxn && (
        <TransactionDetailsModal
          transaction={selectedTxn}
          onClose={() => {
            setShowDetails(false);
            setSelectedTxn(null);
          }}
        />
      )}
    </div>
  );
}

function TransactionDetailsModal({ transaction, onClose }) {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // In a real implementation, fetch ledger entries for this transaction
    // For now, we'll show the transaction details
    setLoading(false);
  }, [transaction]);

  const formatAmount = (cents) => {
    return `€${(cents / 100).toFixed(2)}`;
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString();
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b p-6 flex justify-between items-center">
          <h3 className="text-xl font-semibold">Transaction Details</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
            data-testid="close-modal"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Transaction Info */}
          <div>
            <h4 className="font-semibold mb-3">Transaction Information</h4>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className="text-gray-600">Transaction ID</dt>
                <dd className="font-mono mt-1">{transaction.id}</dd>
              </div>
              <div>
                <dt className="text-gray-600">Type</dt>
                <dd className="font-medium mt-1">{transaction.transaction_type}</dd>
              </div>
              <div>
                <dt className="text-gray-600">Status</dt>
                <dd className="mt-1">
                  <span className={`px-2 py-1 rounded text-xs ${
                    transaction.status === 'POSTED' 
                      ? 'bg-green-100 text-green-800'
                      : transaction.status === 'REVERSED'
                      ? 'bg-purple-100 text-purple-800'
                      : 'bg-gray-100 text-gray-800'
                  }`}>
                    {transaction.status}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="text-gray-600">Created</dt>
                <dd className="mt-1">{formatDate(transaction.created_at)}</dd>
              </div>
              {transaction.external_id && (
                <div className="col-span-2">
                  <dt className="text-gray-600">External ID</dt>
                  <dd className="font-mono text-xs mt-1">{transaction.external_id}</dd>
                </div>
              )}
              {transaction.reason && (
                <div className="col-span-2">
                  <dt className="text-gray-600">Reason</dt>
                  <dd className="mt-1">{transaction.reason}</dd>
                </div>
              )}
              {transaction.performed_by && (
                <div>
                  <dt className="text-gray-600">Performed By</dt>
                  <dd className="font-mono text-xs mt-1">{transaction.performed_by}</dd>
                </div>
              )}
            </dl>
          </div>

          {/* Ledger Entries Info */}
          <div className="border-t pt-6">
            <h4 className="font-semibold mb-3">Double-Entry Ledger Details</h4>
            <p className="text-sm text-gray-600 mb-4">
              This transaction follows double-entry bookkeeping principles. Every transaction creates balanced debit and credit entries.
            </p>
            <div className="bg-gray-50 rounded p-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Transaction Type:</span>
                <span className="font-medium">{transaction.transaction_type}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Status:</span>
                <span className="font-medium">{transaction.status}</span>
              </div>
              {transaction.reverses_txn_id && (
                <div className="flex justify-between border-t pt-2">
                  <span className="text-gray-600">Reverses Transaction:</span>
                  <span className="font-mono text-xs">{transaction.reverses_txn_id}</span>
                </div>
              )}
              {transaction.reversed_by_txn_id && (
                <div className="flex justify-between border-t pt-2">
                  <span className="text-gray-600">Reversed By:</span>
                  <span className="font-mono text-xs">{transaction.reversed_by_txn_id}</span>
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          {transaction.status === 'POSTED' && (
            <div className="border-t pt-6">
              <h4 className="font-semibold mb-3">Actions</h4>
              <button
                onClick={() => alert('Reversal feature requires admin privileges')}
                className="px-4 py-2 border border-red-600 text-red-600 rounded hover:bg-red-50"
                data-testid="request-reversal"
              >
                Request Reversal
              </button>
            </div>
          )}
        </div>

        <div className="sticky bottom-0 bg-gray-50 border-t p-6">
          <button
            onClick={onClose}
            className="w-full py-2 bg-gray-600 text-white rounded hover:bg-gray-700"
            data-testid="close-details"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}

export { TransactionDetailsModal };
