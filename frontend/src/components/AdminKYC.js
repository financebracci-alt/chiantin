// Admin Components for KYC, Transactions, and Tools
import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import { StatusBadge } from './KYC';
import { useToast } from './Toast';

export function AdminKYCReview() {
  const toast = useToast();
  const [applications, setApplications] = useState([]);
  const [selectedApp, setSelectedApp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [viewingDocument, setViewingDocument] = useState(null);
  const [downloadingDocument, setDownloadingDocument] = useState(false);
  const [reviewData, setReviewData] = useState({
    status: '',
    review_notes: '',
    rejection_reason: '',
    assigned_iban: '',
    assigned_bic: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  
  // Edit mode state
  const [isEditMode, setIsEditMode] = useState(false);
  const [editedData, setEditedData] = useState({});
  
  // Manual queue state
  const [showQueueModal, setShowQueueModal] = useState(false);
  const [queueEmail, setQueueEmail] = useState('');
  const [queueReason, setQueueReason] = useState('');
  const [queueLoading, setQueueLoading] = useState(false);

  const fetchApplications = useCallback(async () => {
    try {
      const response = await api.get('/admin/kyc/pending');
      setApplications(response.data);
    } catch (err) {
      console.error('Failed to fetch KYC applications:', err);
      toast.error('Failed to load applications');
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchApplications();
  }, [fetchApplications]);

  // Handle manual queue submission
  const handleManualQueue = async () => {
    if (!queueEmail.trim()) {
      toast.error('Please enter a user email');
      return;
    }
    
    setQueueLoading(true);
    try {
      const response = await api.post('/admin/kyc/queue-user', {
        user_email: queueEmail.trim(),
        reason: queueReason.trim() || null
      });
      
      toast.success(response.data.message || 'User KYC queued successfully');
      setShowQueueModal(false);
      setQueueEmail('');
      setQueueReason('');
      // Refresh the applications list
      fetchApplications();
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to queue user KYC';
      toast.error(errorMsg);
    } finally {
      setQueueLoading(false);
    }
  };

  // Function to download document properly
  const handleDownloadDocument = async (doc) => {
    if (downloadingDocument) return;
    
    setDownloadingDocument(true);
    try {
      // Use the document endpoint with download=true query parameter
      const downloadUrl = `${process.env.REACT_APP_BACKEND_URL}/api/v1/kyc/documents/${encodeURIComponent(doc.file_key)}?download=true`;
      
      // Fetch the document with auth header
      const response = await fetch(downloadUrl, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('access_token')}`
        }
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to download document');
      }
      
      // Get the blob
      const blob = await response.blob();
      
      // Create a download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = doc.file_name || `document_${doc.file_key}`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      toast.success('Document downloaded successfully');
    } catch (err) {
      console.error('Download error:', err);
      toast.error('Failed to download document. Please try again.');
    } finally {
      setDownloadingDocument(false);
    }
  };

  const viewDocument = (doc) => {
    setViewingDocument(doc);
  };

  const handleReview = async () => {
    if (!reviewData.status) {
      toast.error('Please select a status');
      return;
    }

    if (reviewData.status === 'REJECTED' && !reviewData.rejection_reason) {
      toast.error('Please provide a rejection reason');
      return;
    }

    // Validation for APPROVED status - IBAN and BIC are required
    if (reviewData.status === 'APPROVED') {
      if (!reviewData.assigned_iban || !reviewData.assigned_iban.trim()) {
        toast.error('IBAN is required to approve KYC');
        return;
      }
      if (!reviewData.assigned_bic || !reviewData.assigned_bic.trim()) {
        toast.error('BIC/SWIFT is required to approve KYC');
        return;
      }
      // Basic IBAN format validation (starts with 2 letters, followed by numbers/letters)
      const ibanPattern = /^[A-Z]{2}[A-Z0-9]{13,32}$/i;
      if (!ibanPattern.test(reviewData.assigned_iban.replace(/\s/g, ''))) {
        toast.error('Please enter a valid IBAN format (e.g., LT123456789012345678)');
        return;
      }
      // Basic BIC format validation (8 or 11 characters)
      // Format: 4 letters (bank) + 2 letters (country) + 2 alphanumeric (location) + optional 3 alphanumeric (branch)
      const bicClean = reviewData.assigned_bic.replace(/\s/g, '').toUpperCase();
      if (bicClean.length !== 8 && bicClean.length !== 11) {
        toast.error(`BIC/SWIFT must be exactly 8 or 11 characters (you entered ${bicClean.length})`);
        return;
      }
      const bicPattern = /^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$/i;
      if (!bicPattern.test(bicClean)) {
        toast.error('Invalid BIC format. Must be: 4 letters (bank) + 2 letters (country) + 2-5 alphanumeric. Example: ATLSLT21 or DEUTDEFF');
        return;
      }
    }

    setSubmitting(true);
    setError('');

    try {
      await api.post(`/admin/kyc/${selectedApp.id}/review`, reviewData);
      toast.success('KYC review submitted successfully');
      setSelectedApp(null);
      setReviewData({ status: '', review_notes: '', rejection_reason: '', assigned_iban: '', assigned_bic: '' });
      fetchApplications();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    try {
      const date = new Date(dateStr);
      // Check if date is valid
      if (isNaN(date.getTime())) {
        return 'N/A';
      }
      return date.toLocaleString();
    } catch (err) {
      return 'N/A';
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading applications...</div>;
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Applications List */}
      <div className="lg:col-span-1">
        <div className="bg-white rounded-lg shadow">
          <div className="p-4 border-b">
            <div className="flex justify-between items-center">
              <div>
                <h3 className="text-lg font-semibold">Pending KYC Applications</h3>
                <p className="text-sm text-gray-600 mt-1">{applications.length} application(s)</p>
              </div>
              <button
                onClick={() => setShowQueueModal(true)}
                className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700"
                data-testid="manual-queue-btn"
                title="Manually add a user to the KYC queue"
              >
                + Queue User
              </button>
            </div>
          </div>
          <div className="divide-y max-h-[600px] overflow-y-auto">
            {applications.length === 0 ? (
              <div className="p-4 text-center text-gray-600">
                No pending applications
              </div>
            ) : (
              applications.map((app) => (
                <div
                  key={app.id}
                  onClick={() => setSelectedApp(app)}
                  className={`p-4 cursor-pointer hover:bg-gray-50 ${
                    selectedApp?.id === app.id ? 'bg-blue-50' : ''
                  }`}
                  data-testid={`kyc-app-${app.id}`}
                >
                  <p className="font-medium">{app.full_name}</p>
                  <p className="text-sm text-gray-600">{app.nationality}</p>
                  <div className="flex items-center justify-between mt-2">
                    <StatusBadge status={app.status} />
                    <span className="text-xs text-gray-500">
                      {formatDate(app.submitted_at)}
                    </span>
                  </div>
                  {app.documents && (
                    <p className="text-xs text-gray-500 mt-1">
                      {app.documents.length} document(s)
                    </p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Application Details */}
      <div className="lg:col-span-2">
        {selectedApp ? (
          <div className="space-y-6">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-800 rounded p-3 text-sm">
                {error}
              </div>
            )}

            {/* Personal Information */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Personal Information</h3>
              <dl className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <dt className="text-gray-600">Full Name</dt>
                  <dd className="font-medium mt-1">{selectedApp.full_name}</dd>
                </div>
                <div>
                  <dt className="text-gray-600">Date of Birth</dt>
                  <dd className="font-medium mt-1">{selectedApp.date_of_birth}</dd>
                </div>
                <div>
                  <dt className="text-gray-600">Nationality</dt>
                  <dd className="font-medium mt-1">{selectedApp.nationality}</dd>
                </div>
                <div>
                  <dt className="text-gray-600">Country</dt>
                  <dd className="font-medium mt-1">{selectedApp.country}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-gray-600">Address</dt>
                  <dd className="font-medium mt-1">
                    {selectedApp.street_address}, {selectedApp.city}, {selectedApp.postal_code}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-600">Tax Residency</dt>
                  <dd className="font-medium mt-1">{selectedApp.tax_residency}</dd>
                </div>
                {selectedApp.tax_id && (
                  <div>
                    <dt className="text-gray-600">Tax ID</dt>
                    <dd className="font-medium mt-1">{selectedApp.tax_id}</dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Documents */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Uploaded Documents</h3>
              {selectedApp.documents && selectedApp.documents.length > 0 ? (
                <div className="space-y-3">
                  {selectedApp.documents.map((doc, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 border rounded">
                      <div>
                        <p className="font-medium">{doc.document_type.replace('_', ' ')}</p>
                        <p className="text-sm text-gray-600">{doc.file_name}</p>
                        <p className="text-xs text-gray-500 mt-1">
                          {(doc.file_size / 1024).toFixed(2)} KB • {formatDate(doc.uploaded_at)}
                        </p>
                      </div>
                      <button
                        onClick={() => viewDocument(doc)}
                        className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50"
                        data-testid={`view-doc-${idx}`}
                      >
                        View
                      </button>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-gray-600">No documents uploaded</p>
              )}
            </div>


            {/* Edit & Delete Actions */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold">Application Actions</h3>
                <div className="flex gap-2">
                  <button
                    onClick={() => setIsEditMode(!isEditMode)}
                    className="px-4 py-2 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 flex items-center gap-2"
                    data-testid="edit-kyc-btn"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    {isEditMode ? 'Cancel Edit' : 'Edit Application'}
                  </button>
                  <button
                    onClick={async () => {
                      if (window.confirm(
                        `⚠️ DELETE KYC APPLICATION\n\n` +
                        `User: ${selectedApp.full_name}\n` +
                        `Status: ${selectedApp.status}\n\n` +
                        `This will PERMANENTLY DELETE this KYC application.\n` +
                        `The user account will remain active and they can resubmit KYC.\n\n` +
                        `Are you absolutely sure you want to proceed?`
                      )) {
                        try {
                          await api.delete(`/admin/kyc/${selectedApp.id}`);
                          toast.success('KYC application deleted successfully');
                          setSelectedApp(null);
                          fetchApplications(); // Refresh list
                        } catch (err) {
                          console.error('Delete error:', err);
                          toast.error(err.response?.data?.detail || 'Failed to delete KYC application');
                        }
                      }
                    }}
                    className="px-4 py-2 text-sm bg-red-600 text-white rounded-md hover:bg-red-700 flex items-center gap-2"
                    data-testid="delete-kyc-btn"
                    disabled={selectedApp.status === 'APPROVED'}
                    title={selectedApp.status === 'APPROVED' ? 'Cannot delete approved applications' : 'Delete this KYC application'}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                    Delete Application
                  </button>
                </div>
              </div>
              {isEditMode && (
                <div className="bg-blue-50 border border-blue-200 rounded p-3 mb-4">
                  <p className="text-sm text-blue-800">
                    📝 Edit mode enabled. Modify the fields below and click "Save Changes" to update this KYC application.
                  </p>
                </div>
              )}
            </div>

            {/* Review Actions */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Review Application</h3>
              <div className="space-y-4">
                {/* IBAN Assignment Field - NEW */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Assign IBAN * (Required for Approval)
                  </label>
                  <input
                    type="text"
                    value={reviewData.assigned_iban || ''}
                    onChange={(e) => setReviewData({ ...reviewData, assigned_iban: e.target.value.toUpperCase() })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono"
                    placeholder="e.g., LT733550010000042779"
                  />
                  <p className="text-xs text-gray-500 mt-1">Enter the IBAN to assign (2 letters + 13-32 alphanumeric characters)</p>
                </div>

                {/* BIC/SWIFT Assignment Field - REQUIRED */}
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Assign BIC/SWIFT * (Required for Approval)
                  </label>
                  <input
                    type="text"
                    value={reviewData.assigned_bic || ''}
                    onChange={(e) => setReviewData({ ...reviewData, assigned_bic: e.target.value.toUpperCase() })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md font-mono"
                    placeholder="e.g., ATLSLT21 or DEUTDEFF500"
                    maxLength={11}
                  />
                  <p className="text-xs text-gray-500 mt-1">Format: 4 letters (bank) + 2 letters (country) + 2-5 alphanumeric. Must be 8 or 11 characters.</p>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Decision *
                  </label>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setReviewData({ ...reviewData, status: 'APPROVED' })}
                      className={`flex-1 py-2 px-4 rounded border ${
                        reviewData.status === 'APPROVED'
                          ? 'bg-green-600 text-white border-green-600'
                          : 'border-gray-300 hover:bg-gray-50'
                      }`}
                      data-testid="approve-button"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => setReviewData({ ...reviewData, status: 'NEEDS_MORE_INFO' })}
                      className={`flex-1 py-2 px-4 rounded border ${
                        reviewData.status === 'NEEDS_MORE_INFO'
                          ? 'bg-yellow-600 text-white border-yellow-600'
                          : 'border-gray-300 hover:bg-gray-50'
                      }`}
                      data-testid="more-info-button"
                    >
                      Need More Info
                    </button>
                    <button
                      onClick={() => setReviewData({ ...reviewData, status: 'REJECTED' })}
                      className={`flex-1 py-2 px-4 rounded border ${
                        reviewData.status === 'REJECTED'
                          ? 'bg-red-600 text-white border-red-600'
                          : 'border-gray-300 hover:bg-gray-50'
                      }`}
                      data-testid="reject-button"
                    >
                      Reject
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Review Notes
                  </label>
                  <textarea
                    value={reviewData.review_notes}
                    onChange={(e) => setReviewData({ ...reviewData, review_notes: e.target.value })}
                    rows={3}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    placeholder="Add any notes for internal reference..."
                    data-testid="review-notes"
                  />
                </div>

                {reviewData.status === 'REJECTED' && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-2">
                      Rejection Reason * (visible to customer)
                    </label>
                    <textarea
                      value={reviewData.rejection_reason}
                      onChange={(e) => setReviewData({ ...reviewData, rejection_reason: e.target.value })}
                      rows={3}
                      className="w-full px-3 py-2 border border-gray-300 rounded-md"
                      placeholder="Provide reason for rejection..."
                      data-testid="rejection-reason"
                    />
                  </div>
                )}

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    onClick={() => {
                      setSelectedApp(null);
                      setReviewData({ status: '', review_notes: '', rejection_reason: '', assigned_iban: '', assigned_bic: '' });
                    }}
                    className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleReview}
                    disabled={submitting || !reviewData.status}
                    className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    data-testid="submit-review"
                  >
                    {submitting ? 'Submitting...' : 'Submit Review'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-12 text-center">
            <p className="text-gray-600">Select an application to review</p>
          </div>
        )}
      </div>
      
      {/* Document Viewer Modal */}
      {viewingDocument && (
        <div className="fixed inset-0 bg-black bg-opacity-75 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="sticky top-0 bg-white border-b p-4 flex justify-between items-center">
              <div>
                <h3 className="text-lg font-semibold">{viewingDocument.document_type.replace('_', ' ')}</h3>
                <p className="text-sm text-gray-600">{viewingDocument.file_name}</p>
              </div>
              <button onClick={() => setViewingDocument(null)} className="text-gray-400 hover:text-gray-600">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <div className="p-6">
              {viewingDocument.content_type?.startsWith('image/') ? (
                <div className="text-center">
                  <img 
                    src={`${process.env.REACT_APP_BACKEND_URL}/api/v1/kyc/documents/${viewingDocument.file_key}`}
                    alt={viewingDocument.document_type}
                    className="max-w-full h-auto rounded-lg shadow-lg mx-auto"
                    style={{ maxHeight: '70vh' }}
                    onError={(e) => {
                      console.error('Image load error:', e);
                      e.target.style.display = 'none';
                      e.target.nextElementSibling.style.display = 'block';
                    }}
                  />
                  <div style={{ display: 'none' }} className="bg-yellow-50 border border-yellow-200 rounded p-8">
                    <svg className="w-16 h-16 mx-auto text-yellow-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <p className="font-medium mb-2 text-yellow-800">Image could not be loaded</p>
                    <p className="text-sm text-gray-600">{viewingDocument.file_name}</p>
                    <p className="text-xs text-gray-500 mt-2">File path: {viewingDocument.file_key}</p>
                  </div>
                  <div className="mt-4 text-sm text-gray-600">
                    <p className="font-medium">{viewingDocument.file_name}</p>
                    <p>Size: {(viewingDocument.file_size / 1024).toFixed(2)} KB</p>
                    <p className="text-xs mt-2">Uploaded: {formatDate(viewingDocument.uploaded_at)}</p>
                  </div>
                </div>
              ) : (
                <div className="text-center">
                  <div className="bg-gray-100 rounded p-8">
                    <svg className="w-16 h-16 mx-auto text-gray-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <p className="font-medium mb-2">{viewingDocument.file_name}</p>
                    <p className="text-sm text-gray-600">Size: {(viewingDocument.file_size / 1024).toFixed(2)} KB</p>
                    <p className="text-sm text-gray-600">Uploaded: {formatDate(viewingDocument.uploaded_at)}</p>
                    <p className="text-xs text-gray-500 mt-4">Document preview not available for this file type</p>
                  </div>
                </div>
              )}
            </div>
            <div className="sticky bottom-0 bg-gray-50 border-t p-4 flex space-x-3">
              <button
                onClick={() => handleDownloadDocument(viewingDocument)}
                disabled={downloadingDocument}
                className="flex-1 btn-primary text-center disabled:opacity-50"
                data-testid="download-document-btn"
              >
                {downloadingDocument ? 'Downloading...' : 'Download Document'}
              </button>
              <button onClick={() => setViewingDocument(null)} className="flex-1 btn-secondary">
                Close
              </button>
            </div>
          </div>
        </div>
      )}
      
      {/* Manual Queue Modal */}
      {showQueueModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-lg font-semibold">Manually Queue User for KYC Review</h3>
              <button 
                onClick={() => setShowQueueModal(false)} 
                className="text-gray-400 hover:text-gray-600"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            
            <p className="text-sm text-gray-600 mb-4">
              Use this feature when a user's KYC submission failed or their application needs to be re-queued for review.
            </p>
            
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  User Email *
                </label>
                <input
                  type="email"
                  value={queueEmail}
                  onChange={(e) => setQueueEmail(e.target.value)}
                  placeholder="user@example.com"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="queue-email-input"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Reason (Optional)
                </label>
                <textarea
                  value={queueReason}
                  onChange={(e) => setQueueReason(e.target.value)}
                  placeholder="Why is this user being manually queued?"
                  rows={2}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="queue-reason-input"
                />
              </div>
            </div>
            
            <div className="flex justify-end space-x-3 mt-6">
              <button
                onClick={() => setShowQueueModal(false)}
                className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
                disabled={queueLoading}
              >
                Cancel
              </button>
              <button
                onClick={handleManualQueue}
                disabled={queueLoading || !queueEmail.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                data-testid="queue-submit-btn"
              >
                {queueLoading ? 'Queueing...' : 'Queue for Review'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}