// Cards Page - Professional Visual Card Display
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { NotificationBell } from './Notifications';
import { MobileBottomTabs } from './MobileNav';
import { CardOrderingModal } from './CardOrderingModal';
import { useToast } from './Toast';
import api from '../api';
import { useLanguage, useTheme } from '../contexts/AppContext';

// Styled Logo Component - displays "ecomm" with "bx" in red
const StyledLogo = ({ isDark = false }) => (
  <span className={`font-bold ${isDark ? 'text-white' : 'text-gray-900'}`}>
    ecomm<span className="text-red-500">bx</span>
  </span>
);

export function CardsPage({ user, logout }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [cards, setCards] = useState([]);
  const [cardRequests, setCardRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [kycStatus, setKycStatus] = useState(null);
  const [showCardDetails, setShowCardDetails] = useState(null);
  const { t, language, setLanguage } = useLanguage();
  const { isDark, toggleTheme } = useTheme();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const [cardsRes, requestsRes, kycRes] = await Promise.all([
        api.get('/cards').catch(() => ({data: {ok: true, data: []}})),
        api.get('/card-requests').catch(() => ({data: {ok: true, data: []}})),
        api.get('/kyc/application')
      ]);
      
      setCards(cardsRes.data.data || []);
      setCardRequests(requestsRes.data.data || []);
      setKycStatus(kycRes.data?.status);
    } catch (err) {
      console.error('Failed to load cards:', err);
    } finally {
      setLoading(false);
    }
  };

  const canOrderCard = kycStatus === 'APPROVED';
  const pendingRequests = cardRequests.filter(r => r.status === 'PENDING');

  return (
    <div className={`min-h-screen ${isDark ? 'bg-gray-900' : 'bg-white'}`}>
      <header className={`border-b px-4 sm:px-6 h-16 flex items-center justify-between ${isDark ? 'bg-gray-900 border-gray-800' : 'bg-white border-gray-200'}`}>
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/dashboard')} className={`${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-700'}`}>
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="logo-text" data-testid="logo"><StyledLogo isDark={isDark} /></span>
        </div>
        <div className="flex items-center gap-4">
          {/* Language Toggle */}
          <button
            onClick={() => setLanguage(language === 'en' ? 'it' : 'en')}
            className={`flex items-center space-x-1 px-2 py-1.5 rounded-md text-sm font-medium transition ${isDark ? 'hover:bg-gray-700 text-gray-300' : 'hover:bg-gray-100 text-gray-700'}`}
            title={language === 'en' ? 'Switch to Italian' : 'Passa a Inglese'}
          >
            <span className="text-base">{language === 'en' ? '🇬🇧' : '🇮🇹'}</span>
            <span className="hidden sm:inline">{language === 'en' ? 'EN' : 'IT'}</span>
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
          <NotificationBell userId={user?.id} />
        </div>
      </header>

      <main className="main-content pb-20 sm:pb-6">
        <div className="max-w-4xl mx-auto">
          {/* Page Header */}
          <div className="mb-8">
            <div className="flex items-start justify-between">
              <div>
                <h1 className={`text-2xl font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('myCards')}</h1>
                <p className={`text-sm mt-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('managePhysicalVirtual')}</p>
              </div>
              {/* Desktop: Show button inline */}
              {canOrderCard && (
                <button 
                  onClick={() => setShowOrderModal(true)}
                  className="hidden sm:inline-flex btn-primary items-center gap-2"
                  data-testid="order-card-button"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  {t('orderNewCard')}
                </button>
              )}
            </div>
            {/* Mobile: Show button below title */}
            {canOrderCard && (
              <button 
                onClick={() => setShowOrderModal(true)}
                className="sm:hidden mt-4 w-full btn-primary inline-flex items-center justify-center gap-2"
                data-testid="order-card-button-mobile"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                {t('orderNewCard')}
              </button>
            )}
          </div>

          {loading ? (
            <div className={`text-center py-12 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('loading')}</div>
          ) : cards.length === 0 && pendingRequests.length === 0 ? (
            <div className="text-center py-16">
              <div className={`w-20 h-20 mx-auto mb-6 rounded-full flex items-center justify-center ${isDark ? 'bg-gray-800' : 'bg-gray-100'}`}>
                <svg className={`w-10 h-10 ${isDark ? 'text-gray-500' : 'text-gray-400'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              </div>
              <h3 className={`text-lg font-medium mb-2 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('noCardsYet')}</h3>
              <p className={`mb-6 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('orderFirstCard')}</p>
              {canOrderCard && (
                <button onClick={() => setShowOrderModal(true)} className="btn-primary">
                  {t('orderYourFirstCard')}
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-8">
              {/* Active Cards */}
              {cards.length > 0 && (
                <div>
                  <h2 className={`text-sm font-medium uppercase tracking-wider mb-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('activeCards')}</h2>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {cards.map((card) => (
                      <div key={card.id} className="space-y-3" data-testid={`card-${card.id}`}>
                        {/* Visual Card */}
                        <div 
                          className="relative w-full aspect-[1.586/1] rounded-2xl overflow-hidden cursor-pointer transform transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl shadow-xl"
                          style={{
                            background: card.card_type === 'VIRTUAL' 
                              ? 'linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%)'
                              : 'linear-gradient(135deg, #2d2d2d 0%, #1a1a1a 50%, #0d0d0d 100%)'
                          }}
                          onClick={() => setShowCardDetails(showCardDetails === card.id ? null : card.id)}
                        >
                          {/* Card Chip */}
                          <div className="absolute top-6 left-6">
                            <div className="w-12 h-10 rounded-md bg-gradient-to-br from-yellow-300 via-yellow-400 to-yellow-600 opacity-90 shadow-md">
                              <div className="w-full h-full grid grid-cols-3 gap-0.5 p-1.5">
                                {[...Array(6)].map((_, i) => (
                                  <div key={i} className="bg-yellow-600/30 rounded-sm"></div>
                                ))}
                              </div>
                            </div>
                          </div>

                          {/* Contactless Icon */}
                          <div className="absolute top-6 right-6">
                            <svg className="w-10 h-10 text-white/50" viewBox="0 0 24 24" fill="currentColor">
                              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8z" opacity="0.3"/>
                              <path d="M7.5 12c0-2.48 2.02-4.5 4.5-4.5v-2c-3.58 0-6.5 2.92-6.5 6.5s2.92 6.5 6.5 6.5v-2c-2.48 0-4.5-2.02-4.5-4.5z"/>
                              <path d="M12 7.5c2.48 0 4.5 2.02 4.5 4.5s-2.02 4.5-4.5 4.5v2c3.58 0 6.5-2.92 6.5-6.5s-2.92-6.5-6.5-6.5v2z"/>
                            </svg>
                          </div>

                          {/* Card Type Badge */}
                          <div className="absolute top-16 left-6">
                            <span className="text-white/60 text-xs font-medium uppercase tracking-widest">
                              {card.card_type === 'VIRTUAL' ? t('virtualCard') : t('physicalCard')}
                            </span>
                          </div>

                          {/* Card Number */}
                          <div className="absolute bottom-20 left-6 right-6">
                            <p className="text-white font-mono text-xl tracking-[0.25em]">
                              {showCardDetails === card.id 
                                ? (card.pan || '').match(/.{1,4}/g)?.join(' ') || '•••• •••• •••• ••••'
                                : `•••• •••• •••• ${card.pan?.slice(-4) || '••••'}`
                              }
                            </p>
                          </div>

                          {/* Card Holder & Expiry */}
                          <div className="absolute bottom-6 left-6 right-20 flex justify-between items-end">
                            <div>
                              <p className="text-white/40 text-[10px] uppercase tracking-widest mb-1">{t('cardHolder')}</p>
                              <p className="text-white text-sm font-medium uppercase tracking-wider">
                                {card.cardholder_name || `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || 'CARD HOLDER'}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-white/40 text-[10px] uppercase tracking-widest mb-1">{t('validThru')}</p>
                              <p className="text-white text-sm font-mono">
                                {String(card.exp_month || 12).padStart(2, '0')}/{String(card.exp_year || 2030).slice(-2)}
                              </p>
                            </div>
                          </div>

                          {/* Mastercard Logo */}
                          <div className="absolute bottom-4 right-4">
                            <div className="flex">
                              <div className="w-7 h-7 rounded-full bg-red-500 opacity-90"></div>
                              <div className="w-7 h-7 rounded-full bg-yellow-400 opacity-90 -ml-2"></div>
                            </div>
                          </div>

                          {/* Status Indicator */}
                          <div className="absolute top-6 left-20 ml-2">
                            <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${
                              card.status === 'ACTIVE' ? 'bg-green-500/20 text-green-300' : 'bg-yellow-500/20 text-yellow-300'
                            }`}>
                              {card.status}
                            </span>
                          </div>
                        </div>

                        {/* Card Details Panel */}
                        {showCardDetails === card.id && (
                          <div className={`rounded-xl p-5 border animate-fadeIn ${isDark ? 'bg-gray-800 border-gray-700' : 'bg-gray-50 border-gray-200'}`}>
                            <h4 className={`text-sm font-medium mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('cardDetails')}</h4>
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <p className={`text-xs mb-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('cardNumber')}</p>
                                <p className={`font-mono text-sm tracking-wide ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>
                                  {(card.pan || '').match(/.{1,4}/g)?.join(' ') || 'N/A'}
                                </p>
                              </div>
                              <div>
                                <p className={`text-xs mb-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('cvvCvc')}</p>
                                <p className={`font-mono text-sm ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{card.cvv || '•••'}</p>
                              </div>
                              <div>
                                <p className={`text-xs mb-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('expiryDate')}</p>
                                <p className={`font-mono text-sm ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>
                                  {String(card.exp_month).padStart(2, '0')}/{card.exp_year}
                                </p>
                              </div>
                              <div>
                                <p className={`text-xs mb-1 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('cardType')}</p>
                                <p className={`text-sm capitalize ${isDark ? 'text-gray-200' : 'text-gray-900'}`}>{card.card_type?.toLowerCase()}</p>
                              </div>
                            </div>
                            <div className={`mt-4 pt-4 border-t ${isDark ? 'border-gray-700' : 'border-gray-200'}`}>
                              <p className={`text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                                {t('cardId')}: <span className="font-mono">{card.id}</span>
                              </p>
                            </div>
                          </div>
                        )}

                        {/* Click Hint */}
                        <p className={`text-center text-xs ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                          {showCardDetails === card.id ? t('clickCardToHide') : t('clickCardToShow')}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Pending Card Requests */}
              {pendingRequests.length > 0 && (
                <div>
                  <h2 className={`text-sm font-medium uppercase tracking-wider mb-4 ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('pendingRequests')}</h2>
                  <div className="space-y-3">
                    {pendingRequests.map((request) => (
                      <div key={request.id} className={`rounded-xl p-4 flex items-center justify-between ${isDark ? 'bg-yellow-900/20 border border-yellow-800/30' : 'bg-yellow-50 border border-yellow-200'}`}>
                        <div className="flex items-center gap-4">
                          <div className={`w-12 h-12 rounded-full flex items-center justify-center ${isDark ? 'bg-yellow-900/30' : 'bg-yellow-100'}`}>
                            <svg className={`w-6 h-6 ${isDark ? 'text-yellow-500' : 'text-yellow-600'}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          </div>
                          <div>
                            <p className={`font-medium ${isDark ? 'text-gray-100' : 'text-gray-900'}`}>
                              {request.card_type === 'VIRTUAL' ? t('virtualCardRequest') : t('physicalCardRequest')}
                            </p>
                            <p className={`text-sm ${isDark ? 'text-gray-400' : 'text-gray-500'}`}>{t('waitingForApproval')}</p>
                          </div>
                        </div>
                        <span className={`px-3 py-1 rounded-full text-sm font-medium ${isDark ? 'bg-yellow-900/40 text-yellow-400' : 'bg-yellow-100 text-yellow-800'}`}>
                          {t('pending')}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      <MobileBottomTabs user={user} />

      {showOrderModal && <CardOrderingModal onClose={() => setShowOrderModal(false)} onSuccess={fetchData} />}
    </div>
  );
}
