// Admin Components for KYC, Transactions, and Tools
import React, { useState, useEffect } from 'react';
import api from '../api';
import { StatusBadge } from './KYC';

export function AdminKYCReview() {
  const [applications, setApplications] = useState([]);
  const [selectedApp, setSelectedApp] = useState(null);
  const [loading, setLoading] = useState(true);
  const [reviewData, setReviewData] = useState({
    status: '',
    review_notes: '',
    rejection_reason: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchApplications();
  }, []);

  const fetchApplications = async () => {
    try {
      const response = await api.get('/admin/kyc/pending');
      setApplications(response.data);
    } catch (err) {
      console.error('Failed to fetch KYC applications:', err);
      setError('Failed to load applications');
    } finally {
      setLoading(false);
    }
  };

  const handleReview = async () => {
    if (!reviewData.status) {
      setError('Please select a status');
      return;
    }

    if (reviewData.status === 'REJECTED' && !reviewData.rejection_reason) {
      setError('Please provide a rejection reason');
      return;
    }

    setSubmitting(true);
    setError('');

    try {
      await api.post(`/admin/kyc/${selectedApp.id}/review`, reviewData);
      alert('KYC review submitted successfully');
      setSelectedApp(null);
      setReviewData({ status: '', review_notes: '', rejection_reason: '' });
      fetchApplications();
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to submit review');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'N/A';
    return new Date(dateStr).toLocaleString();
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
            <h3 className="text-lg font-semibold">Pending KYC Applications</h3>
            <p className="text-sm text-gray-600 mt-1">{applications.length} application(s)</p>
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
                        onClick={() => alert('Document viewer to be implemented')}
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

            {/* Review Actions */}
            <div className="bg-white rounded-lg shadow p-6">
              <h3 className="text-lg font-semibold mb-4">Review Application</h3>
              <div className="space-y-4">
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
                      setReviewData({ status: '', review_notes: '', rejection_reason: '' });
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
    </div>
  );
}