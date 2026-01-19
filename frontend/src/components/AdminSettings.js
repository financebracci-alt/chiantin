// Admin Settings Component with Language and Theme
import React, { useState } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { useLanguage, useTheme } from '../contexts/AppContext';

export function AdminSettings() {
  const toast = useToast();
  const { language, setLanguage, t } = useLanguage();
  const { theme, setTheme, isDark } = useTheme();
  const [settings, setSettings] = useState({
    maxDailyTopUp: 100000,  // €1000 in cents
    maxTransferAmount: 50000,  // €500
    requireMFAForLargeTransfers: true,
    autoApproveKYCEnabled: false
  });

  const handleSave = () => {
    toast.success(t('changesSaved'));
  };

  return (
    <div className={`space-y-6 ${isDark ? 'text-gray-100' : ''}`}>
      <div>
        <h2 className={`text-2xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('settings')}</h2>
        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Configure platform settings, language, and theme</p>
      </div>

      {/* Language & Theme Settings */}
      <div className={`card p-6 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : ''}`}>{t('languageSettings')}</h3>
        <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
          {t('selectLanguage')}
        </p>
        
        <div className="flex gap-3 mb-6">
          <button
            onClick={() => setLanguage('en')}
            className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
              language === 'en'
                ? 'bg-red-600 text-white shadow-lg'
                : isDark 
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600 border border-gray-600' 
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-100'
            }`}
          >
            <span className="text-sm font-bold">EN</span>
            {t('english')}
          </button>
          <button
            onClick={() => setLanguage('it')}
            className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
              language === 'it'
                ? 'bg-red-600 text-white shadow-lg'
                : isDark 
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600 border border-gray-600' 
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-100'
            }`}
          >
            <span className="text-xl">🇮🇹</span>
            {t('italian')}
          </button>
        </div>

        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : ''}`}>{t('themeSettings')}</h3>
        <div className="flex gap-3">
          <button
            onClick={() => setTheme('light')}
            className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
              theme === 'light'
                ? 'bg-red-600 text-white shadow-lg'
                : isDark 
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600 border border-gray-600' 
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-100'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            {t('lightMode')}
          </button>
          <button
            onClick={() => setTheme('dark')}
            className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all flex items-center justify-center gap-2 ${
              theme === 'dark'
                ? 'bg-red-600 text-white shadow-lg'
                : isDark 
                  ? 'bg-gray-700 text-gray-300 hover:bg-gray-600 border border-gray-600' 
                  : 'bg-white text-gray-700 border border-gray-300 hover:bg-gray-100'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
            {t('darkMode')}
          </button>
        </div>
      </div>

      {/* Transaction Limits */}
      <div className={`card p-6 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : ''}`}>Transaction Limits</h3>
        <div className="space-y-4">
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              Max Daily Top-Up (cents)
            </label>
            <input
              type="number"
              value={settings.maxDailyTopUp}
              onChange={(e) => setSettings({...settings, maxDailyTopUp: parseInt(e.target.value)})}
              className={`input-field ${isDark ? 'bg-gray-700 border-gray-600 text-white' : ''}`}
            />
            <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>= €{(settings.maxDailyTopUp / 100).toFixed(2)}</p>
          </div>
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              Max P2P Transfer Amount (cents)
            </label>
            <input
              type="number"
              value={settings.maxTransferAmount}
              onChange={(e) => setSettings({...settings, maxTransferAmount: parseInt(e.target.value)})}
              className={`input-field ${isDark ? 'bg-gray-700 border-gray-600 text-white' : ''}`}
            />
            <p className={`text-xs mt-1 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>= €{(settings.maxTransferAmount / 100).toFixed(2)}</p>
          </div>
        </div>
      </div>

      {/* Security Settings */}
      <div className={`card p-6 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : ''}`}>Security Rules</h3>
        <div className="space-y-3">
          <label className="flex items-center space-x-3">
            <input
              type="checkbox"
              checked={settings.requireMFAForLargeTransfers}
              onChange={(e) => setSettings({...settings, requireMFAForLargeTransfers: e.target.checked})}
              className="rounded border-gray-300"
            />
            <div>
              <p className={`text-sm font-medium ${isDark ? 'text-gray-200' : ''}`}>Require MFA for Large Transfers</p>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-600'}`}>Transfers above €500 require MFA verification</p>
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
              <p className={`text-sm font-medium ${isDark ? 'text-gray-200' : ''}`}>Auto-Approve KYC (Sandbox Only)</p>
              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-600'}`}>Automatically approve KYC applications for testing</p>
            </div>
          </label>
        </div>
      </div>

      {/* Platform Info */}
      <div className={`card p-6 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
        <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : ''}`}>Platform Information</h3>
        <dl className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <dt className={isDark ? 'text-gray-500' : 'text-gray-600'}>Environment</dt>
            <dd className={`font-medium ${isDark ? 'text-gray-200' : ''}`}>Sandbox</dd>
          </div>
          <div>
            <dt className={isDark ? 'text-gray-500' : 'text-gray-600'}>API Version</dt>
            <dd className={`font-medium ${isDark ? 'text-gray-200' : ''}`}>v1.0.0</dd>
          </div>
          <div>
            <dt className={isDark ? 'text-gray-500' : 'text-gray-600'}>Database</dt>
            <dd className={`font-medium ${isDark ? 'text-gray-200' : ''}`}>MongoDB</dd>
          </div>
          <div>
            <dt className={isDark ? 'text-gray-500' : 'text-gray-600'}>Ledger Mode</dt>
            <dd className={`font-medium ${isDark ? 'text-gray-200' : ''}`}>Sandbox (Double-Entry)</dd>
          </div>
        </dl>
      </div>

      <button onClick={handleSave} className="btn-primary">
        {t('save')} {t('settings')}
      </button>
    </div>
  );
}
