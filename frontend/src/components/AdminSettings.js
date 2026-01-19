// Admin Settings Component
import React, { useState } from 'react';
import api from '../api';
import { useToast } from './Toast';

export function AdminSettings() {
  const toast = useToast();
  const [settings, setSettings] = useState({
    maxDailyTopUp: 100000,  // €1000 in cents
    maxTransferAmount: 50000,  // €500
    requireMFAForLargeTransfers: true,
    autoApproveKYCEnabled: false
  });

  const handleSave = () => {
    toast.success('Settings saved (mock - backend implementation pending)');
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold mb-2">System Settings</h2>
        <p className="text-sm text-gray-600">Configure platform limits and security rules</p>
      </div>

      {/* Transaction Limits */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4">Transaction Limits</h3>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max Daily Top-Up (cents)
            </label>
            <input
              type="number"
              value={settings.maxDailyTopUp}
              onChange={(e) => setSettings({...settings, maxDailyTopUp: parseInt(e.target.value)})}
              className="input-field"
            />
            <p className="text-xs text-gray-500 mt-1">= €{(settings.maxDailyTopUp / 100).toFixed(2)}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Max P2P Transfer Amount (cents)
            </label>
            <input
              type="number"
              value={settings.maxTransferAmount}
              onChange={(e) => setSettings({...settings, maxTransferAmount: parseInt(e.target.value)})}
              className="input-field"
            />
            <p className="text-xs text-gray-500 mt-1">= €{(settings.maxTransferAmount / 100).toFixed(2)}</p>
          </div>
        </div>
      </div>

      {/* Security Settings */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4">Security Rules</h3>
        <div className="space-y-3">
          <label className="flex items-center space-x-3">
            <input
              type="checkbox"
              checked={settings.requireMFAForLargeTransfers}
              onChange={(e) => setSettings({...settings, requireMFAForLargeTransfers: e.target.checked})}
              className="rounded border-gray-300"
            />
            <div>
              <p className="text-sm font-medium">Require MFA for Large Transfers</p>
              <p className="text-xs text-gray-600">Transfers above €500 require MFA verification</p>
            </div>
          </label>
          <label className="flex items-center space-x-3">
            <input
              type="checkbox"
              checked={settings.autoApproveKYCEnabled}
              onChange={(e) => setSettings({...settings, autoApproveKYCEnabled: e.target.checked})}
              className="rounded border-gray-300"
            />
            <div>
              <p className="text-sm font-medium">Auto-Approve KYC (Sandbox Only)</p>
              <p className="text-xs text-gray-600">Automatically approve KYC applications for testing</p>
            </div>
          </label>
        </div>
      </div>

      {/* Platform Info */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold mb-4">Platform Information</h3>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className="text-gray-600">Environment</dt>
            <dd className="font-medium">Sandbox</dd>
          </div>
          <div>
            <dt className="text-gray-600">API Version</dt>
            <dd className="font-medium">v1.0.0</dd>
          </div>
          <div>
            <dt className="text-gray-600">Database</dt>
            <dd className="font-medium">MongoDB</dd>
          </div>
          <div>
            <dt className="text-gray-600">Ledger Mode</dt>
            <dd className="font-medium">Sandbox (Double-Entry)</dd>
          </div>
        </dl>
      </div>

      <button onClick={handleSave} className="btn-primary">
        Save Settings
      </button>
    </div>
  );
}
