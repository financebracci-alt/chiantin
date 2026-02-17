// Admin Analytics Dashboard
import React, { useState, useEffect } from 'react';
import { LineChart, Line, BarChart, Bar, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import api from '../api';

export function AnalyticsDashboard() {
  const [stats, setStats] = useState({
    totalUsers: 0,
    activeUsers: 0,
    pendingKYC: 0,
    approvedKYC: 0,
    totalTransactions: 0,
    totalVolume: 0
  });
  const [monthlyData, setMonthlyData] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAnalytics();
  }, []);

  const fetchAnalytics = async () => {
    try {
      // Fetch both overview stats and monthly data in parallel
      const [analyticsRes, monthlyRes] = await Promise.all([
        api.get('/admin/analytics/overview'),
        api.get('/admin/analytics/monthly')
      ]);
      
      const analytics = analyticsRes.data;
      const monthly = monthlyRes.data;
      
      // Volume is in cents, convert to euros
      const volumeInEuros = (analytics.transfers?.volume_cents || 0) / 100;
      
      setStats({
        totalUsers: analytics.users?.total || 0,
        activeUsers: analytics.users?.active || 0,
        pendingKYC: analytics.kyc?.pending || 0,
        approvedKYC: analytics.kyc?.approved || 0,
        totalTransactions: analytics.transfers?.total || 0,
        totalVolume: volumeInEuros
      });
      
      // Set real monthly data from backend
      if (monthly.monthly_data && monthly.monthly_data.length > 0) {
        setMonthlyData(monthly.monthly_data);
      }
    } catch (err) {
      console.error('Failed to fetch analytics:', err);
    } finally {
      setLoading(false);
    }
  };

  // Format currency in EU format
  const formatEuroCurrency = (amount) => {
    return new Intl.NumberFormat('de-DE', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount);
  };

  const userStatusData = [
    { name: 'Active', value: stats.activeUsers, color: '#2E7D32' },
    { name: 'Pending', value: stats.totalUsers - stats.activeUsers, color: '#F57C00' }
  ];

  const kycData = [
    { name: 'Approved', value: stats.approvedKYC, color: '#2E7D32' },
    { name: 'Pending', value: stats.pendingKYC, color: '#F57C00' }
  ];

  const monthlyData = [
    { month: 'Jan', users: 5, transactions: 12 },
    { month: 'Feb', users: 8, transactions: 25 },
    { month: 'Mar', users: 12, transactions: 38 },
    { month: 'Apr', users: stats.totalUsers, transactions: 45 }
  ];

  if (loading) {
    return (
      <div className="space-y-4">
        {[1,2,3].map(i => <div key={i} className="skeleton-card"></div>)}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div className="stat-tile" data-testid="stat-total-users">
          <div className="stat-tile-number">{stats.totalUsers}</div>
          <div className="stat-tile-label">Total Users</div>
        </div>
        <div className="stat-tile" data-testid="stat-active-users">
          <div className="stat-tile-number">{stats.activeUsers}</div>
          <div className="stat-tile-label">Active Users</div>
        </div>
        <div className="stat-tile" data-testid="stat-pending-kyc">
          <div className="stat-tile-number">{stats.pendingKYC}</div>
          <div className="stat-tile-label">Pending KYC</div>
        </div>
        <div className="stat-tile" data-testid="stat-transactions">
          <div className="stat-tile-number">{stats.totalTransactions}</div>
          <div className="stat-tile-label">Transactions</div>
        </div>
        <div className="stat-tile" data-testid="stat-volume">
          <div className="stat-tile-number text-lg">{formatEuroCurrency(stats.totalVolume)}</div>
          <div className="stat-tile-label">Total Volume</div>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-2 gap-6">
        {/* User Growth */}
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">User Growth</h3>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEEEEE" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Line type="monotone" dataKey="users" stroke="#D32F2F" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Transaction Volume */}
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Monthly Transactions</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#EEEEEE" />
              <XAxis dataKey="month" tick={{ fontSize: 12 }} />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Bar dataKey="transactions" fill="#D32F2F" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* User Status Distribution */}
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">User Status</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={userStatusData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {userStatusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* KYC Status */}
        <div className="card p-6">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">KYC Status</h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={kycData}
                cx="50%"
                cy="50%"
                labelLine={false}
                label={({ name, value }) => `${name}: ${value}`}
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
              >
                {kycData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
