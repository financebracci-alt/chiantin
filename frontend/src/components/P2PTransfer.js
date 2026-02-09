// Professional Bank-Style P2P Transfer
import React, { useState, useEffect } from 'react';
import api from '../api';
import { useToast } from './Toast';
import { useLanguage, useTheme } from '../contexts/AppContext';
import { useBalanceVisibility, formatBalance } from '../hooks/useBalanceVisibility';
import BalanceToggle from './BalanceToggle';

export function P2PTransferForm({ onSuccess }) {
  const toast = useToast();
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const { isBalanceVisible, toggleBalanceVisibility } = useBalanceVisibility();
  const [beneficiaries, setBeneficiaries] = useState([]);
  const [accounts, setAccounts] = useState([]);
  const [formData, setFormData] = useState({
    to_iban: '',
    to_name: '',
    amount: '',
    reason: '',
    reference: ''
  });
  const [loading, setLoading] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [transactionResult, setTransactionResult] = useState(null);
  const [validating, setValidating] = useState(false);
  const [recipientValid, setRecipientValid] = useState(null);
  const [showReference, setShowReference] = useState(false);
  const [selectedAccount, setSelectedAccount] = useState(null);
  
  // Password Authorization State
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [authPassword, setAuthPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [verifyingPassword, setVerifyingPassword] = useState(false);
  const [showAuthPassword, setShowAuthPassword] = useState(false);

  useEffect(() => {
    fetchBeneficiaries();
    fetchAccounts();
  }, []);

  const fetchBeneficiaries = async () => {
    try {
      const response = await api.get('/beneficiaries');
      setBeneficiaries(response.data);
    } catch (err) {
      console.error(err);
    }
  };

  const fetchAccounts = async () => {
    try {
      const response = await api.get('/accounts');
      setAccounts(response.data);
      if (response.data.length > 0) {
        setSelectedAccount(response.data[0]);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const validateIBAN = () => {
    if (!formData.to_iban) return;
    
    setValidating(true);
    try {
      // Basic IBAN validation (2 letters + 2 digits + up to 30 alphanumeric)
      const cleanIban = formData.to_iban.replace(/\s/g, '').toUpperCase();
      const ibanRegex = /^[A-Z]{2}[0-9]{2}[A-Z0-9]{4,30}$/;
      
      if (ibanRegex.test(cleanIban) && cleanIban.length >= 15 && cleanIban.length <= 34) {
        setRecipientValid(true);
      } else {
        setRecipientValid(false);
        toast.error(t('invalidIbanFormat'));
      }
    } catch (err) {
      setRecipientValid(false);
      toast.error(t('invalidIbanFormat'));
    } finally {
      setValidating(false);
    }
  };

  const formatIBANInput = (value) => {
    // Remove all spaces and convert to uppercase
    const clean = value.replace(/\s/g, '').toUpperCase();
    // Add space every 4 characters for display
    return clean.replace(/(.{4})/g, '$1 ').trim();
  };

  const availableBalance = selectedAccount?.balance || 0;
  // Convert euro input to cents for comparison
  const transferAmountCents = Math.round(parseFloat(formData.amount || 0) * 100);
  const hasEnoughBalance = transferAmountCents > 0 && transferAmountCents <= availableBalance;

  // Step 1: When user clicks "Send", show password modal
  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!hasEnoughBalance) {
      toast.error(t('insufficientBalance'));
      return;
    }
    
    // Show password authorization modal
    setAuthPassword('');
    setAuthError('');
    setShowPasswordModal(true);
  };

  // Step 2: Verify password and process transfer
  const handlePasswordVerification = async () => {
    if (!authPassword.trim()) {
      setAuthError(t('pleaseEnterPassword') || 'Please enter your password');
      return;
    }

    setVerifyingPassword(true);
    setAuthError('');

    try {
      // Verify password with backend
      await api.post('/auth/verify-password', { password: authPassword });
      
      // Password verified - close modal and process transfer
      setShowPasswordModal(false);
      setAuthPassword('');
      
      // Now process the actual transfer
      await processTransfer();
      
    } catch (err) {
      const errorDetail = err.response?.data?.detail;
      if (errorDetail === 'Incorrect password') {
        setAuthError(t('incorrectPassword') || 'Incorrect password. Please try again.');
      } else {
        setAuthError(t('verificationFailed') || 'Verification failed. Please try again.');
      }
    } finally {
      setVerifyingPassword(false);
    }
  };

  // Step 3: Process the actual transfer after password verification
  const processTransfer = async () => {
    setLoading(true);

    try {
      // Convert euros to cents for API
      const amountInCents = Math.round(parseFloat(formData.amount) * 100);
      // Clean IBAN (remove spaces)
      const cleanIban = formData.to_iban.replace(/\s/g, '').toUpperCase();
      
      const result = await api.post('/transfers/p2p', {
        to_iban: cleanIban,
        amount: amountInCents,
        reason: formData.reason || 'P2P Transfer',
        recipient_name: formData.to_name || null
      });
      setTransactionResult({...result.data, amount: amountInCents});
      setShowConfirmation(true);
      toast.success(t('transferSuccessful'));
      setTimeout(() => {
        setFormData({ to_iban: '', to_name: '', amount: '', reason: '', reference: '' });
        setShowConfirmation(false);
        setRecipientValid(null);
        onSuccess && onSuccess();
      }, 3000);
    } catch (err) {
      // Check for tax hold error
      const errorDetail = err.response?.data?.detail;
      if (errorDetail?.code === 'TAX_HOLD') {
        toast.error(t('accountRestrictedTax'));
        // Show detailed message in alert for better visibility
        alert(errorDetail.formatted_message || t('accountRestrictedTax'));
      } else {
        toast.error(typeof errorDetail === 'string' ? errorDetail : t('transferFailed'));
      }
    } finally {
      setLoading(false);
    }
  };

  const selectBeneficiary = (beneficiary) => {
    setFormData({
      ...formData, 
      to_iban: beneficiary.recipient_iban || '', 
      to_name: beneficiary.recipient_name || beneficiary.nickname
    });
    if (beneficiary.recipient_iban) {
      setRecipientValid(true);
    }
  };

  const formatIBAN = (iban) => {
    if (!iban) return 'No IBAN';
    return iban.replace(/(.{4})/g, '$1 ').trim();
  };

  if (showConfirmation && transactionResult) {
    return (
      <div className="max-w-lg mx-auto">
        <div className={`rounded-xl shadow-lg p-8 text-center ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
          <div className={`w-20 h-20 rounded-full flex items-center justify-center mx-auto mb-6 ${isDark ? 'bg-green-900/30' : 'bg-green-100'}`}>
            <svg className={`w-10 h-10 ${isDark ? 'text-green-400' : 'text-green-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
          </div>
          <h3 className={`text-2xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('paymentSuccessful')}</h3>
          <p className={`text-3xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>€{(transactionResult.amount / 100).toFixed(2)}</p>
          <p className={`mb-2 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('sentTo')} {transactionResult.recipient}</p>
          {transactionResult.recipient_iban && (
            <p className={`text-sm font-mono mb-6 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{formatIBAN(transactionResult.recipient_iban)}</p>
          )}
          <div className={`rounded-lg p-4 mb-6 ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
            <p className={`text-xs mb-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('transactionId')}</p>
            <p className={`text-sm font-mono ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{transactionResult.transaction_id}</p>
          </div>
          <div className={`flex items-center justify-center ${isDark ? 'text-green-400' : 'text-green-600'}`}>
            <svg className="animate-spin mr-2 h-4 w-4" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {t('redirecting')}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-lg mx-auto">
      <div className={`rounded-xl shadow-lg overflow-hidden ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        {/* Header with Bank Icon */}
        <div className="bg-gradient-to-r from-red-600 to-red-700 px-6 py-8 text-center">
          <div className="w-16 h-16 bg-white/20 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 14v3m4-3v3m4-3v3M3 21h18M3 10h18M3 7l9-4 9 4M4 10h16v11H4V10z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-white">{t('sendMoney')}</h2>
          <p className="text-red-100 text-sm mt-1">{t('transferFundsSecurely')}</p>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          {/* Recipient Name */}
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              {t('sendMoneyTo')}
            </label>
            <input
              type="text"
              value={formData.to_name}
              onChange={(e) => setFormData({...formData, to_name: e.target.value})}
              className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-colors ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'border-gray-300 text-gray-900'}`}
              placeholder={t('recipientName')}
              data-testid="transfer-name"
            />
          </div>

          {/* Recipient IBAN */}
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              {t('recipientIban')}
            </label>
            <div className="relative">
              <input
                type="text"
                value={formData.to_iban}
                onChange={(e) => {
                  const formatted = formatIBANInput(e.target.value);
                  setFormData({...formData, to_iban: formatted});
                  setRecipientValid(null);
                }}
                onBlur={validateIBAN}
                required
                className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-red-500 transition-colors font-mono text-sm tracking-wider ${
                  recipientValid === true ? 'border-green-500 bg-green-50 dark:bg-green-900/20' : 
                  recipientValid === false ? 'border-red-500 bg-red-50 dark:bg-red-900/20' : 
                  isDark ? 'bg-gray-700 border-gray-600 text-white' : 'border-gray-300'
                } ${isDark && recipientValid === null ? 'text-white' : ''}`}
                placeholder="DE89 3704 0044 0532 0130 00"
                data-testid="transfer-iban"
              />
              {recipientValid === true && (
                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                  <svg className="w-5 h-5 text-green-600" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              )}
            </div>
            {validating && <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('validatingIban')}</p>}
            {recipientValid === true && <p className="text-xs text-green-600 mt-1">✓ {t('validIbanFormat')}</p>}
            {recipientValid === false && <p className="text-xs text-red-600 mt-1">✗ {t('invalidIbanFormat')}</p>}
          </div>

          {/* Saved Recipients */}
          {beneficiaries.length > 0 && beneficiaries.some(b => b.recipient_iban) && (
            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                {t('orSelectFromSaved')}
              </label>
              <div className="flex flex-wrap gap-2">
                {beneficiaries.filter(b => b.recipient_iban).slice(0, 4).map(b => (
                  <button
                    key={b.id}
                    type="button"
                    onClick={() => selectBeneficiary(b)}
                    className={`px-3 py-2 text-sm rounded-full border transition-colors ${
                      formData.to_iban.replace(/\s/g, '') === (b.recipient_iban || '').replace(/\s/g, '')
                        ? 'border-red-600 bg-red-50 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                        : isDark ? 'border-gray-600 text-gray-300 hover:border-red-500 hover:bg-red-900/20' : 'border-gray-300 hover:border-red-300 hover:bg-red-50'
                    }`}
                  >
                    {b.nickname || b.recipient_name}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Pay From Account */}
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              {t('payFrom')}
            </label>
            <div className={`border rounded-lg p-4 ${isDark ? 'border-gray-600 bg-gray-700' : 'border-gray-300 bg-gray-50'}`}>
              {selectedAccount ? (
                <div className="flex justify-between items-center">
                  <div>
                    <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('currentAccount')}</p>
                    <p className={`text-sm font-mono ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{formatIBAN(selectedAccount.iban)}</p>
                  </div>
                  <div className="text-right">
                    <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('available')}</p>
                    <div className="flex items-center gap-2 justify-end">
                      <p className={`font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                        {formatBalance(availableBalance, isBalanceVisible)}
                      </p>
                      <BalanceToggle 
                        isVisible={isBalanceVisible} 
                        onToggle={toggleBalanceVisibility} 
                        isDark={isDark}
                        size="small"
                      />
                    </div>
                  </div>
                </div>
              ) : (
                <p className={`${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('noAccountAvailable')}</p>
              )}
            </div>
          </div>

          {/* Amount */}
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              {t('amount')}
            </label>
            <div className="relative">
              <span className={`absolute left-4 top-1/2 -translate-y-1/2 text-lg font-medium ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>€</span>
              <input
                type="number"
                step="0.01"
                min="0.01"
                value={formData.amount}
                onChange={(e) => setFormData({...formData, amount: e.target.value})}
                required
                className={`w-full pl-10 pr-4 py-3 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-colors text-lg ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'border-gray-300'}`}
                placeholder="0.00"
                data-testid="transfer-amount"
              />
            </div>
            {formData.amount && (
              <div className="flex justify-between items-center mt-2">
                <span className="text-xs">
                  {hasEnoughBalance ? (
                    <span className="text-green-600">✓ {t('sufficientBalance')}</span>
                  ) : (
                    <span className="text-red-600">✗ {t('insufficientBalance')}</span>
                  )}
                </span>
                <span className={`text-xs ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                  {t('remaining')}: €{((availableBalance - transferAmountCents) / 100).toFixed(2)}
                </span>
              </div>
            )}
          </div>

          {/* Quick Amounts */}
          <div className="flex gap-2">
            {[10, 25, 50, 100, 250].map(euro => (
              <button
                key={euro}
                type="button"
                onClick={() => setFormData({...formData, amount: euro.toString()})}
                className={`flex-1 py-2 text-sm rounded-lg border transition-colors ${
                  parseFloat(formData.amount) === euro
                    ? 'border-red-600 bg-red-50 text-red-700 font-medium dark:bg-red-900/30 dark:text-red-300'
                    : isDark ? 'border-gray-600 text-gray-300 hover:border-red-500' : 'border-gray-300 hover:border-red-300 text-gray-700'
                }`}
              >
                €{euro}
              </button>
            ))}
          </div>

          {/* Payment Details */}
          <div>
            <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              {t('details')}
            </label>
            <textarea
              value={formData.reason}
              onChange={(e) => setFormData({...formData, reason: e.target.value})}
              rows={2}
              className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-colors resize-none ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'border-gray-300'}`}
              placeholder={t('paymentPurpose')}
              data-testid="transfer-reason"
            />
            <p className={`text-xs mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
              💡 {t('detailsVisibleToRecipient')}
            </p>
          </div>

          {/* Reference Number Toggle */}
          <div className="flex items-center">
            <input
              type="checkbox"
              id="showReference"
              checked={showReference}
              onChange={(e) => setShowReference(e.target.checked)}
              className="w-4 h-4 text-red-600 border-gray-300 rounded focus:ring-red-500"
            />
            <label htmlFor="showReference" className={`ml-2 text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
              {t('addReferenceNumber')}
            </label>
          </div>

          {showReference && (
            <div>
              <input
                type="text"
                value={formData.reference}
                onChange={(e) => setFormData({...formData, reference: e.target.value})}
                className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-colors ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'border-gray-300'}`}
                placeholder={t('referencePlaceholder')}
                data-testid="transfer-reference"
              />
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={loading || !recipientValid || !hasEnoughBalance || !formData.amount || !formData.to_iban}
            className="w-full py-4 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
            data-testid="submit-transfer"
          >
            {loading ? (
              <>
                <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {t('processing')}
              </>
            ) : (
              <>
                <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
                {t('makePayment')}
              </>
            )}
          </button>

          {/* Save as Draft */}
          <button
            type="button"
            className={`w-full py-3 border font-medium rounded-lg transition-colors ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'}`}
          >
            {t('saveAsDraft')}
          </button>
        </form>
      </div>

      {/* Password Authorization Modal */}
      {showPasswordModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className={`w-full max-w-md rounded-2xl shadow-2xl overflow-hidden ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
            {/* Modal Header */}
            <div className="bg-gradient-to-r from-red-600 to-red-700 px-6 py-5 text-center">
              <div className="w-14 h-14 bg-white/20 rounded-full flex items-center justify-center mx-auto mb-3">
                <svg className="w-7 h-7 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className="text-lg font-semibold text-white">{t('authorizeTransfer') || 'Authorize Transfer'}</h3>
              <p className="text-red-100 text-sm mt-1">{t('securityVerification') || 'Security Verification Required'}</p>
            </div>

            {/* Modal Body */}
            <div className="p-6">
              {/* Transfer Summary */}
              <div className={`rounded-lg p-4 mb-5 ${isDark ? 'bg-gray-700' : 'bg-gray-50'}`}>
                <div className="flex justify-between items-center mb-2">
                  <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('amount') || 'Amount'}</span>
                  <span className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>€{parseFloat(formData.amount || 0).toFixed(2)}</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('to') || 'To'}</span>
                  <span className={`text-sm font-medium ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{formData.to_name || t('recipient')}</span>
                </div>
              </div>

              {/* Security Message */}
              <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {t('enterPasswordToAuthorize') || 'For your security, please enter your account password to authorize this transfer.'}
              </p>

              {/* Password Input */}
              <div className="mb-4">
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                  {t('password') || 'Password'}
                </label>
                <div className="relative">
                  <input
                    type={showAuthPassword ? 'text' : 'password'}
                    value={authPassword}
                    onChange={(e) => {
                      setAuthPassword(e.target.value);
                      setAuthError('');
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handlePasswordVerification();
                      }
                    }}
                    placeholder={t('enterYourPassword') || 'Enter your password'}
                    className={`w-full px-4 py-3 pr-12 border rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 transition-colors ${
                      authError 
                        ? 'border-red-500 bg-red-50 dark:bg-red-900/20' 
                        : isDark 
                          ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' 
                          : 'border-gray-300'
                    }`}
                    autoFocus
                    data-testid="transfer-auth-password"
                  />
                  <button
                    type="button"
                    onClick={() => setShowAuthPassword(!showAuthPassword)}
                    className={`absolute right-3 top-1/2 -translate-y-1/2 ${isDark ? 'text-gray-400 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`}
                  >
                    {showAuthPassword ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
                {authError && (
                  <p className="text-sm text-red-500 mt-2 flex items-center">
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {authError}
                  </p>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => {
                    setShowPasswordModal(false);
                    setAuthPassword('');
                    setAuthError('');
                  }}
                  disabled={verifyingPassword}
                  className={`flex-1 py-3 border font-medium rounded-lg transition-colors ${isDark ? 'border-gray-600 text-gray-300 hover:bg-gray-700' : 'border-gray-300 text-gray-700 hover:bg-gray-50'} disabled:opacity-50`}
                >
                  {t('cancel') || 'Cancel'}
                </button>
                <button
                  type="button"
                  onClick={handlePasswordVerification}
                  disabled={verifyingPassword || !authPassword.trim()}
                  className="flex-1 py-3 bg-red-600 text-white font-semibold rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center"
                  data-testid="confirm-transfer-auth"
                >
                  {verifyingPassword ? (
                    <>
                      <svg className="animate-spin -ml-1 mr-2 h-5 w-5 text-white" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                      </svg>
                      {t('verifying') || 'Verifying...'}
                    </>
                  ) : (
                    <>
                      <svg className="w-5 h-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                      </svg>
                      {t('confirmAndSend') || 'Confirm & Send'}
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
