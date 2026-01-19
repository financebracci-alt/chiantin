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
      title: language === 'it' ? 'Conti e-Personali' : 'Personal e-Accounts',
      description: language === 'it' ? 'Conti multivaluta con IBAN UE, configurazione istantanea e controllo completo' : 'Multi-currency accounts with EU IBAN, instant setup and full control',
    },
    {
      icon: '🏢',
      title: language === 'it' ? 'Conti Aziendali' : 'Business Accounts',
      description: language === 'it' ? 'Banking aziendale dedicato con strumenti di gestione della tesoreria' : 'Dedicated business banking with treasury management tools',
    },
    {
      icon: '💸',
      title: language === 'it' ? 'Trasferimenti Istantanei' : 'Instant Transfers',
      description: language === 'it' ? 'Trasferimenti SEPA e internazionali con tariffe competitive' : 'SEPA and international transfers with competitive rates',
    },
    {
      icon: '🎴',
      title: language === 'it' ? 'Carte Virtuali e Fisiche' : 'Virtual & Physical Cards',
      description: language === 'it' ? 'Carte di debito Visa per pagamenti senza problemi in tutto il mondo' : 'Visa debit cards for seamless payments worldwide',
    },
    {
      icon: '🔒',
      title: language === 'it' ? 'Sicurezza Bancaria' : 'Bank-Grade Security',
      description: language === 'it' ? 'Autenticazione a più fattori e protezione antifrode in tempo reale' : 'Multi-factor authentication and real-time fraud protection',
    },
    {
      icon: '📊',
      title: language === 'it' ? 'Analisi Intelligenti' : 'Smart Analytics',
      description: language === 'it' ? 'Monitora le spese, imposta budget e ottieni approfondimenti finanziari' : 'Track spending, set budgets and gain financial insights',
    },
  ];

  const stats = [
    { value: '50K+', label: language === 'it' ? 'Utenti Attivi' : 'Active Users' },
    { value: '€2B+', label: language === 'it' ? 'Elaborati Annualmente' : 'Processed Annually' },
    { value: '99.9%', label: language === 'it' ? 'Uptime' : 'Uptime' },
    { value: '24/7', label: language === 'it' ? 'Supporto' : 'Support' },
  ];

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      {/* Navigation */}
      <nav className={`fixed top-0 left-0 right-0 ${isDark ? 'bg-gray-900/95 border-gray-800' : 'bg-white/95 border-gray-100'} backdrop-blur-sm border-b z-50`}>
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
                {language === 'it' ? 'Funzionalità' : 'Features'}
              </button>
              <button
                onClick={() => scrollToSection('about')}
                className={`font-medium transition-all duration-300 ${activeSection === 'about' ? 'text-red-500 scale-105' : isDark ? 'text-gray-300 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}
              >
                {language === 'it' ? 'Chi Siamo' : 'About'}
              </button>
              <button
                onClick={() => scrollToSection('security')}
                className={`font-medium transition-all duration-300 ${activeSection === 'security' ? 'text-red-500 scale-105' : isDark ? 'text-gray-300 hover:text-white' : 'text-gray-600 hover:text-gray-900'}`}
              >
                {language === 'it' ? 'Sicurezza' : 'Security'}
              </button>
              
              {/* Language Toggle */}
              <button
                onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
                className={`p-2 rounded-lg transition ${isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-100'}`}
                title={language === 'en' ? 'Switch to Italian' : 'Passa all\'Inglese'}
              >
                <span className="text-lg">{language === 'en' ? '🇬🇧' : '🇮🇹'}</span>
              </button>
              
              {/* Theme Toggle */}
              <button
                onClick={toggleTheme}
                className={`p-2 rounded-lg transition ${isDark ? 'hover:bg-gray-800 text-yellow-400' : 'hover:bg-gray-100 text-gray-600'}`}
                title={isDark ? (language === 'it' ? 'Modalità Chiara' : 'Light Mode') : (language === 'it' ? 'Modalità Scura' : 'Dark Mode')}
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
              {/* Mobile Theme Toggle */}
              <button
                onClick={toggleTheme}
                className={`p-2 rounded-lg ${isDark ? 'text-yellow-400' : 'text-gray-600'}`}
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
              
              {/* Mobile Language Toggle */}
              <button
                onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
                className="p-2"
              >
                <span className="text-lg">{language === 'en' ? '🇬🇧' : '🇮🇹'}</span>
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
            <div className={`md:hidden py-4 border-t ${isDark ? 'border-gray-800' : 'border-gray-100'} animate-slideDown`}>
              <div className="flex flex-col space-y-4">
                <button
                  onClick={() => scrollToSection('features')}
                  className={`text-left font-medium transition-colors ${isDark ? 'text-gray-300 hover:text-red-400' : 'text-gray-600 hover:text-red-600'}`}
                >
                  {language === 'it' ? 'Funzionalità' : 'Features'}
                </button>
                <button
                  onClick={() => scrollToSection('about')}
                  className={`text-left font-medium transition-colors ${isDark ? 'text-gray-300 hover:text-red-400' : 'text-gray-600 hover:text-red-600'}`}
                >
                  {language === 'it' ? 'Chi Siamo' : 'About'}
                </button>
                <button
                  onClick={() => scrollToSection('security')}
                  className={`text-left font-medium transition-colors ${isDark ? 'text-gray-300 hover:text-red-400' : 'text-gray-600 hover:text-red-600'}`}
                >
                  {language === 'it' ? 'Sicurezza' : 'Security'}
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
      <section className="pt-24 sm:pt-32 pb-16 sm:pb-24 relative overflow-hidden">
        {/* Background Pattern */}
        <div className="absolute inset-0 opacity-5">
          <div className="absolute top-20 right-20 w-96 h-96 bg-red-500 rounded-full blur-3xl"></div>
          <div className="absolute bottom-20 left-20 w-72 h-72 bg-blue-500 rounded-full blur-3xl"></div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative">
          <div className="grid lg:grid-cols-2 gap-12 items-center">
            {/* Left Content */}
            <div className="text-center lg:text-left">
              <div className={`inline-flex items-center space-x-2 ${isDark ? 'bg-red-900/30 text-red-400' : 'bg-red-50 text-red-600'} px-4 py-2 rounded-full text-sm font-medium mb-6`}>
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
                </span>
                <span>{language === 'it' ? 'Banca Digitale con Licenza UE' : 'EU Licensed Digital Bank'}</span>
              </div>
              
              <h1 className={`text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight mb-6 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {language === 'it' ? 'Una piattaforma per' : 'A platform to'}{' '}
                <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-red-600">
                  {language === 'it' ? 'governarle tutte' : 'rule them all'}
                </span>
              </h1>
              
              <p className={`text-lg sm:text-xl mb-8 max-w-xl mx-auto lg:mx-0 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
                {language === 'it' 
                  ? 'Project Atlas rappresenta la nuova era del fintech, rivoluzionando il modo in cui gestisci le transazioni globali con conti multivaluta, trasferimenti istantanei e sicurezza bancaria.'
                  : 'Project Atlas represents the new age of fintech, revolutionizing the way you handle global transactions with multi-currency accounts, instant transfers, and bank-grade security.'}
              </p>

              <div className="flex flex-col sm:flex-row gap-4 justify-center lg:justify-start">
                <button
                  onClick={() => navigate('/signup')}
                  className="px-8 py-4 bg-gradient-to-r from-red-500 to-red-600 text-white font-semibold rounded-full text-lg hover:shadow-xl hover:shadow-red-500/30 transition-all duration-300 transform hover:-translate-y-1"
                >
                  {language === 'it' ? 'Unisciti al Futuro' : 'Join the Future'}
                </button>
                <button
                  onClick={() => navigate('/login')}
                  className={`px-8 py-4 font-semibold rounded-full text-lg transition-all duration-300 ${isDark ? 'bg-gray-800 text-white hover:bg-gray-700' : 'bg-gray-100 text-gray-800 hover:bg-gray-200'}`}
                >
                  {t('signIn')}
                </button>
              </div>

              {/* Trust Badges */}
              <div className={`mt-10 flex flex-wrap items-center justify-center lg:justify-start gap-6 text-sm ${isDark ? 'text-gray-500' : 'text-gray-500'}`}>
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>{language === 'it' ? 'Conforme GDPR' : 'GDPR Compliant'}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>{language === 'it' ? 'Certificato PSD2' : 'PSD2 Certified'}</span>
                </div>
                <div className="flex items-center space-x-2">
                  <svg className="w-5 h-5 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                  <span>{language === 'it' ? 'Crittografia 256-bit' : '256-bit Encryption'}</span>
                </div>
              </div>
            </div>

            {/* Right Content - App Preview */}
            <div className="relative lg:pl-10">
              <div className="relative mx-auto max-w-sm">
                {/* Phone Frame */}
                <div className="relative bg-gray-900 rounded-[3rem] p-3 shadow-2xl shadow-gray-900/30">
                  <div className={`rounded-[2.5rem] overflow-hidden ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
                    {/* App Screen Preview */}
                    <div className={`p-6 h-[500px] ${isDark ? 'bg-gradient-to-br from-gray-800 to-gray-900' : 'bg-gradient-to-br from-gray-50 to-white'}`}>
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
      <section className={`py-12 border-y ${isDark ? 'bg-gray-800/50 border-gray-800' : 'bg-gray-50 border-gray-100'}`}>
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
      <section id="features" className="py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className={`text-3xl sm:text-4xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {language === 'it' ? 'Perché scegliere Project Atlas' : 'Why choose Project Atlas'}
            </h2>
            <p className={`text-lg max-w-2xl mx-auto ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {language === 'it' 
                ? 'Perché sappiamo che la tecnologia innovativa è valida solo quanto il servizio che la accompagna — il servizio Atlas 24/7.'
                : 'Because we know that innovative technology is only as good as the service that accompanies it — the 24/7 Atlas service.'}
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {features.map((feature, index) => (
              <div
                key={index}
                className={`group p-8 border rounded-2xl hover:shadow-xl hover:shadow-red-500/5 transition-all duration-300 ${isDark ? 'bg-gray-800 border-gray-700 hover:border-red-500/30' : 'bg-white border-gray-200 hover:border-red-200'}`}
              >
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center text-2xl mb-5 group-hover:scale-110 transition-transform duration-300 ${isDark ? 'bg-red-900/30' : 'bg-red-50'}`}>
                  {feature.icon}
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">{feature.title}</h3>
                <p className="text-gray-600">{feature.description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* About Section */}
      <section id="about" className="py-20 sm:py-28 bg-gray-900 text-white">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid lg:grid-cols-2 gap-16 items-center">
            <div>
              <h2 className="text-3xl sm:text-4xl font-bold mb-6">
                {language === 'it' ? 'Questo è Project Atlas' : 'This is Project Atlas'}
              </h2>
              <p className="text-lg text-gray-300 mb-6">
                {language === 'it' 
                  ? 'Project Atlas rappresenta la nuova era del fintech, rivoluzionando il modo in cui aziende e privati gestiscono le loro transazioni globali.'
                  : 'Project Atlas represents the new age of fintech, revolutionizing the way businesses and individuals handle their global transactions.'}
              </p>
              <p className="text-gray-400 mb-6">
                {language === 'it'
                  ? 'Siamo specializzati in gestione di conti elettronici, pagamenti transfrontalieri, carte personali e aziendali e conversioni multivaluta — tutto attraverso un\'unica piattaforma innovativa e intuitiva che ti dà accesso istantaneo a tutti i nostri servizi.'
                  : 'We specialize in e-account management, cross-border payments, personal & business cards, and multi-currency conversions — all through a single, innovative and intuitive platform that gives you instant access to all of our services.'}
              </p>
              <p className="text-gray-400 mb-8">
                {language === 'it'
                  ? 'Il nostro modello di servizio si basa su quattro pilastri: tecnologia all\'avanguardia progettata per il settore bancario globale; connessioni personalizzate con partner bancari in tutto il mondo; sicurezza rigorosa; e massima velocità operativa.'
                  : 'Our service model is based on four cornerstones: cutting-edge technology designed for the global banking industry; customized connections with banking partners around the world; stringent security; and maximum operational speed.'}
              </p>
              <button
                onClick={() => navigate('/signup')}
                className="px-8 py-4 bg-white text-gray-900 font-semibold rounded-full hover:bg-gray-100 transition"
              >
                {t('openAccount')}
              </button>
            </div>
            <div className="relative">
              <div className="bg-gradient-to-br from-red-500/20 to-red-600/20 rounded-3xl p-8">
                <div className="grid grid-cols-2 gap-4">
                  <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
                    <div className="text-3xl mb-2">🌍</div>
                    <p className="text-lg font-semibold">{language === 'it' ? 'Portata Globale' : 'Global Reach'}</p>
                    <p className="text-sm text-gray-400">{language === 'it' ? '150+ paesi' : '150+ countries'}</p>
                  </div>
                  <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
                    <div className="text-3xl mb-2">💱</div>
                    <p className="text-lg font-semibold">{language === 'it' ? 'Multivaluta' : 'Multi-Currency'}</p>
                    <p className="text-sm text-gray-400">{language === 'it' ? '30+ valute' : '30+ currencies'}</p>
                  </div>
                  <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
                    <div className="text-3xl mb-2">⚡</div>
                    <p className="text-lg font-semibold">{language === 'it' ? 'Istantaneo' : 'Instant'}</p>
                    <p className="text-sm text-gray-400">{language === 'it' ? 'Trasferimenti in tempo reale' : 'Real-time transfers'}</p>
                  </div>
                  <div className="bg-white/10 backdrop-blur rounded-2xl p-6">
                    <div className="text-3xl mb-2">🛡️</div>
                    <p className="text-lg font-semibold">{language === 'it' ? 'Sicuro' : 'Secure'}</p>
                    <p className="text-sm text-gray-400">{language === 'it' ? 'Sicurezza bancaria' : 'Bank-grade security'}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Security Section */}
      <section id="security" className="py-20 sm:py-28">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className={`text-3xl sm:text-4xl font-bold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>
              {language === 'it' ? 'Sicurezza bancaria' : 'Bank-grade security'}
            </h2>
            <p className={`text-lg max-w-2xl mx-auto ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>
              {language === 'it' 
                ? 'La tua sicurezza è la nostra priorità. Impieghiamo più livelli di protezione per mantenere al sicuro i tuoi soldi e i tuoi dati.'
                : 'Your security is our priority. We employ multiple layers of protection to keep your money and data safe.'}
            </p>
          </div>

          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center p-8">
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5 ${isDark ? 'bg-red-900/30' : 'bg-red-100'}`}>
                <svg className={`w-8 h-8 ${isDark ? 'text-red-400' : 'text-red-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
              </div>
              <h3 className={`text-xl font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {language === 'it' ? 'Crittografia 256-bit' : '256-bit Encryption'}
              </h3>
              <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>
                {language === 'it' ? 'Tutti i dati sono crittografati con standard di crittografia di livello militare.' : 'All data is encrypted using military-grade encryption standards.'}
              </p>
            </div>
            <div className="text-center p-8">
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5 ${isDark ? 'bg-red-900/30' : 'bg-red-100'}`}>
                <svg className={`w-8 h-8 ${isDark ? 'text-red-400' : 'text-red-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                </svg>
              </div>
              <h3 className={`text-xl font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {language === 'it' ? 'Autenticazione Multi-Fattore' : 'Multi-Factor Auth'}
              </h3>
              <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>
                {language === 'it' ? 'Proteggi il tuo account con biometria, SMS e app di autenticazione.' : 'Protect your account with biometrics, SMS, and authenticator apps.'}
              </p>
            </div>
            <div className="text-center p-8">
              <div className={`w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5 ${isDark ? 'bg-red-900/30' : 'bg-red-100'}`}>
                <svg className={`w-8 h-8 ${isDark ? 'text-red-400' : 'text-red-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                </svg>
              </div>
              <h3 className={`text-xl font-semibold mb-3 ${isDark ? 'text-white' : 'text-gray-900'}`}>
                {language === 'it' ? 'Monitoraggio 24/7' : '24/7 Monitoring'}
              </h3>
              <p className={isDark ? 'text-gray-400' : 'text-gray-600'}>
                {language === 'it' ? 'Rilevamento frodi in tempo reale e avvisi di attività sospette.' : 'Real-time fraud detection and suspicious activity alerts.'}
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 sm:py-28 bg-gradient-to-r from-red-500 to-red-600">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-6">
            {language === 'it' ? 'Unisciti al futuro...' : 'Join the future...'}
          </h2>
          <p className="text-lg text-white/90 mb-8 max-w-2xl mx-auto">
            {language === 'it'
              ? 'Tutti i tuoi servizi di e-money e conto elettronico internazionali sono ora a portata di mano, per un banking digitale più facile, veloce e fluido… sempre e ovunque!'
              : 'All your international e-money and e-account services are now at your fingertips, for easier, faster and smoother digital banking… anytime, anywhere!'}
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => navigate('/signup')}
              className="px-8 py-4 bg-white text-red-600 font-semibold rounded-full text-lg hover:bg-gray-100 transition-all duration-300 transform hover:-translate-y-1"
            >
              {language === 'it' ? 'Crea Account Gratuito' : 'Create Free Account'}
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
      <footer className="bg-gray-900 text-gray-400 py-16">
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
                {language === 'it' 
                  ? 'Piattaforma di Banking Digitale con Licenza UE. Rivoluzionando il modo in cui gestisci le transazioni globali.'
                  : 'EU Licensed Digital Banking Platform. Revolutionizing the way you handle global transactions.'}
              </p>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">{language === 'it' ? 'Prodotti' : 'Products'}</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Conti Personali' : 'Personal Accounts'}</a></li>
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Conti Aziendali' : 'Business Accounts'}</a></li>
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Carte' : 'Cards'}</a></li>
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Trasferimenti' : 'Transfers'}</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">{language === 'it' ? 'Azienda' : 'Company'}</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Chi Siamo' : 'About Us'}</a></li>
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Lavora con Noi' : 'Careers'}</a></li>
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Stampa' : 'Press'}</a></li>
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Contatti' : 'Contact'}</a></li>
              </ul>
            </div>
            <div>
              <h4 className="text-white font-semibold mb-4">{language === 'it' ? 'Legale' : 'Legal'}</h4>
              <ul className="space-y-2 text-sm">
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Privacy Policy' : 'Privacy Policy'}</a></li>
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Termini di Servizio' : 'Terms of Service'}</a></li>
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Cookie Policy' : 'Cookie Policy'}</a></li>
                <li><a href="#" className="hover:text-white transition">{language === 'it' ? 'Conformità' : 'Compliance'}</a></li>
              </ul>
            </div>
          </div>
          <div className="border-t border-gray-800 mt-12 pt-8 text-sm text-center">
            <p>© 2026 Project Atlas. All rights reserved. Licensed by the European Banking Authority.</p>
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
