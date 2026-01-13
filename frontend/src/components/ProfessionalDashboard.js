// Customer Dashboard - Professional (No Fake Cards!)
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';

export function ProfessionalDashboard({ user, logout }) {
  const navigate = useNavigate();
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
          <button onClick={() => accounts[0] && navigate(`/accounts/${accounts[0].id}/transactions`)} className="stat-tile-link">
            <span>View</span><span>→</span>
          </button>
        </div>

        <div className="stat-tile">
          <div className="stat-tile-icon">
            <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
            </svg>
          </div>
          <div className="stat-tile-number">0</div>
          <div className="stat-tile-label">Cards</div>
          <button onClick={() => navigate('/cards')} className="stat-tile-link">
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
          <button onClick={() => navigate('/transfers')} className="stat-tile-link">
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
          <button onClick={() => accounts[0] && navigate(`/accounts/${accounts[0].id}/transactions`)} className="stat-tile-link">
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
                <button onClick={async () => { try { await api.post('/accounts/create'); fetchDashboardData(); } catch(e) {} }} className="btn-primary">Create Account</button>
              </div>
            ) : (
              <div className="space-y-3">
                {accounts.slice(0, 2).map((account) => (
                  <div key={account.id} className="account-item">
                    <div>
                      <p className="text-sm font-medium text-gray-900 mb-1">EUR e-Account</p>
                      <p className="text-xs text-gray-500 font-mono">{account.iban}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-lg font-semibold text-gray-900">€{formatAmount(account.balance)}</p>
                      <button onClick={() => navigate(`/accounts/${account.id}/transactions`)} className="text-xs text-red-600 hover:text-red-700 font-medium mt-1">
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
                <button onClick={() => navigate('/transfers')} className="btn-primary">Make Your First Transfer</button>
              </div>
            ) : (
              <div className="card p-4">
                {transactions.map((txn) => (
                  <div key={txn.id} className="transaction-item">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{txn.transaction_type.replace('_', ' ')}</p>
                      <p className="text-xs text-gray-500">{formatDate(txn.created_at)}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold amount-positive">€100.00</p>
                      <span className="badge badge-success">{txn.status}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Quick Actions */}
        <div className="space-y-6">
          <div>
            <div className="section-header">Quick Actions</div>
            <div className="card p-4 space-y-2">
              <button onClick={() => navigate('/transfers')} className="w-full btn-primary">Send Money</button>
              {kycStatus === 'APPROVED' && (
                <button onClick={() => navigate('/cards')} className="w-full btn-primary">Order Card</button>
              )}
              <button onClick={() => navigate('/cards')} className="w-full btn-secondary">Manage Cards</button>
            </div>
          </div>

          <div>
            <div className="section-header">This Month</div>
            <div className="card p-4">
              <div className="flex justify-between mb-3">
                <span className="text-sm text-gray-600">Total Spending</span>
                <span className="text-lg font-bold">€850.00</span>
              </div>
              <button onClick={() => navigate('/insights')} className="text-xs text-red-600 hover:text-red-700 font-medium">
                View full breakdown →
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

