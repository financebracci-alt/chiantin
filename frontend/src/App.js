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
import { AdminTransfersQueue } from './components/AdminTransfersQueue';
import { AdminAccountsControl } from './components/AdminAccountsControl';

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

// Customer Dashboard - Professional UI
function CustomerDashboard() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-white">
      {/* Simple Professional Header */}
      <header className="header-bar">
        <div className="container-main h-full flex justify-between items-center">
          <h1 className="text-lg font-semibold text-gray-900">{APP_NAME}</h1>
          <div className="flex items-center space-x-4">
            <NotificationBell />
            <button onClick={logout} className="text-sm text-gray-600 hover:text-gray-900" data-testid="logout-button">
              Logout
            </button>
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

  const renderContent = () => {
    switch(activeSection) {
      case 'overview':
        return <AnalyticsDashboard />;
      case 'users':
        return (
          <div className="space-y-6">
            {selectedUser ? (
              <div className="space-y-6">
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
      <header className="header-bar">
        <div className="container-main h-full flex justify-between items-center">
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
    
    // Force KYC if not completed
    if (!kycStatus || kycStatus === 'NONE' || kycStatus === 'DRAFT') {
      if (window.location.pathname !== '/kyc') {
        return <Navigate to="/kyc" replace />;
      }
    }
    
    // Show review page if submitted
    if (kycStatus === 'SUBMITTED' || kycStatus === 'UNDER_REVIEW') {
      if (window.location.pathname !== '/kyc-review') {
        return <Navigate to="/kyc-review" replace />;
      }
    }
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
            path="/transfers"
            element={
              <ProtectedRoute>
                <TransfersPageWrapper />
              </ProtectedRoute>
            }
          />
          <Route
            path="/insights"
            element={
              <ProtectedRoute>
                <InsightsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/cards"
            element={
              <ProtectedRoute>
                <CardsPageWrapper />
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
