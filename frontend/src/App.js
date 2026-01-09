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

// Signup Page
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
      alert('Account created successfully! You can now login.');
      navigate('/login');
    } catch (err) {
      setError(err.response?.data?.detail || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center hero-gradient">
      <div className="max-w-md w-full space-y-8 p-8 bg-white/95 backdrop-blur rounded-xl shadow-blue border border-blue-100">
        <div className="blue-corner">
          <h2 className="text-3xl font-bold text-center text-gradient-blue" style={{ fontFamily: 'Space Grotesk' }}>
            {APP_NAME}
          </h2>
          <p className="mt-2 text-center text-gray-600">Create your account</p>
        </div>
        <form onSubmit={handleSubmit} className="mt-8 space-y-4">
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
                className="input-enhanced w-full"
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
                className="input-enhanced w-full"
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
              className="input-enhanced w-full"
              data-testid="signup-email"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">Phone (Optional)</label>
            <input
              type="tel"
              value={formData.phone}
              onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
              className="input-enhanced w-full"
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
              className="input-enhanced w-full"
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
              className="input-enhanced w-full"
              data-testid="signup-confirm-password"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full btn-primary btn-glow"
            data-testid="signup-button"
          >
            {loading ? 'Creating Account...' : 'Create Account'}
          </button>

          <div className="text-center pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600">
              Already have an account?{' '}
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="text-blue-600 hover:text-blue-700 font-medium"
                data-testid="goto-login"
              >
                Sign in
              </button>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}

// Login Page
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
    <div className="min-h-screen flex items-center justify-center hero-gradient">
      <div className="max-w-md w-full space-y-8 p-8 bg-white/95 backdrop-blur rounded-xl shadow-blue border border-blue-100">
        <div className="blue-corner">
          <h2 className="text-3xl font-bold text-center text-gradient-blue" style={{ fontFamily: 'Space Grotesk' }}>
            {APP_NAME}
          </h2>
          <p className="mt-2 text-center text-gray-600">Sign in to your account</p>
        </div>
        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
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
              className="input-enhanced w-full"
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
              className="input-enhanced w-full"
              data-testid="password-input"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full btn-primary btn-glow"
            data-testid="login-button"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>

          <div className="text-center pt-4 border-t border-gray-200">
            <p className="text-sm text-gray-600 mb-3">
              Don't have an account?{' '}
              <button
                type="button"
                onClick={() => navigate('/signup')}
                className="text-blue-600 hover:text-blue-700 font-medium"
                data-testid="goto-signup"
              >
                Create Account
              </button>
            </p>
            <p className="text-xs font-medium text-gray-700 mb-1">Demo credentials:</p>
            <p className="text-xs text-gray-600">Customer: customer@demo.com / Demo@123456</p>
            <p className="text-xs text-gray-600">Admin: admin@atlas.local / Admin@123456</p>
          </div>
        </form>
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
            {/* Account Summary */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-start">
                <div>
                  <p className="text-sm text-gray-600">Account</p>
                  <p className="text-lg font-semibold font-mono">{account.account_number}</p>
                  <p className="text-sm text-gray-600 mt-2">IBAN</p>
                  <p className="font-mono">{account.iban}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm text-gray-600">Current Balance</p>
                  <p className="text-3xl font-bold" style={{ color: 'hsl(162, 85%, 27%)' }}>
                    {formatAmount(account.balance)}
                  </p>
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

// Customer Dashboard
function CustomerDashboard() {
  const { user, logout } = useAuth();
  const [accounts, setAccounts] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await api.get('/accounts');
      setAccounts(response.data);
    } catch (err) {
      console.error('Failed to fetch accounts:', err);
    } finally {
      setLoading(false);
    }
  };

  const createAccount = async () => {
    try {
      await api.post('/accounts/create');
      fetchAccounts();
    } catch (err) {
      alert('Failed to create account');
    }
  };

  const formatAmount = (cents) => {
    return `€${(cents / 100).toFixed(2)}`;
  };

  return (
    <div className="min-h-screen page-background">
      {/* Header */}
      <header className="header-gradient">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gradient-blue" style={{ fontFamily: 'Space Grotesk' }}>
              {APP_NAME}
            </h1>
            <div className="flex items-center space-x-4">
              <NotificationBell />
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
      <div className="border-b border-gray-200 bg-white/80 backdrop-blur">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => navigate('/dashboard')}
            className="tab-active"
            data-testid="accounts-tab"
          >
            Accounts
          </button>
          <button
            onClick={() => navigate('/kyc')}
            className="tab-inactive"
            data-testid="kyc-tab"
          >
            KYC
          </button>
          <button
            onClick={() => navigate('/security')}
            className="tab-inactive"
            data-testid="security-tab"
          >
            Security
          </button>
          <button
            onClick={() => navigate('/support')}
            className="tab-inactive"
            data-testid="support-tab"
          >
            Support
          </button>
        </nav>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Your Accounts</h2>
            {accounts.length === 0 && (
              <button
                onClick={createAccount}
                className="btn-primary btn-glow"
                data-testid="create-account-button"
              >
                Create Account
              </button>
            )}
          </div>

          {loading ? (
            <div className="text-center py-8">
              <div className="skeleton h-32 rounded-lg"></div>
            </div>
          ) : accounts.length === 0 ? (
            <div className="card-blue-accent p-8 text-center animate-card">
              <div className="circle-pattern">
                <p className="text-gray-600">No accounts yet. Create your first account to get started!</p>
              </div>
            </div>
          ) : (
            <div className="grid gap-6">
              {accounts.map((account) => (
                <div key={account.id} className="balance-card p-6 hover-lift corner-accent animate-card">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-sm text-gray-600 font-medium">Account</p>
                      <p className="text-lg font-semibold font-mono mt-1">{account.account_number}</p>
                      <p className="text-sm text-gray-600 font-medium mt-3">IBAN</p>
                      <p className="text-base font-mono mt-1">{account.iban}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600 font-medium">Balance</p>
                      <p className="text-4xl font-bold balance-display mt-1">
                        {formatAmount(account.balance)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">{account.currency}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => navigate(`/accounts/${account.id}/transactions`)}
                    className="mt-6 text-sm text-blue-600 hover:text-blue-700 font-medium"
                    data-testid={`view-transactions-${account.id}`}
                  >
                    View Transactions →
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

// Admin Dashboard
function AdminDashboard() {
  const { user, logout } = useAuth();
  const [activeTab, setActiveTab] = useState('users'); // users, kyc, audit
  const [users, setUsers] = useState([]);
  const [filteredUsers, setFilteredUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState('all');
  const [roleFilter, setRoleFilter] = useState('all');
  const navigate = useNavigate();

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [users, searchQuery, statusFilter, roleFilter]);

  const applyFilters = () => {
    try {
      const response = await api.get('/admin/users');
      setUsers(response.data);
    } catch (err) {
      console.error('Failed to fetch users:', err);
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
      alert('Failed to fetch user details: ' + (err.response?.data?.detail || err.message));
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
      alert('Top-up successful!');
      viewUserDetails(selectedUser.user.id);
    } catch (err) {
      alert('Top-up failed: ' + (err.response?.data?.detail || err.message));
    }
  };

  const formatAmount = (cents) => `€${(cents / 100).toFixed(2)}`;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold" style={{ fontFamily: 'Space Grotesk' }}>
              {APP_NAME} Admin
            </h1>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600 font-medium">
                {user?.role}
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

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 bg-white">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-8">
          <button
            onClick={() => setActiveTab('users')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'users'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            data-testid="admin-users-tab"
          >
            User Management
          </button>
          <button
            onClick={() => setActiveTab('kyc')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'kyc'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            data-testid="admin-kyc-tab"
          >
            KYC Review
          </button>
          <button
            onClick={() => setActiveTab('support')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'support'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            data-testid="admin-support-tab"
          >
            Support Tickets
          </button>
          <button
            onClick={() => setActiveTab('audit')}
            className={`py-4 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'audit'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
            data-testid="admin-audit-tab"
          >
            Audit Logs
          </button>
        </nav>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'users' ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Users List */}
          <div className="lg:col-span-1">
            <div className="card-enhanced">
              <div className="p-4 border-b bg-blue-50/30">
                <h2 className="text-lg font-semibold">Users</h2>
                <p className="text-sm text-gray-600 mt-1">{filteredUsers.length} user(s)</p>
              </div>
              
              {/* Search and Filters */}
              <div className="p-4 space-y-3 border-b bg-gray-50/50">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by name, email..."
                  className="input-enhanced w-full text-sm"
                  data-testid="user-search"
                />
                <div className="grid grid-cols-2 gap-2">
                  <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    className="input-enhanced text-sm"
                    data-testid="status-filter"
                  >
                    <option value="all">All Status</option>
                    <option value="ACTIVE">Active</option>
                    <option value="PENDING">Pending</option>
                    <option value="DISABLED">Disabled</option>
                  </select>
                  <select
                    value={roleFilter}
                    onChange={(e) => setRoleFilter(e.target.value)}
                    className="input-enhanced text-sm"
                    data-testid="role-filter"
                  >
                    <option value="all">All Roles</option>
                    <option value="CUSTOMER">Customer</option>
                    <option value="ADMIN">Admin</option>
                    <option value="SUPER_ADMIN">Super Admin</option>
                  </select>
                </div>
                {(searchQuery || statusFilter !== 'all' || roleFilter !== 'all') && (
                  <button
                    onClick={() => {
                      setSearchQuery('');
                      setStatusFilter('all');
                      setRoleFilter('all');
                    }}
                    className="text-xs text-blue-600 hover:text-blue-700"
                    data-testid="clear-user-filters"
                  >
                    Clear filters
                  </button>
                )}
              </div>
              
              <div className="divide-y max-h-[600px] overflow-y-auto">
                {loading ? (
                  <div className="p-4 text-center">Loading...</div>
                ) : filteredUsers.length === 0 ? (
                  <div className="p-4 text-center text-gray-600">
                    No users match your filters
                  </div>
                ) : (
                  filteredUsers.map((u) => (
                    <div
                      key={u.id}
                      onClick={() => viewUserDetails(u.id)}
                      className="p-4 hover:bg-gray-50 cursor-pointer"
                      data-testid={`user-${u.id}`}
                    >
                      <p className="font-medium">{u.first_name} {u.last_name}</p>
                      <p className="text-sm text-gray-600">{u.email}</p>
                      <div className="flex items-center space-x-2 mt-1">
                        <span className={`text-xs px-2 py-1 rounded ${
                          u.status === 'ACTIVE' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'
                        }`}>
                          {u.status}
                        </span>
                        <span className="text-xs text-gray-500">{u.role}</span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* User Details */}
          <div className="lg:col-span-2">
            {selectedUser ? (
              <div className="space-y-6">
                {/* User Info */}
                <div className="card-enhanced p-6">
                  <div className="flex justify-between items-start mb-4">
                    <h2 className="text-lg font-semibold">User Details</h2>
                    <div className="flex space-x-2">
                      {selectedUser.user.status === 'ACTIVE' ? (
                        <button
                          onClick={async () => {
                            if (window.confirm('Disable this user? They will not be able to login.')) {
                              try {
                                await api.patch(`/admin/users/${selectedUser.user.id}/status`, { status: 'DISABLED' });
                                alert('User disabled successfully');
                                viewUserDetails(selectedUser.user.id);
                              } catch (err) {
                                alert('Failed to disable user');
                              }
                            }
                          }}
                          className="px-3 py-1 text-sm border border-red-600 text-red-600 rounded hover:bg-red-50"
                          data-testid="disable-user-btn"
                        >
                          Disable User
                        </button>
                      ) : (
                        <button
                          onClick={async () => {
                            try {
                              await api.patch(`/admin/users/${selectedUser.user.id}/status`, { status: 'ACTIVE' });
                              alert('User enabled successfully');
                              viewUserDetails(selectedUser.user.id);
                            } catch (err) {
                              alert('Failed to enable user');
                            }
                          }}
                          className="px-3 py-1 text-sm border border-green-600 text-green-600 rounded hover:bg-green-50"
                          data-testid="enable-user-btn"
                        >
                          Enable User
                        </button>
                      )}
                      <button
                        onClick={async () => {
                          if (window.confirm('Revoke all active sessions for this user? They will be logged out from all devices.')) {
                            try {
                              await api.post(`/admin/users/${selectedUser.user.id}/revoke-sessions`);
                              alert('All sessions revoked successfully');
                            } catch (err) {
                              alert('Failed to revoke sessions');
                            }
                          }
                        }}
                        className="px-3 py-1 text-sm border border-orange-600 text-orange-600 rounded hover:bg-orange-50"
                        data-testid="revoke-sessions-btn"
                      >
                        Revoke Sessions
                      </button>
                    </div>
                  </div>
                  <dl className="grid grid-cols-2 gap-4">
                    <div>
                      <dt className="text-sm text-gray-600">Name</dt>
                      <dd className="font-medium">{selectedUser.user.first_name} {selectedUser.user.last_name}</dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">Email</dt>
                      <dd className="font-medium">{selectedUser.user.email}</dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">Status</dt>
                      <dd className="font-medium">{selectedUser.user.status}</dd>
                    </div>
                    <div>
                      <dt className="text-sm text-gray-600">KYC Status</dt>
                      <dd className="font-medium">{selectedUser.kyc_status || 'Not submitted'}</dd>
                    </div>
                  </dl>
                </div>

                {/* Accounts */}
                <div className="bg-white rounded-lg shadow">
                  <div className="p-4 border-b">
                    <h3 className="text-lg font-semibold">Accounts</h3>
                  </div>
                  <div className="p-4 space-y-4">
                    {selectedUser.accounts.length === 0 ? (
                      <p className="text-gray-600">No accounts</p>
                    ) : (
                      selectedUser.accounts.map((acc) => (
                        <div key={acc.id} className="border rounded p-4">
                          <div className="flex justify-between items-start">
                            <div>
                              <p className="font-mono text-sm">{acc.account_number}</p>
                              <p className="font-mono text-xs text-gray-600 mt-1">{acc.iban}</p>
                            </div>
                            <div className="text-right">
                              <p className="text-2xl font-bold" style={{ color: 'hsl(162, 85%, 27%)' }}>
                                {formatAmount(acc.balance)}
                              </p>
                              <p className="text-xs text-gray-500">{acc.currency}</p>
                            </div>
                          </div>
                          <div className="mt-4">
                            <EnhancedLedgerTools 
                              account={acc} 
                              onSuccess={() => viewUserDetails(selectedUser.user.id)}
                            />
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow p-12 text-center">
                <p className="text-gray-600">Select a user to view details</p>
              </div>
            )}
          </div>
        </div>
        ) : activeTab === 'kyc' ? (
          <AdminKYCReview />
        ) : activeTab === 'support' ? (
          <SupportTickets isAdmin={true} />
        ) : (
          <AuditLogViewer />
        )}
      </main>
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

// Protected Route
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
                <TransactionsPage />
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
            path="/security"
            element={
              <ProtectedRoute>
                <SecurityPage />
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
            path="/profile"
            element={
              <ProtectedRoute>
                <ProfilePage />
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
          <Route path="/" element={<Navigate to="/login" replace />} />
        </Routes>
      </AuthProvider>
      </ToastProvider>
    </Router>
  );
}

export default App;