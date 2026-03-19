// KYC Components
import React, { useState, useEffect } from 'react';
import api from '../api';
import { useLanguage, useTheme } from '../contexts/AppContext';

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
  const { t } = useLanguage();
  const { isDark } = useTheme();

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

  const validateStep1 = () => {
    const required = ['full_name', 'date_of_birth', 'nationality', 'country', 'street_address', 'city', 'postal_code', 'tax_residency'];
    const missing = required.filter(field => !formData[field] || formData[field].trim() === '');
    
    if (missing.length > 0) {
      setError(`Please fill in all required fields: ${missing.join(', ').replace(/_/g, ' ')}`);
      return false;
    }
    
    setError('');
    return true;
  };

  const validateStep2 = () => {
    // Check if at least passport and proof of address are uploaded
    const hasPassport = application?.documents?.find(d => d.document_type === 'PASSPORT') || documents.PASSPORT;
    const hasProofOfAddress = application?.documents?.find(d => d.document_type === 'PROOF_OF_ADDRESS') || documents.PROOF_OF_ADDRESS;
    
    if (!hasPassport) {
      setError('Please upload your Passport or ID Card');
      return false;
    }
    
    if (!hasProofOfAddress) {
      setError('Please upload Proof of Address');
      return false;
    }
    
    setError('');
    return true;
  };

  const goToStep2 = () => {
    if (validateStep1()) {
      setStep(2);
    }
  };

  const goToStep3 = () => {
    if (validateStep2()) {
      setStep(3);
    }
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
      alert(t('kycSubmittedSuccess'));
      fetchApplication();
    } catch (err) {
      const errorMsg = err.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : t('kycValidationError'))
        : t('kycSubmitFailed');
      setError(errorMsg);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !application) {
    return <div className="text-center py-8">{t('loading')}</div>;
  }

  // Show status if already submitted (but NOT for DRAFT, REJECTED, or NEEDS_MORE_INFO - those can edit)
  if (application?.status && !['DRAFT', 'NEEDS_MORE_INFO', 'REJECTED'].includes(application.status)) {
    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4">{t('kycApplicationStatus')}</h3>
          <div className="space-y-4">
            <div>
              <span className="text-sm text-gray-600">{t('status')}:</span>
              <div className="mt-1">
                <StatusBadge status={application.status} t={t} />
              </div>
            </div>
            {application.status === 'APPROVED' && (
              <div className="p-4 bg-green-50 border border-green-200 rounded">
                <p className="text-sm font-medium text-green-800">✓ {t('kycIdentityVerified')}</p>
                <p className="text-sm text-green-700 mt-1">{t('kycFullAccess')}</p>
              </div>
            )}
            {application.status === 'SUBMITTED' && (
              <div className="p-4 bg-blue-50 border border-blue-200 rounded">
                <p className="text-sm font-medium text-blue-800">{t('underReview')}</p>
                <p className="text-sm text-blue-700 mt-1">{t('ourTeamReviewing')}</p>
              </div>
            )}
            {application.submitted_at && (
              <div>
                <span className="text-sm text-gray-600">{t('submitted')}:</span>
                <p className="text-sm">{(() => {
                  try {
                    const date = new Date(application.submitted_at);
                    if (isNaN(date.getTime())) return 'Date unavailable';
                    return date.toLocaleString(undefined, { 
                      year: 'numeric',
                      month: '2-digit', 
                      day: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                      hour12: true
                    });
                  } catch (e) {
                    return 'Date unavailable';
                  }
                })()}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  }

  // For REJECTED or NEEDS_MORE_INFO, show message AND form below
  const showRejectionMessage = application?.status === 'REJECTED' || application?.status === 'NEEDS_MORE_INFO';

  return (
    <div className="space-y-6">
      {showRejectionMessage && (
        <div className={`card p-6 ${
          application.status === 'REJECTED' ? 'border-l-4 border-red-500' : 'border-l-4 border-yellow-500'
        }`}>
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0">
              {application.status === 'REJECTED' ? (
                <div className="h-10 w-10 rounded-full bg-red-100 flex items-center justify-center">
                  <span className="text-red-600 text-xl">✗</span>
                </div>
              ) : (
                <div className="h-10 w-10 rounded-full bg-yellow-100 flex items-center justify-center">
                  <span className="text-yellow-600 text-xl">!</span>
                </div>
              )}
            </div>
            <div className="flex-1">
              <h4 className="font-semibold text-lg">
                {application.status === 'REJECTED' ? 'Application Rejected' : 'More Information Required'}
              </h4>
              <p className="text-sm text-gray-700 mt-2">
                {application.rejection_reason || application.review_notes}
              </p>
              <p className="text-sm text-red-600 font-medium mt-3">
                👇 Update your information below and resubmit your application
              </p>
            </div>
          </div>
        </div>
      )}
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
          <span className="text-xs text-gray-600">{t('kycPersonalInfo')}</span>
          <span className="text-xs text-gray-600">{t('kycDocuments')}</span>
          <span className="text-xs text-gray-600">{t('kycReview')}</span>
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
          <h3 className="text-lg font-semibold mb-4 text-gray-900">{t('kycPersonalInformation')}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('kycFullLegalName')}</label>
              <input
                type="text"
                name="full_name"
                value={formData.full_name}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white"
                data-testid="kyc-full-name"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('kycDateOfBirth')}</label>
              <input
                type="date"
                name="date_of_birth"
                value={formData.date_of_birth}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white"
                data-testid="kyc-dob"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('kycNationality')}</label>
              <input
                type="text"
                name="nationality"
                value={formData.nationality}
                onChange={handleInputChange}
                placeholder="e.g., DE"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white placeholder-gray-400"
                data-testid="kyc-nationality"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('kycCountry')}</label>
              <input
                type="text"
                name="country"
                value={formData.country}
                onChange={handleInputChange}
                placeholder="e.g., Germany"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white placeholder-gray-400"
                data-testid="kyc-country"
              />
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('kycStreetAddress')}</label>
              <input
                type="text"
                name="street_address"
                value={formData.street_address}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white"
                data-testid="kyc-address"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('kycCity')}</label>
              <input
                type="text"
                name="city"
                value={formData.city}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white"
                data-testid="kyc-city"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('kycPostalCode')}</label>
              <input
                type="text"
                name="postal_code"
                value={formData.postal_code}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white"
                data-testid="kyc-postal"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('kycTaxResidency')}</label>
              <input
                type="text"
                name="tax_residency"
                value={formData.tax_residency}
                onChange={handleInputChange}
                placeholder="e.g., DE"
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white placeholder-gray-400"
                data-testid="kyc-tax-residency"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">{t('kycTaxIdOptional')}</label>
              <input
                type="text"
                name="tax_id"
                value={formData.tax_id}
                onChange={handleInputChange}
                className="w-full px-3 py-2 border border-gray-300 rounded-md text-gray-900 bg-white"
                data-testid="kyc-tax-id"
              />
            </div>
          </div>
          <div className="mt-6 flex justify-end">
            <button
              type="button"
              onClick={goToStep2}
              className="btn-primary btn-glow"
              data-testid="kyc-next-step1"
            >
              {t('kycNextUploadDocuments')}
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Document Upload */}
      {step === 2 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900">{t('kycUploadDocuments')}</h3>
          <div className="space-y-4">
            {['PASSPORT', 'PROOF_OF_ADDRESS', 'SELFIE'].map((docType) => (
              <DocumentUpload
                key={docType}
                docType={docType}
                uploaded={documents[docType] || (application?.documents?.find(d => d.document_type === docType)?.file_name)}
                onUpload={(file) => handleFileUpload(docType, file)}
                uploading={uploadingDoc === docType}
                t={t}
              />
            ))}
          </div>
          <div className="mt-6 flex justify-between">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="px-6 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-gray-900"
            >
              {t('back')}
            </button>
            <button
              type="button"
              onClick={goToStep3}
              className="btn-primary btn-glow"
              data-testid="kyc-next-step2"
            >
              {t('kycNextReviewSubmit')}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Review & Submit */}
      {step === 3 && (
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold mb-4 text-gray-900">{t('kycReviewSubmit')}</h3>
          <div className="space-y-6">
            <div>
              <h4 className="font-medium mb-2 text-gray-900">{t('kycPersonalInformation')}</h4>
              <dl className="grid grid-cols-2 gap-2 text-sm">
                <dt className="text-gray-600">{t('name')}:</dt>
                <dd className="text-gray-900">{formData.full_name}</dd>
                <dt className="text-gray-600">{t('kycDateOfBirth')}:</dt>
                <dd className="text-gray-900">{formData.date_of_birth}</dd>
                <dt className="text-gray-600">{t('address')}:</dt>
                <dd className="text-gray-900">{formData.street_address}, {formData.city}, {formData.postal_code}</dd>
              </dl>
            </div>
            
            <div>
              <h4 className="font-medium mb-2 text-gray-900">{t('kycConsents')}</h4>
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
                  <span className="text-sm text-gray-900">{t('kycAcceptTerms')}</span>
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
                  <span className="text-sm text-gray-900">{t('kycAcceptPrivacy')}</span>
                </label>
              </div>
            </div>
          </div>
          
          <div className="mt-6 flex justify-between">
            <button
              onClick={() => setStep(2)}
              className="px-6 py-2 border border-gray-300 rounded-md hover:bg-gray-50 text-gray-900"
            >
              {t('back')}
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading || !formData.terms_accepted || !formData.privacy_accepted}
              className="px-6 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
              data-testid="kyc-submit"
            >
              {loading ? t('submitting') : t('kycSubmitApplication')}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function DocumentUpload({ docType, uploaded, onUpload, uploading, t }) {
  const labels = {
    PASSPORT: t ? t('kycPassportId') : 'Passport or ID Card',
    PROOF_OF_ADDRESS: t ? t('kycProofOfAddress') : 'Proof of Address',
    SELFIE: t ? t('kycSelfiePhoto') : 'Selfie Photo'
  };

  return (
    <div className="border rounded-lg p-4 bg-white" data-testid={`upload-${docType}`}>
      <div className="flex justify-between items-center">
        <div>
          <p className="font-medium text-gray-900">{labels[docType]}</p>
          {uploaded && (
            <p className="text-sm text-green-600 mt-1">✓ {uploaded}</p>
          )}
        </div>
        <label className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 cursor-pointer">
          {uploading ? (t ? t('uploading') : 'Uploading...') : uploaded ? (t ? t('replace') : 'Replace') : (t ? t('upload') : 'Upload')}
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

function StatusBadge({ status, t }) {
  const colors = {
    DRAFT: 'bg-gray-100 text-gray-800',
    SUBMITTED: 'bg-blue-100 text-blue-800',
    UNDER_REVIEW: 'bg-yellow-100 text-yellow-800',
    NEEDS_MORE_INFO: 'bg-orange-100 text-orange-800',
    APPROVED: 'bg-green-100 text-green-800',
    REJECTED: 'bg-red-100 text-red-800'
  };

  const labels = {
    DRAFT: t ? t('draft') : 'Draft',
    SUBMITTED: t ? t('submitted') : 'Submitted',
    UNDER_REVIEW: t ? t('underReview') : 'Under Review',
    NEEDS_MORE_INFO: t ? t('needsMoreInfo') : 'Needs More Info',
    APPROVED: t ? t('approved') : 'Approved',
    REJECTED: t ? t('rejected') : 'Rejected'
  };

  return (
    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${colors[status] || colors.DRAFT}`}>
      {labels[status] || status.replace('_', ' ')}
    </span>
  );
}

export { StatusBadge };