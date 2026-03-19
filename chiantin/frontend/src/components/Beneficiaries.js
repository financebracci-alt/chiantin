// Beneficiary Management Component
import React, { useState, useEffect } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { useLanguage, useTheme } from '../contexts/AppContext';

export function BeneficiaryManager() {
  const toast = useToast();
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [showAddForm, setShowAddForm] = useState(false);
  const [formData, setFormData] = useState({
    recipient_email: '',
    recipient_name: '',
    nickname: ''
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchBeneficiaries();
  }, []);

  const fetchBeneficiaries = async () => {
    try {
      const response = await api.get('/beneficiaries');
      setBeneficiaries(response.data);
    } catch (err) {
      console.error('Failed to fetch beneficiaries:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleAdd = async (e) => {
    e.preventDefault();
    try {
      await api.post('/beneficiaries', formData);
      toast.success(t('beneficiaryAdded'));
      setFormData({ recipient_email: '', recipient_name: '', nickname: '' });
      setShowAddForm(false);
      fetchBeneficiaries();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('failedToAddBeneficiary'));
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm(t('removeThisBeneficiary'))) return;
    try {
      await api.delete(`/beneficiaries/${id}`);
      toast.success(t('beneficiaryRemoved'));
      fetchBeneficiaries();
    } catch (err) {
      toast.error(t('failedToRemoveBeneficiary'));
    }
  };

  return (
    <div className={`card p-6 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
      <div className="flex justify-between items-center mb-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('savedRecipients')}</h3>
        <button onClick={() => setShowAddForm(!showAddForm)} className="btn-primary">
          {showAddForm ? t('cancel') : t('addRecipient')}
        </button>
      </div>

      {showAddForm && (
        <form onSubmit={handleAdd} className={`mb-6 card p-4 space-y-4 ${isDark ? 'bg-gray-700 border-gray-600' : 'bg-gray-50'}`}>
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('recipientEmail')}</label>
            <input 
              type="email" 
              value={formData.recipient_email} 
              onChange={(e) => setFormData({...formData, recipient_email: e.target.value})} 
              required 
              className={`input-field ${isDark ? 'bg-gray-600 border-gray-500 text-white placeholder-gray-400' : ''}`}
            />
          </div>
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('recipientName')}</label>
            <input 
              type="text" 
              value={formData.recipient_name} 
              onChange={(e) => setFormData({...formData, recipient_name: e.target.value})} 
              required 
              className={`input-field ${isDark ? 'bg-gray-600 border-gray-500 text-white placeholder-gray-400' : ''}`}
            />
          </div>
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('nicknameOptional')}</label>
            <input 
              type="text" 
              value={formData.nickname} 
              onChange={(e) => setFormData({...formData, nickname: e.target.value})} 
              className={`input-field ${isDark ? 'bg-gray-600 border-gray-500 text-white placeholder-gray-400' : ''}`}
              placeholder={t('nicknamePlaceholder')}
            />
          </div>
          <button type="submit" className="btn-primary w-full">{t('saveRecipient')}</button>
        </form>
      )}

      {loading ? (
        <div className="skeleton-card"></div>
      ) : beneficiaries.length === 0 ? (
        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('noSavedRecipientsYet')}</p>
      ) : (
        <div className="space-y-2">
          {beneficiaries.map(b => (
            <div key={b.id} className={`flex justify-between items-center p-3 border rounded ${isDark ? 'border-gray-600 hover:bg-gray-700' : 'hover:bg-gray-50'}`}>
              <div>
                <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{b.nickname || b.recipient_name}</p>
                <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{b.recipient_email}</p>
              </div>
              <button onClick={() => handleDelete(b.id)} className="text-sm text-red-600 hover:text-red-700">{t('remove')}</button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
