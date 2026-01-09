import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate, useParams } from 'react-router-dom';
import './App.css';
import api from './api';
import { APP_NAME } from './config';
import { SecuritySettings } from './components/Security';
import { KYCApplication } from './components/KYC';
import { AdminKYCReview } from './components/AdminKYC';
import { TransactionsList } from './components/Transactions';

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
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full space-y-8 p-8 bg-white rounded-lg shadow">
        <div>
          <h2 className="text-3xl font-bold text-center" style={{ fontFamily: 'Space Grotesk' }}>
            {APP_NAME}
          </h2>
          <p className="mt-2 text-center text-gray-600">Sign in to your account</p>
        </div>
        <form onSubmit={handleSubmit} className="mt-8 space-y-6">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-800 rounded p-3 text-sm">
              {error}
            </div>
          )}
          <div>
            <label className="block text-sm font-medium text-gray-700">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              data-testid="email-input"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              data-testid="password-input"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
            data-testid="login-button"
          >
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
          <div className="text-sm text-center text-gray-600">
            <p className="mt-2">Demo credentials:</p>
            <p>Customer: customer@demo.com / Demo@123456</p>
            <p>Admin: admin@atlas.local / Admin@123456</p>
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

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-6">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-semibold">Your Accounts</h2>
            {accounts.length === 0 && (
              <button
                onClick={createAccount}
                className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                data-testid="create-account-button"
              >
                Create Account
              </button>
            )}
          </div>

          {loading ? (
            <div className="text-center py-8">Loading...</div>
          ) : accounts.length === 0 ? (
            <div className="bg-white rounded-lg shadow p-8 text-center">
              <p className="text-gray-600">No accounts yet. Create your first account to get started!</p>
            </div>
          ) : (
            <div className="grid gap-6">
              {accounts.map((account) => (
                <div key={account.id} className="bg-white rounded-lg shadow p-6">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="text-sm text-gray-600">Account</p>
                      <p className="text-lg font-semibold font-mono">{account.account_number}</p>
                      <p className="text-sm text-gray-600 mt-2">IBAN</p>
                      <p className="text-base font-mono">{account.iban}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-gray-600">Balance</p>
                      <p className="text-3xl font-bold" style={{ color: 'hsl(162, 85%, 27%)' }}>
                        {formatAmount(account.balance)}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">{account.currency}</p>
                    </div>
                  </div>
                  <button
                    onClick={() => navigate(`/accounts/${account.id}/transactions`)}
                    className="mt-4 text-sm text-blue-600 hover:text-blue-700"
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
  const [activeTab, setActiveTab] = useState('users'); // users, kyc
  const [users, setUsers] = useState([]);
  const [selectedUser, setSelectedUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchUsers();
  }, []);

  const fetchUsers = async () => {
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
    try {
      const response = await api.get(`/admin/users/${userId}`);
      setSelectedUser(response.data);
    } catch (err) {
      alert('Failed to fetch user details');
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
        </nav>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'users' ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Users List */}
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow">
              <div className="p-4 border-b">
                <h2 className="text-lg font-semibold">Users</h2>
              </div>
              <div className="divide-y max-h-[600px] overflow-y-auto">
                {loading ? (
                  <div className="p-4 text-center">Loading...</div>
                ) : (
                  users.map((u) => (
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
                <div className="bg-white rounded-lg shadow p-6">
                  <h2 className="text-lg font-semibold mb-4">User Details</h2>
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
                          <div className="mt-4 flex space-x-2">
                            <button
                              onClick={() => topUp(acc.id)}
                              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                              data-testid={`topup-${acc.id}`}
                            >
                              Top Up
                            </button>
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
        ) : (
          <AdminKYCReview />
        )}
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
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
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
    </Router>
  );
}

export default App;