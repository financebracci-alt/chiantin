// KYC Components
import React, { useState, useEffect } from 'react';
import api from '../api';

export function KYCApplication() {
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(1); // 1: Personal Info, 2: Documents, 3: Review & Submit
  const [formData, setFormData] = useState({
    full_name: '',
    date_of_birth: '',
    nationality: '',
    street_address: '',
    city: '',
    postal_code: '',
    country: '',
    tax_residency: '',
    tax_id: '',
    terms_accepted: false,
    privacy_accepted: false
  });
  const [documents, setDocuments] = useState({
    PASSPORT: null,
    PROOF_OF_ADDRESS: null,
    SELFIE: null
  });
  const [uploadingDoc, setUploadingDoc] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchApplication();
  }, []);

  const fetchApplication = async () => {
    try {
      const response = await api.get('/kyc/application');
      setApplication(response.data);
      if (response.data && response.data.full_name) {
        setFormData({
          full_name: response.data.full_name || '',
          date_of_birth: response.data.date_of_birth || '',
          nationality: response.data.nationality || '',
          street_address: response.data.street_address || '',
          city: response.data.city || '',
          postal_code: response.data.postal_code || '',
          country: response.data.country || '',
          tax_residency: response.data.tax_residency || '',
          tax_id: response.data.tax_id || '',
          terms_accepted: response.data.terms_accepted || false,
          privacy_accepted: response.data.privacy_accepted || false
        });
      }
    } catch (err) {
      console.error('Failed to fetch KYC application:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    const { name, value, type, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value
    }));
  };

  const handleFileUpload = async (docType, file) => {
    if (!file) return;

    setUploadingDoc(docType);
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      await api.post(`/kyc/documents/upload?document_type=${docType}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setDocuments(prev => ({ ...prev, [docType]: file.name }));
      fetchApplication(); // Refresh to get updated documents
    } catch (err) {
      const errorMsg = err.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : JSON.stringify(err.response.data.detail))
        : err.message;
      setError(`Failed to upload ${docType}: ${errorMsg}`);
    } finally {
      setUploadingDoc(null);
    }
  };

  const handleSubmit = async () => {
    if (!formData.terms_accepted || !formData.privacy_accepted) {
      setError('Please accept terms and privacy policy');
      return;
    }

    setLoading(true);
    setError('');

    try {
      await api.post('/kyc/submit', formData);
      alert('KYC application submitted successfully! Our team will review it shortly.');
      fetchApplication();
    } catch (err) {
      const errorMsg = err.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : 'Validation error - please check all fields')
        : 'Failed to submit KYC application';
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !application) {
    return <div className="text-center py-8">Loading...</div>;
  }

  // Show status if already submitted
  if (application?.status && application.status !== 'DRAFT') {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">KYC Application Status</h3>
          <div className="space-y-4">
            <div>
              <span className="text-sm text-gray-600">Status:</span>
              <div className="mt-1">
                <StatusBadge status={application.status} />
              </div>
            </div>
            {application.status === 'NEEDS_MORE_INFO' && application.review_notes && (
              <div className="p-4 bg-yellow-50 border border-yellow-200 rounded">
                <p className="text-sm font-medium text-yellow-800">Action Required</p>
                <p className="text-sm text-yellow-700 mt-1">{application.review_notes}</p>
              </div>
            )}
            {application.status === 'APPROVED' && (
              <div className="p-4 bg-green-50 border border-green-200 rounded">
                <p className="text-sm font-medium text-green-800">✓ Your identity has been verified</p>
                <p className="text-sm text-green-700 mt-1">You now have full access to all banking features.</p>
              </div>
            )}
            {application.status === 'REJECTED' && application.rejection_reason && (
              <div className="p-4 bg-red-50 border border-red-200 rounded">
                <p className="text-sm font-medium text-red-800">Application Rejected</p>
                <p className="text-sm text-red-700 mt-1">{application.rejection_reason}</p>
              </div>
            )}
            {application.submitted_at && (
              <div>
                <span className="text-sm text-gray-600">Submitted:</span>
                <p className="text-sm">{new Date(application.submitted_at).toLocaleString()}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Progress Steps */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-center">
          {[1, 2, 3].map((s) => (
            <div key={s} className="flex items-center">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                step >= s ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-600'
              }`}>
                {s}
              </div>
              {s < 3 && (
                <div className={`h-1 w-24 ${
                  step > s ? 'bg-blue-600' : 'bg-gray-200'
                }`} />
              )}
            </div>
          ))}
        </div>
        <div className="flex justify-between mt-2">
          <span className="text-xs text-gray-600">Personal Info</span>
          <span className="text-xs text-gray-600">Documents</span>
          <span className="text-xs text-gray-600">Review</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-800 rounded p-3 text-sm">
          {error}
        </div>
      )}

      {/* Step 1: Personal Information */}
      {step === 1 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Personal Information</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Legal Name</label>
              <input
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="kyc-full-name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Date of Birth</label>
              <input
                type="date"
                name="date_of_birth"
                value={formData.date_of_birth}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="kyc-dob"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Nationality</label>
              <input
                type="text"
                name="nationality"
                value={formData.nationality}
                onChange={handleInputChange}
                placeholder="e.g., DE"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="kyc-nationality"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Country</label>
              <input
                type="text"
                name="country"
                value={formData.country}
                onChange={handleInputChange}
                placeholder="e.g., Germany"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="kyc-country"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Street Address</label>
              <input
                type="text"
                name="street_address"
                value={formData.street_address}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="kyc-address"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">City</label>
              <input
                type="text"
                name="city"
                value={formData.city}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="kyc-city"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Postal Code</label>
              <input
                type="text"
                name="postal_code"
                value={formData.postal_code}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="kyc-postal"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tax Residency</label>
              <input
                type="text"
                name="tax_residency"
                value={formData.tax_residency}
                onChange={handleInputChange}
                placeholder="e.g., DE"
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="kyc-tax-residency"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Tax ID (Optional)</label>
              <input
                type="text"
                name="tax_id"
                value={formData.tax_id}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md"
                data-testid="kyc-tax-id"
              />
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <button
              onClick={() => setStep(2)}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              data-testid="kyc-next-step1"
            >
              Next: Upload Documents
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Document Upload */}
      {step === 2 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Upload Documents</h3>
          <div className="space-y-4">
            {['PASSPORT', 'PROOF_OF_ADDRESS', 'SELFIE'].map((docType) => (
              <DocumentUpload
                key={docType}
                docType={docType}
                uploaded={documents[docType] || (application?.documents?.find(d => d.document_type === docType)?.file_name)}
                onUpload={(file) => handleFileUpload(docType, file)}
                uploading={uploadingDoc === docType}
              />
            ))}
          </div>
          <div className="mt-6 flex justify-between">
            <button
              onClick={() => setStep(1)}
              className="px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={() => setStep(3)}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              data-testid="kyc-next-step2"
            >
              Next: Review & Submit
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Review & Submit */}
      {step === 3 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">Review & Submit</h3>
          <div className="space-y-6">
            <div>
              <h4 className="font-medium mb-2">Personal Information</h4>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <dt className="text-gray-600">Name:</dt>
                <dd>{formData.full_name}</dd>
                <dt className="text-gray-600">Date of Birth:</dt>
                <dd>{formData.date_of_birth}</dd>
                <dt className="text-gray-600">Address:</dt>
                <dd>{formData.street_address}, {formData.city}, {formData.postal_code}</dd>
              </dl>
            </div>
            
            <div>
              <h4 className="font-medium mb-2">Consents</h4>
              <div className="space-y-2">
                <label className="flex items-start space-x-2">
                  <input
                    type="checkbox"
                    name="terms_accepted"
                    checked={formData.terms_accepted}
                    onChange={handleInputChange}
                    className="mt-1"
                    data-testid="kyc-terms"
                  />
                  <span className="text-sm">I accept the terms and conditions</span>
                </label>
                <label className="flex items-start space-x-2">
                  <input
                    type="checkbox"
                    name="privacy_accepted"
                    checked={formData.privacy_accepted}
                    onChange={handleInputChange}
                    className="mt-1"
                    data-testid="kyc-privacy"
                  />
                  <span className="text-sm">I accept the privacy policy</span>
                </label>
              </div>
            </div>
          </div>
          
          <div className="mt-6 flex justify-between">
            <button
              onClick={() => setStep(2)}
              className="px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !formData.terms_accepted || !formData.privacy_accepted}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              data-testid="kyc-submit"
            >
              {loading ? 'Submitting...' : 'Submit Application'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function DocumentUpload({ docType, uploaded, onUpload, uploading }) {
  const labels = {
    PASSPORT: 'Passport or ID Card',
    PROOF_OF_ADDRESS: 'Proof of Address',
    SELFIE: 'Selfie Photo'
  };

  return (
    <div className="border rounded-lg p-4" data-testid={`upload-${docType}`}>
      <div className="flex justify-between items-center">
        <div>
          <p className="font-medium">{labels[docType]}</p>
          {uploaded && (
            <p className="text-sm text-green-600 mt-1">✓ {uploaded}</p>
          )}
        </div>
        <label className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer">
          {uploading ? 'Uploading...' : uploaded ? 'Replace' : 'Upload'}
          <input
            type="file"
            onChange={(e) => onUpload(e.target.files[0])}
            className="hidden"
            accept="image/*,.pdf"
            disabled={uploading}
          />
        </label>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = {
    DRAFT: 'bg-gray-100 text-gray-800',
    SUBMITTED: 'bg-blue-100 text-blue-800',
    UNDER_REVIEW: 'bg-yellow-100 text-yellow-800',
    NEEDS_MORE_INFO: 'bg-orange-100 text-orange-800',
    APPROVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800'
  };

  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${colors[status] || colors.DRAFT}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

export { StatusBadge };