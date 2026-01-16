// Customer Dashboard - Professional (No Fake Cards!)
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

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
    <div className="container-main py-8">
      {/* Tax Hold Banner */}
      {taxHoldStatus?.is_blocked && (
        <div className="bg-red-50 border-l-4 border-red-500 rounded-lg p-4 mb-6" data-testid="tax-hold-banner">
          <div className="flex items-start space-x-3">
            <svg className="w-6 h-6 text-red-600 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <div className="flex-1">
              <h3 className="font-semibold text-red-800">Account Restricted</h3>
              <p className="text-sm text-red-700 mt-1">
                Your account has been temporarily restricted due to outstanding tax obligations.
              </p>
              <div className="mt-2 p-3 bg-white/50 rounded border border-red-200">
                <p className="text-sm text-red-800">
                  <span className="font-medium">Amount Due:</span>{' '}
                  <span className="font-bold text-lg">€{taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}</span>
                </p>
                <p className="text-xs text-red-600 mt-1">{taxHoldStatus.reason}</p>
              </div>
              <p className="text-sm text-red-600 mt-3">
                To restore full access to your banking services, please settle the required amount. 
                For assistance, <button onClick={() => navigate('/support')} className="underline font-medium hover:text-red-800 transition-colors">contact our support team</button>.
              </p>
            </div>
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
          <div className="stat-tile-label">Accounts</div>
          <button onClick={() => {
            if (taxHoldStatus?.is_blocked) {
              alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nPlease settle the required amount to restore full access. For assistance, contact support.`);
            } else if (accounts[0]) {
              navigate(`/accounts/${accounts[0].id}/transactions`);
            }
          }} className="stat-tile-link">
            <span>View</span><span>→</span>
          </button>
        </div>

        <div className="stat-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <div className="stat-tile-number">{cards.filter(c => c.status === 'ACTIVE').length}</div>
          <div className="stat-tile-label">Cards</div>
          <button onClick={() => {
            if (taxHoldStatus?.is_blocked) {
              alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nPlease settle the required amount to restore full access. For assistance, contact support.`);
            } else {
              navigate('/cards');
            }
          }} className="stat-tile-link">
            <span>View</span><span>→</span>
          </button>
        </div>

        <div className="stat-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          </div>
          <div className="stat-tile-number">{transactions.length}</div>
          <div className="stat-tile-label">Transfers</div>
          <button onClick={() => {
            if (taxHoldStatus?.is_blocked) {
              alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nPlease settle the required amount to restore full access. For assistance, contact support.`);
            } else {
              navigate('/transfers');
            }
          }} className="stat-tile-link">
            <span>View</span><span>→</span>
          </button>
        </div>

        <div className="stat-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="stat-tile-number">0</div>
          <div className="stat-tile-label">Statements</div>
          <button onClick={() => {
            if (taxHoldStatus?.is_blocked) {
              alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nPlease settle the required amount to restore full access. For assistance, contact support.`);
            } else if (accounts[0]) {
              navigate(`/accounts/${accounts[0].id}/transactions`);
            }
          }} className="stat-tile-link">
            <span>View</span><span>→</span>
          </button>
        </div>
      </div>

      {/* Dashboard Grid */}
      <div className="dashboard-grid">
        {/* Left: Accounts + Recent Activity */}
        <div className="space-y-6">
          {/* Accounts */}
          <div>
            <div className="section-header">Accounts</div>
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
            <div className="section-header">Recent Activity</div>
            {transactions.length === 0 ? (
              <div className="card p-8 text-center">
                <p className="text-sm text-gray-600 mb-4">No transactions yet</p>
                <button 
                  onClick={() => {
                    if (taxHoldStatus?.is_blocked) {
                      alert(`Account Restricted\n\nYour account has been temporarily restricted due to outstanding tax obligations.\n\nAmount Due: €${taxHoldStatus.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}\n\nPlease settle the required amount to restore full access. For assistance, contact support.`);
                    } else {
                      navigate('/transfers');
                    }
                  }} 
                  className="btn-primary"
                >
                  Make Your First Transfer
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

