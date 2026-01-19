// Notifications Component
import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api';
import { useLanguage } from '../contexts/AppContext';

export function NotificationBell() {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [showDropdown, setShowDropdown] = useState(false);
  const [loading, setLoading] = useState(false);
  const { t } = useLanguage();

  useEffect(() => {
    fetchNotifications();
    // Poll for new notifications every 30 seconds
    const interval = setInterval(fetchNotifications, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchNotifications = async () => {
    try {
      const response = await api.get('/notifications');
      setNotifications(response.data);
      setUnreadCount(response.data.filter(n => !n.read).length);
    } catch (err) {
      console.error('Failed to fetch notifications:', err);
    }
  };

  const markAsRead = async (id) => {
    try {
      await api.post(`/notifications/${id}/read`);
      fetchNotifications();
    } catch (err) {
      console.error('Failed to mark as read:', err);
    }
  };

  const markAllAsRead = async () => {
    try {
      await api.post('/notifications/mark-all-read');
      fetchNotifications();
    } catch (err) {
      console.error('Failed to mark all as read:', err);
    }
  };

  const handleNotificationClick = async (notif) => {
    // Mark as read first
    if (!notif.read) {
      await markAsRead(notif.id);
    }
    
    // Close dropdown
    setShowDropdown(false);
    
    // Navigate based on entity type or notification type
    const entityType = notif.entity_type?.toLowerCase() || '';
    const notifType = notif.notification_type?.toLowerCase() || '';
    const title = notif.title?.toLowerCase() || '';
    
    // Card-related notifications
    if (entityType === 'card' || entityType === 'card_request' || title.includes('card')) {
      navigate('/cards');
      return;
    }
    
    // Transaction-related notifications
    if (entityType === 'transaction' || entityType === 'transfer' || notifType === 'transaction') {
      navigate('/dashboard');
      return;
    }
    
    // KYC-related notifications
    if (entityType === 'kyc' || notifType === 'kyc_update' || title.includes('kyc') || title.includes('verification')) {
      navigate('/kyc');
      return;
    }
    
    // Support ticket notifications
    if (entityType === 'ticket' || notifType === 'support' || title.includes('support') || title.includes('ticket')) {
      navigate('/support');
      return;
    }
    
    // Security/Tax Hold/Restriction notifications - go to support page
    if (notifType === 'security' || title.includes('restriction') || title.includes('restricted') || title.includes('tax') || title.includes('blocked')) {
      navigate('/support');
      return;
    }
    
    // Account-related notifications
    if (entityType === 'account' || notifType === 'account') {
      navigate('/dashboard');
      return;
    }
    
    // Default to dashboard
    navigate('/dashboard');
  };

  const getTypeIcon = (type) => {
    const icons = {
      KYC_UPDATE: '📋',
      TRANSACTION: '💳',
      SECURITY: '🔒',
      ACCOUNT: '🏦',
      SUPPORT: '💬'
    };
    return icons[type] || '🔔';
  };

  const formatTime = (dateStr) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;
    const diffDays = Math.floor(diffHours / 24);
    return `${diffDays}d ago`;
  };

  // Helper to determine if notification is clickable
  const getClickHint = (notif) => {
    const entityType = notif.entity_type?.toLowerCase() || '';
    const notifType = notif.notification_type?.toLowerCase() || '';
    const title = notif.title?.toLowerCase() || '';
    
    if (entityType === 'card' || entityType === 'card_request' || title.includes('card')) {
      return t('viewCards') || 'View your cards →';
    }
    if (entityType === 'transaction' || entityType === 'transfer') {
      return t('viewTransactions') || 'View transactions →';
    }
    if (entityType === 'kyc' || title.includes('kyc') || title.includes('verification')) {
      return t('checkKycStatus') || 'Check KYC status →';
    }
    if (entityType === 'ticket' || title.includes('support')) {
      return t('viewSupportTickets') || 'View support tickets →';
    }
    // Security/restriction notifications
    if (notifType === 'security' || title.includes('restriction') || title.includes('restricted') || title.includes('tax') || title.includes('blocked')) {
      return t('contactSupport') || 'Contact support →';
    }
    return t('viewDetails') || 'View details →';
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowDropdown(!showDropdown)}
        className="relative p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-lg transition"
        data-testid="notification-bell"
      >
        <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center font-medium">
            {unreadCount > 9 ? '9+' : unreadCount}
          </span>
        )}
      </button>

      {showDropdown && (
        <>
          <div
            className="fixed inset-0 z-10"
            onClick={() => setShowDropdown(false)}
          />
          {/* Desktop: absolute right-0, Mobile: fixed centered */}
          <div className="hidden sm:block absolute right-0 mt-2 w-96 bg-white rounded-lg shadow-blue border border-blue-100 z-20 overflow-hidden">
            <div className="p-4 border-b bg-blue-50/50 flex justify-between items-center">
              <h3 className="font-semibold">{t('notifications')}</h3>
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="text-sm text-blue-600 hover:text-blue-700"
                  data-testid="mark-all-read"
                >
                  {t('markAllAsRead')}
                </button>
              )}
            </div>
            <div className="max-h-96 overflow-y-auto">
              {notifications.length === 0 ? (
                <div className="p-8 text-center text-gray-600">
                  <p>{t('noNotifications')}</p>
                </div>
              ) : (
                notifications.slice(0, 10).map((notif) => (
                  <div
                    key={notif.id}
                    onClick={() => handleNotificationClick(notif)}
                    className={`p-4 border-b hover:bg-blue-50 cursor-pointer transition-colors ${
                      !notif.read ? 'bg-blue-50/30' : ''
                    }`}
                    data-testid={`notification-${notif.id}`}
                  >
                    <div className="flex items-start space-x-3">
                      <span className="text-2xl">{getTypeIcon(notif.notification_type)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className={`text-sm font-medium ${!notif.read ? 'text-blue-900' : 'text-gray-900'}`}>
                            {notif.title}
                          </p>
                          {!notif.read && (
                            <span className="ml-2 h-2 w-2 bg-blue-600 rounded-full flex-shrink-0"></span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mt-1">{notif.message}</p>
                        <div className="flex items-center justify-between mt-2">
                          <p className="text-xs text-gray-500">{formatTime(notif.created_at)}</p>
                          <p className="text-xs text-red-600 font-medium">{getClickHint(notif)}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
          
          {/* Mobile: Full-width centered dropdown */}
          <div className="sm:hidden fixed left-4 right-4 top-16 bg-white rounded-lg shadow-xl border border-gray-200 z-20 overflow-hidden max-h-[70vh]">
            <div className="p-4 border-b bg-gray-50 flex justify-between items-center sticky top-0">
              <h3 className="font-semibold text-gray-900">{t('notifications')}</h3>
              {unreadCount > 0 && (
                <button
                  onClick={markAllAsRead}
                  className="text-sm text-red-600 hover:text-red-700 font-medium"
                >
                  {t('markAllRead')}
                </button>
              )}
            </div>
            <div className="overflow-y-auto max-h-[calc(70vh-56px)]">
              {notifications.length === 0 ? (
                <div className="p-8 text-center text-gray-600">
                  <p>{t('noNotifications')}</p>
                </div>
              ) : (
                notifications.slice(0, 10).map((notif) => (
                  <div
                    key={`mobile-${notif.id}`}
                    onClick={() => handleNotificationClick(notif)}
                    className={`p-4 border-b hover:bg-gray-50 cursor-pointer transition-colors ${
                      !notif.read ? 'bg-red-50/30' : ''
                    }`}
                  >
                    <div className="flex items-start space-x-3">
                      <span className="text-xl">{getTypeIcon(notif.notification_type)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <p className={`text-sm font-medium ${!notif.read ? 'text-gray-900' : 'text-gray-700'}`}>
                            {notif.title}
                          </p>
                          {!notif.read && (
                            <span className="ml-2 h-2 w-2 bg-red-500 rounded-full flex-shrink-0"></span>
                          )}
                        </div>
                        <p className="text-sm text-gray-600 mt-1 line-clamp-2">{notif.message}</p>
                        <div className="flex items-center justify-between mt-2">
                          <p className="text-xs text-gray-500">{formatTime(notif.created_at)}</p>
                          <p className="text-xs text-red-600 font-medium">{getClickHint(notif)}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
