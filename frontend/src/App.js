import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate, useParams, useLocation } from 'react-router-dom';
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
import { AdminNotificationBell } from './components/AdminNotificationBell';
import { LandingPage } from './components/LandingPage';
import { useLanguage, useTheme } from './contexts/AppContext';
import { useBalanceVisibility, formatBalance } from './hooks/useBalanceVisibility';
import BalanceToggle from './components/BalanceToggle';
import { Sun, Moon, Mail, CheckCircle, XCircle, Loader2, Eye, EyeOff } from 'lucide-react';

// Styled Logo Component - displays "ecomm" with "bx" in red
const StyledLogo = ({ className = '', isDark = false }) => (
  <span className={className}>
    <span className={isDark ? 'text-white' : ''}>ecomm</span>
    <span className="text-red-500">bx</span>
  </span>
);

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
  const [signupSuccess, setSignupSuccess] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);
  const { signup } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    // Validate
    if (formData.password !== formData.confirmPassword) {
      setError(t('passwordsDoNotMatch') || 'Passwords do not match');
      return;
    }

    if (formData.password.length < 8) {
      setError(t('passwordMinLength') || 'Password must be at least 8 characters');
      return;
    }

    setLoading(true);
    try {
      await signup({
        email: formData.email,
        password: formData.password,
        first_name: formData.first_name,
        last_name: formData.last_name,
        phone: formData.phone || undefined,
        language: language
      });
      setRegisteredEmail(formData.email);
      setSignupSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || t('signupFailed') || 'Signup failed');
    } finally {
      setLoading(false);
    }
  };

  // Show success screen after signup
  if (signupSuccess) {
    return (
      <div className={`min-h-screen flex flex-col ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
        <div className={`flex justify-end items-center p-4 space-x-2`}>
          <button
            onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
            className={`px-3 py-1.5 rounded-lg font-bold text-sm transition ${isDark ? 'bg-gray-800 hover:bg-gray-700 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
          >
            {language === 'en' ? 'EN' : 'IT'}
          </button>
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-lg transition ${isDark ? 'hover:bg-gray-800 text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}
          >
            {isDark ? <Sun size={20} /> : <Moon size={20} />}
          </button>
        </div>
        <div className="flex-1 flex items-center justify-center p-4">
          <div className={`w-full max-w-md rounded-xl shadow-xl p-8 text-center ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white'}`}>
            <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
              <Mail className="w-8 h-8 text-green-600" />
            </div>
            <h2 className={`text-2xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {t('checkYourEmail')}
            </h2>
            <p className={`mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('checkYourEmailDesc')}
            </p>
            <div className={`p-4 rounded-lg mb-6 ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}>
              <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{registeredEmail}</p>
            </div>
            <p className={`text-sm mb-6 ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
              {t('dontSeeEmail')}
            </p>
            <button
              onClick={() => navigate('/login')}
              className="w-full bg-[#dc3545] hover:bg-[#c82333] text-white py-3 rounded-lg font-semibold transition"
            >
              {t('goToLogin')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen flex flex-col ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header with Language/Theme toggles */}
      <div className={`flex justify-end items-center p-4 space-x-2`}>
        {/* Language Toggle */}
        <button
          onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
          className={`px-3 py-1.5 rounded-lg font-bold text-sm transition ${isDark ? 'bg-gray-800 hover:bg-gray-700 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
          title={language === 'en' ? 'Switch to Italian' : 'Passa all\'Inglese'}
        >
          {language === 'en' ? 'EN' : 'IT'}
        </button>
        
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className={`p-2 rounded-lg transition ${isDark ? 'hover:bg-gray-800 text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}
          title={isDark ? t('lightMode') : t('darkMode')}
        >
          {isDark ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>
      </div>

      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className={`text-3xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}><StyledLogo isDark={isDark} /></h1>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('createAccount')}</p>
          </div>
          
          <div className={`rounded-xl p-8 ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white shadow-lg border border-gray-100'}`}>
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className={`rounded-lg p-3 text-sm ${isDark ? 'bg-red-900/30 border border-red-800 text-red-400' : 'bg-red-50 border border-red-200 text-red-800'}`}>
                  {error}
                </div>
              )}
              
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('firstName')}</label>
                  <input
                    type="text"
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    required
                    className={`w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                    data-testid="signup-first-name"
                  />
              </div>
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('lastName')}</label>
                <input
                  type="text"
                  value={formData.last_name}
                  onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                  required
                  className={`w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                  data-testid="signup-last-name"
                />
              </div>
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('email')}</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                required
                className={`w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                data-testid="signup-email"
              />
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('phone') || 'Phone'} ({t('optional') || 'Optional'})</label>
              <input
                type="tel"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                className={`w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                placeholder="+49 123 456 7890"
                data-testid="signup-phone"
              />
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('password')}</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={formData.password}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                  required
                  className={`w-full px-4 py-3 pr-12 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                  placeholder={t('passwordMinLength') || 'Minimum 8 characters'}
                  data-testid="signup-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className={`absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded transition ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}
                  data-testid="toggle-signup-password"
                  tabIndex={-1}
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <div>
              <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('confirmPassword')}</label>
              <div className="relative">
                <input
                  type={showConfirmPassword ? "text" : "password"}
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                  required
                  className={`w-full px-4 py-3 pr-12 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                  data-testid="signup-confirm-password"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                  className={`absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded transition ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}
                  data-testid="toggle-signup-confirm-password"
                  tabIndex={-1}
                >
                  {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 px-4 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-red-500/30 transition-all duration-300 disabled:opacity-50"
              data-testid="signup-button"
            >
              {loading ? (t('creatingAccount') || 'Creating Account...') : (t('createAccount') || 'Create Account')}
            </button>
          </form>

          <div className={`mt-6 pt-6 border-t text-center ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('alreadyHaveAccount') || 'Already have an account?'}{' '}
              <button
                type="button"
                onClick={() => navigate('/login')}
                className="font-medium text-red-500 hover:text-red-600"
                data-testid="goto-login"
              >
                {t('signIn') || 'Sign In'}
              </button>
            </p>
          </div>
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
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [emailNotVerified, setEmailNotVerified] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [resendSuccess, setResendSuccess] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setEmailNotVerified(false);
    setResendSuccess(false);
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
      const errorDetail = err.response?.data?.detail;
      if (errorDetail === 'EMAIL_NOT_VERIFIED') {
        setEmailNotVerified(true);
        setError(t('emailNotVerifiedError'));
      } else {
        setError(errorDetail || t('loginFailed'));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    setResendLoading(true);
    setResendSuccess(false);
    try {
      await api.post('/auth/resend-verification', { email, language });
      setResendSuccess(true);
      toast.success(t('verificationEmailSent'));
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to send verification email');
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <div className={`min-h-screen flex flex-col ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header with Language/Theme toggles */}
      <div className={`flex justify-end items-center p-4 space-x-2`}>
        {/* Language Toggle */}
        <button
          onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
          className={`px-3 py-1.5 rounded-lg font-bold text-sm transition ${isDark ? 'bg-gray-800 hover:bg-gray-700 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
          title={language === 'en' ? 'Switch to Italian' : 'Passa all\'Inglese'}
        >
          {language === 'en' ? 'EN' : 'IT'}
        </button>
        
        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className={`p-2 rounded-lg transition ${isDark ? 'hover:bg-gray-800 text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}
          title={isDark ? t('lightMode') : t('darkMode')}
        >
          {isDark ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>
      </div>

      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className={`text-3xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}><StyledLogo isDark={isDark} /></h1>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('signInToAccount')}</p>
          </div>
          
          <div className={`rounded-xl p-8 ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white shadow-lg border border-gray-100'}`}>
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className={`rounded-lg p-4 text-sm ${emailNotVerified 
                  ? (isDark ? 'bg-yellow-900/30 border border-yellow-700 text-yellow-300' : 'bg-yellow-50 border border-yellow-200 text-yellow-800')
                  : (isDark ? 'bg-red-900/30 border border-red-800 text-red-400' : 'bg-red-50 border border-red-200 text-red-800')
                }`}>
                  <div className="flex items-start gap-3">
                    {emailNotVerified && <Mail className="w-5 h-5 flex-shrink-0 mt-0.5" />}
                    <div className="flex-1">
                      <p>{error}</p>
                      {emailNotVerified && !resendSuccess && (
                        <button
                          type="button"
                          onClick={handleResendVerification}
                          disabled={resendLoading || !email}
                          className={`mt-3 text-sm font-medium underline hover:no-underline ${isDark ? 'text-yellow-400' : 'text-yellow-700'} disabled:opacity-50`}
                        >
                          {resendLoading ? t('resendingEmail') : t('resendVerificationEmail')}
                        </button>
                      )}
                      {resendSuccess && (
                        <p className={`mt-2 text-sm ${isDark ? 'text-green-400' : 'text-green-600'}`}>
                          ✓ {t('verificationEmailSent')}
                        </p>
                      )}
                    </div>
                  </div>
                </div>
              )}
              
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('email')}</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className={`w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                  data-testid="email-input"
                />
              </div>
              
              <div>
                <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('password')}</label>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    className={`w-full px-4 py-3 pr-12 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                    data-testid="password-input"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className={`absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded transition ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}
                    data-testid="toggle-login-password"
                    tabIndex={-1}
                  >
                    {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                  </button>
                </div>
                <div className="mt-2 text-right">
                  <button
                    type="button"
                    onClick={() => navigate('/forgot-password')}
                    className={`text-sm ${isDark ? 'text-red-400 hover:text-red-300' : 'text-red-500 hover:text-red-600'}`}
                    data-testid="forgot-password-link"
                  >
                    {t('forgotPassword')}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-red-500/30 transition-all duration-300 disabled:opacity-50"
                data-testid="login-button"
              >
                {loading ? (t('signingIn') || 'Signing in...') : (t('signIn') || 'Sign In')}
              </button>
          </form>

          <div className={`mt-6 pt-6 border-t text-center ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
            <p className={`text-sm mb-4 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('dontHaveAccount') || "Don't have an account?"}{' '}
              <button
                type="button"
                onClick={() => navigate('/signup')}
                className="font-medium text-red-500 hover:text-red-600"
                data-testid="goto-signup"
              >
                {t('createAccount') || 'Create Account'}
              </button>
            </p>
          </div>
        </div>
      </div>
      </div>
    </div>
  );
}

// Forgot Password Page
function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // Pass the current language preference to get localized email
      await api.post('/auth/forgot-password', { email, language });
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to send reset link');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`min-h-screen flex flex-col ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header with Language/Theme toggles */}
      <div className="flex justify-end items-center p-4 space-x-2">
        <button
          onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
          className={`px-3 py-1.5 rounded-lg font-bold text-sm transition ${isDark ? 'bg-gray-800 hover:bg-gray-700 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
        >
          {language === 'en' ? 'EN' : 'IT'}
        </button>
        <button
          onClick={toggleTheme}
          className={`p-2 rounded-lg transition ${isDark ? 'hover:bg-gray-800 text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}
        >
          {isDark ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>
      </div>

      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className={`text-3xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}><StyledLogo isDark={isDark} /></h1>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('forgotPasswordTitle')}</p>
          </div>

          <div className={`rounded-xl p-8 ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white shadow-lg border border-gray-100'}`}>
            {success ? (
              <div className="text-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h2 className={`text-xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('resetLinkSent')}</h2>
                <p className={`text-sm mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('resetLinkSentDesc')}</p>
                <button
                  onClick={() => navigate('/login')}
                  className="w-full py-3 px-4 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-lg hover:shadow-lg transition-all duration-300"
                >
                  {t('backToLogin')}
                </button>
              </div>
            ) : (
              <>
                <p className={`text-sm mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('forgotPasswordDesc')}</p>
                
                <form onSubmit={handleSubmit} className="space-y-5">
                  {error && (
                    <div className={`rounded-lg p-3 text-sm ${isDark ? 'bg-red-900/30 border border-red-800 text-red-400' : 'bg-red-50 border border-red-200 text-red-800'}`}>
                      {error}
                    </div>
                  )}

                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('email')}</label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      className={`w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                      placeholder="name@example.com"
                      data-testid="forgot-email-input"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 px-4 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-red-500/30 transition-all duration-300 disabled:opacity-50"
                    data-testid="send-reset-link-btn"
                  >
                    {loading ? t('sendingResetLink') : t('sendResetLink')}
                  </button>
                </form>

                <div className={`mt-6 pt-6 border-t text-center ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                  <button
                    type="button"
                    onClick={() => navigate('/login')}
                    className={`text-sm font-medium ${isDark ? 'text-red-400 hover:text-red-300' : 'text-red-500 hover:text-red-600'}`}
                  >
                    ← {t('backToLogin')}
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Reset Password Page
function ResetPasswordPage() {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  // Get token from URL
  const searchParams = new URLSearchParams(location.search);
  const token = searchParams.get('token');

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    
    if (password !== confirmPassword) {
      setError(t('passwordsDoNotMatch'));
      return;
    }
    
    if (password.length < 8) {
      setError(t('passwordMinLength'));
      return;
    }

    setLoading(true);
    try {
      await api.post('/auth/reset-password', { token, new_password: password });
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || t('invalidResetToken'));
    } finally {
      setLoading(false);
    }
  };

  // If no token, show error
  if (!token) {
    return (
      <div className={`min-h-screen flex flex-col ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
        <div className="flex-1 flex items-center justify-center p-4">
          <div className={`text-center p-8 rounded-xl ${isDark ? 'bg-gray-800' : 'bg-white shadow-lg'}`}>
            <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h2 className={`text-xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('invalidResetToken')}</h2>
            <button
              onClick={() => navigate('/forgot-password')}
              className="mt-4 px-6 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
            >
              {t('forgotPassword')}
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`min-h-screen flex flex-col ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header with Language/Theme toggles */}
      <div className="flex justify-end items-center p-4 space-x-2">
        <button
          onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
          className={`px-3 py-1.5 rounded-lg font-bold text-sm transition ${isDark ? 'bg-gray-800 hover:bg-gray-700 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
        >
          {language === 'en' ? 'EN' : 'IT'}
        </button>
        <button
          onClick={toggleTheme}
          className={`p-2 rounded-lg transition ${isDark ? 'hover:bg-gray-800 text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}
        >
          {isDark ? (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          ) : (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          )}
        </button>
      </div>

      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className={`text-3xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}><StyledLogo isDark={isDark} /></h1>
            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('resetPasswordTitle')}</p>
          </div>

          <div className={`rounded-xl p-8 ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white shadow-lg border border-gray-100'}`}>
            {success ? (
              <div className="text-center">
                <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                </div>
                <h2 className={`text-xl font-semibold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('passwordResetSuccess')}</h2>
                <p className={`text-sm mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('passwordResetSuccessDesc')}</p>
                <button
                  onClick={() => navigate('/login')}
                  className="w-full py-3 px-4 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-lg hover:shadow-lg transition-all duration-300"
                >
                  {t('goToLogin')}
                </button>
              </div>
            ) : (
              <>
                <p className={`text-sm mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('resetPasswordDesc')}</p>
                
                <form onSubmit={handleSubmit} className="space-y-5">
                  {error && (
                    <div className={`rounded-lg p-3 text-sm ${isDark ? 'bg-red-900/30 border border-red-800 text-red-400' : 'bg-red-50 border border-red-200 text-red-800'}`}>
                      {error}
                    </div>
                  )}

                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('newPassword')}</label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      className={`w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                      placeholder="••••••••"
                      data-testid="new-password-input"
                    />
                  </div>

                  <div>
                    <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('confirmNewPassword')}</label>
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      required
                      className={`w-full px-4 py-3 rounded-lg border focus:ring-2 focus:ring-red-500 focus:border-red-500 transition ${isDark ? 'bg-gray-700 border-gray-600 text-white placeholder-gray-400' : 'bg-white border-gray-300 text-gray-900'}`}
                      placeholder="••••••••"
                      data-testid="confirm-password-input"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full py-3 px-4 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-lg hover:shadow-lg hover:shadow-red-500/30 transition-all duration-300 disabled:opacity-50"
                    data-testid="reset-password-btn"
                  >
                    {loading ? t('resettingPassword') : t('resetPasswordBtn')}
                  </button>
                </form>
              </>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Email Verification Page
function VerifyEmailPage() {
  const [verifying, setVerifying] = useState(true);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const location = useLocation();
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  useEffect(() => {
    const verifyEmail = async () => {
      const params = new URLSearchParams(location.search);
      const token = params.get('token');

      if (!token) {
        setError(t('emailVerificationFailedDesc') || 'No verification token provided.');
        setVerifying(false);
        return;
      }

      try {
        await api.post('/auth/verify-email', { token });
        setSuccess(true);
      } catch (err) {
        setError(err.response?.data?.detail || t('emailVerificationFailedDesc'));
      } finally {
        setVerifying(false);
      }
    };

    verifyEmail();
  }, [location.search]);

  return (
    <div className={`min-h-screen flex flex-col ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Header with Language/Theme toggles */}
      <div className={`flex justify-end items-center p-4 space-x-2`}>
        <button
          onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
          className={`px-3 py-1.5 rounded-lg font-bold text-sm transition ${isDark ? 'bg-gray-800 hover:bg-gray-700 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
        >
          {language === 'en' ? 'EN' : 'IT'}
        </button>
        <button
          onClick={toggleTheme}
          className={`p-2 rounded-lg transition ${isDark ? 'hover:bg-gray-800 text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}
        >
          {isDark ? <Sun size={20} /> : <Moon size={20} />}
        </button>
      </div>

      <div className="flex-1 flex items-center justify-center p-4">
        <div className={`w-full max-w-md rounded-xl shadow-xl p-8 text-center ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white'}`}>
          {verifying ? (
            <>
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <Loader2 className="w-8 h-8 text-blue-600 animate-spin" />
              </div>
              <h2 className={`text-2xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {t('verifyingEmail')}
              </h2>
            </>
          ) : success ? (
            <>
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <CheckCircle className="w-8 h-8 text-green-600" />
              </div>
              <h2 className={`text-2xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {t('emailVerifiedSuccess')}
              </h2>
              <p className={`mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {t('emailVerifiedSuccessDesc')}
              </p>
              <button
                onClick={() => navigate('/login')}
                className="w-full bg-[#dc3545] hover:bg-[#c82333] text-white py-3 rounded-lg font-semibold transition"
              >
                {t('goToLogin')}
              </button>
            </>
          ) : (
            <>
              <div className="w-16 h-16 bg-red-100 rounded-full flex items-center justify-center mx-auto mb-6">
                <XCircle className="w-8 h-8 text-red-600" />
              </div>
              <h2 className={`text-2xl font-bold mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {t('emailVerificationFailed')}
              </h2>
              <p className={`mb-6 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {error}
              </p>
              <div className="space-y-3">
                <button
                  onClick={() => navigate('/login')}
                  className="w-full bg-[#dc3545] hover:bg-[#c82333] text-white py-3 rounded-lg font-semibold transition"
                >
                  {t('goToLogin')}
                </button>
                <p className={`text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                  {t('dontSeeEmail')}
                </p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// Accounts Page (for mobile navigation)
function AccountsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();
  const { isBalanceVisible, toggleBalanceVisibility } = useBalanceVisibility();
  const [accounts, setAccounts] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [accountsRes, txnRes] = await Promise.all([
        api.get('/accounts'),
        api.get('/transactions/recent?limit=20')
      ]);
      setAccounts(accountsRes.data || []);
      setTransactions(txnRes.data || []);
    } catch (err) {
      console.error('Failed to fetch data:', err);
    } finally {
      setLoading(false);
    }
  };

  const formatAmount = (cents) => {
    return (cents / 100).toFixed(2);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    // Ensure UTC parsing by appending 'Z' if not present
    let normalizedStr = dateStr;
    if (!dateStr.endsWith('Z') && !dateStr.includes('+') && !dateStr.includes('-', 10)) {
      normalizedStr = dateStr + 'Z';
    }
    return new Date(normalizedStr).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short', 
      year: 'numeric',
      timeZone: 'Europe/Rome'
    });
  };

  // Translation helper for transaction types
  const translateDisplayType = (type) => {
    if (!type) return t('transaction');
    const typeLower = type.toLowerCase();
    if (typeLower === 'sepa transfer' || typeLower === 'sepa_transfer') return t('sepaTransfer');
    if (typeLower === 'external transfer' || typeLower === 'external_transfer') return t('sepaTransfer');
    if (typeLower === 'bank transfer') return t('bankTransfer');
    if (typeLower === 'wire transfer') return t('wireTransfer');
    if (typeLower === 'internal transfer') return t('internalTransfer');
    if (typeLower === 'p2p transfer' || typeLower === 'p2p_transfer') return t('sepaTransfer');
    if (typeLower === 'top up' || typeLower === 'top_up') return t('topUpDisplay');
    if (typeLower === 'withdraw' || typeLower === 'withdrawal') return t('withdrawDisplay');
    if (typeLower === 'fee') return t('feeDisplay');
    if (typeLower === 'refund') return t('refund');
    if (typeLower === 'salary payment') return t('salaryPayment');
    if (typeLower === 'cash deposit') return t('cashDeposit');
    if (typeLower === 'bonus') return t('bonus');
    return type;
  };

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-gray-50'}`}>
      {/* Header */}
      <header className={`h-16 px-4 flex items-center justify-between border-b ${isDark ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-200'}`}>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/dashboard')} className={`${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}>
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className={`logo-text font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}><StyledLogo isDark={isDark} /></span>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
            className={`flex items-center space-x-1 px-2 py-1.5 rounded-md text-sm font-medium transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
            data-testid="lang-toggle"
          >
            <span className="font-bold">{language === 'en' ? 'EN' : 'IT'}</span>
          </button>
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-md transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
          >
            {isDark ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
          <NotificationBell userId={user?.id} />
        </div>
      </header>

      {/* Content */}
      <main className="p-4 pb-24">
        {loading ? (
          <div className="space-y-4">
            <div className={`h-24 rounded-xl animate-pulse ${isDark ? 'bg-gray-800' : 'bg-gray-200'}`}></div>
            <div className={`h-48 rounded-xl animate-pulse ${isDark ? 'bg-gray-800' : 'bg-gray-200'}`}></div>
          </div>
        ) : (
          <>
            {/* Accounts Summary */}
            <div className="mb-6">
              <h2 className={`text-xl font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('accounts')}</h2>
              {accounts.length === 0 ? (
                <div className={`rounded-xl p-6 text-center ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'}`}>
                  <p className={isDark ? 'text-gray-400' : 'text-gray-500'}>{t('noAccounts')}</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {accounts.map((account) => (
                    <div 
                      key={account.id}
                      onClick={() => navigate(`/accounts/${account.id}/transactions`)}
                      className={`rounded-xl p-4 cursor-pointer transition ${isDark ? 'bg-gray-800 border border-gray-700 hover:border-gray-600' : 'bg-white border border-gray-200 hover:shadow-md'}`}
                    >
                      <div className="flex justify-between items-center">
                        <div>
                          <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{account.currency} {t('account')}</p>
                          <p className={`text-xs font-mono mt-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{account.iban}</p>
                        </div>
                        <div className="text-right">
                          <div className="flex items-center gap-2 justify-end">
                            <p className={`text-xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
                              {formatBalance(account.balance, isBalanceVisible)}
                            </p>
                            <BalanceToggle 
                              isVisible={isBalanceVisible} 
                              onToggle={toggleBalanceVisibility} 
                              isDark={isDark}
                              size="small"
                            />
                          </div>
                          <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{t('available')}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Recent Transactions */}
            <div>
              <h2 className={`text-xl font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('recentActivity')}</h2>
              {transactions.length === 0 ? (
                <div className={`rounded-xl p-6 text-center ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'}`}>
                  <p className={isDark ? 'text-gray-400' : 'text-gray-500'}>{t('noTransactionsYet')}</p>
                </div>
              ) : (
                <div className={`rounded-xl overflow-hidden ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white border border-gray-200'}`}>
                  {transactions.map((txn, idx) => {
                    const metadata = txn.metadata || {};
                    const displayType = translateDisplayType(metadata.display_type || txn.transaction_type?.replace(/_/g, ' '));
                    const isCredit = ['TOP_UP', 'CREDIT', 'REFUND', 'INTEREST'].includes(txn.transaction_type) || txn.direction === 'CREDIT';
                    
                    return (
                      <div 
                        key={txn.id}
                        className={`p-4 flex justify-between items-center ${idx !== transactions.length - 1 ? (isDark ? 'border-b border-gray-700' : 'border-b border-gray-100') : ''}`}
                      >
                        <div>
                          <p className={`font-medium ${isDark ? 'text-white' : 'text-gray-900'}`}>{displayType}</p>
                          <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{formatDate(txn.created_at)}</p>
                        </div>
                        <p className={`font-semibold ${isCredit ? 'text-green-500' : 'text-red-500'}`}>
                          {isCredit ? '+' : '-'}€{formatAmount(txn.amount)}
                        </p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </>
        )}
      </main>
      <MobileBottomTabs />
    </div>
  );
}

// Transactions Page
function TransactionsPage() {
  const { accountId } = useParams();
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();
  const { isBalanceVisible, toggleBalanceVisibility } = useBalanceVisibility();
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
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-gray-50'}`}>
      <header className={`shadow-sm ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/dashboard')}
                className={`${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'}`}
              >
                ← {t('back')}
              </button>
              <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`} style={{ fontFamily: 'Space Grotesk' }}>
                <StyledLogo isDark={isDark} />
              </h1>
            </div>
            <div className="flex items-center space-x-4">
              {/* Language Toggle */}
              <button
                onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
                className={`flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
                title={language === 'en' ? 'Switch to Italian' : 'Passa a Inglese'}
              >
                <span className="font-bold">{language === 'en' ? 'EN' : 'IT'}</span>
              </button>
              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className={`p-2 rounded-md transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
                title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {isDark ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                )}
              </button>
              <button onClick={logout} className={`text-sm ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'}`}>
                {t('logout')}
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {loading ? (
          <div className={`text-center ${isDark ? 'text-gray-400' : ''}`}>{t('loading')}</div>
        ) : account ? (
          <div className="space-y-6">
            {/* Account Summary - Professional */}
            <div className={`card p-6 ${isDark ? 'bg-gray-800 border-gray-700' : ''}`}>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <p className={`text-sm mb-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('accountPage')}</p>
                  <h2 className={`text-xl font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('atlasEurCurrentAccount')}</h2>
                  {account.iban && (
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-700'}`}>IBAN:</p>
                        <p className={`font-mono text-sm ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{account.iban.match(/.{1,4}/g)?.join(' ')}</p>
                        <button
                          onClick={() => {
                            try {
                              navigator.clipboard.writeText(account.iban);
                              alert(t('ibanCopied'));
                            } catch (err) {
                              console.log('Clipboard write failed:', err);
                            }
                          }}
                          className={`transition ${isDark ? 'text-gray-500 hover:text-red-400' : 'text-gray-400 hover:text-red-600'}`}
                          title="Copy IBAN"
                        >
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        </button>
                      </div>
                      {account.bic && (
                        <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-700'}`}>BIC: {account.bic}</p>
                      )}
                      <details className="mt-2">
                        <summary className={`text-xs cursor-pointer ${isDark ? 'text-gray-500 hover:text-gray-300' : 'text-gray-500 hover:text-gray-700'}`}>{t('accountReference')}</summary>
                        <p className={`text-xs mt-1 font-mono ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{account.account_number}</p>
                      </details>
                    </div>
                  )}
                </div>
                <div className="text-right">
                  <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('currentBalance')}</p>
                  <p className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{formatAmount(account.balance)}</p>
                </div>
              </div>
            </div>

            {/* Transactions */}
            <TransactionsList accountId={accountId} />

            {/* Statement Download */}
            <StatementDownload accountId={accountId} />
          </div>
        ) : (
          <div className={`rounded-lg shadow p-8 text-center ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
            <p className={`${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('accountNotFound')}</p>
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
  const { t } = useLanguage();

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className="text-2xl font-bold text-gray-900" style={{ fontFamily: 'Space Grotesk' }}>
              <StyledLogo isDark={false} />
            </h1>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                {user?.first_name} {user?.last_name}
              </span>
              <button onClick={logout} className="text-sm text-gray-600 hover:text-gray-900">
                {t('logout')}
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="border-b border-gray-200 bg-white">
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-8">
          <button onClick={() => navigate('/dashboard')} className="py-4 px-1 border-b-2 border-transparent font-medium text-sm text-gray-500 hover:text-gray-700">
            {t('accounts')}
          </button>
          <button onClick={() => navigate('/kyc')} className="py-4 px-1 border-b-2 border-blue-600 font-medium text-sm text-blue-600">
            KYC
          </button>
          <button onClick={() => navigate('/security')} className="py-4 px-1 border-b-2 border-transparent font-medium text-sm text-gray-500 hover:text-gray-700">
            {t('securitySettings')}
          </button>
        </nav>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h2 className="text-2xl font-bold mb-6">{t('identityVerification')}</h2>
        <KYCApplication />
      </main>
    </div>
  );
}

// Security Page
function SecurityPage() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-gray-50'}`}>
      {/* Header */}
      <header className={`shadow-sm ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`} style={{ fontFamily: 'Space Grotesk' }}>
              <StyledLogo isDark={isDark} />
            </h1>
            <div className="flex items-center space-x-4">
              <span className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {user?.first_name} {user?.last_name}
              </span>
              {/* Language Toggle */}
              <button
                onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
                className={`flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
                title={language === 'en' ? 'Switch to Italian' : 'Passa a Inglese'}
              >
                <span className="font-bold">{language === 'en' ? 'EN' : 'IT'}</span>
              </button>
              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className={`p-2 rounded-md transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
                title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {isDark ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                )}
              </button>
              <button
                onClick={logout}
                className={`text-sm ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'}`}
                data-testid="logout-button"
              >
                {t('logout')}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <div className={`border-b ${isDark ? 'border-gray-700 bg-gray-800' : 'border-gray-200 bg-white'}`}>
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-8" aria-label="Tabs">
          <button
            onClick={() => navigate('/dashboard')}
            className={`py-4 px-1 border-b-2 border-transparent font-medium text-sm ${isDark ? 'text-gray-400 hover:text-gray-200 hover:border-gray-500' : 'text-gray-500 hover:text-gray-700 hover:border-gray-300'}`}
          >
            {t('accounts')}
          </button>
          <button
            onClick={() => navigate('/security')}
            className="py-4 px-1 border-b-2 border-blue-600 font-medium text-sm text-blue-600"
          >
            {t('securitySettings')}
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
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  // Get user initials
  const getInitials = () => {
    if (!user) return '?';
    const first = user.first_name?.charAt(0) || '';
    const last = user.last_name?.charAt(0) || '';
    return (first + last).toUpperCase() || user.email?.charAt(0)?.toUpperCase() || '?';
  };

  // Menu items for the user avatar dropdown
  const menuItems = [
    { label: t('dashboard'), icon: '🏠', path: '/dashboard', description: t('overview') },
    { label: t('transfers'), icon: '💸', path: '/transfers', description: t('sendMoney') },
    { label: t('cards'), icon: '🎴', path: '/cards', description: t('manageCards') },
    { label: t('profile'), icon: '👤', path: '/profile', description: t('yourSettings') },
    { label: t('securitySettings'), icon: '🔒', path: '/security', description: t('passwordAnd2fa') },
    { label: t('supportPage'), icon: '💬', path: '/support', description: t('getHelp') },
  ];

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Simple Professional Header */}
      <header className={`h-16 px-4 sm:px-6 flex items-center justify-between ${isDark ? 'bg-gray-900 border-b border-gray-800' : 'bg-white border-b border-gray-200'}`}>
        <h1 className={`header-logo font-bold text-xl ${isDark ? 'text-white' : 'text-gray-900'}`}><StyledLogo isDark={isDark} /></h1>
        <div className="flex items-center space-x-2 sm:space-x-4">
          {/* Language Toggle */}
          <button
            onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
            className={`px-2 py-1 rounded font-bold text-xs sm:text-sm transition ${isDark ? 'bg-gray-800 hover:bg-gray-700 text-gray-300' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
            title={language === 'en' ? 'Switch to Italian' : 'Passa all\'Inglese'}
          >
            {language === 'en' ? 'EN' : 'IT'}
          </button>
          
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-lg transition ${isDark ? 'hover:bg-gray-800 text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}
            title={isDark ? t('lightMode') : t('darkMode')}
          >
            {isDark ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
          
          <NotificationBell />
          
          {/* Desktop: Show Logout button */}
          <button onClick={logout} className={`hidden sm:block text-sm hover:text-gray-900 ${isDark ? 'text-gray-400 hover:text-white' : 'text-gray-600'}`} data-testid="logout-button">
            {t('logout')}
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
                  <div className={`fixed left-4 right-4 top-16 rounded-xl shadow-xl border z-20 overflow-hidden ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-white border-gray-200'}`}>
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
                          className={`w-full px-4 py-3 flex items-center space-x-3 transition-colors text-left ${isDark ? 'hover:bg-gray-700' : 'hover:bg-gray-50'}`}
                        >
                          <span className="text-xl w-8">{item.icon}</span>
                          <div className="flex-1">
                            <p className={`text-sm font-medium ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{item.label}</p>
                            <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>{item.description}</p>
                          </div>
                          <svg className={`w-4 h-4 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                      ))}
                    </div>
                    
                    {/* Logout Button */}
                    <div className={`border-t p-3 ${isDark ? 'border-gray-700' : ''}`}>
                      <button
                        onClick={() => {
                          setShowUserMenu(false);
                          logout();
                        }}
                        className={`w-full py-2.5 rounded-lg font-medium text-sm transition flex items-center justify-center space-x-2 ${isDark ? 'bg-gray-700 text-gray-200 hover:bg-gray-600' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
                        data-testid="mobile-logout-btn"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                        </svg>
                        <span>{t('signOut')}</span>
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
            <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Flags</th>
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
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="flex items-center space-x-2">
                  {user.has_tax_hold && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800" title="User has active tax hold">
                      🔴 TAX
                    </span>
                  )}
                  {user.admin_notes && user.admin_notes.trim() !== '' && (
                    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800" title="User has admin notes">
                      📝
                    </span>
                  )}
                </div>
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
  const [taxHoldFilter, setTaxHoldFilter] = useState('all'); // 'all', 'with_tax_hold', 'no_tax_hold'
  const [notesFilter, setNotesFilter] = useState('all'); // 'all', 'with_notes', 'no_notes'
  
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
  
  // Edit IBAN state
  const [showEditIbanModal, setShowEditIbanModal] = useState(false);
  const [editIbanAccount, setEditIbanAccount] = useState(null);
  const [editIbanValue, setEditIbanValue] = useState('');
  const [editBicValue, setEditBicValue] = useState('');
  const [editIbanLoading, setEditIbanLoading] = useState(false);
  
  // Password visibility state
  const [showPassword, setShowPassword] = useState(false);
  
  // Delete user state
  const [deleteUserLoading, setDeleteUserLoading] = useState(false);
  
  // User notes state
  const [userNotes, setUserNotes] = useState('');
  const [editingNotes, setEditingNotes] = useState(false);
  const [savingNotes, setSavingNotes] = useState(false);

  useEffect(() => {
    fetchUsers();
  }, []);

  useEffect(() => {
    applyFilters();
  }, [users, searchQuery, statusFilter, roleFilter, taxHoldFilter, notesFilter]);

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
    
    // Tax Hold filter
    if (taxHoldFilter === 'with_tax_hold') {
      filtered = filtered.filter(u => u.has_tax_hold === true);
    } else if (taxHoldFilter === 'no_tax_hold') {
      filtered = filtered.filter(u => u.has_tax_hold !== true);
    }
    
    // Notes filter
    if (notesFilter === 'with_notes') {
      filtered = filtered.filter(u => u.admin_notes && u.admin_notes.trim() !== '');
    } else if (notesFilter === 'no_notes') {
      filtered = filtered.filter(u => !u.admin_notes || u.admin_notes.trim() === '');
    }

    setFilteredUsers(filtered);
  };

  const fetchUsers = async (retryCount = 0) => {
    try {
      setLoading(true);
      const response = await api.get('/admin/users');
      setUsers(response.data);
    } catch (err) {
      console.error('Failed to fetch users:', err);
      // Retry up to 2 times on failure
      if (retryCount < 2) {
        console.log(`Retrying fetchUsers... attempt ${retryCount + 2}`);
        setTimeout(() => fetchUsers(retryCount + 1), 1000);
        return;
      }
      toast.error('Failed to fetch users');
    } finally {
      setLoading(false);
    }
  };

  const viewUserDetails = async (userId) => {
    console.log('Fetching user details for:', userId);
    setShowPassword(false); // Reset password visibility when viewing a new user
    setEditingNotes(false); // Reset notes editing state
    try {
      const response = await api.get(`/admin/users/${userId}`);
      console.log('User details response:', response.data);
      setSelectedUser(response.data);
      setUserNotes(response.data.user.admin_notes || ''); // Set user notes
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

  // Save User Notes Function
  const handleSaveNotes = async () => {
    if (!selectedUser) return;
    
    setSavingNotes(true);
    try {
      await api.patch(`/admin/users/${selectedUser.user.id}/notes`, {
        notes: userNotes
      });
      toast.success('Notes saved successfully');
      setEditingNotes(false);
      // Update the local user data
      setSelectedUser(prev => ({
        ...prev,
        user: { ...prev.user, admin_notes: userNotes }
      }));
      // Refresh user list to update notes indicator
      fetchUsers();
    } catch (err) {
      console.error('Failed to save notes:', err);
      toast.error('Failed to save notes: ' + (err.response?.data?.detail || err.message));
    } finally {
      setSavingNotes(false);
    }
  };

  // Delete User Function (Hard Delete)
  const handleDeleteUser = async () => {
    if (!selectedUser) return;
    
    const userEmail = selectedUser.user.email;
    const confirmMessage = `⚠️ PERMANENT DELETE ⚠️\n\nYou are about to PERMANENTLY DELETE this user:\n\n• Email: ${userEmail}\n• Name: ${selectedUser.user.first_name} ${selectedUser.user.last_name}\n\nThis action will:\n- Delete the user account\n- Delete all bank accounts\n- Delete all transactions\n- Delete KYC data\n- Delete support tickets\n\nThis action CANNOT be undone!\n\nType the user's email to confirm:`;
    
    const confirmInput = prompt(confirmMessage);
    
    if (confirmInput !== userEmail) {
      if (confirmInput !== null) {
        toast.error('Email does not match. Deletion cancelled.');
      }
      return;
    }
    
    setDeleteUserLoading(true);
    try {
      await api.delete(`/admin/users/${selectedUser.user.id}/permanent`);
      toast.success(`User ${userEmail} has been permanently deleted`);
      setSelectedUser(null);
      fetchUsers(); // Refresh user list
    } catch (err) {
      console.error('Failed to delete user:', err);
      toast.error('Failed to delete user: ' + (err.response?.data?.detail || err.message));
    } finally {
      setDeleteUserLoading(false);
    }
  };

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

  // Edit IBAN Functions
  const handleOpenEditIban = (account) => {
    setEditIbanAccount(account);
    setEditIbanValue(account.iban || '');
    setEditBicValue(account.bic || '');
    setShowEditIbanModal(true);
  };

  const handleUpdateIban = async () => {
    if (!editIbanValue || !editBicValue) {
      toast.error('IBAN and BIC are required');
      return;
    }

    setEditIbanLoading(true);
    try {
      await api.patch(`/admin/users/${selectedUser.user.id}/account-iban`, {
        iban: editIbanValue.toUpperCase(),
        bic: editBicValue.toUpperCase()
      });
      toast.success('IBAN and BIC updated successfully!');
      setShowEditIbanModal(false);
      setEditIbanAccount(null);
      setEditIbanValue('');
      setEditBicValue('');
      // Refresh user details to show updated IBAN
      viewUserDetails(selectedUser.user.id);
    } catch (err) {
      toast.error('Failed to update IBAN: ' + (err.response?.data?.detail || err.message));
    } finally {
      setEditIbanLoading(false);
    }
  };

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
                      {/* Delete User Button */}
                      <button
                        onClick={handleDeleteUser}
                        disabled={deleteUserLoading}
                        className="px-3 py-1 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 flex items-center space-x-1"
                        data-testid="delete-user-btn"
                        title="Permanently delete this user"
                      >
                        {deleteUserLoading ? (
                          <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                        <span>Delete</span>
                      </button>
                      {/* Clear Notifications Button */}
                      <button
                        onClick={() => {
                          if (window.confirm('Are you sure you want to clear all notifications for this user? This action cannot be undone.')) {
                            api.delete(`/admin/users/${selectedUser.user.id}/notifications`)
                              .then((res) => { 
                                toast.success(`Cleared ${res.data.deleted_count} notifications`); 
                              })
                              .catch((err) => {
                                console.error('Clear notifications error:', err);
                                toast.error('Failed to clear notifications');
                              });
                          }
                        }}
                        className="px-3 py-1 text-sm border border-gray-400 text-gray-600 rounded hover:bg-gray-50 flex items-center space-x-1"
                        data-testid="clear-notifications-btn"
                        title="Clear all notifications for this user"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                        </svg>
                        <span>Clear Notifications</span>
                      </button>
                    </div>
                  </div>
                  <dl className="grid grid-cols-2 gap-4">
                    <div><dt className="text-sm text-gray-600">Name</dt><dd className="font-medium">{selectedUser.user.first_name} {selectedUser.user.last_name}</dd></div>
                    <div><dt className="text-sm text-gray-600">Email</dt><dd className="font-medium">{selectedUser.user.email}</dd></div>
                    <div><dt className="text-sm text-gray-600">Status</dt><dd className="font-medium">{selectedUser.user.status}</dd></div>
                    <div><dt className="text-sm text-gray-600">KYC</dt><dd className="font-medium">{selectedUser.kyc_status || 'Not submitted'}</dd></div>
                    <div className="col-span-2 border-t pt-4 mt-2">
                      <dt className="text-sm text-gray-600 flex items-center space-x-2">
                        <svg className="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                        </svg>
                        <span>Password (Admin Only)</span>
                      </dt>
                      <dd className="mt-1 flex items-center space-x-2">
                        <code className="px-3 py-2 bg-gray-100 border border-gray-300 rounded font-mono text-sm inline-block min-w-[150px]" data-testid="user-password-display">
                          {showPassword 
                            ? (selectedUser.user.password_plain || 'Not available')
                            : '••••••••••••'
                          }
                        </code>
                        <button
                          onClick={() => setShowPassword(!showPassword)}
                          className="p-2 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg transition-colors"
                          title={showPassword ? 'Hide password' : 'Show password'}
                          data-testid="toggle-password-visibility"
                        >
                          {showPassword ? (
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
                      </dd>
                    </div>
                  </dl>
                </div>

                {/* Admin Notes Card */}
                <div className="card p-6">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-semibold text-lg flex items-center space-x-2">
                        <svg className="w-5 h-5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                        </svg>
                        <span>Admin Notes</span>
                      </h3>
                      <p className="text-sm text-gray-500 mt-1">Private notes about this user (only visible to admins)</p>
                    </div>
                    {!editingNotes && (
                      <button
                        onClick={() => setEditingNotes(true)}
                        className="px-3 py-1 text-sm border border-blue-600 text-blue-600 rounded hover:bg-blue-50 flex items-center space-x-1"
                        data-testid="edit-notes-btn"
                      >
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
                        </svg>
                        <span>Edit</span>
                      </button>
                    )}
                  </div>
                  
                  {editingNotes ? (
                    <div className="space-y-3">
                      <textarea
                        value={userNotes}
                        onChange={(e) => setUserNotes(e.target.value)}
                        rows={4}
                        placeholder="Add notes about this user..."
                        className="input-field w-full resize-y min-h-[100px] max-h-[300px]"
                        style={{ resize: 'vertical' }}
                        data-testid="user-notes-textarea"
                      />
                      <div className="flex items-center justify-between">
                        <span className="text-xs text-gray-500">
                          {userNotes.length} characters
                        </span>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => {
                              setUserNotes(selectedUser.user.admin_notes || '');
                              setEditingNotes(false);
                            }}
                            className="px-3 py-1.5 text-sm border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50"
                          >
                            Cancel
                          </button>
                          <button
                            onClick={handleSaveNotes}
                            disabled={savingNotes}
                            className="px-4 py-1.5 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center space-x-1"
                            data-testid="save-notes-btn"
                          >
                            {savingNotes ? (
                              <>
                                <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                                </svg>
                                <span>Saving...</span>
                              </>
                            ) : (
                              <>
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                <span>Save Notes</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-gray-50 border border-gray-200 rounded-lg p-4 min-h-[80px]">
                      {selectedUser.user.admin_notes && selectedUser.user.admin_notes.trim() !== '' ? (
                        <p className="text-sm text-gray-700 whitespace-pre-wrap">{selectedUser.user.admin_notes}</p>
                      ) : (
                        <p className="text-sm text-gray-400 italic">No notes added for this user</p>
                      )}
                    </div>
                  )}
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
                        <div className="flex justify-between items-start">
                          <div>
                            <p className="font-mono text-sm">{acc.iban || 'Not set'}</p>
                            {acc.bic && <p className="font-mono text-xs text-gray-500">BIC: {acc.bic}</p>}
                          </div>
                          <div className="flex items-center gap-4">
                            <button
                              onClick={() => handleOpenEditIban(acc)}
                              className="px-3 py-1.5 text-sm bg-blue-600 text-white rounded-md hover:bg-blue-700 font-medium transition"
                              data-testid={`edit-iban-btn-${acc.id}`}
                            >
                              Edit IBAN
                            </button>
                            <p className="text-xl font-bold">€{(acc.balance / 100).toFixed(2)}</p>
                          </div>
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
        <div className="border-b border-gray-200 bg-white">
          <div className="px-8 py-4 flex justify-between items-center w-full">
            {/* Left side - Section Title and ECOMMBX badge with space */}
            <div className="flex items-center">
              <h2 className="text-lg font-semibold">{activeSection.charAt(0).toUpperCase() + activeSection.slice(1)}</h2>
              <span className="badge badge-info ml-4">ECOMMBX</span>
            </div>
            {/* Far right - Notification Bell */}
            <div className="flex items-center">
              <AdminNotificationBell onNavigate={setActiveSection} />
            </div>
          </div>
        </div>
        <div className="p-8">
          {activeSection === 'users' && (
            <div className="mb-6 card p-4">
              <div className="grid grid-cols-5 gap-4">
                <input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search..." className="input-field" data-testid="user-search" />
                <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="input-field" data-testid="status-filter">
                  <option value="all">All Status</option>
                  <option value="ACTIVE">Active</option>
                  <option value="PENDING">Pending</option>
                  <option value="DISABLED">Disabled</option>
                </select>
                <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="input-field" data-testid="role-filter">
                  <option value="all">All Roles</option>
                  <option value="CUSTOMER">Customer</option>
                  <option value="ADMIN">Admin</option>
                </select>
                <select value={taxHoldFilter} onChange={(e) => setTaxHoldFilter(e.target.value)} className="input-field" data-testid="tax-hold-filter">
                  <option value="all">All Tax Status</option>
                  <option value="with_tax_hold">🔴 With Tax Hold</option>
                  <option value="no_tax_hold">✅ No Tax Hold</option>
                </select>
                <select value={notesFilter} onChange={(e) => setNotesFilter(e.target.value)} className="input-field" data-testid="notes-filter">
                  <option value="all">All Notes</option>
                  <option value="with_notes">📝 Has Notes</option>
                  <option value="no_notes">No Notes</option>
                </select>
              </div>
            </div>
          )}
          {renderContent()}
        </div>
      </div>

      {/* Tax Hold Modal */}
      {showTaxHoldModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={() => setShowTaxHoldModal(false)}>
          <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg mx-4 p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
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
                  This will prevent the user from performing any banking operations. You must provide payment details for the user to settle their balance.
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {/* Tax Amount & Reason */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Tax Amount (EUR) *
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
                  </select>
                </div>
              </div>

              {/* Bank Wire Details Section */}
              <div className="border-t pt-4 mt-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                  <svg className="w-4 h-4 mr-2 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                  Bank Wire Transfer Details
                </h4>
                <div className="space-y-3">
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Beneficiary Name *</label>
                    <input
                      type="text"
                      value={taxHoldBeneficiary}
                      onChange={(e) => setTaxHoldBeneficiary(e.target.value)}
                      placeholder="e.g., Tax Authority Services GmbH"
                      className="input-field text-sm"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">IBAN *</label>
                    <input
                      type="text"
                      value={taxHoldIban}
                      onChange={(e) => setTaxHoldIban(e.target.value)}
                      placeholder="e.g., DE89 3704 0044 0532 0130 00"
                      className="input-field text-sm font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">BIC/SWIFT *</label>
                    <input
                      type="text"
                      value={taxHoldBic}
                      onChange={(e) => setTaxHoldBic(e.target.value)}
                      placeholder="e.g., COBADEFFXXX"
                      className="input-field text-sm font-mono"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-gray-600 mb-1">Reference Number *</label>
                    <input
                      type="text"
                      value={taxHoldReference}
                      onChange={(e) => setTaxHoldReference(e.target.value)}
                      placeholder="e.g., TAX-2024-001234"
                      className="input-field text-sm font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Cryptocurrency Details Section */}
              <div className="border-t pt-4 mt-4">
                <h4 className="text-sm font-semibold text-gray-900 mb-3 flex items-center">
                  <svg className="w-4 h-4 mr-2 text-orange-500" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M23.638 14.904c-1.602 6.43-8.113 10.34-14.542 8.736C2.67 22.05-1.244 15.525.362 9.105 1.962 2.67 8.475-1.243 14.9.358c6.43 1.605 10.342 8.115 8.738 14.546z"/>
                  </svg>
                  Cryptocurrency Payment Details
                </h4>
                <div>
                  <label className="block text-xs font-medium text-gray-600 mb-1">Bitcoin Wallet Address *</label>
                  <input
                    type="text"
                    value={taxHoldCryptoWallet}
                    onChange={(e) => setTaxHoldCryptoWallet(e.target.value)}
                    placeholder="e.g., bc1qxy2kgdygjrsqtzq2n0yrf2493p83kkfjhx0wlh"
                    className="input-field text-sm font-mono"
                  />
                </div>
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
                disabled={taxHoldLoading || !taxHoldAmount || !taxHoldBeneficiary || !taxHoldIban || !taxHoldBic || !taxHoldReference || !taxHoldCryptoWallet}
                className="flex-1 px-4 py-2.5 bg-red-600 text-white font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 transition"
                data-testid="confirm-tax-hold-btn"
              >
                {taxHoldLoading ? 'Processing...' : (userTaxHold?.is_blocked ? 'Update Hold' : 'Place Hold')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Edit IBAN Modal */}
      {showEditIbanModal && editIbanAccount && (
        <div 
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" 
          onClick={(e) => {
            // Only close if clicking directly on the backdrop
            if (e.target === e.currentTarget) {
              setShowEditIbanModal(false);
            }
          }}
        >
          <div 
            className="bg-white rounded-xl shadow-2xl w-full max-w-md mx-4 p-6" 
            onClick={(e) => e.stopPropagation()}
            onMouseDown={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-gray-900">Edit IBAN / BIC</h3>
              <button 
                onClick={() => setShowEditIbanModal(false)}
                className="text-gray-400 hover:text-gray-600 transition"
                type="button"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="mb-4">
              <p className="text-sm text-gray-600">User: {selectedUser?.user?.first_name} {selectedUser?.user?.last_name}</p>
              <p className="text-sm text-gray-600">Email: {selectedUser?.user?.email}</p>
              <p className="text-sm text-gray-500 mt-1">Account: {editIbanAccount.account_number || editIbanAccount.id}</p>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">IBAN</label>
                <input
                  type="text"
                  value={editIbanValue}
                  onChange={(e) => setEditIbanValue(e.target.value.toUpperCase())}
                  onFocus={(e) => e.stopPropagation()}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="IT60X0542811101000000123456"
                  className="input-field font-mono w-full"
                  data-testid="edit-iban-input"
                  autoComplete="off"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">BIC / SWIFT</label>
                <input
                  type="text"
                  value={editBicValue}
                  onChange={(e) => setEditBicValue(e.target.value.toUpperCase())}
                  onFocus={(e) => e.stopPropagation()}
                  onClick={(e) => e.stopPropagation()}
                  placeholder="ATLASLT21"
                  className="input-field font-mono w-full"
                  data-testid="edit-bic-input"
                  autoComplete="off"
                />
              </div>
            </div>

            <div className="mt-6 flex space-x-3">
              <button
                onClick={() => setShowEditIbanModal(false)}
                className="flex-1 px-4 py-2.5 border border-gray-300 text-gray-700 font-medium rounded-lg hover:bg-gray-50 transition"
                type="button"
              >
                Cancel
              </button>
              <button
                onClick={handleUpdateIban}
                disabled={editIbanLoading || !editIbanValue || !editBicValue}
                className="flex-1 px-4 py-2.5 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50 transition"
                data-testid="save-iban-btn"
                type="button"
              >
                {editIbanLoading ? 'Saving...' : 'Save Changes'}
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
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'page-background'}`}>
      <header className={`${isDark ? 'bg-gray-800' : 'header-gradient'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-4">
            <h1 className={`text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`} style={{ fontFamily: 'Space Grotesk' }}>
              <StyledLogo isDark={isDark} />
            </h1>
            <div className="flex items-center space-x-4">
              <NotificationBell />
              {/* Language Toggle */}
              <button
                onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
                className={`flex items-center space-x-1 px-3 py-1.5 rounded-md text-sm font-medium transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
                title={language === 'en' ? 'Switch to Italian' : 'Passa a Inglese'}
              >
                <span className="font-bold">{language === 'en' ? 'EN' : 'IT'}</span>
              </button>
              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className={`p-2 rounded-md transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
                title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
              >
                {isDark ? (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                  </svg>
                )}
              </button>
              <button onClick={logout} className={`text-sm ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-600 hover:text-gray-900'}`}>
                {t('logout')}
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className={`border-b ${isDark ? 'border-gray-700 bg-gray-800/80' : 'border-gray-200 bg-white/80 backdrop-blur'}`}>
        <nav className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex space-x-8">
          <button onClick={() => navigate('/dashboard')} className={`py-4 px-1 border-b-2 border-transparent font-medium text-sm ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}>
            {t('accounts')}
          </button>
          <button onClick={() => navigate('/kyc')} className={`py-4 px-1 border-b-2 border-transparent font-medium text-sm ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}>
            KYC
          </button>
          <button onClick={() => navigate('/security')} className={`py-4 px-1 border-b-2 border-transparent font-medium text-sm ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}>
            {t('securitySettings')}
          </button>
          <button onClick={() => navigate('/support')} className={`py-4 px-1 border-b-2 border-transparent font-medium text-sm ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}>
            {t('support')}
          </button>
          <button onClick={() => navigate('/profile')} className="py-4 px-1 border-b-2 border-blue-600 font-medium text-sm text-blue-600">
            {t('profile')}
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
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'page-background'}`}>
      <header className={`border-b px-4 sm:px-6 h-16 flex items-center justify-between ${isDark ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-200'}`}>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/dashboard')} className={`${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`} data-testid="support-back-btn">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className={`logo-text font-bold ${isDark ? 'text-white' : 'text-gray-900'}`} data-testid="logo"><StyledLogo isDark={isDark} /></span>
        </div>
        <div className="flex items-center gap-4">
          {/* Language Toggle */}
          <button
            onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
            className={`flex items-center space-x-1 px-2 py-1.5 rounded-md text-sm font-medium transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
            title={language === 'en' ? 'Switch to Italian' : 'Passa a Inglese'}
            data-testid="support-language-toggle"
          >
            <span className="font-bold">{language === 'en' ? 'EN' : 'IT'}</span>
          </button>
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-md transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
            title={isDark ? 'Switch to light mode' : 'Switch to dark mode'}
            data-testid="support-theme-toggle"
          >
            {isDark ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
          <NotificationBell userId={user?.id} />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <SupportTickets />
      </main>
      <MobileBottomTabs />
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
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-white'}`} data-testid="insights-page">
      <header className={`border-b px-4 sm:px-6 h-16 flex items-center justify-between ${isDark ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-200'}`}>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/dashboard')} className={`${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`} data-testid="insights-back-btn">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className={`logo-text font-bold ${isDark ? 'text-white' : 'text-gray-900'}`} data-testid="logo"><StyledLogo isDark={isDark} /></span>
        </div>
        <div className="flex items-center gap-4">
          {/* Language Toggle */}
          <button
            onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
            className={`flex items-center space-x-1 px-2 py-1.5 rounded-md text-sm font-medium transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
            title={language === 'en' ? t('switchToItalian') : t('switchToEnglish')}
            data-testid="insights-language-toggle"
          >
            <span className="font-bold">{language === 'en' ? 'EN' : 'IT'}</span>
          </button>
          {/* Theme Toggle */}
          <button
            onClick={toggleTheme}
            className={`p-2 rounded-md transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
            title={isDark ? t('switchToLightMode') : t('switchToDarkMode')}
            data-testid="insights-theme-toggle"
          >
            {isDark ? (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
            ) : (
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
              </svg>
            )}
          </button>
          <NotificationBell userId={user?.id} />
        </div>
      </header>
      <div className="container-main py-8">
        <h2 className={`text-2xl font-semibold mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`} data-testid="insights-title">{t('spendingInsights')}</h2>
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
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <CustomerDashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/accounts"
            element={
              <ProtectedRoute>
                <TaxHoldRestrictedRoute>
                  <AccountsPage />
                </TaxHoldRestrictedRoute>
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
            path="/transactions"
            element={
              <ProtectedRoute>
                <TaxHoldRestrictedRoute>
                  <AccountsPage />
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
