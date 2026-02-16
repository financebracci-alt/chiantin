// Transaction Components
import React, { useState, useEffect } from 'react';
import api from '../api';
import { useLanguage, useTheme } from '../contexts/AppContext';
import { getStatusBadgeClasses, isTransactionCredit, formatTransactionAmount } from '../utils/transactions';
import { formatCurrency } from '../utils/currency';

export function TransactionsList({ accountId, isAdmin = false }) {
  const { t } = useLanguage();
  const { isDark } = useTheme();
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
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transactions_${accountId}_${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
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

  const getTypeLabel = (type) => {
    const labels = {
      TOP_UP: t('topUp'),
      WITHDRAW: t('withdraw'),
      FEE: t('fee'),
      TRANSFER: t('transfer'),
      REVERSAL: t('reversal')
    };
    return labels[type] || type.replace('_', ' ');
  };

  const getStatusLabel = (status) => {
    const labels = {
      POSTED: t('posted'),
      REVERSED: t('reversed'),
      PENDING: t('pending'),
      REJECTED: t('rejected'),
      SUBMITTED: t('submitted')
    };
    return labels[status] || status;
  };

  if (loading) {
    return <div className={`text-center py-8 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('loadingTransactions')}</div>;
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-between items-center">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('transactionHistory')}</h3>
        {filteredTransactions.length > 0 && (
          <button
            onClick={exportToCSV}
            className={`px-4 py-2 border rounded-md text-sm ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 hover:bg-gray-50'}`}
            data-testid="export-csv"
          >
            {t('exportCsv')}
          </button>
        )}
      </div>

      {/* Filters */}
      <div className={`rounded-lg shadow p-4 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
          <div>
            <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('type')}</label>
            <select
              value={filters.type}
              onChange={(e) => setFilters({ ...filters, type: e.target.value })}
              className={`w-full px-3 py-2 border rounded-md text-sm ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'border-gray-300'}`}
              data-testid="filter-type"
            >
              <option value="all">{t('allTypes')}</option>
              <option value="TOP_UP">{t('topUp')}</option>
              <option value="WITHDRAW">{t('withdraw')}</option>
              <option value="FEE">{t('fee')}</option>
              <option value="TRANSFER">{t('transfer')}</option>
              <option value="REVERSAL">{t('reversal')}</option>
            </select>
          </div>
          <div>
            <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('status')}</label>
            <select
              value={filters.status}
              onChange={(e) => setFilters({ ...filters, status: e.target.value })}
              className={`w-full px-3 py-2 border rounded-md text-sm ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'border-gray-300'}`}
              data-testid="filter-status"
            >
              <option value="all">{t('allStatus')}</option>
              <option value="POSTED">{t('posted')}</option>
              <option value="REVERSED">{t('reversed')}</option>
              <option value="PENDING">{t('pending')}</option>
              <option value="REJECTED">{t('rejected')}</option>
              <option value="SUBMITTED">{t('submitted')}</option>
            </select>
          </div>
          <div>
            <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('fromDate')}</label>
            <input
              type="date"
              value={filters.dateFrom}
              onChange={(e) => setFilters({ ...filters, dateFrom: e.target.value })}
              className={`w-full px-3 py-2 border rounded-md text-sm ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'border-gray-300'}`}
              data-testid="filter-date-from"
            />
          </div>
          <div>
            <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('toDate')}</label>
            <input
              type="date"
              value={filters.dateTo}
              onChange={(e) => setFilters({ ...filters, dateTo: e.target.value })}
              className={`w-full px-3 py-2 border rounded-md text-sm ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'border-gray-300'}`}
              data-testid="filter-date-to"
            />
          </div>
          <div>
            <label className={`block text-sm font-medium mb-1 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('search')}</label>
            <input
              type="text"
              value={filters.search}
              onChange={(e) => setFilters({ ...filters, search: e.target.value })}
              placeholder={t('idOrReason')}
              className={`w-full px-3 py-2 border rounded-md text-sm ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'border-gray-300'}`}
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
            {t('clearAllFilters')}
          </button>
        )}
      </div>
      
      {filteredTransactions.length === 0 ? (
        <div className={`rounded-lg shadow p-8 text-center ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
          <p className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {transactions.length === 0 ? t('noTransactionsYet') : t('noTransactionsMatchFilters')}
          </p>
        </div>
      ) : (
        <div className={`rounded-lg shadow divide-y ${isDark ? 'bg-gray-800 divide-gray-700' : 'bg-white divide-gray-100'}`}>
          {filteredTransactions.map((txn) => {
            // Determine if credit or debit
            const isCredit = isTransactionCredit(txn);
            
            return (
              <div
                key={txn.id}
                onClick={() => {
                  setSelectedTxn(txn);
                  setShowDetails(true);
                }}
                className={`p-4 cursor-pointer transition-colors ${isDark ? 'hover:bg-gray-700/50' : 'hover:bg-gray-50'}`}
                data-testid={`transaction-${txn.id}`}
              >
                <div className="flex justify-between items-center">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                      <span className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        {getTypeLabel(txn.transaction_type)}
                      </span>
                    </div>
                    {txn.reason && (
                      <p className={`text-sm mt-1 truncate ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{txn.reason}</p>
                    )}
                    <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                      {formatDate(txn.created_at)}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0 ml-4">
                    {/* Professional banking amount display: +/- with color */}
                    <p className={`text-base font-bold ${isCredit ? 'text-green-600' : 'text-red-600'}`}>
                      {formatTransactionAmount(txn.amount, isCredit)}
                    </p>
                    {/* Professional status badge */}
                    <span className={getStatusBadgeClasses(txn.status, isDark)}>
                      {getStatusLabel(txn.status)}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
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
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(false);
  }, [transaction]);

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString();
  };

  const getTypeLabel = (type) => {
    const labels = {
      TOP_UP: t('topUp'),
      WITHDRAW: t('withdraw'),
      FEE: t('fee'),
      TRANSFER: t('transfer'),
      REVERSAL: t('reversal')
    };
    return labels[type] || type.replace('_', ' ');
  };

  const getStatusLabel = (status) => {
    const labels = {
      POSTED: t('posted'),
      REVERSED: t('reversed'),
      PENDING: t('pending'),
      REJECTED: t('rejected'),
      SUBMITTED: t('submitted'),
      COMPLETED: t('completed'),
      PROCESSING: t('processing'),
      FAILED: t('failed'),
      CANCELLED: t('cancelled')
    };
    return labels[status] || status;
  };
  
  // Determine if credit or debit
  const isCredit = isTransactionCredit(transaction);

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className={`rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <div className={`sticky top-0 border-b p-6 flex justify-between items-center ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white'}`}>
          <h3 className={`text-xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('transactionDetails')}</h3>
          <button
            onClick={onClose}
            className={`${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-400 hover:text-gray-600'}`}
            data-testid="close-modal"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Transaction Amount Header - Professional Banking Style */}
          <div className={`text-center p-6 rounded-xl ${isDark ? 'bg-gray-700/50' : 'bg-gray-50'}`}>
            <p className={`text-3xl font-bold ${isCredit ? 'text-green-600' : 'text-red-600'}`}>
              {formatTransactionAmount(transaction.amount, isCredit)}
            </p>
            <div className="mt-2">
              <span className={getStatusBadgeClasses(transaction.status, isDark)}>
                {getStatusLabel(transaction.status)}
              </span>
            </div>
          </div>
          
          {/* Transaction Info */}
          <div>
            <h4 className={`font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('transactionInformation')}</h4>
            <dl className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <dt className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('transactionIdLabel')}</dt>
                <dd className={`font-mono mt-1 ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{transaction.id}</dd>
              </div>
              <div>
                <dt className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('type')}</dt>
                <dd className={`font-medium mt-1 ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{getTypeLabel(transaction.transaction_type)}</dd>
              </div>
              <div>
                <dt className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('status')}</dt>
                <dd className="mt-1">
                  <span className={getStatusBadgeClasses(transaction.status, isDark)}>
                    {getStatusLabel(transaction.status)}
                  </span>
                </dd>
              </div>
              <div>
                <dt className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('created')}</dt>
                <dd className={`mt-1 ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{formatDate(transaction.created_at)}</dd>
              </div>
              {transaction.reason && (
                <div className="col-span-2">
                  <dt className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('reason')}</dt>
                  <dd className={`mt-1 ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{transaction.reason}</dd>
                </div>
              )}
              {/* Show rejection reason for REJECTED transactions */}
              {transaction.status === 'REJECTED' && (transaction.rejection_reason || transaction.metadata?.rejection_reason) && (
                <div className="col-span-2">
                  <dt className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('rejectionReason')}</dt>
                  <dd className="mt-1">
                    <span className="px-3 py-2 bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400 rounded-lg inline-block">
                      {transaction.rejection_reason || transaction.metadata?.rejection_reason}
                    </span>
                  </dd>
                </div>
              )}
            </dl>
          </div>

          {/* Ledger Entries Info */}
          <div className={`border-t pt-6 ${isDark ? 'border-gray-700' : ''}`}>
            <h4 className={`font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('doubleEntryLedgerDetails')}</h4>
            <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('doubleEntryDesc')}
            </p>
            <div className={`rounded p-4 space-y-2 text-sm ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
              <div className="flex justify-between">
                <span className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('transactionType')}:</span>
                <span className={`font-medium ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{getTypeLabel(transaction.transaction_type)}</span>
              </div>
              <div className="flex justify-between">
                <span className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('status')}:</span>
                <span className={`font-medium ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{getStatusLabel(transaction.status)}</span>
              </div>
              {transaction.reverses_txn_id && (
                <div className={`flex justify-between border-t pt-2 ${isDark ? 'border-gray-600' : ''}`}>
                  <span className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('reversesTransaction')}:</span>
                  <span className={`font-mono text-xs ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{transaction.reverses_txn_id}</span>
                </div>
              )}
              {transaction.reversed_by_txn_id && (
                <div className={`flex justify-between border-t pt-2 ${isDark ? 'border-gray-600' : ''}`}>
                  <span className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('reversedBy')}:</span>
                  <span className={`font-mono text-xs ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{transaction.reversed_by_txn_id}</span>
                </div>
              )}
            </div>
          </div>

          {/* Actions */}
          {transaction.status === 'POSTED' && (
            <div className={`border-t pt-6 ${isDark ? 'border-gray-700' : ''}`}>
              <h4 className={`font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('actions')}</h4>
              <button
                onClick={() => alert(t('reversalRequiresAdmin'))}
                className="px-4 py-2 border border-red-600 text-red-600 rounded hover:bg-red-50 dark:hover:bg-red-900/20"
                data-testid="request-reversal"
              >
                {t('requestReversal')}
              </button>
            </div>
          )}
        </div>

        <div className={`sticky bottom-0 border-t p-6 ${isDark ? 'bg-gray-700 border-gray-600' : 'bg-gray-50'}`}>
          <button
            onClick={onClose}
            className={`w-full py-2 rounded ${isDark ? 'bg-gray-600 text-white hover:bg-gray-500' : 'bg-gray-600 text-white hover:bg-gray-700'}`}
            data-testid="close-details"
          >
            {t('close')}
          </button>
        </div>
      </div>
    </div>
  );
}

export { TransactionDetailsModal };
