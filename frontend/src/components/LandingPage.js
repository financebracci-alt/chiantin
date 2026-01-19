// Project Atlas - Professional Landing Page (Inspired by ECOMMBANX)
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useLanguage, useTheme } from '../contexts/AppContext';

export function LandingPage() {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('');
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  // Smooth scroll to section with animation
  const scrollToSection = (sectionId) => {
    setMobileMenuOpen(false);
    setActiveSection(sectionId);
    
    const element = document.getElementById(sectionId);
    if (element) {
      const navHeight = 80; // Account for fixed nav
      const elementPosition = element.getBoundingClientRect().top;
      const offsetPosition = elementPosition + window.pageYOffset - navHeight;

      window.scrollTo({
        top: offsetPosition,
        behavior: 'smooth'
      });

      // Reset active section after animation
      setTimeout(() => setActiveSection(''), 1000);
    }
  };

  const features = [
    {
      icon: '💳',
      title: t('personalAccounts'),
      description: t('personalAccountsDesc'),
    },
    {
      icon: '🏢',
      title: t('businessAccounts'),
      description: t('businessAccountsDesc'),
    },
    {
      icon: '💸',
      title: t('instantTransfers'),
      description: t('instantTransfersDesc'),
    },
    {
      icon: '🎴',
      title: t('virtualPhysicalCards'),
      description: t('virtualPhysicalCardsDesc'),
    },
    {
      icon: '🔒',
      title: t('bankGradeSecurity'),
      description: t('bankGradeSecurityDesc'),
    },
    {
      icon: '📊',
      title: t('smartAnalytics'),
      description: t('smartAnalyticsDesc'),
    },
  ];

  const stats = [
    { value: '50K+', label: t('activeUsers') },
    { value: '€2B+', label: t('processedAnnually') },
    { value: '99.9%', label: t('uptime') },
    { value: '24/7', label: t('support') },
  ];

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Navigation */}
      <nav className={`fixed top-0 left-0 right-0 backdrop-blur-sm border-b z-50 ${isDark ? 'bg-gray-900/95 border-gray-800' : 'bg-white/95 border-gray-100'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16 sm:h-20">
            {/* Logo */}
            <div className="flex items-center space-x-2 cursor-pointer" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
              <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold text-lg">A</span>
              </div>
              <span className={`text-xl sm:text-2xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>Project Atlas</span>
            </div>

            {/* Desktop Menu */}
            <div className="hidden md:flex items-center space-x-6">
              <button
                onClick={() => scrollToSection('features')}
                className={`font-medium transition-all duration-300 ${activeSection === 'features' ? 'text-red-500 scale-105' : isDark ? 'text-gray-300 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}
              >
                {t('features')}
              </button>
              <button
                onClick={() => scrollToSection('about')}
                className={`font-medium transition-all duration-300 ${activeSection === 'about' ? 'text-red-500 scale-105' : isDark ? 'text-gray-300 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}
              >
                {t('about')}
              </button>
              <button
                onClick={() => scrollToSection('security')}
                className={`font-medium transition-all duration-300 ${activeSection === 'security' ? 'text-red-500 scale-105' : isDark ? 'text-gray-300 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}
              >
                {t('security')}
              </button>
              
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
              
              <button
                onClick={() => navigate('/login')}
                className={`font-medium transition ${isDark ? 'text-gray-300 hover:text-white' : 'text-gray-700 hover:text-gray-900'}`}
              >
                {t('signIn')}
              </button>
              <button
                onClick={() => navigate('/signup')}
                className="px-6 py-2.5 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-full hover:shadow-lg hover:shadow-red-500/30 transition-all duration-300"
              >
                {t('getStarted')}
              </button>
            </div>

            {/* Mobile Menu Button */}
            <div className="flex items-center space-x-2 md:hidden">
              <button
                onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
                className={`px-2 py-1 rounded font-bold text-xs ${isDark ? 'bg-gray-800 text-gray-300' : 'bg-gray-100 text-gray-700'}`}
              >
                {language === 'en' ? 'EN' : 'IT'}
              </button>
              <button
                onClick={toggleTheme}
                className={`p-1.5 rounded ${isDark ? 'text-yellow-400' : 'text-gray-600'}`}
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
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                className={`p-2 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}
              >
                {mobileMenuOpen ? (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                ) : (
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                )}
              </button>
            </div>
          </div>

          {/* Mobile Menu */}
          {mobileMenuOpen && (
            <div className={`md:hidden py-4 border-t animate-slideDown ${isDark ? 'border-gray-800' : 'border-gray-100'}`}>
              <div className="flex flex-col space-y-4">
                <button
                  onClick={() => scrollToSection('features')}
                  className={`text-left font-medium transition-colors ${isDark ? 'text-gray-300 hover:text-red-400' : 'text-gray-600 hover:text-red-600'}`}
                >
                  {t('features')}
                </button>
                <button
                  onClick={() => scrollToSection('about')}
                  className={`text-left font-medium transition-colors ${isDark ? 'text-gray-300 hover:text-red-400' : 'text-gray-600 hover:text-red-600'}`}
                >
                  {t('about')}
                </button>
                <button
                  onClick={() => scrollToSection('security')}
                  className={`text-left font-medium transition-colors ${isDark ? 'text-gray-300 hover:text-red-400' : 'text-gray-600 hover:text-red-600'}`}
                >
                  {t('security')}
                </button>
                <button
                  onClick={() => navigate('/login')}
                  className={`text-left font-medium ${isDark ? 'text-gray-300 hover:text-white' : 'text-gray-700 hover:text-gray-900'}`}
                >
                  {t('signIn')}
                </button>
                <button
                  onClick={() => navigate('/signup')}
                  className="w-full py-3 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-full"
                >
                  {t('getStarted')}
                </button>
              </div>
            </div>
          )}
        </div>
      </nav>

      {/* Hero Section */}
      <section className={`pt-24 sm:pt-32 pb-16 sm:pb-24 relative overflow-hidden ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-20 right-20 w-96 h-96 bg-red-500 rounded-full blur-3xl"></div>
          <div className="absolute bottom-20 left-20 w-72 h-72 bg-blue-500 rounded-full blur-3xl"></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="text-center lg:text-left">
              <div className={`inline-flex items-center space-x-2 px-4 py-2 rounded-full text-sm font-medium mb-6 ${isDark ? 'bg-red-900/30 text-red-400' : 'bg-red-50 text-red-600'}`}>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                </span>
                <span>{t('euLicensedBank')}</span>
              </div>
              
              <h1 className={`text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {t('heroTitle')}{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-red-600">
                  {t('heroTitleHighlight')}
                </span>
              </h1>
              
              <p className={`text-lg sm:text-xl mb-8 max-w-xl mx-auto lg:mx-0 ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>
                {t('heroSubtitle')}
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                <button
                  onClick={() => navigate('/signup')}
                  className="px-8 py-4 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-full text-lg hover:shadow-xl hover:shadow-red-500/30 transition-all duration-300 transform hover:-translate-y-1"
                >
                  {t('joinTheFuture')}
                </button>
                <button
                  onClick={() => navigate('/login')}
                  className={`px-8 py-4 font-semibold rounded-full text-lg transition-all duration-300 ${isDark ? 'bg-gray-800 text-gray-200 hover:bg-gray-700' : 'bg-gray-100 text-gray-800 hover:bg-gray-200'}`}
                >
                  {t('signIn')}
                </button>
              </div>

              {/* Trust Badges */}
              <div className={`mt-10 flex flex-wrap items-center justify-center lg:justify-start gap-6 text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>{t('gdprCompliant')}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>{t('psd2Certified')}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>{t('encryption256')}</span>
                </div>
              </div>
            </div>

            {/* Right Content - App Preview */}
            <div className="relative lg:pl-10">
              <div className="relative mx-auto max-w-sm">
                {/* Phone Frame */}
                <div className="relative bg-gray-900 rounded-[3rem] p-3 shadow-2xl shadow-gray-900/30">
                  <div className="bg-white rounded-[2.5rem] overflow-hidden">
                    {/* App Screen Preview */}
                    <div className="bg-gradient-to-br from-gray-50 to-white p-6 h-[500px]">
                      {/* Mini Header */}
                      <div className="flex items-center justify-between mb-8">
                        <div>
                          <p className="text-xs text-gray-500">Good morning</p>
                          <p className="text-lg font-semibold text-gray-900">John Doe</p>
                        </div>
                        <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-full flex items-center justify-center text-white font-bold">
                          JD
                        </div>
                      </div>

                      {/* Balance Card */}
                      <div className="bg-gradient-to-r from-gray-900 to-gray-800 rounded-2xl p-5 text-white mb-6">
                        <p className="text-sm text-gray-400 mb-1">Total Balance</p>
                        <p className="text-3xl font-bold mb-4">€12,458.90</p>
                        <div className="flex items-center text-sm">
                          <span className="text-green-400">↑ 12.5%</span>
                          <span className="text-gray-400 ml-2">vs last month</span>
                        </div>
                      </div>

                      {/* Quick Actions */}
                      <div className="grid grid-cols-4 gap-3 mb-6">
                        {['Send', 'Request', 'Cards', 'More'].map((action) => (
                          <div key={action} className="text-center">
                            <div className="w-12 h-12 mx-auto bg-red-50 rounded-xl flex items-center justify-center mb-2">
                              <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                            </div>
                            <p className="text-xs text-gray-600">{action}</p>
                          </div>
                        ))}
                      </div>

                      {/* Recent */}
                      <p className="text-sm font-semibold text-gray-900 mb-3">Recent Activity</p>
                      <div className="space-y-3">
                        <div className="flex items-center justify-between py-2">
                          <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-gray-100 rounded-full"></div>
                            <div>
                              <p className="text-sm font-medium text-gray-900">Amazon EU</p>
                              <p className="text-xs text-gray-500">Shopping</p>
                            </div>
                          </div>
                          <p className="text-sm font-semibold text-gray-900">-€49.99</p>
                        </div>
                        <div className="flex items-center justify-between py-2">
                          <div className="flex items-center space-x-3">
                            <div className="w-10 h-10 bg-green-100 rounded-full"></div>
                            <div>
                              <p className="text-sm font-medium text-gray-900">Salary</p>
                              <p className="text-xs text-gray-500">Income</p>
                            </div>
                          </div>
                          <p className="text-sm font-semibold text-green-600">+€3,500</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
                
                {/* Floating Elements */}
                <div className="absolute -top-6 -right-6 bg-white rounded-2xl shadow-xl p-4 animate-bounce-slow">
                  <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-green-100 rounded-full flex items-center justify-center">
                      <svg className="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Transfer</p>
                      <p className="text-sm font-semibold text-gray-900">Complete</p>
                    </div>
                  </div>
                </div>

                <div className="absolute -bottom-4 -left-6 bg-white rounded-2xl shadow-xl p-4">
                  <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 bg-red-100 rounded-full flex items-center justify-center">
                      <svg className="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-xs text-gray-500">Security</p>
                      <p className="text-sm font-semibold text-gray-900">Protected</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className={`py-12 border-y ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-100'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {stats.map((stat, index) => (
              <div key={index} className="text-center">
                <p className={`text-3xl sm:text-4xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>{stat.value}</p>
                <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className={`py-20 sm:py-28 ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className={`text-3xl sm:text-4xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {t('whyChooseAtlas')}
            </h2>
            <p className={`text-lg max-w-2xl mx-auto ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('whyChooseDesc')}
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className={`group p-8 border rounded-2xl transition-all duration-300 ${isDark ? 'bg-gray-800 border-gray-700 hover:border-red-500/50 hover:shadow-xl hover:shadow-red-500/10' : 'bg-white border-gray-200 hover:border-red-200 hover:shadow-xl hover:shadow-red-500/5'}`}
              >
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl mb-5 group-hover:scale-110 transition-transform duration-300 ${isDark ? 'bg-red-900/30' : 'bg-red-50'}`}>
                  {feature.icon}
                </div>
                <h3 className={`text-xl font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{feature.title}</h3>
                <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className={`py-20 sm:py-28 ${isDark ? 'bg-gray-800' : 'bg-gray-900'} text-white`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold mb-6">
                {t('thisIsAtlas')}
              </h2>
              <p className="text-lg text-gray-300 mb-6">
                {t('aboutDesc1')}
              </p>
              <p className="text-gray-400 mb-6">
                {t('aboutDesc2')}
              </p>
              <p className="text-gray-400 mb-8">
                {t('aboutDesc3')}
              </p>
              <button
                onClick={() => navigate('/signup')}
                className="px-8 py-4 bg-white text-gray-900 font-semibold rounded-full hover:bg-gray-100 transition"
              >
                {t('openYourAccount')}
              </button>
            </div>
            <div className="relative">
              <div className="bg-gradient-to-br from-red-500/20 to-red-600/20 rounded-3xl p-8">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
                    <div className="text-3xl mb-2">🌍</div>
                    <p className="text-lg font-semibold">{t('globalReach')}</p>
                    <p className="text-sm text-gray-400">150+ {t('countries')}</p>
                  </div>
                  <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
                    <div className="text-3xl mb-2">💱</div>
                    <p className="text-lg font-semibold">{t('multiCurrency')}</p>
                    <p className="text-sm text-gray-400">30+ {t('currencies')}</p>
                  </div>
                  <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
                    <div className="text-3xl mb-2">⚡</div>
                    <p className="text-lg font-semibold">{t('instant')}</p>
                    <p className="text-sm text-gray-400">{t('realTimeTransfers')}</p>
                  </div>
                  <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
                    <div className="text-3xl mb-2">🛡️</div>
                    <p className="text-lg font-semibold">{t('secure')}</p>
                    <p className="text-sm text-gray-400">{t('bankGradeSecurity')}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section id="security" className={`py-20 sm:py-28 ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className={`text-3xl sm:text-4xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {t('securityTitle')}
            </h2>
            <p className={`text-lg max-w-2xl mx-auto ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {t('securityDesc')}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center p-8">
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5 ${isDark ? 'bg-red-900/30' : 'bg-red-100'}`}>
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className={`text-xl font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('encryption')}</h3>
              <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>{t('encryptionDesc')}</p>
            </div>
            <div className="text-center p-8">
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5 ${isDark ? 'bg-red-900/30' : 'bg-red-100'}`}>
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className={`text-xl font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('multiFactorAuth')}</h3>
              <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>{t('multiFactorAuthDesc')}</p>
            </div>
            <div className="text-center p-8">
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5 ${isDark ? 'bg-red-900/30' : 'bg-red-100'}`}>
                <svg className="w-8 h-8 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </div>
              <h3 className={`text-xl font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('monitoring247')}</h3>
              <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>{t('monitoring247Desc')}</p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 sm:py-28 bg-gradient-to-r from-red-500 to-red-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
            {t('joinTheFutureTitle')}
          </h2>
          <p className="text-lg text-white/90 mb-8 max-w-2xl mx-auto">
            {t('ctaDesc')}
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => navigate('/signup')}
              className="px-8 py-4 bg-white text-red-600 font-semibold rounded-full text-lg hover:bg-gray-100 transition-all duration-300 transform hover:-translate-y-1"
            >
              {t('createFreeAccount')}
            </button>
            <button
              onClick={() => navigate('/login')}
              className="px-8 py-4 bg-transparent border-2 border-white text-white font-semibold rounded-full text-lg hover:bg-white/10 transition-all duration-300"
            >
              {t('signIn')}
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className={`py-16 ${isDark ? 'bg-gray-950 text-gray-400' : 'bg-gray-900 text-gray-400'}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid md:grid-cols-4 gap-10">
            <div>
              <div className="flex items-center space-x-2 mb-6">
                <div className="w-10 h-10 bg-gradient-to-br from-red-500 to-red-600 rounded-xl flex items-center justify-center">
                  <span className="text-white font-bold text-lg">A</span>
                </div>
                <span className="text-xl font-bold text-white">Project Atlas</span>
              </div>
              <p className="text-sm">
                {t('footerDesc')}
              </p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">{t('products')}</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition">{t('personalAccounts')}</a></li>
                <li><a href="#" className="hover:text-white transition">{t('businessAccounts')}</a></li>
                <li><a href="#" className="hover:text-white transition">{t('cards')}</a></li>
                <li><a href="#" className="hover:text-white transition">{t('transfers')}</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">{t('company')}</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition">{t('aboutUs')}</a></li>
                <li><a href="#" className="hover:text-white transition">{t('careers')}</a></li>
                <li><a href="#" className="hover:text-white transition">{t('press')}</a></li>
                <li><a href="#" className="hover:text-white transition">{t('contact')}</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">{t('legal')}</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition">{t('privacyPolicy')}</a></li>
                <li><a href="#" className="hover:text-white transition">{t('termsOfService')}</a></li>
                <li><a href="#" className="hover:text-white transition">{t('cookiePolicy')}</a></li>
                <li><a href="#" className="hover:text-white transition">{t('compliance')}</a></li>
              </ul>
            </div>
          </div>
          <div className={`border-t mt-12 pt-8 text-sm text-center ${isDark ? 'border-gray-800' : 'border-gray-800'}`}>
            <p>© 2026 Project Atlas. {t('allRightsReserved')} {t('licensedBy')}</p>
          </div>
        </div>
      </footer>

      {/* Custom Animation Styles */}
      <style>{`
        @keyframes bounce-slow {
          0%, 100% { transform: translateY(0); }
          50% { transform: translateY(-10px); }
        }
        .animate-bounce-slow {
          animation: bounce-slow 3s ease-in-out infinite;
        }
        
        @keyframes slideDown {
          from {
            opacity: 0;
            transform: translateY(-10px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        .animate-slideDown {
          animation: slideDown 0.3s ease-out;
        }
        
        /* Smooth scroll behavior for the entire page */
        html {
          scroll-behavior: smooth;
        }
        
        /* Section highlight animation */
        @keyframes sectionHighlight {
          0% { opacity: 0.5; }
          50% { opacity: 1; }
          100% { opacity: 0.5; }
        }
        
        /* Fade in animation for sections when scrolled to */
        .scroll-animate {
          opacity: 0;
          transform: translateY(20px);
          transition: all 0.6s ease-out;
        }
        .scroll-animate.visible {
          opacity: 1;
          transform: translateY(0);
        }
      `}</style>
    </div>
  );
}

export default LandingPage;
