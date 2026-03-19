// KYC Review Status Page - "Application Under Review"
import React from 'react';
import { useNavigate } from 'react-router-dom';
import { NotificationBell } from './Notifications';
import { useToast } from './Toast';
import api from '../api';
import { useLanguage, useTheme } from '../contexts/AppContext';

// Styled Logo Component - displays "ecomm" with "bx" in red
const StyledLogo = ({ isDark = false }) => (
  <span className={isDark ? 'text-white' : 'text-gray-900'}>
    ecomm<span className="text-red-500">bx</span>
  </span>
);

export function KYCReviewPage({ user, logout }) {
  const navigate = useNavigate();
  const toast = useToast();
  const { t } = useLanguage();
  const { isDark } = useTheme();

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      <header className={`h-16 border-b ${isDark ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-200'}`}>
        <div className="max-w-[1200px] mx-auto px-4 sm:px-6 h-full flex items-center justify-between">
          <h1 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}><StyledLogo isDark={isDark} /></h1>
          <div className="flex items-center space-x-4">
            <NotificationBell />
            <button onClick={logout} className={`text-sm ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}>{t('logout')}</button>
          </div>
        </div>
      </header>

      <div className="container-main py-16">
        <div className="max-w-2xl mx-auto text-center">
          {/* Illustration */}
          <div className="mb-8">
            <div className={`w-32 h-32 rounded-full flex items-center justify-center mx-auto ${isDark ? 'bg-yellow-900/30' : 'bg-yellow-100'}`}>
              <svg className="w-16 h-16 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
          </div>

          <h1 className={`text-3xl font-bold mb-4 ${isDark ? 'text-white' : ''}`}>{t('kycApplicationBeingReviewed')}</h1>
          <p className={`mb-8 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
            {t('kycThankYouSubmitting')}
          </p>

          <div className={`card p-6 text-left mb-8 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
            <h3 className={`font-semibold mb-4 ${isDark ? 'text-white' : ''}`}>{t('kycWhatHappensNext')}</h3>
            <ul className="space-y-3">
              <li className="flex items-start space-x-3">
                <span className="text-red-600 mt-1">1.</span>
                <div>
                  <p className={`font-medium ${isDark ? 'text-gray-200' : ''}`}>{t('kycReviewProcess')}</p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('kycReviewProcessDesc')}</p>
                </div>
              </li>
              <li className="flex items-start space-x-3">
                <span className="text-red-600 mt-1">2.</span>
                <div>
                  <p className={`font-medium ${isDark ? 'text-gray-200' : ''}`}>{t('kycAccountActivation')}</p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('kycAccountActivationDesc')}</p>
                </div>
              </li>
              <li className="flex items-start space-x-3">
                <span className="text-red-600 mt-1">3.</span>
                <div>
                  <p className={`font-medium ${isDark ? 'text-gray-200' : ''}`}>{t('kycFullBankingAccess')}</p>
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('kycFullBankingAccessDesc')}</p>
                </div>
              </li>
            </ul>
          </div>

          <button 
            onClick={async () => {
              try {
                const response = await api.get('/kyc/application');
                const status = response.data?.status;
                
                if (status === 'APPROVED') {
                  // Refresh the page to go to dashboard
                  window.location.href = '/dashboard';
                } else {
                  // Translate the status
                  const statusLabels = {
                    DRAFT: t('draft'),
                    SUBMITTED: t('submitted'),
                    UNDER_REVIEW: t('underReview'),
                    NEEDS_MORE_INFO: t('needsMoreInfo'),
                    APPROVED: t('approved'),
                    REJECTED: t('rejected')
                  };
                  const translatedStatus = statusLabels[status] || status;
                  toast.info(`${t('kycStatus')}: ${translatedStatus}`);
                }
              } catch (err) {
                toast.error(t('kycCheckStatusFailed'));
              }
            }}
            className="btn-secondary"
          >
            {t('kycCheckStatus')}
          </button>
        </div>
      </div>
    </div>
  );
}

