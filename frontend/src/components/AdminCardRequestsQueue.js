// Admin Card Requests Queue
import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { useToast } from './Toast';

export function AdminCardRequestsQueue() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState('PENDING');
  const [requests, setRequests] = useState([]);
  const [selectedRequest, setSelectedRequest] = useState(null);
  const [loading, setLoading] = useState(true);
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

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get(`/admin/card-requests?status=${activeTab}`);
      console.log('Card requests response:', response.data);
      const reqs = response.data.data || [];
      console.log(`${activeTab} requests:`, reqs);
      // User info (user_name, user_email) is now included in the response - no more N+1 queries!
      setRequests(reqs);
    } catch (err) {
      toast.error('Failed to load requests');
    } finally {
      setLoading(false);
    }
  }, [activeTab, toast]);

  useEffect(() => {
    setSelectedRequest(null); // Clear selection when tab changes
    fetchRequests();
  }, [fetchRequests]);

  const handleFulfill = async () => {
    try {
      // Convert exp_month and exp_year to integers
      const payload = {
        ...fulfillData,
        exp_month: parseInt(fulfillData.exp_month, 10),
        exp_year: parseInt(fulfillData.exp_year, 10)
      };
      await api.post(`/admin/card-requests/${selectedRequest.id}/fulfill`, payload);
      toast.success('Card fulfilled!');
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

  // Helper function to get user display name
  const getUserName = (request) => {
    return request.user_name || request.user_id?.substring(0, 8) || 'Unknown';
  };

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Card Requests</h2>
      <div className="flex space-x-4 mb-6">
        {['PENDING', 'FULFILLED', 'REJECTED'].map(tab => (
          <button key={tab} onClick={() => setActiveTab(tab)} className={`px-4 py-2 rounded ${activeTab === tab ? 'bg-red-600 text-white' : 'bg-gray-100'}`}>{tab}</button>
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
        <div className="table-wrapper">
          <table className="table-main">
            <thead>
              <tr><th>Date</th><th>User</th><th>Email</th><th>Type</th><th>Status</th><th>Action</th></tr>
            </thead>
            <tbody>
              {requests.map(r => (
                <tr key={r.id} className="cursor-pointer hover:bg-gray-50" onClick={() => setSelectedRequest(r)}>
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
                  <td><button className="btn-text text-xs">View</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
