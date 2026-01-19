// Transfers Page - P2P, Beneficiaries, Scheduled Payments
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { P2PTransferForm } from './P2PTransfer';
import { BeneficiaryManager } from './Beneficiaries';
import { ScheduledPayments } from './ScheduledPayments';
import { NotificationBell } from './Notifications';
import { APP_NAME } from '../config';
import { useLanguage, useTheme } from '../contexts/AppContext';

export function TransfersPage({ user, logout }) {
  const navigate = useNavigate();
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header */}
      <header className={`h-16 px-4 sm:px-6 flex items-center justify-between border-b ${isDark ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-200'}`}>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/dashboard')} className={`${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`} data-testid="transfers-back-btn">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className={`logo-text ${isDark ? 'text-white' : ''}`} data-testid="logo">{APP_NAME}</span>
        </div>
        <div className="flex items-center gap-4">
          {/* Language Toggle */}
          <button
            onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
            className={`flex items-center space-x-1 px-2 py-1.5 rounded-md text-sm font-medium transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
            title={language === 'en' ? 'Switch to Italian' : 'Passa a Inglese'}
            data-testid="transfers-language-toggle"
          >
            <span className="text-base">{language === 'en' ? '🇬🇧' : '🇮🇹'}</span>
            <span className="hidden sm:inline">{language === 'en' ? 'EN' : 'IT'}</span>
          </button>
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-md transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            data-testid="transfers-theme-toggle"
          >
            {isDark ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
          <NotificationBell userId={user?.id} />
        </div>
      </header>

      {/* Content */}
      <div className="container-main py-8">
        <h2 className={`text-2xl font-semibold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('transfersAndPayments')}</h2>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* P2P Transfer */}
          <div>
            <div className={`section-header ${isDark ? 'text-gray-300' : ''}`}>{t('sendMoney')}</div>
            <P2PTransferForm onSuccess={() => navigate('/dashboard')} />
          </div>

          {/* Beneficiaries */}
          <div>
            <div className={`section-header ${isDark ? 'text-gray-300' : ''}`}>{t('savedRecipients')}</div>
            <BeneficiaryManager />
          </div>

          {/* Scheduled Payments - Full Width */}
          <div className="lg:col-span-2">
            <div className={`section-header ${isDark ? 'text-gray-300' : ''}`}>{t('scheduledPayments')}</div>
            <ScheduledPayments />
          </div>
        </div>
      </div>
    </div>
  );
}
