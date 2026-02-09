// Admin Notification Bell Component
import React, { useState, useEffect, useRef, useCallback } from 'react';
import api from '../api';

export function AdminNotificationBell({ onNavigate }) {
  const [isOpen, setIsOpen] = useState(false);
  const [counts, setCounts] = useState({
    kyc: 0,
    cards: 0,
    transfers: 0,
    tickets: 0,
    total: 0
  });
  const [loading, setLoading] = useState(true);
  const [isRead, setIsRead] = useState(false);
  const [clearedAt, setClearedAt] = useState(null); // Store the cleared timestamp from backend
  const dropdownRef = useRef(null);

  const fetchCounts = useCallback(async () => {
    try {
      // Use the new smart endpoint that counts only items created after last clear
      const response = await api.get('/admin/notifications/counts-since-clear');
      
      if (response.data) {
        const { kyc, cards, transfers, tickets, total, cleared_at } = response.data;
        
        setCounts({
          kyc,
          cards,
          transfers,
          tickets,
          total
        });
        
        // Update cleared_at from server if present
        if (cleared_at) {
          setClearedAt(new Date(cleared_at));
        }
      }
    } catch (err) {
      console.error('Failed to fetch notification counts:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch counts on mount and every 30 seconds
  // The counts endpoint also returns cleared_at, so we get both in one call
  useEffect(() => {
    fetchCounts();
    const interval = setInterval(fetchCounts, 30000);
    return () => clearInterval(interval);
  }, [fetchCounts]);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);


  const handleItemClick = (section) => {
    setIsOpen(false);
    if (onNavigate) {
      onNavigate(section);
    }
  };

  const handleMarkAllAsRead = () => {
    setIsRead(true);
  };

  const handleClearAll = async () => {
    try {
      const response = await api.post('/admin/notifications/clear');
      if (response.data.success) {
        // Store the cleared timestamp from the backend
        setClearedAt(new Date(response.data.cleared_at));
        setIsOpen(false);
      }
    } catch (err) {
      console.error('Failed to clear notifications:', err);
      // Fallback to local state if API fails
      setClearedAt(new Date());
      setIsOpen(false);
    }
  };

  // Badge calculation - backend already handles smart counting
  // Shows only items created after last clear
  const badgeCount = counts.total;
  const showBadge = badgeCount > 0 && !isRead;

  const notificationItems = [
    {
      id: 'kyc',
      label: 'KYC Requests',
      count: counts.kyc,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      color: 'text-blue-600 bg-blue-50'
    },
    {
      id: 'card_requests',
      label: 'Card Requests',
      count: counts.cards,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" />
        </svg>
      ),
      color: 'text-purple-600 bg-purple-50'
    },
    {
      id: 'ledger',
      label: 'Pending Transfers',
      count: counts.transfers,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
        </svg>
      ),
      color: 'text-green-600 bg-green-50'
    },
    {
      id: 'support',
      label: 'Open Tickets',
      count: counts.tickets,
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
        </svg>
      ),
      color: 'text-orange-600 bg-orange-50'
    }
  ];

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500"
        data-testid="admin-notification-bell"
        aria-label="Notifications"
      >
        <svg className="w-6 h-6 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
        </svg>
        
        {/* Notification Badge */}
        {showBadge && (
          <span className="absolute -top-1 -right-1 flex items-center justify-center min-w-[20px] h-5 px-1.5 text-xs font-bold text-white bg-red-500 rounded-full animate-pulse">
            {badgeCount > 99 ? '99+' : badgeCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 bg-white rounded-xl shadow-2xl border border-gray-200 z-50 overflow-hidden">
          {/* Header */}
          <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Notifications</h3>
                <p className="text-xs text-gray-500 mt-0.5">
                  {isCleared ? 'All notifications cleared' : (counts.total > 0 ? `${counts.total} items need attention` : 'All caught up!')}
                </p>
              </div>
              {counts.total > 0 && !isCleared && (
                <div className="flex items-center space-x-1">
                  {!isRead && (
                    <button
                      onClick={handleMarkAllAsRead}
                      className="p-1.5 text-gray-500 hover:text-blue-600 hover:bg-blue-50 rounded-lg transition-colors"
                      title="Mark all as read"
                      data-testid="mark-all-read-btn"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </button>
                  )}
                  <button
                    onClick={handleClearAll}
                    className="p-1.5 text-gray-500 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Clear all notifications"
                    data-testid="clear-all-btn"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              )}
            </div>
          </div>

          {/* Notification Items */}
          <div className="max-h-80 overflow-y-auto">
            {loading ? (
              <div className="p-4 text-center text-gray-500 text-sm">Loading...</div>
            ) : (
              <div className="py-2">
                {notificationItems.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleItemClick(item.id)}
                    className={`w-full px-4 py-3 flex items-center space-x-3 hover:bg-gray-50 transition-colors text-left ${isRead ? 'opacity-60' : ''}`}
                    data-testid={`notification-item-${item.id}`}
                  >
                    <div className={`p-2 rounded-lg ${item.color}`}>
                      {item.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-gray-900">{item.label}</p>
                      <p className="text-xs text-gray-500">
                        {isCleared ? 'Cleared' : (item.count > 0 ? `${item.count} pending` : 'No pending items')}
                      </p>
                    </div>
                    {item.count > 0 && !isCleared && (
                      <span className={`flex items-center justify-center min-w-[24px] h-6 px-2 text-xs font-bold text-white rounded-full ${isRead ? 'bg-gray-400' : 'bg-red-500'}`}>
                        {item.count}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-3 bg-gray-50 border-t border-gray-200">
            <div className="flex items-center justify-between">
              <p className="text-xs text-gray-500">
                Auto-refreshes every 30 seconds
              </p>
              {(isRead || isCleared) && (
                <span className="text-xs text-green-600 font-medium">
                  {isCleared ? '✓ Cleared' : '✓ Read'}
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
