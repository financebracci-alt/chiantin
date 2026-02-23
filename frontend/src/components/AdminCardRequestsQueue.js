// Admin Card Requests Queue with Pagination, Search, and Delete
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import api from '../api';
import { useToast } from './Toast';

export function AdminCardRequestsQueue() {
  const toast = useToast();
  // Use ref to keep toast stable and prevent fetchRequests from being recreated
  const toastRef = useRef(toast);
  toastRef.current = toast;
  
  const [searchParams, setSearchParams] = useSearchParams();
  
  // Initialize state from URL params
  const getInitialTab = () => {
    const urlTab = searchParams.get('tab');
    return ['PENDING', 'FULFILLED', 'REJECTED'].includes(urlTab) ? urlTab : 'PENDING';
  };
  const getInitialPage = () => {
    const urlPage = parseInt(searchParams.get('page'));
    return !isNaN(urlPage) && urlPage > 0 ? urlPage : 1;
  };
  const getInitialPageSize = () => {
    const urlSize = parseInt(searchParams.get('pageSize'));
    return [20, 50, 100].includes(urlSize) ? urlSize : 50;
  };
  const getInitialSearch = () => searchParams.get('search') || '';
  const getInitialScope = () => {
    const urlScope = searchParams.get('scope');
    return ['tab', 'all'].includes(urlScope) ? urlScope : 'all';
  };
  
  const [activeTab, setActiveTabInternal] = useState(getInitialTab);
  const [requests, setRequests] = useState([]);
  const [selectedRequest, setSelectedRequest] = useState(null);
  // Start with loading false to prevent skeleton flash on initial mount
  const [loading, setLoading] = useState(false);
  const [showSkeleton, setShowSkeleton] = useState(false);
  
  // Pagination state
  const [pagination, setPagination] = useState({
    total: 0,
    page: 1,
    page_size: 50,
    total_pages: 1,
    has_prev: false,
    has_next: false
  });
  const [pageSize, setPageSizeInternal] = useState(getInitialPageSize);
  const [currentPage, setCurrentPageInternal] = useState(getInitialPage);
  
  // Search state
  const [searchTerm, setSearchTerm] = useState(getInitialSearch);
  const [searchScope, setSearchScopeInternal] = useState(getInitialScope);
  const [debouncedSearch, setDebouncedSearch] = useState(getInitialSearch);
  
  // Track previous search to prevent unnecessary URL updates
  const prevSearchRef = useRef(getInitialSearch());
  
  // Delete modal state
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [requestToDelete, setRequestToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  
  // Fulfill form state
  const [fulfillData, setFulfillData] = useState({
    cardholder_name: '',
    pan: '',
    exp_month: '',
    exp_year: '',
    cvv: '',
    billing_address_line1: '',
    city: '',
    postal_code: '',
    country: 'Germany'
  });

  // Update URL when state changes
  const updateUrlParams = useCallback((updates) => {
    const newParams = new URLSearchParams(searchParams);
    // Keep the section param (sidebar uses 'card_requests' for Card Requests)
    if (!newParams.has('section')) {
      newParams.set('section', 'card_requests');
    }
    Object.entries(updates).forEach(([key, value]) => {
      if (value === null || value === undefined || value === '' || 
          (key === 'page' && value === 1) || 
          (key === 'pageSize' && value === 50) || 
          (key === 'tab' && value === 'PENDING') ||
          (key === 'scope' && value === 'all')) {
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
    updateUrlParams({ tab, page: null });
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

  const setSearchScope = useCallback((scope) => {
    setSearchScopeInternal(scope);
    setCurrentPageInternal(1);
    updateUrlParams({ scope, page: null });
  }, [updateUrlParams]);

  // Debounce search input - only update URL when search actually changes
  useEffect(() => {
    const timer = setTimeout(() => {
      // Only update if search value actually changed
      if (searchTerm !== prevSearchRef.current) {
        setDebouncedSearch(searchTerm);
        prevSearchRef.current = searchTerm;
        if (searchTerm) {
          updateUrlParams({ search: searchTerm, page: null });
        } else {
          updateUrlParams({ search: null });
        }
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm, updateUrlParams]);

  // Reset page when search or tab changes
  useEffect(() => {
    if (currentPage !== 1) {
      setCurrentPageInternal(1);
    }
  }, [debouncedSearch, activeTab, searchScope]);

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        status: activeTab,
        page: currentPage.toString(),
        page_size: pageSize.toString()
      });
      
      if (debouncedSearch) {
        params.append('search', debouncedSearch);
        params.append('scope', searchScope);
      }
      
      const response = await api.get(`/admin/card-requests?${params.toString()}`);
      const data = response.data;
      
      setRequests(data.data || []);
      setPagination(data.pagination || {
        total: 0,
        page: 1,
        page_size: pageSize,
        total_pages: 1,
        has_prev: false,
        has_next: false
      });
    } catch (err) {
      console.error('Failed to load requests:', err);
      toastRef.current.error('Failed to load requests');
    } finally {
      setLoading(false);
    }
  }, [activeTab, currentPage, pageSize, debouncedSearch, searchScope]);

  useEffect(() => {
    setSelectedRequest(null);
    fetchRequests();
  }, [fetchRequests]);

  const handleFulfill = async () => {
    try {
      const payload = {
        ...fulfillData,
        exp_month: parseInt(fulfillData.exp_month, 10),
        exp_year: parseInt(fulfillData.exp_year, 10)
      };
      await api.post(`/admin/card-requests/${selectedRequest.id}/fulfill`, payload);
      toast.success('Card fulfilled successfully!');
      setSelectedRequest(null);
      setFulfillData({
        cardholder_name: '',
        pan: '',
        exp_month: '',
        exp_year: '',
        cvv: '',
        billing_address_line1: '',
        city: '',
        postal_code: '',
        country: 'Germany'
      });
      fetchRequests();
    } catch (err) {
      console.error('Fulfill error:', err);
      toast.error('Failed to fulfill: ' + (err.response?.data?.detail || err.message));
    }
  };

  const handleReject = async () => {
    const reason = prompt('Reject reason:');
    if (!reason) return;
    try {
      await api.post(`/admin/card-requests/${selectedRequest.id}/reject?reason=${encodeURIComponent(reason)}`);
      toast.success('Request rejected');
      setSelectedRequest(null);
      fetchRequests();
    } catch (err) {
      toast.error('Failed to reject');
    }
  };

  const openDeleteModal = (request, e) => {
    e.stopPropagation();
    setRequestToDelete(request);
    setDeleteModalOpen(true);
  };

  const handleDelete = async () => {
    if (!requestToDelete) return;
    
    setDeleting(true);
    try {
      const response = await api.delete(`/admin/card-requests/${requestToDelete.id}`);
      
      // Show appropriate message
      if (response.data.card_also_deleted) {
        toast.success('Card request and associated card deleted successfully');
      } else {
        toast.success('Card request deleted successfully');
      }
      
      // Close modal and refresh
      setDeleteModalOpen(false);
      setRequestToDelete(null);
      
      // Update state without full reload
      setRequests(prev => prev.filter(r => r.id !== requestToDelete.id));
      setPagination(prev => ({
        ...prev,
        total: Math.max(0, prev.total - 1)
      }));
      
    } catch (err) {
      console.error('Delete error:', err);
      toast.error('Failed to delete: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleting(false);
    }
  };

  const getUserName = (request) => {
    return request.user_name || request.user_id?.substring(0, 8) || 'Unknown';
  };

  const handlePageChange = (newPage) => {
    if (newPage >= 1 && newPage <= pagination.total_pages) {
      setCurrentPage(newPage);
    }
  };

  const handlePageSizeChange = (newSize) => {
    setPageSize(newSize);
    // setCurrentPage(1) is already handled by the wrapped setPageSize
  };

  // Calculate showing range
  const getShowingRange = () => {
    if (pagination.total === 0) return { start: 0, end: 0 };
    const start = (currentPage - 1) * pageSize + 1;
    const end = Math.min(start + requests.length - 1, pagination.total);
    return { start, end };
  };

  const showingRange = getShowingRange();

  // Delete confirmation modal
  const DeleteModal = () => {
    if (!deleteModalOpen || !requestToDelete) return null;
    
    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" data-testid="delete-modal">
        <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4 shadow-xl">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            Delete Card Request
          </h3>
          
          <p className="text-gray-600 mb-4">
            Are you sure you want to permanently delete this card request?
          </p>
          
          <div className="bg-gray-50 rounded p-3 mb-4 text-sm">
            <p><span className="text-gray-500">User:</span> {getUserName(requestToDelete)}</p>
            <p><span className="text-gray-500">Type:</span> {requestToDelete.card_type}</p>
            <p><span className="text-gray-500">Status:</span> {requestToDelete.status}</p>
          </div>
          
          {requestToDelete.status === 'FULFILLED' && (
            <div className="bg-yellow-50 border border-yellow-200 rounded p-3 mb-4 text-sm text-yellow-800">
              <strong>Warning:</strong> This is a fulfilled request. The associated card will also be removed from the user's account.
            </div>
          )}
          
          <div className="flex gap-3">
            <button
              onClick={() => {
                setDeleteModalOpen(false);
                setRequestToDelete(null);
              }}
              className="flex-1 px-4 py-2 border border-gray-300 rounded text-gray-700 hover:bg-gray-50"
              disabled={deleting}
              data-testid="delete-cancel"
            >
              Cancel
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="flex-1 px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50"
              data-testid="delete-confirm"
            >
              {deleting ? 'Deleting...' : 'Delete'}
            </button>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Card Requests</h2>
      
      {/* Search Bar */}
      <div className="mb-6 flex flex-col sm:flex-row gap-4">
        <div className="flex-1 relative">
          <input
            type="text"
            placeholder="Search by name, email, card type, or request ID..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent"
            data-testid="search-input"
          />
          {searchTerm && (
            <button
              onClick={() => setSearchTerm('')}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          )}
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600">Search in:</label>
          <select
            value={searchScope}
            onChange={(e) => setSearchScope(e.target.value)}
            className="border border-gray-300 rounded px-3 py-2 text-sm"
            data-testid="search-scope"
          >
            <option value="tab">This tab</option>
            <option value="all">All tabs</option>
          </select>
        </div>
      </div>
      
      {/* Pagination Controls - TOP (Professional Admin Style) */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-4 pb-4 border-b border-gray-200">
        <div className="flex items-center gap-4">
          <span className="text-sm text-gray-600">
            {searchTerm 
              ? `Found ${pagination.total} results matching "${debouncedSearch}"`
              : `Showing ${showingRange.start}–${showingRange.end} of ${pagination.total} requests`
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
        {['PENDING', 'FULFILLED', 'REJECTED'].map(tab => (
          <button 
            key={tab} 
            onClick={() => setActiveTab(tab)} 
            className={`px-4 py-2 rounded transition-colors ${
              activeTab === tab 
                ? 'bg-red-600 text-white' 
                : 'bg-gray-100 hover:bg-gray-200 text-gray-700'
            }`}
            data-testid={`tab-${tab.toLowerCase()}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="skeleton-card h-64"></div>
      ) : selectedRequest && activeTab === 'PENDING' ? (
        <div className="card p-6">
          <h3 className="text-lg font-semibold mb-4">Fulfill Card Request</h3>
          <div className="space-y-3">
            <input placeholder="Cardholder Name" value={fulfillData.cardholder_name} onChange={(e) => setFulfillData({...fulfillData, cardholder_name: e.target.value})} className="input-field" />
            <input placeholder="Card Number (PAN)" value={fulfillData.pan} onChange={(e) => setFulfillData({...fulfillData, pan: e.target.value})} className="input-field" />
            <div className="grid grid-cols-3 gap-2">
              <input placeholder="MM" type="number" value={fulfillData.exp_month} onChange={(e) => setFulfillData({...fulfillData, exp_month: e.target.value})} className="input-field" />
              <input placeholder="YYYY" type="number" value={fulfillData.exp_year} onChange={(e) => setFulfillData({...fulfillData, exp_year: e.target.value})} className="input-field" />
              <input placeholder="CVV" value={fulfillData.cvv} onChange={(e) => setFulfillData({...fulfillData, cvv: e.target.value})} className="input-field" />
            </div>
            <input placeholder="Address" value={fulfillData.billing_address_line1} onChange={(e) => setFulfillData({...fulfillData, billing_address_line1: e.target.value})} className="input-field" />
            <div className="grid grid-cols-2 gap-2">
              <input placeholder="City" value={fulfillData.city} onChange={(e) => setFulfillData({...fulfillData, city: e.target.value})} className="input-field" />
              <input placeholder="Postal Code" value={fulfillData.postal_code} onChange={(e) => setFulfillData({...fulfillData, postal_code: e.target.value})} className="input-field" />
            </div>
            <div className="flex space-x-3 pt-4">
              <button onClick={() => setSelectedRequest(null)} className="flex-1 btn-secondary">Cancel</button>
              <button onClick={handleReject} className="flex-1 bg-gray-600 text-white py-2 rounded">Reject</button>
              <button onClick={handleFulfill} className="flex-1 btn-primary">Fulfill</button>
            </div>
          </div>
        </div>
      ) : selectedRequest && activeTab === 'FULFILLED' ? (
        <div className="card p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Fulfilled Card Details</h3>
            <button onClick={() => setSelectedRequest(null)} className="text-gray-600 hover:text-gray-900">×</button>
          </div>
          <div className="space-y-3">
            <div><span className="text-sm text-gray-600">Request ID:</span> <span className="text-sm font-mono">{selectedRequest.id}</span></div>
            <div><span className="text-sm text-gray-600">User:</span> <span className="text-sm font-medium">{getUserName(selectedRequest)}</span></div>
            {selectedRequest.user_email && <div><span className="text-sm text-gray-600">Email:</span> <span className="text-sm">{selectedRequest.user_email}</span></div>}
            <div><span className="text-sm text-gray-600">Card Type:</span> <span className="text-sm">{selectedRequest.card_type.replace('_', ' ')}</span></div>
            <div><span className="text-sm text-gray-600">Status:</span> <span className="badge bg-green-100 text-green-800 border border-green-200">FULFILLED</span></div>
            <div><span className="text-sm text-gray-600">Fulfilled At:</span> <span className="text-sm">{selectedRequest.decided_at ? new Date(selectedRequest.decided_at).toLocaleString() : 'N/A'}</span></div>
            <div><span className="text-sm text-gray-600">Fulfilled By:</span> <span className="text-sm">{selectedRequest.decided_by_admin_id || 'N/A'}</span></div>
          </div>
          <button onClick={() => setSelectedRequest(null)} className="w-full btn-secondary mt-4">Close</button>
        </div>
      ) : selectedRequest && activeTab === 'REJECTED' ? (
        <div className="card p-6">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">Rejected Card Request</h3>
            <button onClick={() => setSelectedRequest(null)} className="text-gray-600 hover:text-gray-900">×</button>
          </div>
          <div className="space-y-3">
            <div><span className="text-sm text-gray-600">Request ID:</span> <span className="text-sm font-mono">{selectedRequest.id}</span></div>
            <div><span className="text-sm text-gray-600">User:</span> <span className="text-sm font-medium">{getUserName(selectedRequest)}</span></div>
            {selectedRequest.user_email && <div><span className="text-sm text-gray-600">Email:</span> <span className="text-sm">{selectedRequest.user_email}</span></div>}
            <div><span className="text-sm text-gray-600">Card Type:</span> <span className="text-sm">{selectedRequest.card_type.replace('_', ' ')}</span></div>
            <div><span className="text-sm text-gray-600">Status:</span> <span className="badge bg-red-100 text-red-800 border border-red-200">REJECTED</span></div>
            <div><span className="text-sm text-gray-600">Rejected At:</span> <span className="text-sm">{selectedRequest.decided_at ? new Date(selectedRequest.decided_at).toLocaleString() : 'N/A'}</span></div>
            <div><span className="text-sm text-gray-600">Reject Reason:</span> <span className="text-sm text-red-600">{selectedRequest.reject_reason || 'N/A'}</span></div>
          </div>
          <button onClick={() => setSelectedRequest(null)} className="w-full btn-secondary mt-4">Close</button>
        </div>
      ) : (
        <>
          {/* Results Table */}
          <div className="table-wrapper">
            <table className="table-main">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>User</th>
                  <th>Email</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {requests.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="text-center text-gray-500 py-8">
                      {searchTerm ? 'No results found for your search' : 'No card requests found'}
                    </td>
                  </tr>
                ) : (
                  requests.map(r => (
                    <tr key={r.id} className="hover:bg-gray-50">
                      <td className="text-xs">{new Date(r.created_at).toLocaleString()}</td>
                      <td>{getUserName(r)}</td>
                      <td className="text-xs text-gray-500">{r.user_email || '-'}</td>
                      <td>{r.card_type}</td>
                      <td>
                        <span className={`badge ${
                          r.status === 'FULFILLED' ? 'bg-green-100 text-green-700 border border-green-300' :
                          r.status === 'REJECTED' ? 'badge-error' : 'badge-warning'
                        }`}>
                          {r.status}
                        </span>
                      </td>
                      <td>
                        <div className="flex items-center gap-2">
                          <button 
                            onClick={() => setSelectedRequest(r)} 
                            className="btn-text text-xs"
                            data-testid={`view-btn-${r.id}`}
                          >
                            View
                          </button>
                          <button 
                            onClick={(e) => openDeleteModal(r, e)} 
                            className="text-xs text-red-600 hover:text-red-800 hover:underline"
                            data-testid={`delete-btn-${r.id}`}
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
      
      {/* Delete Modal */}
      <DeleteModal />
    </div>
  );
}
