// Cards Page - Professional Visual Card Display
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { NotificationBell } from './Notifications';
import { MobileBottomTabs } from './MobileNav';
import { CardOrderingModal } from './CardOrderingModal';
import { APP_NAME } from '../config';
import { useToast } from './Toast';
import api from '../api';

export function CardsPage({ user, logout }) {
  const navigate = useNavigate();
  const toast = useToast();
  const [cards, setCards] = useState([]);
  const [cardRequests, setCardRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showOrderModal, setShowOrderModal] = useState(false);
  const [kycStatus, setKycStatus] = useState(null);
  const [showCardDetails, setShowCardDetails] = useState(null);

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
    <div className="min-h-screen bg-white">
      <header className="bg-white border-b border-gray-200 px-4 sm:px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <button onClick={() => navigate('/dashboard')} className="text-gray-500 hover:text-gray-700">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
          </button>
          <span className="logo-text" data-testid="logo">{APP_NAME}</span>
        </div>
        <div className="flex items-center gap-4">
          <NotificationBell userId={user?.id} />
        </div>
      </header>

      <main className="main-content pb-20 sm:pb-6">
        <div className="max-w-4xl mx-auto">
          {/* Page Header */}
          <div className="mb-8">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div>
                <h1 className="text-2xl font-semibold text-gray-900">My Cards</h1>
                <p className="text-sm text-gray-500 mt-1">Manage your physical and virtual cards</p>
              </div>
              {canOrderCard && (
                <button 
                  onClick={() => setShowOrderModal(true)}
                  className="btn-primary inline-flex items-center gap-2 self-start sm:self-auto"
                  data-testid="order-card-button"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                  </svg>
                  Order New Card
                </button>
              )}
            </div>
          </div>

          {loading ? (
            <div className="text-center py-12 text-gray-500">Loading cards...</div>
          ) : cards.length === 0 && pendingRequests.length === 0 ? (
            <div className="text-center py-16">
              <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-gray-100 flex items-center justify-center">
                <svg className="w-10 h-10 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">No cards yet</h3>
              <p className="text-gray-500 mb-6">Order your first card to start making payments</p>
              {canOrderCard && (
                <button onClick={() => setShowOrderModal(true)} className="btn-primary">
                  Order Your First Card
                </button>
              )}
            </div>
          ) : (
            <div className="space-y-8">
              {/* Active Cards */}
              {cards.length > 0 && (
                <div>
                  <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">Active Cards</h2>
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
                              {card.card_type === 'VIRTUAL' ? 'Virtual Card' : 'Physical Card'}
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
                              <p className="text-white/40 text-[10px] uppercase tracking-widest mb-1">Card Holder</p>
                              <p className="text-white text-sm font-medium uppercase tracking-wider">
                                {card.cardholder_name || `${user?.first_name || ''} ${user?.last_name || ''}`.trim() || 'CARD HOLDER'}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-white/40 text-[10px] uppercase tracking-widest mb-1">Valid Thru</p>
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
                          <div className="bg-gray-50 rounded-xl p-5 border border-gray-200 animate-fadeIn">
                            <h4 className="text-sm font-medium text-gray-900 mb-4">Card Details</h4>
                            <div className="grid grid-cols-2 gap-4">
                              <div>
                                <p className="text-xs text-gray-500 mb-1">Card Number</p>
                                <p className="font-mono text-sm text-gray-900 tracking-wide">
                                  {(card.pan || '').match(/.{1,4}/g)?.join(' ') || 'N/A'}
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500 mb-1">CVV/CVC</p>
                                <p className="font-mono text-sm text-gray-900">{card.cvv || '•••'}</p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500 mb-1">Expiry Date</p>
                                <p className="font-mono text-sm text-gray-900">
                                  {String(card.exp_month).padStart(2, '0')}/{card.exp_year}
                                </p>
                              </div>
                              <div>
                                <p className="text-xs text-gray-500 mb-1">Card Type</p>
                                <p className="text-sm text-gray-900 capitalize">{card.card_type?.toLowerCase()}</p>
                              </div>
                            </div>
                            <div className="mt-4 pt-4 border-t border-gray-200">
                              <p className="text-xs text-gray-400">
                                Card ID: <span className="font-mono">{card.id}</span>
                              </p>
                            </div>
                          </div>
                        )}

                        {/* Click Hint */}
                        <p className="text-center text-xs text-gray-400">
                          {showCardDetails === card.id ? 'Click card to hide details' : 'Click card to reveal full details'}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Pending Card Requests */}
              {pendingRequests.length > 0 && (
                <div>
                  <h2 className="text-sm font-medium text-gray-500 uppercase tracking-wider mb-4">Pending Requests</h2>
                  <div className="space-y-3">
                    {pendingRequests.map((request) => (
                      <div key={request.id} className="bg-yellow-50 border border-yellow-200 rounded-xl p-4 flex items-center justify-between">
                        <div className="flex items-center gap-4">
                          <div className="w-12 h-12 rounded-full bg-yellow-100 flex items-center justify-center">
                            <svg className="w-6 h-6 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          </div>
                          <div>
                            <p className="font-medium text-gray-900">
                              {request.card_type === 'VIRTUAL' ? 'Virtual Card' : 'Physical Card'} Request
                            </p>
                            <p className="text-sm text-gray-500">Waiting for approval</p>
                          </div>
                        </div>
                        <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm font-medium">
                          Pending
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
