// Admin Transfers Queue
import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { formatCurrency } from '../utils/currency';
import { getStatusBadgeClasses } from '../utils/transactions';

export function AdminTransfersQueue() {
  const toast = useToast();
  const [activeTab, setActiveTab] = useState('SUBMITTED');
  const [transfers, setTransfers] = useState([]);
  const [selectedTransfer, setSelectedTransfer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [rejectReason, setRejectReason] = useState('');
  const [editingRejectReason, setEditingRejectReason] = useState(false);
  const [editedRejectReason, setEditedRejectReason] = useState('');
  const [savingRejectReason, setSavingRejectReason] = useState(false);
  const [deletingTransfer, setDeletingTransfer] = useState(false);

  const fetchTransfers = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get(`/admin/transfers?status=${activeTab}`);
      setTransfers(response.data.data);
    } catch (err) {
      toast.error('Failed to load transfers');
    } finally {
      setLoading(false);
    }
  }, [activeTab, toast]);

  useEffect(() => {
    fetchTransfers();
  }, [fetchTransfers]);

  const handleApprove = async (id) => {
    try {
      await api.post(`/admin/transfers/${id}/approve`);
      toast.success('Transfer approved');
      setSelectedTransfer(null);
      fetchTransfers();
    } catch (err) {
      toast.error('Failed to approve');
    }
  };

  const handleReject = async (id) => {
    if (!rejectReason) {
      toast.error('Reject reason required');
      return;
    }
    try {
      await api.post(`/admin/transfers/${id}/reject`, { reason: rejectReason });
      toast.success('Transfer rejected');
      setSelectedTransfer(null);
      setRejectReason('');
      fetchTransfers();
    } catch (err) {
      toast.error('Failed to reject');
    }
  };

  const handleDeleteTransfer = async (id) => {
    const transfer = selectedTransfer || transfers.find(t => t.id === id);
    const formattedAmount = formatCurrency(transfer?.amount || 0);
    const confirmMessage = `⚠️ DELETE TRANSFER ⚠️\n\nYou are about to permanently delete this transfer:\n\n• Beneficiary: ${transfer?.beneficiary_name}\n• Amount: ${formattedAmount}\n• Status: ${transfer?.status}\n\nThis action CANNOT be undone!\n\nType "DELETE" to confirm:`;
    
    const confirmInput = prompt(confirmMessage);
    
    if (confirmInput !== "DELETE") {
      if (confirmInput !== null) {
        toast.error('Confirmation failed. Transfer not deleted.');
      }
      return;
    }
    
    setDeletingTransfer(true);
    try {
      await api.delete(`/admin/transfers/${id}`);
      toast.success('Transfer permanently deleted');
      setSelectedTransfer(null);
      fetchTransfers();
    } catch (err) {
      toast.error('Failed to delete transfer: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeletingTransfer(false);
    }
  };

  const handleEditRejectReason = () => {
    setEditedRejectReason(selectedTransfer?.reject_reason || '');
    setEditingRejectReason(true);
  };

  const handleSaveRejectReason = async () => {
    if (!editedRejectReason.trim()) {
      toast.error('Rejection reason cannot be empty');
      return;
    }
    
    setSavingRejectReason(true);
    try {
      await api.patch(`/admin/transfers/${selectedTransfer.id}/reject-reason`, {
        reason: editedRejectReason
      });
      toast.success('Rejection reason updated');
      setEditingRejectReason(false);
      // Update local state
      setSelectedTransfer(prev => ({
        ...prev,
        reject_reason: editedRejectReason
      }));
      fetchTransfers();
    } catch (err) {
      toast.error('Failed to update rejection reason: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSavingRejectReason(false);
    }
  };

  const handleCancelEditRejectReason = () => {
    setEditingRejectReason(false);
    setEditedRejectReason('');
  };

  return (
    <div>
      <h2 className="text-2xl font-semibold mb-6">Transfers Queue</h2>
      <div className="flex space-x-4 mb-6">
        {['SUBMITTED', 'COMPLETED', 'REJECTED'].map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 rounded ${activeTab === tab ? 'bg-red-600 text-white' : 'bg-gray-100'}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="skeleton-card h-64"></div>
      ) : selectedTransfer ? (
        <div className="card p-6">
          <div className="flex justify-between mb-4">
            <h3 className="text-lg font-semibold">Transfer Details</h3>
            <button onClick={() => setSelectedTransfer(null)} className="text-gray-600 hover:text-gray-800">×</button>
          </div>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-gray-600">To:</dt><dd className="font-medium">{selectedTransfer.beneficiary_name}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-600">IBAN:</dt><dd className="font-mono text-xs">{selectedTransfer.beneficiary_iban}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-600">Amount:</dt><dd className="font-bold">{formatCurrency(selectedTransfer.amount)}</dd></div>
            <div className="flex justify-between"><dt className="text-gray-600">Details:</dt><dd>{selectedTransfer.details}</dd></div>
            {selectedTransfer.reference_number && <div className="flex justify-between"><dt className="text-gray-600">Reference:</dt><dd>{selectedTransfer.reference_number}</dd></div>}
            <div className="flex justify-between"><dt className="text-gray-600">Status:</dt><dd><span className={getStatusBadgeClasses(selectedTransfer.status, false)}>{selectedTransfer.status}</span></dd></div>
            
            {/* Rejection Reason Section - Editable */}
            {selectedTransfer.status === 'REJECTED' && (
              <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex justify-between items-start mb-1">
                  <dt className="text-red-700 font-medium text-sm">Rejection Reason:</dt>
                  {!editingRejectReason && (
                    <button
                      onClick={handleEditRejectReason}
                      className="text-xs text-blue-600 hover:text-blue-800 flex items-center space-x-1"
                      data-testid="edit-reject-reason-btn"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                      </svg>
                      <span>Edit</span>
                    </button>
                  )}
                </div>
                {editingRejectReason ? (
                  <div className="space-y-2">
                    <textarea
                      value={editedRejectReason}
                      onChange={(e) => setEditedRejectReason(e.target.value)}
                      rows={3}
                      className="w-full px-3 py-2 border border-red-300 rounded-lg text-sm resize-y min-h-[60px] focus:outline-none focus:ring-2 focus:ring-red-500"
                      placeholder="Enter rejection reason..."
                      data-testid="edit-reject-reason-textarea"
                    />
                    <div className="flex space-x-2">
                      <button
                        onClick={handleSaveRejectReason}
                        disabled={savingRejectReason}
                        className="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700 disabled:opacity-50"
                        data-testid="save-reject-reason-btn"
                      >
                        {savingRejectReason ? 'Saving...' : 'Save'}
                      </button>
                      <button
                        onClick={handleCancelEditRejectReason}
                        className="px-3 py-1 bg-gray-200 text-gray-700 text-xs rounded hover:bg-gray-300"
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                ) : (
                  <dd className="text-red-600 text-sm">{selectedTransfer.reject_reason || 'No reason provided'}</dd>
                )}
              </div>
            )}
            
            {selectedTransfer.admin_action_by && (
              <div className="flex justify-between mt-2"><dt className="text-gray-600">Processed by:</dt><dd className="text-xs text-gray-500">ECOMMBX Staff</dd></div>
            )}
            {selectedTransfer.admin_action_at && (
              <div className="flex justify-between"><dt className="text-gray-600">Processed at:</dt><dd className="text-xs text-gray-500">{new Date(selectedTransfer.admin_action_at).toLocaleString()}</dd></div>
            )}
          </dl>
          
          {selectedTransfer.status === 'SUBMITTED' && (
            <div className="mt-6 space-y-3">
              <button onClick={() => handleApprove(selectedTransfer.id)} className="w-full btn-primary">Approve Transfer</button>
              <div>
                <input type="text" value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="Reject reason..." className="input-field mb-2" />
                <button onClick={() => handleReject(selectedTransfer.id)} className="w-full btn-secondary">Reject Transfer</button>
              </div>
            </div>
          )}
          
          {/* Delete Transfer Button - Always visible */}
          <div className="mt-6 pt-4 border-t border-gray-200">
            <button
              onClick={() => handleDeleteTransfer(selectedTransfer.id)}
              disabled={deletingTransfer}
              className="w-full px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 flex items-center justify-center space-x-2"
              data-testid="delete-transfer-btn"
            >
              {deletingTransfer ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                  <span>Deleting...</span>
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                  </svg>
                  <span>Delete Transfer Permanently</span>
                </>
              )}
            </button>
            <p className="text-xs text-gray-500 text-center mt-2">This action cannot be undone</p>
          </div>
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="table-main">
            <thead>
              <tr>
                <th>Date</th>
                <th>Beneficiary</th>
                <th>Amount</th>
                <th>Status</th>
                {activeTab === 'REJECTED' && <th>Reason</th>}
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {transfers.map(t => (
                <tr key={t.id} className="cursor-pointer hover:bg-gray-50" onClick={() => setSelectedTransfer(t)}>
                  <td className="text-xs">{new Date(t.created_at).toLocaleDateString()}</td>
                  <td>{t.beneficiary_name}</td>
                  <td className="font-semibold">{formatCurrency(t.amount)}</td>
                  <td><span className={getStatusBadgeClasses(t.status, false)}>{t.status}</span></td>
                  {activeTab === 'REJECTED' && (
                    <td className="max-w-xs">
                      <span className="text-xs text-red-600 truncate block" title={t.reject_reason}>
                        {t.reject_reason ? (t.reject_reason.length > 50 ? t.reject_reason.substring(0, 50) + '...' : t.reject_reason) : 'N/A'}
                      </span>
                    </td>
                  )}
                  <td><button className="btn-text text-xs">Open</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
