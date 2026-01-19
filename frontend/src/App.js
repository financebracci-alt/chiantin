import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate, useParams } from 'react-router-dom';
import './App.css';
import api from './api';
import { APP_NAME } from './config';
import { SecuritySettings } from './components/Security';
import { KYCApplication } from './components/KYC';
import { AdminKYCReview } from './components/AdminKYC';
import { TransactionsList } from './components/Transactions';
import { EnhancedLedgerTools } from './components/AdminLedger';
import { AuditLogViewer } from './components/AuditLogs';
import { StatementDownload } from './components/Statements';
import { SupportTickets } from './components/Support';
import { NotificationBell } from './components/Notifications';
import { CustomerProfile } from './components/Profile';
import { ToastProvider, useToast } from './components/Toast';
import { ProfessionalDashboard } from './components/ProfessionalDashboard';
import { AdminSidebar, AdminLayout } from './components/AdminLayout';
import { MobileBottomTabs } from './components/MobileNav';
import { P2PTransferForm } from './components/P2PTransfer';
import { AnalyticsDashboard } from './components/Analytics';
import { AdminSettings } from './components/AdminSettings';
import { TransfersPage } from './components/TransfersPage';
import { SpendingInsights } from './components/SpendingInsights';
import { CardsPage } from './components/CardsPage';
import { AdminCardRequestsQueue } from './components/AdminCardRequestsQueue';
import { KYCReviewPage } from './components/KYCReviewPage';
import { AdminTransfersQueue } from './components/AdminTransfersQueue';
import { AdminAccountsControl } from './components/AdminAccountsControl';
import { LandingPage } from './components/LandingPage';

// Auth Context
const AuthContext = React.createContext(null);

const useAuth = () => {
  const context = React.useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within AuthProvider');
  return context;
};

function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const savedUser = localStorage.getItem('user');
    if (token && savedUser) {
      setUser(JSON.parse(savedUser));
    }
    setLoading(false);
  }, []);

  const login = async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    localStorage.setItem('access_token', response.data.access_token);
    localStorage.setItem('user', JSON.stringify(response.data.user));
    
    // CRITICAL: Check KYC status immediately after login
    try {
      const kycResponse = await api.get('/kyc/application', {
        headers: { 'Authorization': `Bearer ${response.data.access_token}` }
      });
      const kycStatus = kycResponse.data?.status || 'NONE';
      localStorage.setItem('kyc_status', kycStatus);
    } catch (err) {
      localStorage.setItem('kyc_status', 'NONE');
    }
    
    setUser(response.data.user);
    return response.data.user;
  };

  const signup = async (data) => {
    const response = await api.post('/auth/signup', data);
    return response.data;
  };

  const logout = () => {
    localStorage.removeItem('access_token');
    localStorage.removeItem('user');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Signup Page - Professional Style
function SignupPage() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
    first_name: '',
    last_name: '',
    phone: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validate
    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      await signup({
        email: formData.email,
        password: formData.password,
        first_name: formData.first_name,
        last_name: formData.last_name,
        phone: formData.phone || undefined
      });
      toast.success('Account created successfully! You can now login.');
      navigate('/login');
    } catch (err) {
      setError(err.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 mb-2">{APP_NAME}</h1>
          <p className="text-sm text-gray-600">Create your account</p>
        </div>
        
        <div className="card p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-3 text-sm">
                {error}
              </div>
            )}
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">First Name</label>
                <input
                  type="text"
                  value={formData.first_name}
                  onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                  required
                  className="input-field"
                  data-testid="signup-first-name"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">Last Name</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  required
                  className="input-field"
                  data-testid="signup-last-name"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className="input-field"
                data-testid="signup-email"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Phone (Optional)</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className="input-field"
                placeholder="+49 123 456 7890"
                data-testid="signup-phone"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                required
                className="input-field"
                placeholder="Minimum 8 characters"
                data-testid="signup-password"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Confirm Password</label>
              <input
                type="password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                required
                className="input-field"
                data-testid="signup-confirm-password"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary"
              data-testid="signup-button"
            >
              {loading ? 'Creating Account...' : 'Create Account'}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-200 text-center">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="font-medium text-red-600 hover:text-red-700"
                data-testid="goto-login"
              >
                Sign in
              </button>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// Login Page - Professional Style
function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const user = await login(email, password);
      // Redirect based on role
      if (user.role === 'CUSTOMER') {
        navigate('/dashboard');
      } else {
        navigate('/admin');
      }
    } catch (err) {
      setError(err.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-semibold text-gray-900 mb-2">{APP_NAME}</h1>
          <p className="text-sm text-gray-600">Sign in to your account</p>
        </div>
        
        <div className="card p-8">
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-800 rounded-lg p-3 text-sm">
                {error}
              </div>
            )}
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="input-field"
                data-testid="email-input"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                className="input-field"
                data-testid="password-input"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary"
              data-testid="login-button"
            >
              {loading ? 'Signing in...' : 'Sign in'}
            </button>
          </form>

          <div className="mt-6 pt-6 border-t border-gray-200 text-center">
            <p className="text-sm text-gray-600 mb-4">
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => navigate('/signup')}
                className="font-medium text-red-600 hover:text-red-700"
                data-testid="goto-signup"
              >
                Create Account
              </button>
            </p>
            <div className="text-xs text-gray-500 space-y-1">
              <p className="font-medium mb-1">Demo credentials:</p>
              <p>Customer: customer@demo.com / Demo@123456</p>
              <p>Admin: admin@atlas.local / Admin@123456</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

// Transactions Page
function TransactionsPage() {
  const { accountId } = useParams();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [account, setAccount] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchAccount();
  }, [accountId]);

  const fetchAccount = async () => {
    try {
      const response = await api.get('/accounts');
      const acc = response.data.find(a => a.id === accountId);
      setAccount(acc);
    } catch (err) {
      console.error('Failed to fetch account:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatAmount = (cents) => {
    return `€${(cents / 100).toFixed(2)}`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/dashboard')}
                className="text-gray-600 hover:text-gray-900"
              >
                ← Back
              </button>
              <h1 className="text-2xl font-bold" style={{ fontFamily: 'Space Grotesk' }}>
                {APP_NAME}
              </h1>
            </div>
            <button onClick={logout} className="text-sm text-gray-600 hover:text-gray-900">
              Logout
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className="text-center">Loading...</div>
        ) : account ? (
          <div className="space-y-6">
            {/* Account Summary - Professional */}
            <div className="card p-6">
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <p className="text-sm text-gray-600 mb-1">Account</p>
                  <h2 className="text-xl font-semibold text-gray-900 mb-3">Atlas EUR Current Account</h2>
                  {account.iban && (
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <p className="text-sm text-gray-700">IBAN:</p>
                        <p className="font-mono text-sm text-gray-900">{account.iban.match(/.{1,4}/g)?.join(' ')}</p>
                        <button
                          onClick={() => {
                            try {
                              navigator.clipboard.writeText(account.iban);
                              alert('IBAN copied!');
                            } catch (err) {
                              console.log('Clipboard write failed:', err);
                            }
                          }}
                          className="text-gray-400 hover:text-red-600 transition"
                          title="Copy IBAN"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </button>
                      </div>
                      {account.bic && (
                        <p className="text-sm text-gray-700">BIC: {account.bic}</p>
                      )}
                      <details className="mt-2">
                        <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-700">Account reference (for support)</summary>
                        <p className="text-xs text-gray-500 mt-1 font-mono">{account.account_number}</p>
                      </details>
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-600">Current Balance</p>
                  <p className="text-3xl font-bold text-gray-900">{formatAmount(account.balance)}</p>
                </div>
              </div>
            </div>

            {/* Transactions */}
            <TransactionsList accountId={accountId} />

            {/* Statement Download */}
            <StatementDownload accountId={accountId} />
          </div>
        ) : (
          <div className="bg-white rounded-lg shadow p-8 text-center">
            <p className="text-gray-600">Account not found</p>
          </div>
        )}
      </main>
    </div>
  );
}

// KYC Page
function KYCPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold" style={{ fontFamily: 'Space Grotesk' }}>
              {APP_NAME}
            </h1>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                {user?.first_name} {user?.last_name}
              </span>
              <button onClick={logout} className="text-sm text-gray-600 hover:text-gray-900">
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="border-b border-gray-200 bg-white">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-8">
          <button onClick={() => navigate('/dashboard')} className="py-4 px-1 border-b-2 border-transparent font-medium text-sm text-gray-500 hover:text-gray-700">
            Accounts
          </button>
          <button onClick={() => navigate('/kyc')} className="py-4 px-1 border-b-2 border-blue-600 font-medium text-sm text-blue-600">
            KYC
          </button>
          <button onClick={() => navigate('/security')} className="py-4 px-1 border-b-2 border-transparent font-medium text-sm text-gray-500 hover:text-gray-700">
            Security
          </button>
        </nav>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h2 className="text-2xl font-bold mb-6">Identity Verification (KYC)</h2>
        <KYCApplication />
      </main>
    </div>
  );
}

// Security Page
function SecurityPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold" style={{ fontFamily: 'Space Grotesk' }}>
              {APP_NAME}
            </h1>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                {user?.first_name} {user?.last_name}
              </span>
              <button
                onClick={logout}
                className="text-sm text-gray-600 hover:text-gray-900"
                data-testid="logout-button"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className="border-b border-gray-200 bg-white">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => navigate('/dashboard')}
            className="py-4 px-1 border-b-2 border-transparent font-medium text-sm text-gray-500 hover:text-gray-700 hover:border-gray-300"
          >
            Accounts
          </button>
          <button
            onClick={() => navigate('/security')}
            className="py-4 px-1 border-b-2 border-blue-600 font-medium text-sm text-blue-600"
          >
            Security
          </button>
        </nav>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <SecuritySettings user={user} />
      </main>
    </div>
  );
}

// Customer Dashboard - Professional UI
function CustomerDashboard() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);

  // Get user initials
  const getInitials = () => {
    if (!user) return '?';
    const first = user.first_name?.charAt(0) || '';
    const last = user.last_name?.charAt(0) || '';
    return (first + last).toUpperCase() || user.email?.charAt(0)?.toUpperCase() || '?';
  };

  // Menu items for the user avatar dropdown
  const menuItems = [
    { label: 'Dashboard', icon: '🏠', path: '/dashboard', description: 'Overview & Balance' },
    { label: 'Transfers', icon: '💸', path: '/transfers', description: 'Send money' },
    { label: 'Cards', icon: '🎴', path: '/cards', description: 'Manage your cards' },
    { label: 'Profile', icon: '👤', path: '/profile', description: 'Your settings' },
    { label: 'Security', icon: '🔒', path: '/security', description: 'Password & 2FA' },
    { label: 'Support', icon: '💬', path: '/support', description: 'Get help' },
  ];

  return (
    <div className="min-h-screen bg-white">
      {/* Simple Professional Header */}
      <header className="bg-white border-b border-gray-200 h-16 px-4 sm:px-6 flex items-center justify-between">
        <h1 className="header-logo">{APP_NAME}</h1>
        <div className="flex items-center space-x-2 sm:space-x-4">
          <NotificationBell />
          
          {/* Desktop: Show Logout button */}
          <button onClick={logout} className="hidden sm:block text-sm text-gray-600 hover:text-gray-900" data-testid="logout-button">
            Logout
          </button>
          
          {/* Mobile: Show User Avatar */}
          <div className="sm:hidden relative">
            <button
              onClick={() => setShowUserMenu(!showUserMenu)}
              className="w-9 h-9 rounded-full bg-gradient-to-br from-red-500 to-red-600 text-white font-semibold text-sm flex items-center justify-center shadow-md hover:shadow-lg transition-shadow"
              data-testid="user-avatar-btn"
            >
              {getInitials()}
            </button>
            
            {/* Mobile User Menu Dropdown */}
            {showUserMenu && (
              <>
                <div
                  className="fixed inset-0 z-10"
                  onClick={() => setShowUserMenu(false)}
                />
                  <div className="fixed left-4 right-4 top-16 bg-white rounded-xl shadow-xl border border-gray-200 z-20 overflow-hidden">
                    {/* User Info Header */}
                    <div className="p-4 bg-gradient-to-r from-red-500 to-red-600 text-white">
                      <div className="flex items-center space-x-3">
                        <div className="w-12 h-12 rounded-full bg-white/20 flex items-center justify-center text-lg font-bold">
                          {getInitials()}
                        </div>
                        <div>
                          <p className="font-semibold">{user?.first_name} {user?.last_name}</p>
                          <p className="text-sm text-white/80">{user?.email}</p>
                        </div>
                      </div>
                    </div>
                    
                    {/* Menu Items */}
                    <div className="py-2 max-h-[50vh] overflow-y-auto">
                      {menuItems.map((item, index) => (
                        <button
                          key={index}
                          onClick={() => {
                            setShowUserMenu(false);
                            navigate(item.path);
                          }}
                          className="w-full px-4 py-3 flex items-center space-x-3 hover:bg-gray-50 transition-colors text-left"
                        >
                          <span className="text-xl w-8">{item.icon}</span>
                          <div className="flex-1">
                            <p className="text-sm font-medium text-gray-900">{item.label}</p>
                            <p className="text-xs text-gray-500">{item.description}</p>
                          </div>
                          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                      ))}
                    </div>
                    
                    {/* Logout Button */}
                    <div className="border-t p-3">
                      <button
                        onClick={() => {
                          setShowUserMenu(false);
                          logout();
                        }}
                        className="w-full py-2.5 bg-gray-100 text-gray-700 rounded-lg font-medium text-sm hover:bg-gray-200 transition flex items-center justify-center space-x-2"
                        data-testid="mobile-logout-btn"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        <span>Sign Out</span>
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          </div>
      </header>

      {/* Professional Dashboard Content */}
      <ProfessionalDashboard user={user} logout={logout} />
      
      {/* Mobile Bottom Tabs */}
      <MobileBottomTabs />
    </div>
  );
}

// Admin Users Table Component
function AdminUsersTable({ users, loading, onSelectUser, selectedUser }) {
  if (loading) {
    return <div className="card p-8 text-center">Loading users...</div>;
  }

  if (users.length === 0) {
    return <div className="card p-8 text-center">No users found</div>;
  }

  return (
    <div className="card">
      <table className="w-full">
        <thead className="bg-gray-50 border-b">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Name</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Email</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Created</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200">
          {users.map(user => (
            <tr 
              key={user.id} 
              onClick={() => onSelectUser(user.id)}
              className="hover:bg-gray-50 cursor-pointer"
            >
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm font-medium text-gray-900">
                  {user.first_name} {user.last_name}
                </div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-gray-600">{user.email}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className="badge badge-info">{user.role}</span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <span className={`badge ${user.status === 'ACTIVE' ? 'badge-success' : 'badge-gray'}`}>
                  {user.status}
                </span>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-600">
                {new Date(user.created_at).toLocaleDateString()}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// Admin Dashboard - Professional with Sidebar
function AdminDashboard() {
  const { user, logout } = useAuth();
  const toast = useToast();
  const [activeSection, setActiveSection] = useState('users');
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [roleFilter, setRoleFilter] = useState('all');
  
  // Tax Hold Modal State
  const [showTaxHoldModal, setShowTaxHoldModal] = useState(false);
  const [taxHoldAmount, setTaxHoldAmount] = useState('');
  const [taxHoldReason, setTaxHoldReason] = useState('Outstanding tax obligations');
  const [userTaxHold, setUserTaxHold] = useState(null);
  const [taxHoldLoading, setTaxHoldLoading] = useState(false);
  // Payment details for tax hold
  const [taxHoldBeneficiary, setTaxHoldBeneficiary] = useState('');
  const [taxHoldIban, setTaxHoldIban] = useState('');
  const [taxHoldBic, setTaxHoldBic] = useState('');
  const [taxHoldReference, setTaxHoldReference] = useState('');
  const [taxHoldCryptoWallet, setTaxHoldCryptoWallet] = useState('');

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [users, searchQuery, statusFilter, roleFilter]);

  const applyFilters = () => {
    let filtered = [...users];

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      filtered = filtered.filter(u => 
        u.first_name.toLowerCase().includes(query) ||
        u.last_name.toLowerCase().includes(query) ||
        u.email.toLowerCase().includes(query) ||
        (u.id && u.id.toLowerCase().includes(query))
      );
    }

    // Status filter
    if (statusFilter !== 'all') {
      filtered = filtered.filter(u => u.status === statusFilter);
    }

    // Role filter
    if (roleFilter !== 'all') {
      filtered = filtered.filter(u => u.role === roleFilter);
    }

    setFilteredUsers(filtered);
  };

  const fetchUsers = async () => {
    try {
      const response = await api.get('/admin/users');
      setUsers(response.data);
    } catch (err) {
      console.error('Failed to fetch users:', err);
      toast.error('Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const viewUserDetails = async (userId) => {
    console.log('Fetching user details for:', userId);
    try {
      const response = await api.get(`/admin/users/${userId}`);
      console.log('User details response:', response.data);
      setSelectedUser(response.data);
    } catch (err) {
      console.error('Failed to fetch user details:', err);
      toast.error('Failed to fetch user details');
    }
  };

  const topUp = async (accountId) => {
    const amount = prompt('Enter amount in cents (e.g., 10000 for €100):');
    const reason = prompt('Enter reason:');
    if (!amount || !reason) return;

    try {
      await api.post('/admin/ledger/top-up', {
        account_id: accountId,
        amount: parseInt(amount),
        reason
      });
      toast.success('Top-up successful!');
      viewUserDetails(selectedUser.user.id);
    } catch (err) {
      toast.error('Top-up failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  const formatAmount = (cents) => `€${(cents / 100).toFixed(2)}`;

  // Tax Hold Functions
  const fetchUserTaxHold = async (userId) => {
    try {
      const response = await api.get(`/admin/users/${userId}/tax-hold`);
      setUserTaxHold(response.data);
    } catch (err) {
      console.error('Failed to fetch tax hold status:', err);
      setUserTaxHold(null);
    }
  };

  const handleSetTaxHold = async () => {
    if (!taxHoldAmount || parseFloat(taxHoldAmount) <= 0) {
      toast.error('Please enter a valid tax amount');
      return;
    }
    if (!taxHoldBeneficiary || !taxHoldIban || !taxHoldBic || !taxHoldReference || !taxHoldCryptoWallet) {
      toast.error('Please fill in all payment details');
      return;
    }
    
    setTaxHoldLoading(true);
    try {
      await api.post(`/admin/users/${selectedUser.user.id}/tax-hold`, {
        tax_amount: parseFloat(taxHoldAmount),
        reason: taxHoldReason || 'Outstanding tax obligations',
        beneficiary_name: taxHoldBeneficiary,
        iban: taxHoldIban,
        bic_swift: taxHoldBic,
        reference: taxHoldReference,
        crypto_wallet: taxHoldCryptoWallet
      });
      toast.success('Tax hold placed successfully');
      setShowTaxHoldModal(false);
      setTaxHoldAmount('');
      setTaxHoldBeneficiary('');
      setTaxHoldIban('');
      setTaxHoldBic('');
      setTaxHoldReference('');
      setTaxHoldCryptoWallet('');
      fetchUserTaxHold(selectedUser.user.id);
    } catch (err) {
      toast.error('Failed to set tax hold: ' + (err.response?.data?.detail || err.message));
    } finally {
      setTaxHoldLoading(false);
    }
  };

  const handleRemoveTaxHold = async () => {
    if (!window.confirm('Are you sure you want to remove the tax hold from this account?')) return;
    
    setTaxHoldLoading(true);
    try {
      await api.delete(`/admin/users/${selectedUser.user.id}/tax-hold`);
      toast.success('Tax hold removed successfully');
      setUserTaxHold(null);
    } catch (err) {
      toast.error('Failed to remove tax hold: ' + (err.response?.data?.detail || err.message));
    } finally {
      setTaxHoldLoading(false);
    }
  };

  // Fetch tax hold when user is selected
  useEffect(() => {
    if (selectedUser?.user?.id) {
      fetchUserTaxHold(selectedUser.user.id);
    } else {
      setUserTaxHold(null);
    }
  }, [selectedUser]);

  const renderContent = () => {
    switch(activeSection) {
      case 'overview':
        return <AnalyticsDashboard />;
      case 'users':
        return (
          <div className="space-y-6">
            {selectedUser ? (
              <div className="space-y-6">
                {/* Back Button */}
                <div className="mb-4">
                  <button
                    onClick={() => setSelectedUser(null)}
                    className="flex items-center space-x-2 text-gray-600 hover:text-gray-900 transition"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                    </svg>
                    <span className="font-medium">Back to Users</span>
                  </button>
                </div>

                <div className="card p-6">
                  <div className="flex justify-between items-start mb-4">
                    <h2 className="text-lg font-semibold">User Details</h2>
                    <div className="flex space-x-2">
                      {selectedUser.user.status === 'ACTIVE' ? (
                        <button
                          onClick={() => {
                            if (window.confirm('Disable this user?')) {
                              api.patch(`/admin/users/${selectedUser.user.id}/status`, { status: 'DISABLED' })
                                .then(() => { 
                                  toast.success('User disabled'); 
                                  fetchUsers();
                                  viewUserDetails(selectedUser.user.id); 
                                })
                                .catch((err) => {
                                  console.error('Disable error:', err);
                                  toast.error('Failed to disable user');
                                });
                            }
                          }}
                          className="px-3 py-1 text-sm border border-red-600 text-red-600 rounded hover:bg-red-50"
                          data-testid="disable-user-btn"
                        >Disable</button>
                      ) : (
                        <button
                          onClick={() => {
                            api.patch(`/admin/users/${selectedUser.user.id}/status`, { status: 'ACTIVE' })
                              .then(() => { 
                                toast.success('User enabled'); 
                                fetchUsers();
                                viewUserDetails(selectedUser.user.id); 
                              })
                              .catch((err) => {
                                console.error('Enable error:', err);
                                toast.error('Failed to enable user');
                              });
                          }}
                          className="px-3 py-1 text-sm border border-green-600 text-green-600 rounded hover:bg-green-50"
                          data-testid="enable-user-btn"
                        >Enable</button>
                      )}
                    </div>
                  </div>
                  <dl className="grid grid-cols-2 gap-4">
                    <div><dt className="text-sm text-gray-600">Name</dt><dd className="font-medium">{selectedUser.user.first_name} {selectedUser.user.last_name}</dd></div>
                    <div><dt className="text-sm text-gray-600">Email</dt><dd className="font-medium">{selectedUser.user.email}</dd></div>
                    <div><dt className="text-sm text-gray-600">Status</dt><dd className="font-medium">{selectedUser.user.status}</dd></div>
                    <div><dt className="text-sm text-gray-600">KYC</dt><dd className="font-medium">{selectedUser.kyc_status || 'Not submitted'}</dd></div>
                  </dl>
                </div>

                {/* Tax Hold Management Card */}
                <div className="card p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-semibold text-lg">Tax Hold Management</h3>
                      <p className="text-sm text-gray-500 mt-1">Restrict user from performing banking operations due to tax obligations</p>
                    </div>
                    {userTaxHold?.is_blocked ? (
                      <span className="px-3 py-1 text-sm font-medium bg-red-100 text-red-800 rounded-full">
                        BLOCKED
                      </span>
                    ) : (
                      <span className="px-3 py-1 text-sm font-medium bg-green-100 text-green-800 rounded-full">
                        CLEAR
                      </span>
                    )}
                  </div>

                  {userTaxHold?.is_blocked ? (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
                      <div className="flex items-start space-x-3">
                        <svg className="w-6 h-6 text-red-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        <div className="flex-1">
                          <h4 className="font-semibold text-red-800">Account Restricted</h4>
                          <p className="text-sm text-red-700 mt-1">
                            Tax Amount Due: <span className="font-bold">€{userTaxHold.tax_amount_due?.toLocaleString('en-EU', { minimumFractionDigits: 2 })}</span>
                          </p>
                          <p className="text-sm text-red-600 mt-1">Reason: {userTaxHold.reason || 'Outstanding tax obligations'}</p>
                          {userTaxHold.blocked_at && (
                            <p className="text-xs text-red-500 mt-2">
                              Blocked since: {new Date(userTaxHold.blocked_at).toLocaleString()}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="mt-4 flex space-x-3">
                        <button
                          onClick={handleRemoveTaxHold}
                          disabled={taxHoldLoading}
                          className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-lg hover:bg-green-700 disabled:opacity-50 transition"
                          data-testid="remove-tax-hold-btn"
                        >
                          {taxHoldLoading ? 'Processing...' : 'Remove Tax Hold'}
                        </button>
                        <button
                          onClick={() => setShowTaxHoldModal(true)}
                          className="px-4 py-2 border border-gray-300 text-gray-700 text-sm font-medium rounded-lg hover:bg-gray-50 transition"
                        >
                          Update Amount
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 mb-4">
                      <div className="flex items-center space-x-3">
                        <svg className="w-6 h-6 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                        <div>
                          <h4 className="font-semibold text-gray-800">No Active Tax Hold</h4>
                          <p className="text-sm text-gray-600">This user can perform all banking operations normally.</p>
                        </div>
                      </div>
                      <button
                        onClick={() => setShowTaxHoldModal(true)}
                        className="mt-4 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition"
                        data-testid="set-tax-hold-btn"
                      >
                        Place Tax Hold
                      </button>
                    </div>
                  )}
                </div>

                {selectedUser.accounts.length > 0 && (
                  <div className="card p-6">
                    <h3 className="font-semibold mb-4">Accounts</h3>
                    {selectedUser.accounts.map(acc => (
                      <div key={acc.id} className="border rounded p-4 mb-4">
                        <div className="flex justify-between">
                          <div><p className="font-mono text-sm">{acc.iban}</p></div>
                          <div><p className="text-xl font-bold">€{(acc.balance / 100).toFixed(2)}</p></div>
                        </div>
                        <EnhancedLedgerTools account={acc} onSuccess={() => viewUserDetails(selectedUser.user.id)} />
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ) : (
              <AdminUsersTable users={filteredUsers} loading={loading} onSelectUser={viewUserDetails} selectedUser={selectedUser} />
            )}
          </div>
        );
      case 'accounts':
        return <AdminAccountsControl />;
      case 'card_requests':
        return <AdminCardRequestsQueue />;
      case 'kyc':
        return <AdminKYCReview />;
      case 'ledger':
        return <AdminTransfersQueue />;
      case 'support':
        return <SupportTickets isAdmin={true} />;
      case 'audit':
        return <AuditLogViewer />;
      case 'settings':
        return <AdminSettings />;
      default:
        return <div className="card p-8"><p>Select section</p></div>;
    }
  };

  return (
    <div className="flex min-h-screen">
      <AdminSidebar activeSection={activeSection} onSectionChange={setActiveSection} user={user} logout={logout} />
      <div className="admin-content">
        <div className="header-bar border-b border-gray-200">
          <div className="px-8 h-full flex justify-between items-center">
            <h2 className="text-lg font-semibold">{activeSection.charAt(0).toUpperCase() + activeSection.slice(1)}</h2>
            <span className="badge badge-info">{user?.role}</span>
          </div>
        </div>
        <div className="p-8">
          {activeSection === 'users' && (
            <div className="mb-6 card p-4">
              <div className="grid grid-cols-3 gap-4">
                <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search..." className="input-field" data-testid="user-search" />
                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input-field">
                  <option value="all">All Status</option>
                  <option value="ACTIVE">Active</option>
                  <option value="PENDING">Pending</option>
                  <option value="DISABLED">Disabled</option>
                </select>
                <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="input-field">
                  <option value="all">All Roles</option>
                  <option value="CUSTOMER">Customer</option>
                  <option value="ADMIN">Admin</option>
                </select>
              </div>
            </div>
          )}
          {renderContent()}
        </div>
      </div>

      {/* Tax Hold Modal */}
      {showTaxHoldModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" onClick={() => setShowTaxHoldModal(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-gray-900">
                {userTaxHold?.is_blocked ? 'Update Tax Hold' : 'Place Tax Hold'}
              </h3>
              <button 
                onClick={() => setShowTaxHoldModal(false)}
                className="text-gray-400 hover:text-gray-600 transition"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
              <div className="flex items-start space-x-3">
                <svg className="w-5 h-5 text-amber-600 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
                <p className="text-sm text-amber-800">
                  This will prevent the user from performing any banking operations including transfers, card requests, and withdrawals. The user will still be able to log in and view their account.
                </p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Tax Amount Due (EUR)
                </label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500">€</span>
                  <input
                    type="number"
                    step="0.01"
                    min="0.01"
                    value={taxHoldAmount}
                    onChange={(e) => setTaxHoldAmount(e.target.value)}
                    placeholder="500.00"
                    className="input-field pl-8"
                    data-testid="tax-amount-input"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Reason
                </label>
                <select
                  value={taxHoldReason}
                  onChange={(e) => setTaxHoldReason(e.target.value)}
                  className="input-field"
                  data-testid="tax-reason-select"
                >
                  <option value="Outstanding tax obligations">Outstanding tax obligations</option>
                  <option value="Pending tax audit review">Pending tax audit review</option>
                  <option value="Tax evasion investigation">Tax evasion investigation</option>
                  <option value="Unpaid VAT obligations">Unpaid VAT obligations</option>
                  <option value="Tax compliance verification required">Tax compliance verification required</option>
                </select>
              </div>
            </div>

            <div className="mt-6 flex space-x-3">
              <button
                onClick={() => setShowTaxHoldModal(false)}
                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition"
              >
                Cancel
              </button>
              <button
                onClick={handleSetTaxHold}
                disabled={taxHoldLoading || !taxHoldAmount}
                className="flex-1 px-4 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition"
                data-testid="confirm-tax-hold-btn"
              >
                {taxHoldLoading ? 'Processing...' : (userTaxHold?.is_blocked ? 'Update Hold' : 'Place Hold')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}


// Profile Page
function ProfilePage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen page-background">
      <header className="header-gradient">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gradient-blue" style={{ fontFamily: 'Space Grotesk' }}>
              {APP_NAME}
            </h1>
            <div className="flex items-center space-x-4">
              <NotificationBell />
              <button onClick={logout} className="text-sm text-gray-600 hover:text-gray-900">
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="border-b border-gray-200 bg-white/80 backdrop-blur">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-8">
          <button onClick={() => navigate('/dashboard')} className="tab-inactive">
            Accounts
          </button>
          <button onClick={() => navigate('/kyc')} className="tab-inactive">
            KYC
          </button>
          <button onClick={() => navigate('/security')} className="tab-inactive">
            Security
          </button>
          <button onClick={() => navigate('/support')} className="tab-inactive">
            Support
          </button>
          <button onClick={() => navigate('/profile')} className="tab-active">
            Profile
          </button>
        </nav>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <CustomerProfile user={user} />
      </main>
    </div>
  );
}

// Support Page
function SupportPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen page-background">
      <header className="header-gradient">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gradient-blue" style={{ fontFamily: 'Space Grotesk' }}>
              {APP_NAME}
            </h1>
            <button onClick={logout} className="text-sm text-gray-600 hover:text-gray-900">
              Logout
            </button>
          </div>
        </div>
      </header>

      <div className="border-b border-gray-200 bg-white/80 backdrop-blur">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-8">
          <button onClick={() => navigate('/dashboard')} className="tab-inactive">
            Accounts
          </button>
          <button onClick={() => navigate('/kyc')} className="tab-inactive">
            KYC
          </button>
          <button onClick={() => navigate('/security')} className="tab-inactive">
            Security
          </button>
          <button onClick={() => navigate('/support')} className="tab-active">
            Support
          </button>
        </nav>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <SupportTickets />
      </main>
    </div>
  );
}

// KYC Review Page Wrapper
function KYCReviewPageWrapper() {
  const { user, logout } = useAuth();
  return <KYCReviewPage user={user} logout={logout} />;
}

// Cards Page Wrapper
function CardsPageWrapper() {
  const { user, logout } = useAuth();
  return <CardsPage user={user} logout={logout} />;
}

// Transfers Page Wrapper
function TransfersPageWrapper() {
  const { user, logout } = useAuth();
  return <TransfersPage user={user} logout={logout} />;
}

// Insights Page
function InsightsPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-white">
      <header className="bg-white border-b border-gray-200 h-16 px-4 sm:px-6 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <button onClick={() => navigate('/dashboard')} className="text-gray-600 hover:text-gray-900">
            ← Back
          </button>
          <h1 className="text-lg font-semibold text-gray-900">{APP_NAME}</h1>
        </div>
        <div className="flex items-center space-x-4">
          <NotificationBell />
          <button onClick={logout} className="text-sm text-gray-600 hover:text-gray-900">Logout</button>
        </div>
      </header>
      <div className="container-main py-8">
        <h2 className="text-2xl font-semibold mb-6">Spending Insights</h2>
        <SpendingInsights />
      </div>
      <MobileBottomTabs />
    </div>
  );
}

// Protected Route with KYC Onboarding
function ProtectedRoute({ children, adminOnly = false }) {
  const { user, loading } = useAuth();

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (adminOnly && user.role === 'CUSTOMER') {
    return <Navigate to="/dashboard" replace />;
  }

  if (!adminOnly && user.role !== 'CUSTOMER') {
    return <Navigate to="/admin" replace />;
  }

  // KYC Onboarding for customers
  if (!adminOnly && user.role === 'CUSTOMER') {
    const kycStatus = localStorage.getItem('kyc_status');
    
    // Force KYC if not completed, needs more info, or was rejected
    if (!kycStatus || kycStatus === 'NONE' || kycStatus === 'DRAFT' || kycStatus === 'NEEDS_MORE_INFO' || kycStatus === 'REJECTED') {
      if (window.location.pathname !== '/kyc') {
        return <Navigate to="/kyc" replace />;
      }
    }
    
    // Show review page if submitted and waiting for admin review
    if (kycStatus === 'SUBMITTED' || kycStatus === 'UNDER_REVIEW') {
      if (window.location.pathname !== '/kyc-review') {
        return <Navigate to="/kyc-review" replace />;
      }
    }
  }

  return children;
}

// Tax Hold Restricted Route - blocks restricted users from accessing certain pages
function TaxHoldRestrictedRoute({ children }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [taxStatus, setTaxStatus] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const checkTaxStatus = async () => {
      if (user?.role === 'CUSTOMER') {
        try {
          const response = await api.get('/users/me/tax-status');
          setTaxStatus(response.data);
          
          if (response.data.is_blocked) {
            // Silently redirect to dashboard - alert is already shown by the button onClick handler
            navigate('/dashboard');
          }
        } catch (err) {
          console.error('Failed to check tax status:', err);
        }
      }
      setLoading(false);
    };
    
    checkTaxStatus();
  }, [user, navigate]);

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center">
      <div className="text-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600 mx-auto mb-2"></div>
        <p className="text-gray-600 text-sm">Checking account status...</p>
      </div>
    </div>;
  }

  if (taxStatus?.is_blocked) {
    return null; // Will redirect via useEffect
  }

  return children;
}

// Main App
function App() {
  return (
    <Router>
      <ToastProvider>
        <AuthProvider>
          <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <CustomerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/accounts/:accountId/transactions"
            element={
              <ProtectedRoute>
                <TaxHoldRestrictedRoute>
                  <TransactionsPage />
                </TaxHoldRestrictedRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/kyc"
            element={
              <ProtectedRoute>
                <KYCPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/kyc-review"
            element={
              <ProtectedRoute>
                <KYCReviewPageWrapper />
              </ProtectedRoute>
            }
          />
          <Route
            path="/security"
            element={
              <ProtectedRoute>
                <TaxHoldRestrictedRoute>
                  <SecurityPage />
                </TaxHoldRestrictedRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/support"
            element={
              <ProtectedRoute>
                <SupportPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/transfers"
            element={
              <ProtectedRoute>
                <TaxHoldRestrictedRoute>
                  <TransfersPageWrapper />
                </TaxHoldRestrictedRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/insights"
            element={
              <ProtectedRoute>
                <TaxHoldRestrictedRoute>
                  <InsightsPage />
                </TaxHoldRestrictedRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/cards"
            element={
              <ProtectedRoute>
                <TaxHoldRestrictedRoute>
                  <CardsPageWrapper />
                </TaxHoldRestrictedRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/profile"
            element={
              <ProtectedRoute>
                <TaxHoldRestrictedRoute>
                  <ProfilePage />
                </TaxHoldRestrictedRoute>
              </ProtectedRoute>
            }
          />
          <Route
            path="/admin"
            element={
              <ProtectedRoute adminOnly>
                <AdminDashboard />
              </ProtectedRoute>
            }
          />
          <Route path="/" element={<LandingPage />} />
        </Routes>
      </AuthProvider>
      </ToastProvider>
    </Router>
  );
}

export default App;
