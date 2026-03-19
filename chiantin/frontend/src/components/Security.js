// Security & Settings Components
import React, { useState, useEffect } from 'react';
import api from '../api';
import { QRCodeSVG } from 'qrcode.react';
import { useToast } from './Toast';
import { useLanguage, useTheme } from '../contexts/AppContext';

// Password Change Modal Component (defined first)
function PasswordChangeModal({ onClose }) {
  const toast = useToast();
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const [formData, setFormData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (formData.new_password !== formData.confirm_password) {
      setError(t('passwordsDoNotMatch'));
      return;
    }

    if (formData.new_password.length < 8) {
      setError(t('passwordMinLength'));
      return;
    }

    setLoading(true);
    try {
      await api.post('/auth/change-password', {
        current_password: formData.current_password,
        new_password: formData.new_password
      });
      toast.success(t('passwordChanged'));
      setTimeout(() => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        window.location.href = '/login';
      }, 2000);
    } catch (err) {
      setError(err.response?.data?.detail || t('somethingWentWrong'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className={`rounded-lg p-6 max-w-md w-full ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="flex justify-between items-center mb-4">
          <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('changePassword')}</h3>
          <button onClick={onClose} className={`${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-400 hover:text-gray-600'}`}>✕</button>
        </div>

        {error && (
          <div className={`border rounded p-3 text-sm mb-4 ${isDark ? 'bg-red-900/30 border-red-800 text-red-300' : 'bg-red-50 border-red-200 text-red-800'}`}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('currentPassword')}</label>
            <input
              type="password"
              value={formData.current_password}
              onChange={(e) => setFormData({...formData, current_password: e.target.value})}
              required
              className={`input-field ${isDark ? 'bg-gray-700 border-gray-600 text-white' : ''}`}
              data-testid="current-password"
            />
          </div>
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('newPassword')}</label>
            <input
              type="password"
              value={formData.new_password}
              onChange={(e) => setFormData({...formData, new_password: e.target.value})}
              required
              className={`input-field ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : ''}`}
              placeholder={t('minimum8Characters')}
              data-testid="new-password"
            />
          </div>
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('confirmNewPassword')}</label>
            <input
              type="password"
              value={formData.confirm_password}
              onChange={(e) => setFormData({...formData, confirm_password: e.target.value})}
              required
              className={`input-field ${isDark ? 'bg-gray-700 border-gray-600 text-white' : ''}`}
              data-testid="confirm-password"
            />
          </div>
          <div className="flex space-x-3 pt-4">
            <button type="button" onClick={onClose} className={`flex-1 btn-secondary ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : ''}`}>
              {t('cancel')}
            </button>
            <button type="submit" disabled={loading} className="flex-1 btn-primary" data-testid="submit-password-change">
              {loading ? t('changing') : t('changePassword')}
            </button>
          </div>
        </form>

        <p className={`text-xs mt-4 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
          {t('passwordLogoutNote')}
        </p>
      </div>
    </div>
  );
}

export function MFAEnrollment({ onComplete }) {
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const [step, setStep] = useState('setup'); // setup, verify, complete
  const [qrUri, setQrUri] = useState('');
  const [secret, setSecret] = useState('');
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setupMFA();
  }, []);

  const setupMFA = async () => {
    try {
      const response = await api.post('/auth/mfa/setup');
      setSecret(response.data.secret);
      setQrUri(response.data.qr_code_uri);
    } catch (err) {
      setError(t('failedToSetupMfa'));
    }
  };

  const verifyAndEnable = async () => {
    if (token.length !== 6) {
      setError(t('pleaseEnterSixDigit'));
      return;
    }

    setLoading(true);
    setError('');
    try {
      await api.post('/auth/mfa/enable', { token });
      setStep('complete');
      setTimeout(() => onComplete && onComplete(), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || t('invalidCodeTryAgain'));
    } finally {
      setLoading(false);
    }
  };

  if (step === 'complete') {
    return (
      <div className="text-center py-8">
        <div className={`mx-auto w-16 h-16 rounded-full flex items-center justify-center mb-4 ${isDark ? 'bg-green-900/30' : 'bg-green-100'}`}>
          <svg className={`w-8 h-8 ${isDark ? 'text-green-400' : 'text-green-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className={`text-xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('mfaEnabledSuccess')}</h3>
        <p className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('accountProtected2fa')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('enableTwoFactor')}</h3>
        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          {t('scanQrCode')}
        </p>
      </div>

      {/* QR Code */}
      <div className={`p-6 rounded-lg border text-center ${isDark ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-200'}`}>
        {qrUri ? (
          <div className="inline-block p-4 bg-white rounded">
            <QRCodeSVG value={qrUri} size={200} data-testid="mfa-qr-code" />
          </div>
        ) : (
          <div className="h-[200px] flex items-center justify-center">
            <div className={`${isDark ? 'text-gray-400' : 'text-gray-400'}`}>{t('loadingQrCode')}</div>
          </div>
        )}
        <div className={`mt-4 text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          <p className="font-medium mb-1">{t('manualEntryCode')}:</p>
          <code className={`px-3 py-1 rounded font-mono text-xs ${isDark ? 'bg-gray-600 text-gray-200' : 'bg-gray-100'}`}>{secret}</code>
        </div>
      </div>

      {/* Verification */}
      <div>
        <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
          {t('enterSixDigitCode')}
        </label>
        <input
          type="text"
          value={token}
          onChange={(e) => setToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
          placeholder="000000"
          className={`w-full px-4 py-3 border rounded-md text-center text-2xl font-mono tracking-wider focus:outline-none focus:ring-2 focus:ring-blue-500 ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'border-gray-300'}`}
          maxLength={6}
          data-testid="mfa-token-input"
        />
        {error && (
          <p className="mt-2 text-sm text-red-600" data-testid="mfa-error">{error}</p>
        )}
      </div>

      <button
        onClick={verifyAndEnable}
        disabled={loading || token.length !== 6}
        className="w-full py-3 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed font-medium"
        data-testid="mfa-verify-button"
      >
        {loading ? t('verifying') : t('verifyEnableMfa')}
      </button>
    </div>
  );
}

export function DeviceManagement() {
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchSessions();
  }, []);

  const fetchSessions = async () => {
    try {
      // Note: This endpoint needs to be implemented in backend
      // For now, showing mock data structure
      setSessions([
        {
          id: '1',
          device: 'Chrome on Windows',
          ip: '192.168.1.1',
          last_active: new Date().toISOString(),
          current: true
        }
      ]);
    } catch (err) {
      console.error('Failed to fetch sessions:', err);
    } finally {
      setLoading(false);
    }
  };

  const revokeSession = async (sessionId) => {
    if (!window.confirm(t('confirmRevokeSession'))) return;
    
    try {
      // await api.delete(`/auth/sessions/${sessionId}`);
      alert('Session revocation endpoint to be implemented');
      fetchSessions();
    } catch (err) {
      alert(t('somethingWentWrong'));
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString();
  };

  if (loading) {
    return <div className={`text-center py-8 ${isDark ? 'text-gray-400' : ''}`}>{t('loadingDevices')}</div>;
  }

  return (
    <div className="space-y-4">
      <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('activeDevices')}</h3>
      <div className="space-y-3">
        {sessions.map((session) => (
          <div
            key={session.id}
            className={`border rounded-lg p-4 ${isDark ? 'bg-gray-700 border-gray-600' : 'bg-white border-gray-200'}`}
            data-testid={`device-${session.id}`}
          >
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{session.device}</p>
                  {session.current && (
                    <span className={`text-xs px-2 py-1 rounded ${isDark ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-800'}`}>
                      {t('currentDevice')}
                    </span>
                  )}
                </div>
                <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>IP: {session.ip}</p>
                <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                  {t('lastActive')}: {formatDate(session.last_active)}
                </p>
              </div>
              {!session.current && (
                <button
                  onClick={() => revokeSession(session.id)}
                  className="text-sm text-red-600 hover:text-red-700"
                  data-testid={`revoke-${session.id}`}
                >
                  {t('revoke')}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
        {t('dontRecognizeDevice')}
      </p>
    </div>
  );
}

export function SecuritySettings({ user }) {
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const [showMFASetup, setShowMFASetup] = useState(false);
  const [showDevices, setShowDevices] = useState(false);
  const [showPasswordModal, setShowPasswordModal] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h2 className={`text-2xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('securitySettingsTitle')}</h2>
      </div>

      {/* MFA Status */}
      <div className={`rounded-lg shadow p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="flex justify-between items-start">
          <div>
            <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('twoFactorAuthentication')}</h3>
            <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('addExtraLayerSecurity')}
            </p>
            <div className="flex items-center space-x-2">
              <span className={`text-sm px-3 py-1 rounded ${
                user?.mfa_enabled 
                  ? isDark ? 'bg-green-900/30 text-green-400' : 'bg-green-100 text-green-800'
                  : isDark ? 'bg-gray-700 text-gray-300' : 'bg-gray-100 text-gray-800'
              }`}>
                {user?.mfa_enabled ? t('twoFaEnabled') : t('twoFaNotEnabled')}
              </span>
            </div>
          </div>
          {!user?.mfa_enabled && (
            <button
              onClick={() => setShowMFASetup(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              data-testid="enable-mfa-button"
            >
              {t('enableMfa')}
            </button>
          )}
        </div>

        {showMFASetup && !user?.mfa_enabled && (
          <div className={`mt-6 pt-6 border-t ${isDark ? 'border-gray-700' : ''}`}>
            <MFAEnrollment onComplete={() => {
              setShowMFASetup(false);
              window.location.reload();
            }} />
          </div>
        )}
      </div>

      {/* Device Management */}
      <div className={`rounded-lg shadow p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('devicesAndSessions')}</h3>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('manageDevicesAccess')}
            </p>
          </div>
          <button
            onClick={() => setShowDevices(!showDevices)}
            className="text-sm text-blue-600 hover:text-blue-700"
            data-testid="toggle-devices-button"
          >
            {showDevices ? t('hideDevices') : t('showDevices')}
          </button>
        </div>
        
        {showDevices && (
          <div className={`pt-4 border-t ${isDark ? 'border-gray-700' : ''}`}>
            <DeviceManagement />
          </div>
        )}
      </div>

      {/* Password Change */}
      <div className={`rounded-lg shadow p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('changePasswordTitle')}</h3>
        <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          {t('passwordDescription')}
        </p>
        <button
          onClick={() => setShowPasswordModal(true)}
          className={`px-4 py-2 border rounded-md ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 hover:bg-gray-50'}`}
          data-testid="change-password-button"
        >
          {t('changePassword')}
        </button>
      </div>

      {/* Change Password Modal */}
      {showPasswordModal && <PasswordChangeModal onClose={() => setShowPasswordModal(false)} />}

      {/* Security Activity */}
      <div className={`rounded-lg shadow p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <h3 className={`text-lg font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('recentSecurityActivity')}</h3>
        <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          {t('reviewSecurityEvents')}
        </p>
        <div className="space-y-2">
          <div className={`text-sm p-3 rounded ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
            <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('loginFromNewDevice')}</p>
            <p className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('today')} {new Date().toLocaleTimeString()}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
