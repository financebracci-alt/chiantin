// Admin Transfers Queue with Pagination
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api';
import { useToast } from './Toast';
import { formatCurrency } from '../utils/currency';
import { getStatusBadgeClasses } from '../utils/transactions';

export function AdminTransfersQueue() {
  const toast = useToast();
  // Use ref to keep toast stable and prevent fetchTransfers from being recreated
  const toastRef = useRef(toast);
  toastRef.current = toast;
  
  // Track if this is initial mount to avoid showing skeleton on fast loads
  const isInitialMount = useRef(true);
  
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Initialize state from URL params
  const getInitialTab = () => {
    const urlTab = searchParams.get('tab');
    return ['SUBMITTED', 'COMPLETED', 'REJECTED'].includes(urlTab) ? urlTab : 'SUBMITTED';
  };
  const getInitialPage = () => {
    const urlPage = parseInt(searchParams.get('page'));
    return !isNaN(urlPage) && urlPage > 0 ? urlPage : 1;
  };
  const getInitialPageSize = () => {
    const urlSize = parseInt(searchParams.get('pageSize'));
    return [20, 50, 100].includes(urlSize) ? urlSize : 20;
  };
  const getInitialSearch = () => searchParams.get('search') || '';
  
  const [activeTab, setActiveTabInternal] = useState(getInitialTab);
  const [transfers, setTransfers] = useState([]);
  const [selectedTransfer, setSelectedTransfer] = useState(null);
  // Start with loading false to prevent skeleton flash on initial mount
  // The skeleton will show only after a brief delay if data is still loading
  const [loading, setLoading] = useState(false);
  const [showSkeleton, setShowSkeleton] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [editingRejectReason, setEditingRejectReason] = useState(false);
  const [editedRejectReason, setEditedRejectReason] = useState('');
  const [savingRejectReason, setSavingRejectReason] = useState(false);
  const [deletingTransfer, setDeletingTransfer] = useState(false);
  
  // Search state
  const [searchQuery, setSearchQuery] = useState(getInitialSearch);
  const [debouncedSearch, setDebouncedSearch] = useState(getInitialSearch);
  const [isSearchMode, setIsSearchMode] = useState(!!getInitialSearch());
  
  // Track previous search to prevent unnecessary URL updates
  const prevSearchRef = useRef(getInitialSearch());
  
  // Pagination state
  const [currentPage, setCurrentPageInternal] = useState(getInitialPage);
  const [pageSize, setPageSizeInternal] = useState(getInitialPageSize);
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    page_size: 20,
    total_pages: 1,
    has_next: false,
    has_prev: false
  });

  // Update URL when state changes
  const updateUrlParams = useCallback((updates) => {
    const newParams = new URLSearchParams(searchParams);
    // Keep the section param (sidebar uses 'ledger' for Transfers Queue)
    if (!newParams.has('section')) {
      newParams.set('section', 'ledger');
    }
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === undefined || value === '' || (key === 'page' && value === 1) || (key === 'pageSize' && value === 20) || (key === 'tab' && value === 'SUBMITTED')) {
        newParams.delete(key);
      } else {
        newParams.set(key, value);
      }
    });
    setSearchParams(newParams, { replace: true });
  }, [searchParams, setSearchParams]);

  // Wrapper functions to update state and URL
  const setActiveTab = useCallback((tab) => {
    setActiveTabInternal(tab);
    setCurrentPageInternal(1);
    updateUrlParams({ tab, page: null, search: null });
  }, [updateUrlParams]);

  const setCurrentPage = useCallback((page) => {
    setCurrentPageInternal(page);
    updateUrlParams({ page });
  }, [updateUrlParams]);

  const setPageSize = useCallback((size) => {
    setPageSizeInternal(size);
    setCurrentPageInternal(1);
    updateUrlParams({ pageSize: size, page: null });
  }, [updateUrlParams]);

  // Debounce search input - only update URL when search actually changes
  useEffect(() => {
    const timer = setTimeout(() => {
      // Only update if search value actually changed
      if (searchQuery !== prevSearchRef.current) {
        setDebouncedSearch(searchQuery);
        prevSearchRef.current = searchQuery;
        if (searchQuery) {
          updateUrlParams({ search: searchQuery, page: null });
        } else {
          updateUrlParams({ search: null });
        }
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchQuery, updateUrlParams]);

  // Reset page when search, tab, or page size changes
  useEffect(() => {
    if (currentPage !== 1) {
      setCurrentPageInternal(1);
    }
  }, [debouncedSearch, activeTab, pageSize]);

  // Delayed skeleton - only show after 150ms to prevent flash on fast loads
  useEffect(() => {
    let timer;
    if (loading) {
      timer = setTimeout(() => setShowSkeleton(true), 150);
    } else {
      setShowSkeleton(false);
    }
    return () => clearTimeout(timer);
  }, [loading]);

  const fetchTransfers = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: currentPage.toString(),
        page_size: pageSize.toString()
      });
      
      // If searching, search across ALL statuses
      if (debouncedSearch.trim()) {
        params.append('search', debouncedSearch.trim());
        setIsSearchMode(true);
      } else {
        params.append('status', activeTab);
        setIsSearchMode(false);
      }
      
      const response = await api.get(`/admin/transfers?${params.toString()}`);
      setTransfers(response.data.data || []);
      
      if (response.data.pagination) {
        setPagination(response.data.pagination);
      }
    } catch (err) {
      toastRef.current.error('Failed to load transfers');
      setTransfers([]);
    } finally {
      setLoading(false);
      isInitialMount.current = false;
    }
  }, [activeTab, debouncedSearch, currentPage, pageSize]);

  useEffect(() => {
    setSelectedTransfer(null);
    fetchTransfers();
  }, [fetchTransfers]);

  const handleApprove = async (transfer) => {
    try {
      await api.post(`/admin/transfers/${transfer.id}/approve`);
      toast.success('Transfer approved successfully');
      setSelectedTransfer(null);
      fetchTransfers();
    } catch (err) {
      toast.error('Failed to approve: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleReject = async (transfer) => {
    if (!rejectReason.trim()) {
      toast.error('Please enter a rejection reason');
      return;
    }
    try {
      await api.post(`/admin/transfers/${transfer.id}/reject`, { reason: rejectReason });
      toast.success('Transfer rejected');
      setSelectedTransfer(null);
      setRejectReason('');
      fetchTransfers();
    } catch (err) {
      toast.error('Failed to reject: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleUpdateRejectReason = async () => {
    if (!editedRejectReason.trim()) {
      toast.error('Please enter a rejection reason');
      return;
    }
    setSavingRejectReason(true);
    try {
      await api.patch(`/admin/transfers/${selectedTransfer.id}/reject-reason`, { reason: editedRejectReason });
      toast.success('Rejection reason updated');
      setSelectedTransfer(prev => ({...prev, reject_reason: editedRejectReason}));
      setEditingRejectReason(false);
      fetchTransfers();
    } catch (err) {
      toast.error('Failed to update: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSavingRejectReason(false);
    }
  };

  const handleDelete = async (transfer) => {
    if (!window.confirm(`Are you sure you want to permanently delete this transfer?\n\nBeneficiary: ${transfer.beneficiary_name}\nAmount: €${(transfer.amount / 100).toFixed(2)}`)) {
      return;
    }
    setDeletingTransfer(true);
    try {
      await api.delete(`/admin/transfers/${transfer.id}`);
      toast.success('Transfer deleted');
      setSelectedTransfer(null);
      fetchTransfers();
    } catch (err) {
      toast.error('Failed to delete: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeletingTransfer(false);
    }
  };

  const handleTabChange = (newTab) => {
    setActiveTab(newTab);
    setSelectedTransfer(null);
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      setCurrentPage(newPage);
    }
  };

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
  };

  // Calculate showing range
  const getShowingRange = () => {
    if (pagination.total === 0) return { start: 0, end: 0 };
    const start = ((pagination.page || currentPage) - 1) * (pagination.page_size || pageSize) + 1;
    const end = Math.min(start + transfers.length - 1, pagination.total);
    return { start, end };
  };

  const showingRange = getShowingRange();

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Transfers Queue</h2>
      
      {/* Search Bar */}
      <div className="mb-6">
        <div className="relative">
          <input
            type="text"
            placeholder="Search by beneficiary, sender, email, IBAN, reference... (searches ALL statuses)"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            data-testid="search-input"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          )}
        </div>
        {isSearchMode && (
          <p className="text-sm text-blue-600 mt-2">
            Searching across ALL transfers (ignoring tab filter). Found {pagination.total} result(s).
          </p>
        )}
      </div>
      
      {/* Pagination Controls - TOP (Professional Admin Style) */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-4 pb-4 border-b border-gray-200">
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">
            {isSearchMode 
              ? `Found ${pagination.total} results matching "${debouncedSearch}"`
              : `Showing ${showingRange.start}–${showingRange.end} of ${pagination.total} transfers`
            }
          </span>
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-600">Show:</span>
            <select
              value={pageSize}
              onChange={(e) => handlePageSizeChange(Number(e.target.value))}
              className="border border-gray-300 rounded px-2 py-1 text-sm"
              data-testid="page-size-select"
            >
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
            <span className="text-sm text-gray-600">per page</span>
          </div>
        </div>
        
        {pagination.total_pages > 1 && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(1)}
              disabled={!pagination.has_prev}
              className={`px-3 py-1 text-sm rounded ${
                pagination.has_prev 
                  ? 'bg-gray-200 hover:bg-gray-300 text-gray-700' 
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
              data-testid="pagination-first"
            >
              First
            </button>
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={!pagination.has_prev}
              className={`px-3 py-1 text-sm rounded ${
                pagination.has_prev 
                  ? 'bg-gray-200 hover:bg-gray-300 text-gray-700' 
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
              data-testid="pagination-prev"
            >
              Previous
            </button>
            
            <span className="px-3 py-1 text-sm text-gray-700">
              Page {pagination.page || currentPage} of {pagination.total_pages}
            </span>
            
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={!pagination.has_next}
              className={`px-3 py-1 text-sm rounded ${
                pagination.has_next 
                  ? 'bg-gray-200 hover:bg-gray-300 text-gray-700' 
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
              data-testid="pagination-next"
            >
              Next
            </button>
            <button
              onClick={() => handlePageChange(pagination.total_pages)}
              disabled={!pagination.has_next}
              className={`px-3 py-1 text-sm rounded ${
                pagination.has_next 
                  ? 'bg-gray-200 hover:bg-gray-300 text-gray-700' 
                  : 'bg-gray-100 text-gray-400 cursor-not-allowed'
              }`}
              data-testid="pagination-last"
            >
              Last
            </button>
          </div>
        )}
      </div>
      
      {/* Tab Navigation */}
      <div className="flex space-x-4 mb-4">
        {['SUBMITTED', 'COMPLETED', 'REJECTED'].map(tab => (
          <button 
            key={tab} 
            onClick={() => handleTabChange(tab)} 
            className={`px-4 py-2 rounded transition-colors ${
              activeTab === tab && !isSearchMode
                ? 'bg-red-600 text-white' 
                : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
            }`}
            data-testid={`tab-${tab.toLowerCase()}`}
          >
            {tab}
          </button>
        ))}
      </div>
      
      {showSkeleton ? (
        <div className="skeleton-card h-64"></div>
      ) : selectedTransfer ? (
        <div className="card p-6">
          <div className="flex justify-between items-start mb-4">
            <h3 className="text-lg font-semibold">Transfer Details</h3>
            <button onClick={() => setSelectedTransfer(null)} className="text-gray-600 hover:text-gray-900 text-xl">×</button>
          </div>
          
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div><span className="text-sm text-gray-600">Reference:</span> <span className="font-mono text-sm">{selectedTransfer.reference_number || selectedTransfer.id?.substring(0, 8)}</span></div>
            <div><span className="text-sm text-gray-600">Status:</span> <span className={`badge ${getStatusBadgeClasses(selectedTransfer.status)}`}>{selectedTransfer.status}</span></div>
            <div><span className="text-sm text-gray-600">Amount:</span> <span className="font-semibold">{formatCurrency(selectedTransfer.amount)}</span></div>
            <div><span className="text-sm text-gray-600">Date:</span> <span className="text-sm">{new Date(selectedTransfer.created_at).toLocaleString()}</span></div>
            <div><span className="text-sm text-gray-600">Sender:</span> <span className="font-medium">{selectedTransfer.sender_name}</span></div>
            <div><span className="text-sm text-gray-600">Sender Email:</span> <span className="text-sm">{selectedTransfer.sender_email}</span></div>
            <div><span className="text-sm text-gray-600">Sender IBAN:</span> <span className="font-mono text-sm">{selectedTransfer.sender_iban}</span></div>
            <div><span className="text-sm text-gray-600">Beneficiary:</span> <span className="font-medium">{selectedTransfer.beneficiary_name}</span></div>
            <div className="col-span-2"><span className="text-sm text-gray-600">Beneficiary IBAN:</span> <span className="font-mono text-sm">{selectedTransfer.beneficiary_iban}</span></div>
            <div className="col-span-2"><span className="text-sm text-gray-600">Details:</span> <span className="text-sm">{selectedTransfer.details || 'N/A'}</span></div>
            
            {selectedTransfer.status === 'REJECTED' && (
              <div className="col-span-2 bg-red-50 p-3 rounded border border-red-200">
                <div className="flex justify-between items-start">
                  <div>
                    <span className="text-sm text-gray-600 font-medium">Rejection Reason:</span>
                    {editingRejectReason ? (
                      <div className="mt-2">
                        <textarea
                          value={editedRejectReason}
                          onChange={(e) => setEditedRejectReason(e.target.value)}
                          className="w-full p-2 border border-gray-300 rounded text-sm"
                          rows={2}
                        />
                        <div className="flex gap-2 mt-2">
                          <button
                            onClick={handleUpdateRejectReason}
                            disabled={savingRejectReason}
                            className="px-3 py-1 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                          >
                            {savingRejectReason ? 'Saving...' : 'Save'}
                          </button>
                          <button
                            onClick={() => {
                              setEditingRejectReason(false);
                              setEditedRejectReason(selectedTransfer.reject_reason || '');
                            }}
                            className="px-3 py-1 bg-gray-200 text-gray-700 text-sm rounded hover:bg-gray-300"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-red-700 text-sm mt-1">{selectedTransfer.reject_reason || 'No reason provided'}</p>
                    )}
                  </div>
                  {!editingRejectReason && (
                    <button
                      onClick={() => {
                        setEditedRejectReason(selectedTransfer.reject_reason || '');
                        setEditingRejectReason(true);
                      }}
                      className="text-sm text-blue-600 hover:text-blue-800"
                    >
                      Edit
                    </button>
                  )}
                </div>
              </div>
            )}
          </div>
          
          {/* Action Buttons */}
          <div className="flex flex-wrap gap-3 pt-4 border-t border-gray-200">
            {selectedTransfer.status === 'SUBMITTED' && (
              <>
                <button onClick={() => handleApprove(selectedTransfer)} className="btn-primary">
                  Approve
                </button>
                <div className="flex-1">
                  <input
                    type="text"
                    placeholder="Rejection reason..."
                    value={rejectReason}
                    onChange={(e) => setRejectReason(e.target.value)}
                    className="input-field text-sm"
                  />
                </div>
                <button onClick={() => handleReject(selectedTransfer)} className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700">
                  Reject
                </button>
              </>
            )}
            <button 
              onClick={() => handleDelete(selectedTransfer)} 
              disabled={deletingTransfer}
              className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 disabled:opacity-50"
            >
              {deletingTransfer ? 'Deleting...' : 'Delete'}
            </button>
            <button onClick={() => setSelectedTransfer(null)} className="btn-secondary ml-auto">
              Close
            </button>
          </div>
        </div>
      ) : (
        <>
          {/* Table */}
          <div className="table-wrapper">
            <table className="table-main">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Sender</th>
                  <th>Beneficiary</th>
                  <th>Amount</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {transfers.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="text-center text-gray-500 py-8">
                      {isSearchMode ? 'No results found for your search' : 'No transfers found'}
                    </td>
                  </tr>
                ) : (
                  transfers.map(t => (
                    <tr key={t.id} className="hover:bg-gray-50">
                      <td className="text-xs">{new Date(t.created_at).toLocaleString()}</td>
                      <td>
                        <div className="font-medium text-sm">{t.sender_name}</div>
                        <div className="text-xs text-gray-500">{t.sender_email}</div>
                      </td>
                      <td>
                        <div className="font-medium text-sm">{t.beneficiary_name}</div>
                        <div className="text-xs text-gray-500 font-mono">{t.beneficiary_iban?.substring(0, 12)}...</div>
                      </td>
                      <td className="font-semibold">{formatCurrency(t.amount)}</td>
                      <td>
                        <span className={`badge ${getStatusBadgeClasses(t.status)}`}>
                          {t.status}
                        </span>
                      </td>
                      <td>
                        <button 
                          onClick={() => setSelectedTransfer(t)} 
                          className="btn-text text-xs"
                          data-testid={`view-btn-${t.id}`}
                        >
                          Open
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
