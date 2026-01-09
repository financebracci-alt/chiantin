// Security & Settings Components
import React, { useState, useEffect } from 'react';
import api from '../api';
import QRCode from 'qrcode.react';

export function MFAEnrollment({ onComplete }) {
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
      setError('Failed to setup MFA');
    }
  };

  const verifyAndEnable = async () => {
    if (token.length !== 6) {
      setError('Please enter a 6-digit code');
      return;
    }

    setLoading(true);
    setError('');
    try {
      await api.post('/auth/mfa/enable', { token });
      setStep('complete');
      setTimeout(() => onComplete && onComplete(), 2000);
    } catch (err) {
      setError(err.response?.data?.detail || 'Invalid code. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  if (step === 'complete') {
    return (
      <div className="text-center py-8">
        <div className="mx-auto w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mb-4">
          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <h3 className="text-xl font-semibold mb-2">MFA Enabled Successfully!</h3>
        <p className="text-gray-600">Your account is now protected with two-factor authentication.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-semibold mb-2">Enable Two-Factor Authentication</h3>
        <p className="text-sm text-gray-600">
          Scan this QR code with your authenticator app (Google Authenticator, Authy, etc.)
        </p>
      </div>

      {/* QR Code */}
      <div className="bg-white p-6 rounded-lg border text-center">
        {qrUri ? (
          <div className="inline-block p-4 bg-white">
            <QRCode value={qrUri} size={200} data-testid="mfa-qr-code" />
          </div>
        ) : (
          <div className="h-[200px] flex items-center justify-center">
            <div className="text-gray-400">Loading QR code...</div>
          </div>
        )}
        <div className="mt-4 text-sm text-gray-600">
          <p className="font-medium mb-1">Manual entry code:</p>
          <code className="bg-gray-100 px-3 py-1 rounded font-mono text-xs">{secret}</code>
        </div>
      </div>

      {/* Verification */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Enter the 6-digit code from your app
        </label>
        <input
          type="text"
          value={token}
          onChange={(e) => setToken(e.target.value.replace(/\D/g, '').slice(0, 6))}
          placeholder="000000"
          className="w-full px-4 py-3 border border-gray-300 rounded-md text-center text-2xl font-mono tracking-wider focus:outline-none focus:ring-2 focus:ring-blue-500"
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
        {loading ? 'Verifying...' : 'Verify & Enable MFA'}
      </button>
    </div>
  );
}

export function DeviceManagement() {
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
    if (!window.confirm('Are you sure you want to revoke this session?')) return;
    
    try {
      // await api.delete(`/auth/sessions/${sessionId}`);
      alert('Session revocation endpoint to be implemented');
      fetchSessions();
    } catch (err) {
      alert('Failed to revoke session');
    }
  };

  const formatDate = (dateStr) => {
    return new Date(dateStr).toLocaleString();
  };

  if (loading) {
    return <div className="text-center py-8">Loading devices...</div>;
  }

  return (
    <div className="space-y-4">
      <h3 className="text-lg font-semibold">Active Devices</h3>
      <div className="space-y-3">
        {sessions.map((session) => (
          <div
            key={session.id}
            className="bg-white border rounded-lg p-4"
            data-testid={`device-${session.id}`}
          >
            <div className="flex justify-between items-start">
              <div className="flex-1">
                <div className="flex items-center space-x-2">
                  <p className="font-medium">{session.device}</p>
                  {session.current && (
                    <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded">
                      Current
                    </span>
                  )}
                </div>
                <p className="text-sm text-gray-600 mt-1">IP: {session.ip}</p>
                <p className="text-xs text-gray-500 mt-1">
                  Last active: {formatDate(session.last_active)}
                </p>
              </div>
              {!session.current && (
                <button
                  onClick={() => revokeSession(session.id)}
                  className="text-sm text-red-600 hover:text-red-700"
                  data-testid={`revoke-${session.id}`}
                >
                  Revoke
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
      <p className="text-sm text-gray-600">
        Don't recognize a device? Revoke its access immediately.
      </p>
    </div>
  );
}

export function SecuritySettings({ user }) {
  const [showMFASetup, setShowMFASetup] = useState(false);
  const [showDevices, setShowDevices] = useState(false);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold mb-4">Security Settings</h2>
      </div>

      {/* MFA Status */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-start">
          <div>
            <h3 className="text-lg font-semibold mb-2">Two-Factor Authentication</h3>
            <p className="text-sm text-gray-600 mb-4">
              Add an extra layer of security to your account
            </p>
            <div className="flex items-center space-x-2">
              <span className={`text-sm px-3 py-1 rounded ${
                user?.mfa_enabled 
                  ? 'bg-green-100 text-green-800' 
                  : 'bg-gray-100 text-gray-800'
              }`}>
                {user?.mfa_enabled ? 'Enabled' : 'Not Enabled'}
              </span>
            </div>
          </div>
          {!user?.mfa_enabled && (
            <button
              onClick={() => setShowMFASetup(true)}
              className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              data-testid="enable-mfa-button"
            >
              Enable MFA
            </button>
          )}
        </div>

        {showMFASetup && !user?.mfa_enabled && (
          <div className="mt-6 pt-6 border-t">
            <MFAEnrollment onComplete={() => {
              setShowMFASetup(false);
              window.location.reload();
            }} />
          </div>
        )}
      </div>

      {/* Device Management */}
      <div className="bg-white rounded-lg shadow p-6">
        <div className="flex justify-between items-start mb-4">
          <div>
            <h3 className="text-lg font-semibold mb-2">Devices & Sessions</h3>
            <p className="text-sm text-gray-600">
              Manage devices that have access to your account
            </p>
          </div>
          <button
            onClick={() => setShowDevices(!showDevices)}
            className="text-sm text-blue-600 hover:text-blue-700"
            data-testid="toggle-devices-button"
          >
            {showDevices ? 'Hide' : 'Show'} Devices
          </button>
        </div>
        
        {showDevices && (
          <div className="pt-4 border-t">
            <DeviceManagement />
          </div>
        )}
      </div>

      {/* Password Change */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-2">Password</h3>
        <p className="text-sm text-gray-600 mb-4">
          Change your password regularly to keep your account secure
        </p>
        <button
          onClick={() => alert('Password change flow to be implemented')}
          className="px-4 py-2 border border-gray-300 rounded-md hover:bg-gray-50"
          data-testid="change-password-button"
        >
          Change Password
        </button>
      </div>

      {/* Security Activity */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold mb-2">Recent Security Activity</h3>
        <p className="text-sm text-gray-600 mb-4">
          Review recent security events on your account
        </p>
        <div className="space-y-2">
          <div className="text-sm p-3 bg-gray-50 rounded">
            <p className="font-medium">Login from new device</p>
            <p className="text-gray-600">Today at {new Date().toLocaleTimeString()}</p>
          </div>
        </div>
      </div>
    </div>
  );
}