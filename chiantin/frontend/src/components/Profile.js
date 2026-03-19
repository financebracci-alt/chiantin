// Customer Profile Component
import React, { useState } from 'react';
import api from '../api';
import { useLanguage, useTheme } from '../contexts/AppContext';

export function CustomerProfile({ user }) {
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const [editing, setEditing] = useState(false);
  const [formData, setFormData] = useState({
    first_name: user?.first_name || '',
    last_name: user?.last_name || '',
    phone: user?.phone || ''
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const handleSave = async () => {
    setSaving(true);
    setError('');

    try {
      // Note: Update profile endpoint needs to be added to backend
      // await api.patch('/auth/profile', formData);
      alert(t('profileUpdateFeature'));
      setEditing(false);
    } catch (err) {
      setError(err.response?.data?.detail || t('failedToUpdateProfile'));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('profileSettings')}</h2>

      {/* Personal Information */}
      <div className={`card-enhanced p-6 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
        <div className="flex justify-between items-center mb-4">
          <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('personalInformation')}</h3>
          {!editing && (
            <button
              onClick={() => setEditing(true)}
              className="text-sm text-blue-600 hover:text-blue-700"
              data-testid="edit-profile-btn"
            >
              {t('edit')}
            </button>
          )}
        </div>

        {error && (
          <div className={`border rounded p-3 text-sm mb-4 ${isDark ? 'bg-red-900/30 border-red-800 text-red-300' : 'bg-red-50 border-red-200 text-red-800'}`}>
            {error}
          </div>
        )}

        {editing ? (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('firstName')}</label>
                <input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  className={`input-enhanced w-full ${isDark ? 'bg-gray-700 border-gray-600 text-white' : ''}`}
                  data-testid="edit-first-name"
                />
              </div>
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('lastName')}</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  className={`input-enhanced w-full ${isDark ? 'bg-gray-700 border-gray-600 text-white' : ''}`}
                  data-testid="edit-last-name"
                />
              </div>
            </div>
            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('phone')}</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className={`input-enhanced w-full ${isDark ? 'bg-gray-700 border-gray-600 text-white' : ''}`}
                data-testid="edit-phone"
              />
            </div>
            <div className={`flex justify-end space-x-3 pt-4 border-t ${isDark ? 'border-gray-700' : ''}`}>
              <button
                onClick={() => {
                  setEditing(false);
                  setFormData({
                    first_name: user?.first_name || '',
                    last_name: user?.last_name || '',
                    phone: user?.phone || ''
                  });
                }}
                className={`px-4 py-2 border rounded-lg ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 hover:bg-gray-50'}`}
              >
                {t('cancel')}
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="btn-primary btn-glow"
                data-testid="save-profile-btn"
              >
                {saving ? t('saving') : t('saveChanges')}
              </button>
            </div>
          </div>
        ) : (
          <dl className="grid grid-cols-2 gap-4">
            <div>
              <dt className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('firstName')}</dt>
              <dd className={`font-medium mt-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{user?.first_name}</dd>
            </div>
            <div>
              <dt className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('lastName')}</dt>
              <dd className={`font-medium mt-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{user?.last_name}</dd>
            </div>
            <div>
              <dt className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('email')}</dt>
              <dd className={`font-medium mt-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{user?.email}</dd>
            </div>
            <div>
              <dt className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('phone')}</dt>
              <dd className={`font-medium mt-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{user?.phone || t('notProvided')}</dd>
            </div>
            <div>
              <dt className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('accountCreated')}</dt>
              <dd className={`font-medium mt-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
              </dd>
            </div>
            <div>
              <dt className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('status')}</dt>
              <dd className="mt-1">
                <span className={`status-badge ${
                  user?.status === 'ACTIVE' 
                    ? isDark ? 'bg-green-900/30 text-green-400 border-green-700' : 'bg-green-100 text-green-800 border-green-300'
                    : user?.status === 'DISABLED'
                    ? isDark ? 'bg-red-900/30 text-red-400 border-red-700' : 'bg-red-100 text-red-800 border-red-300'
                    : isDark ? 'bg-yellow-900/30 text-yellow-400 border-yellow-700' : 'bg-yellow-100 text-yellow-800 border-yellow-300'
                }`}>
                  {user?.status}
                </span>
              </dd>
            </div>
          </dl>
        )}
      </div>

      {/* Account Summary */}
      <div className={`card-enhanced p-6 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('accountSummary')}</h3>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('role')}</dt>
            <dd className={`font-medium mt-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{user?.role}</dd>
          </div>
          <div>
            <dt className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('emailVerified')}</dt>
            <dd className={`font-medium mt-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{user?.email_verified ? t('yes') : t('no')}</dd>
          </div>
          <div>
            <dt className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('mfaEnabled')}</dt>
            <dd className={`font-medium mt-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>{user?.mfa_enabled ? t('yes') : t('no')}</dd>
          </div>
          <div>
            <dt className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('lastLogin')}</dt>
            <dd className={`font-medium mt-1 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {user?.last_login_at ? new Date(user.last_login_at).toLocaleString() : t('never')}
            </dd>
          </div>
        </dl>
      </div>
    </div>
  );
}
