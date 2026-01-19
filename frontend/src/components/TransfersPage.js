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
  const { t } = useLanguage();
  const { isDark } = useTheme();

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header */}
      <header className={`h-16 px-4 sm:px-6 flex items-center justify-between border-b ${isDark ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-200'}`}>
        <div className="flex items-center space-x-4">
          <button onClick={() => navigate('/dashboard')} className={`${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'}`}>
            ← {t('back')}
          </button>
          <h1 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{APP_NAME}</h1>
        </div>
        <div className="flex items-center space-x-4">
          <NotificationBell />
          <button onClick={logout} className={`text-sm ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'}`}>
            {t('logout')}
          </button>
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
