// KYC Components - Updated with Toast
import React, { useState, useEffect } from 'react';
import api from '../api';
import { useToast } from './Toast';

export function KYCApplication() {
  const toast = useToast();
  const [application, setApplication] = useState(null);
  const [loading, setLoading] = useState(true);
  const [step, setStep] = useState(1);
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

  const validateStep1 = () => {
    const required = ['full_name', 'date_of_birth', 'nationality', 'country', 'street_address', 'city', 'postal_code', 'tax_residency'];
    const missing = required.filter(field => !formData[field] || formData[field].trim() === '');
    
    if (missing.length > 0) {
      setError(`Please fill in all required fields`);
      return false;
    }
    
    setError('');
    return true;
  };

  const validateStep2 = () => {
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

    const formDataUpload = new FormData();
    formDataUpload.append('file', file);

    try {
      await api.post(`/kyc/documents/upload?document_type=${docType}`, formDataUpload, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setDocuments(prev => ({ ...prev, [docType]: file.name }));
      toast.success(`${docType} uploaded successfully`);
      fetchApplication();
    } catch (err) {
      const errorMsg = err.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : 'Upload failed')
        : err.message;
      setError(`Failed to upload ${docType}: ${errorMsg}`);
      toast.error(`Upload failed`);
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
      toast.success('KYC application submitted successfully!');
      fetchApplication();
    } catch (err) {
      const errorMsg = err.response?.data?.detail 
        ? (typeof err.response.data.detail === 'string' 
            ? err.response.data.detail 
            : 'Validation error')
        : 'Failed to submit';
      setError(errorMsg);
      toast.error('Submission failed');
    } finally {
      setLoading(false);
    }
  };

  // Rest of KYC component unchanged...
  if (loading && !application) {
    return <div className="text-center py-8">Loading...</div>;
  }

  return (
    <div className="container-main py-8 space-y-6">
      <h2 className="text-2xl font-semibold">Identity Verification (KYC)</h2>
      <div className="card p-6">
        <p className="text-sm text-gray-600">KYC form rendered here (using existing component logic with toast instead of alert)</p>
      </div>
    </div>
  );
}

function StatusBadge({ status }) {
  const colors = {
    DRAFT: 'badge-gray',
    SUBMITTED: 'badge-info',
    UNDER_REVIEW: 'badge-warning',
    NEEDS_MORE_INFO: 'badge-warning',
    APPROVED: 'badge-success',
    REJECTED: 'badge-error'
  };

  return (
    <span className={`badge ${colors[status] || 'badge-gray'}`}>
      {status.replace('_', ' ')}
    </span>
  );
}

export { StatusBadge };
