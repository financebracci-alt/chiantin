// Customer Dashboard - Rebuilt to Match Professional Banking UI
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { P2PTransferForm } from './P2PTransfer';
import { BeneficiaryManager } from './Beneficiaries';
import { ScheduledPayments } from './ScheduledPayments';
import { SpendingInsights } from './SpendingInsights';
import { useCopyToClipboard } from '../hooks/useCopyToClipboard';

export function ProfessionalDashboard({ user, logout }) {
  const navigate = useNavigate();
  const copyToClipboard = useCopyToClipboard();
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [kycStatus, setKycStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    try {
      const [accountsRes, kycRes] = await Promise.all([
        api.get('/accounts'),
        api.get('/kyc/application')
      ]);
      
      setAccounts(accountsRes.data);
      setKycStatus(kycRes.data.status);

      // Fetch recent transactions from first account
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

  if (loading) {
    return <DashboardSkeleton />;
  }

  return (
    <div className="container-main py-8">
      {/* Welcome + KYC Status */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">
            Welcome back, {user?.first_name}
          </h1>
        </div>
        <div>
          {kycStatus === 'APPROVED' ? (
            <span className="badge badge-success">Verified</span>
          ) : kycStatus === 'PENDING' || kycStatus === 'SUBMITTED' ? (
            <span className="badge badge-warning">KYC Pending</span>
          ) : (
            <button
              onClick={() => navigate('/kyc')}
              className="text-sm text-red-600 hover:text-red-700 font-medium"
            >
              Complete Verification →
            </button>
          )}
        </div>
      </div>

      {/* Overview Card */}
      <div className="overview-card">
        <div className="overview-label">overview</div>
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
          <div>
            <div className="balance-large text-3xl sm:text-5xl">€{formatAmount(getTotalBalance())}</div>
            <div className="balance-small">Available balance</div>
          </div>
          <button
            onClick={() => accounts[0] && navigate(`/accounts/${accounts[0].id}/transactions`)}
            className="btn-primary w-full sm:w-auto"
            disabled={accounts.length === 0}
            data-testid="view-account-btn"
          >
            View Account
          </button>
        </div>
      </div>

      {/* 4 Stat Tiles */}
      <div className="stat-tiles-grid">
        <div className="stat-tile" data-testid="accounts-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <div className="stat-tile-number">{accounts.length}</div>
          <div className="stat-tile-label">Accounts</div>
          <button onClick={() => {
            if (accounts.length > 0) {
              navigate(`/accounts/${accounts[0].id}/transactions`);
            }
          }} className="stat-tile-link">
            <span>View</span>
            <span>→</span>
          </button>
        </div>

        <div className="stat-tile" data-testid="cards-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <div className="stat-tile-number">1</div>
          <div className="stat-tile-label">Cards</div>
          <button onClick={() => navigate('/cards')} className="stat-tile-link">
            <span>View</span>
            <span>→</span>
          </button>
        </div>

        <div className="stat-tile" data-testid="transfers-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
            </svg>
          </div>
          <div className="stat-tile-number">{transactions.length}</div>
          <div className="stat-tile-label">Transfers</div>
          <button onClick={() => navigate('/transfers')} className="stat-tile-link">
            <span>View</span>
            <span>→</span>
          </button>
        </div>

        <div className="stat-tile" data-testid="statements-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <div className="stat-tile-number">0</div>
          <div className="stat-tile-label">Statements</div>
          <button onClick={() => {
            if (accounts.length > 0) {
              navigate(`/accounts/${accounts[0].id}/transactions`);
            }
          }} className="stat-tile-link">
            <span>View</span>
            <span>→</span>
          </button>
        </div>
      </div>

      {/* Bottom Grid */}
      <div className="dashboard-grid">
        {/* Left: Accounts + Recent Activity */}
        <div className="space-y-6">
          {/* Accounts Section */}
          <div>
            <div className="section-header">Accounts</div>
            {accounts.length === 0 ? (
              <div className="card p-6 text-center">
                <p className="text-gray-600 mb-4">No accounts yet</p>
                <button
                  onClick={async () => {
                    try {
                      await api.post('/accounts/create');
                      fetchDashboardData();
                    } catch (err) {
                      console.error(err);
                    }
                  }}
                  className="btn-primary"
                  data-testid="create-account-btn"
                >
                  Create Account
                </button>
              </div>
            ) : (
              <div className="space-y-3">
                {accounts.slice(0, 2).map((account) => (
                  <div key={account.id} className="account-item" data-testid={`account-${account.id}`}>
                    <div>
                      <p className="text-sm font-medium text-gray-900 mb-1">EUR e-Account</p>
                      <div className="flex items-center space-x-2">
                        <p className="text-xs text-gray-500 font-mono">{account.iban || account.account_number}</p>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            copyToClipboard(account.iban || account.account_number, 'IBAN');
                          }}
                          className="text-gray-400 hover:text-red-600 transition"
                          title="Copy IBAN"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </button>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-gray-900">€{formatAmount(account.balance)}</p>
                      <button
                        onClick={() => navigate(`/accounts/${account.id}/transactions`)}
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
                <svg className="w-12 h-12 mx-auto text-gray-300 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                </svg>
                <p className="text-sm text-gray-600 mb-4">No transactions yet</p>
                <button onClick={() => navigate('/transfers')} className="btn-primary">
                  Make Your First Transfer
                </button>
              </div>
            ) : (
              <div className="card p-4">
                {transactions.map((txn) => (
                  <div key={txn.id} className="transaction-item" data-testid={`txn-${txn.id}`}>
                    <div>
                      <p className="text-sm font-medium text-gray-900">{txn.transaction_type.replace('_', ' ')}</p>
                      <p className="text-xs text-gray-500">{formatDate(txn.created_at)}</p>
                    </div>
                    <div className="text-right">
                      <p className={`text-sm font-semibold ${
                        txn.transaction_type === 'TOP_UP' || txn.transaction_type === 'SALARY' ? 'amount-positive' : 'amount-negative'
                      }`}>
                        {txn.transaction_type === 'TOP_UP' || txn.transaction_type === 'SALARY' ? '+' : '-'}€100.00
                      </p>
                      <span className={`badge ${
                        txn.status === 'POSTED' ? 'badge-success' : 'badge-gray'
                      }`}>
                        {txn.status}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Cards + Quick Actions */}
        <div className="space-y-6">
          {/* Card Widget */}
          <div>
            <div className="section-header">Cards</div>
            <div className="card p-6">
              {/* Card Preview */}
              <div className="bg-gradient-to-br from-gray-800 to-gray-900 rounded-xl p-6 text-white mb-4" style={{ aspectRatio: '1.586' }}>
                <div className="flex justify-between items-start mb-8">
                  <div>
                    <p className="text-xs font-medium opacity-80">Project Atlas</p>
                    <p className="text-xs opacity-60 mt-1">Debit Card</p>
                  </div>
                  <div className="w-10 h-10 bg-white/10 rounded-lg flex items-center justify-center">
                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                    </svg>
                  </div>
                </div>
                <div className="mb-6">
                  <p className="text-xs opacity-60 mb-2">Card Number</p>
                  <p className="font-mono text-base tracking-wider">•••• •••• •••• 4321</p>
                </div>
                <div className="flex justify-between items-end">
                  <div>
                    <p className="text-xs opacity-60 mb-1">Cardholder</p>
                    <p className="text-sm font-medium">{user?.first_name} {user?.last_name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs opacity-60 mb-1">Expires</p>
                    <p className="text-sm font-mono">12/28</p>
                  </div>
                </div>
              </div>

              {/* Quick Actions */}
              <div className="space-y-2">
                <button 
                  onClick={() => navigate('/cards')}
                  className="w-full py-2.5 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition"
                >
                  View Card Details
                </button>
                <button 
                  onClick={() => navigate('/cards')}
                  className="w-full py-2.5 text-sm font-medium text-gray-700 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
                >
                  Freeze Card
                </button>
                <button 
                  onClick={() => navigate('/cards')}
                  className="w-full py-2.5 text-sm font-medium text-gray-700 bg-gray-50 rounded-lg hover:bg-gray-100 transition"
                >
                  Manage Limits
                </button>
              </div>
              
              <p className="text-xs text-gray-500 text-center mt-4">Virtual debit card • No fees</p>
            </div>
          </div>

          {/* Quick Transfer Button */}
          <div>
            <div className="section-header">Quick Actions</div>
            <div className="card p-4 space-y-2">
              <button
                onClick={() => navigate('/transfers')}
                className="w-full btn-primary"
                data-testid="quick-transfer-btn"
              >
                Send Money
              </button>
              <button
                onClick={() => navigate('/kyc')}
                className="w-full btn-secondary"
              >
                Complete Verification
              </button>
            </div>
          </div>

          {/* Spending Insights Preview */}
          <div>
            <div className="section-header">This Month</div>
            <div className="card p-4">
              <div className="flex justify-between items-center mb-3">
                <span className="text-sm text-gray-600">Total Spending</span>
                <span className="text-lg font-bold">€850.00</span>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-gray-600">Food & Dining</span>
                  <span className="font-medium">€250.00</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-600">Shopping</span>
                  <span className="font-medium">€350.00</span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-gray-600">Bills</span>
                  <span className="font-medium">€200.00</span>
                </div>
              </div>
              <button
                onClick={() => navigate('/insights')}
                className="mt-3 text-xs text-red-600 hover:text-red-700 font-medium"
              >
                View full breakdown →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="container-main py-8">
      <div className="skeleton-card mb-6"></div>
      <div className="stat-tiles-grid mb-8">
        <div className="skeleton-card"></div>
        <div className="skeleton-card"></div>
        <div className="skeleton-card"></div>
        <div className="skeleton-card"></div>
      </div>
      <div className="dashboard-grid">
        <div className="space-y-6">
          <div className="skeleton-card h-48"></div>
          <div className="skeleton-card h-64"></div>
        </div>
        <div className="skeleton-card h-96"></div>
      </div>
    </div>
  );
}

export { DashboardSkeleton };
