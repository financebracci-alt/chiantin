// Card Ordering Modal - Step by Step (Matching Reference Design)
import React, { useState, useEffect } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { useLanguage, useTheme } from '../contexts/AppContext';

export function CardOrderingModal({ onClose, onSuccess }) {
  const toast = useToast();
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const [step, setStep] = useState(1);
  const [accounts, setAccounts] = useState([]);
  const [selectedCardType, setSelectedCardType] = useState(null);
  const [selectedAccount, setSelectedAccount] = useState(null);

  useEffect(() => {
    api.get('/accounts').then(r => setAccounts(r.data)).catch(() => {});
  }, []);

  const handleSubmit = async () => {
    try {
      await api.post('/card-requests', {
        account_id: selectedAccount,
        card_type: selectedCardType
      });
      setStep(3);
      toast.success(t('cardOrderSubmitted'));
      setTimeout(() => {
        onSuccess && onSuccess();
        onClose();
      }, 2000);
    } catch (err) {
      toast.error(t('failedToOrderCard'));
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className={`rounded-lg p-8 max-w-lg w-full relative ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        {/* Close button */}
        <button 
          onClick={onClose}
          className={`absolute top-4 right-4 ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-400 hover:text-gray-600'}`}
        >
          <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        {/* STEP 1: Choose Card Type (Matching Reference Image) */}
        {step === 1 && (
          <div className="text-center">
            <h3 className={`text-2xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('orderCard')}</h3>
            <p className={`mb-8 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('chooseCardType')}</p>

            <div className="space-y-6">
              {/* Physical Card Option */}
              <button
                onClick={() => {
                  setSelectedCardType('DEBIT_PHYSICAL');
                  setStep(2);
                }}
                className={`w-full p-6 border-2 rounded-xl transition group ${isDark ? 'border-gray-600 hover:border-red-500 hover:bg-red-900/20' : 'border-gray-200 hover:border-red-600 hover:bg-red-50'}`}
              >
                {/* Card Visual - Turquoise Physical Card */}
                <div className="bg-gradient-to-br from-teal-400 to-teal-600 rounded-lg p-6 mb-4 shadow-lg" style={{aspectRatio: '1.586'}}>
                  <div className="flex justify-between items-start mb-8">
                    <div className="w-12 h-8 bg-yellow-400 rounded opacity-80"></div>
                    <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                    </svg>
                  </div>
                  <div className="text-white text-left">
                    <p className="text-xs opacity-80 mb-1">ecommbx</p>
                    <div className="flex justify-end">
                      <p className="text-lg font-bold">VISA</p>
                    </div>
                  </div>
                </div>
                <p className={`text-lg font-semibold group-hover:text-red-600 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('physicalDebitCard')}</p>
              </button>

              {/* Virtual Card Option */}
              <button
                onClick={() => {
                  setSelectedCardType('VIRTUAL');
                  setStep(2);
                }}
                className={`w-full p-6 border-2 rounded-xl transition group ${isDark ? 'border-gray-600 hover:border-red-500 hover:bg-red-900/20' : 'border-gray-200 hover:border-red-600 hover:bg-red-50'}`}
              >
                {/* Card Visual - White Virtual Card */}
                <div className={`border-2 rounded-lg p-6 mb-4 ${isDark ? 'bg-gray-700 border-gray-500' : 'bg-gradient-to-br from-gray-50 to-gray-100 border-gray-300'}`} style={{aspectRatio: '1.586'}}>
                  <div className="flex justify-between items-start mb-8">
                    <div className={`w-12 h-8 rounded ${isDark ? 'bg-gray-600' : 'bg-gray-200'}`}></div>
                    <svg className={`w-8 h-8 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2z"/>
                    </svg>
                  </div>
                  <div className={`text-left ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                    <p className="text-xs opacity-60 mb-1">ecommbx</p>
                    <div className="flex justify-end">
                      <p className="text-lg font-bold">VISA</p>
                    </div>
                  </div>
                </div>
                <p className={`text-lg font-semibold group-hover:text-red-600 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('virtualCard')}</p>
              </button>
            </div>
          </div>
        )}

        {/* STEP 2: Select Account (Matching Reference) */}
        {step === 2 && (
          <div className="text-center">
            {/* Back button */}
            <button 
              onClick={() => setStep(1)}
              className={`absolute top-4 left-4 ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'}`}
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
              </svg>
            </button>

            <h3 className={`text-2xl font-semibold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('orderCard')}</h3>

            {/* Card Illustration */}
            <div className="mb-8 flex justify-center">
              <div className={`w-48 h-48 rounded-full flex items-center justify-center ${isDark ? 'bg-teal-900/30' : 'bg-teal-100'}`}>
                <div className="bg-gradient-to-br from-teal-400 to-teal-600 rounded-lg p-4 shadow-lg transform rotate-12" style={{width: '140px', height: '88px'}}>
                  <div className="w-8 h-6 bg-yellow-400 rounded opacity-80 mb-2"></div>
                  <div className="text-white text-xs">Project Atlas</div>
                </div>
              </div>
            </div>

            <p className={`mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('selectAccountForCard')}</p>

            {/* Account Dropdown */}
            <div className="text-left mb-6">
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('account')}</label>
              <select
                value={selectedAccount || ''}
                onChange={(e) => setSelectedAccount(e.target.value)}
                className={`w-full input-field text-base ${isDark ? 'bg-gray-700 border-gray-600 text-white' : ''}`}
                style={{height: '56px'}}
              >
                <option value="">{t('selectAccount')}</option>
                {accounts.map(acc => (
                  <option key={acc.id} value={acc.id}>
                    {acc.iban ? `${acc.iban} - €${(acc.balance/100).toFixed(2)}` : `Account ${acc.account_number.slice(-4)} - €${(acc.balance/100).toFixed(2)}`}
                  </option>
                ))}
              </select>
              
              {/* Show IBAN below selected account */}
              {selectedAccount && accounts.find(a => a.id === selectedAccount) && (
                <div className={`mt-3 p-3 rounded ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
                  <p className={`text-xs mb-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>IBAN</p>
                  <p className={`font-mono text-sm ${isDark ? 'text-white' : 'text-gray-900'}`}>
                    {accounts.find(a => a.id === selectedAccount).iban}
                  </p>
                </div>
              )}
            </div>

            {/* Continue Button - Teal color matching reference */}
            <button
              onClick={handleSubmit}
              disabled={!selectedAccount}
              className="w-full py-4 rounded-lg font-semibold text-white transition disabled:opacity-50"
              style={{backgroundColor: '#14B8A6'}}
            >
              {t('continueBtn')}
            </button>
          </div>
        )}

        {/* STEP 3: Success (Matching Reference) */}
        {step === 3 && (
          <div className="text-center py-8">
            {/* Card with circuits illustration */}
            <div className="mb-8 flex justify-center">
              <div className="relative">
                {/* Teal circles background */}
                <div className="absolute inset-0 flex justify-around items-center opacity-20">
                  <div className="w-32 h-32 bg-teal-400 rounded-full"></div>
                  <div className="w-32 h-32 bg-teal-400 rounded-full"></div>
                </div>
                
                {/* Card with circuits */}
                <div className={`relative border-2 rounded-2xl p-8 ${isDark ? 'bg-teal-900/30 border-gray-600' : 'bg-gradient-to-br from-teal-50 to-teal-100 border-gray-900'}`} style={{width: '280px', height: '176px'}}>
                  {/* Circuit pattern */}
                  <svg className="absolute inset-0 w-full h-full opacity-30" viewBox="0 0 280 176">
                    <path d="M140 30 L140 80 L80 80 L80 130" stroke="#14B8A6" strokeWidth="2" fill="none" />
                    <path d="M140 30 L140 80 L200 80 L200 130" stroke="#14B8A6" strokeWidth="2" fill="none" />
                    <circle cx="140" cy="30" r="4" fill="#14B8A6" />
                    <circle cx="80" cy="130" r="4" fill="#14B8A6" />
                    <circle cx="200" cy="130" r="4" fill="#14B8A6" />
                  </svg>
                  
                  <div className="relative">
                    <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>Project Atlas</p>
                    <p className={`text-right text-xl font-bold ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>VISA</p>
                  </div>
                </div>
              </div>
            </div>

            <h3 className={`text-3xl font-bold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('orderSuccessful')}</h3>
            <p className={`max-w-md mx-auto mb-8 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('orderSuccessDesc')}
            </p>

            {/* Close button - Teal color */}
            <button
              onClick={() => {
                onSuccess && onSuccess();
                onClose();
              }}
              className="w-full max-w-md mx-auto py-4 rounded-lg font-semibold text-white transition"
              style={{backgroundColor: '#14B8A6'}}
            >
              {t('close')}
            </button>
            
            <button
              onClick={() => {
                onSuccess && onSuccess();
                onClose();
              }}
              className={`mt-4 ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'}`}
            >
              {t('save')}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
