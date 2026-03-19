// Scheduled Payments Component
import React, { useState, useEffect } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { useLanguage, useTheme } from '../contexts/AppContext';
import { formatCurrency } from '../utils/currency';

export function ScheduledPayments() {
  const toast = useToast();
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const [payments, setPayments] = useState([]);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({
    recipient_email: '',
    amount: '',
    reason: '',
    frequency: 'MONTHLY',
    start_date: new Date().toISOString().split('T')[0]
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchPayments();
  }, []);

  const fetchPayments = async () => {
    try {
      const response = await api.get('/scheduled-payments');
      setPayments(response.data);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      await api.post('/scheduled-payments', {
        ...formData,
        amount: parseInt(formData.amount)
      });
      toast.success(t('scheduledPaymentCreated'));
      setFormData({ recipient_email: '', amount: '', reason: '', frequency: 'MONTHLY', start_date: new Date().toISOString().split('T')[0] });
      setShowCreateForm(false);
      fetchPayments();
    } catch (err) {
      toast.error(err.response?.data?.detail || t('somethingWentWrong'));
    }
  };

  const handleCancel = async (id) => {
    if (!window.confirm(t('cancelScheduledPayment'))) return;
    try {
      await api.delete(`/scheduled-payments/${id}`);
      toast.success(t('scheduledPaymentCancelled'));
      fetchPayments();
    } catch (err) {
      toast.error(t('somethingWentWrong'));
    }
  };

  const getFrequencyLabel = (freq) => {
    const labels = {
      'DAILY': t('daily'),
      'WEEKLY': t('weekly'),
      'MONTHLY': t('monthly'),
      'YEARLY': t('yearly')
    };
    return labels[freq] || freq.toLowerCase();
  };

  return (
    <div className={`card p-6 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
      <div className="flex justify-between items-center mb-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('scheduledPayments')}</h3>
        <button onClick={() => setShowCreateForm(!showCreateForm)} className="btn-primary">
          {showCreateForm ? t('cancel') : t('schedulePayment')}
        </button>
      </div>

      {showCreateForm && (
        <form onSubmit={handleCreate} className={`mb-6 card p-4 space-y-4 ${isDark ? 'bg-gray-700 border-gray-600' : 'bg-gray-50'}`}>
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
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('amountCents')}</label>
            <input 
              type="number" 
              value={formData.amount} 
              onChange={(e) => setFormData({...formData, amount: e.target.value})} 
              required 
              className={`input-field ${isDark ? 'bg-gray-600 border-gray-500 text-white placeholder-gray-400' : ''}`}
              placeholder="10000"
            />
          </div>
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('reason')}</label>
            <input 
              type="text" 
              value={formData.reason} 
              onChange={(e) => setFormData({...formData, reason: e.target.value})} 
              required 
              className={`input-field ${isDark ? 'bg-gray-600 border-gray-500 text-white placeholder-gray-400' : ''}`}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('frequency')}</label>
              <select 
                value={formData.frequency} 
                onChange={(e) => setFormData({...formData, frequency: e.target.value})} 
                className={`input-field ${isDark ? 'bg-gray-600 border-gray-500 text-white' : ''}`}
              >
                <option value="DAILY">{t('daily')}</option>
                <option value="WEEKLY">{t('weekly')}</option>
                <option value="MONTHLY">{t('monthly')}</option>
                <option value="YEARLY">{t('yearly')}</option>
              </select>
            </div>
            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('startDate')}</label>
              <input 
                type="date" 
                value={formData.start_date} 
                onChange={(e) => setFormData({...formData, start_date: e.target.value})} 
                required 
                className={`input-field ${isDark ? 'bg-gray-600 border-gray-500 text-white' : ''}`}
              />
            </div>
          </div>
          <button type="submit" className="btn-primary w-full">{t('schedulePaymentBtn')}</button>
        </form>
      )}

      {loading ? (
        <div className="skeleton-card"></div>
      ) : payments.length === 0 ? (
        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('noScheduledPayments')}</p>
      ) : (
        <div className="space-y-3">
          {payments.map(p => (
            <div key={p.id} className={`border rounded p-4 ${isDark ? 'border-gray-600' : ''}`}>
              <div className="flex justify-between items-start">
                <div>
                  <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{p.reason}</p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('to')}: {p.recipient_email}</p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{formatCurrency(p.amount)} - {getFrequencyLabel(p.frequency)}</p>
                </div>
                <div className="text-right">
                  <span className={`badge ${p.active ? 'badge-success' : 'badge-gray'}`}>
                    {p.active ? t('active') : t('cancelled')}
                  </span>
                  {p.active && (
                    <button onClick={() => handleCancel(p.id)} className="block mt-2 text-xs text-red-600">{t('cancel')}</button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
