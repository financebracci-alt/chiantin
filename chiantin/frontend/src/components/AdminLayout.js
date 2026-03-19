// Professional Admin Layout with Sidebar
// PERSISTENT NOTIFICATION BADGES - stored in database, survive logout/login
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

/**
 * Database-backed badge manager for admin sidebar notifications.
 * 
 * Key behaviors:
 * - Badges persist across logout/login (stored in database per admin)
 * - Badge = items created AFTER admin last viewed that section
 * - Clicking a section calls API to mark it as "seen", clearing the badge
 * - Polls every 25 seconds for real-time updates
 */
function useBadgeManager(apiUrl, token) {
  const [counts, setCounts] = useState({
    users: 0,
    kyc: 0,
    card_requests: 0,
    transfers: 0,
    tickets: 0
  });
  const [isInitialized, setIsInitialized] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const fetchIntervalRef = useRef(null);
  const isMountedRef = useRef(true);

  // Fetch counts from API (uses database-stored last_seen_at per section)
  const fetchCounts = useCallback(async () => {
    if (!apiUrl || !token) return null;
    
    try {
      const response = await fetch(`${apiUrl}/api/v1/admin/notification-counts`, {
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        return data;
      } else if (response.status === 401) {
        // Token expired - don't retry
        console.warn('[BadgeManager] Token expired');
        return null;
      }
    } catch (error) {
      // Network error - silent fail, will retry on next poll
      console.warn('[BadgeManager] Network error:', error.message);
    }
    return null;
  }, [apiUrl, token]);

  // Mark a section as seen via API (persists to database)
  const markSectionSeen = useCallback(async (sectionId) => {
    if (!apiUrl || !token) return;
    
    // Map sidebar IDs to API section keys
    const sectionKeyMap = {
      'users': 'users',
      'kyc': 'kyc',
      'card_requests': 'card_requests',
      'ledger': 'transfers',  // Frontend uses 'ledger', API uses 'transfers'
      'support': 'tickets'    // Frontend uses 'support', API uses 'tickets'
    };
    
    const sectionKey = sectionKeyMap[sectionId];
    if (!sectionKey) return;
    
    try {
      const response = await fetch(`${apiUrl}/api/v1/admin/notifications/seen`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ section_key: sectionKey })
      });
      
      if (response.ok) {
        // Immediately clear the badge locally for instant UI feedback
        setCounts(prev => ({
          ...prev,
          [sectionKey]: 0
        }));
      }
    } catch (error) {
      console.warn('[BadgeManager] Error marking section seen:', error.message);
    }
  }, [apiUrl, token]);

  // Initialize counts on mount
  const initialize = useCallback(async () => {
    if (!apiUrl || !token) return;
    
    setIsLoading(true);
    const newCounts = await fetchCounts();
    
    if (isMountedRef.current && newCounts) {
      setCounts(newCounts);
      setIsInitialized(true);
    }
    setIsLoading(false);
  }, [apiUrl, token, fetchCounts]);

  // Start polling for real-time updates
  const startPolling = useCallback(() => {
    if (fetchIntervalRef.current) {
      clearInterval(fetchIntervalRef.current);
    }
    
    // Poll every 25 seconds
    fetchIntervalRef.current = setInterval(async () => {
      if (!isMountedRef.current) return;
      
      const newCounts = await fetchCounts();
      if (isMountedRef.current && newCounts) {
        setCounts(newCounts);
      }
    }, 25000);
  }, [fetchCounts]);

  // Get badge count for a section
  const getBadgeCount = useCallback((sectionId) => {
    if (!isInitialized) return 0;
    
    // Map sidebar IDs to count keys
    const countKeyMap = {
      'users': 'users',
      'kyc': 'kyc',
      'card_requests': 'card_requests',
      'ledger': 'transfers',
      'support': 'tickets'
    };
    
    const countKey = countKeyMap[sectionId];
    return countKey ? (counts[countKey] || 0) : 0;
  }, [counts, isInitialized]);

  // Refresh counts immediately (call after modal actions, etc.)
  const refresh = useCallback(async () => {
    const newCounts = await fetchCounts();
    if (isMountedRef.current && newCounts) {
      setCounts(newCounts);
    }
  }, [fetchCounts]);

  // Initialize on mount
  useEffect(() => {
    isMountedRef.current = true;
    
    if (apiUrl && token) {
      initialize();
    }
    
    return () => {
      isMountedRef.current = false;
    };
  }, [apiUrl, token, initialize]);

  // Start polling after initialization
  useEffect(() => {
    if (isInitialized) {
      startPolling();
    }
    
    return () => {
      if (fetchIntervalRef.current) {
        clearInterval(fetchIntervalRef.current);
      }
    };
  }, [isInitialized, startPolling]);

  return {
    getBadgeCount,
    markSectionSeen,
    refresh,
    isInitialized,
    counts
  };
}

// Badge component - red circle with white text
function NotificationBadge({ count }) {
  if (count <= 0) return null;
  
  const displayCount = count > 99 ? '99+' : count;
  
  return (
    <span 
      className="absolute right-2 top-1/2 -translate-y-1/2 min-w-[20px] h-5 px-1.5 flex items-center justify-center bg-red-500 text-white text-xs font-semibold rounded-full shadow-sm"
      data-testid="notification-badge"
    >
      {displayCount}
    </span>
  );
}

export function AdminSidebar({ activeSection, onSectionChange, user, logout }) {
  const navigate = useNavigate();
  const apiUrl = process.env.REACT_APP_BACKEND_URL;
  const token = localStorage.getItem('access_token');
  
  const { getBadgeCount, markSectionSeen, refresh, isInitialized } = useBadgeManager(apiUrl, token);
  
  // Handle section change - change section IMMEDIATELY, mark as seen in background
  const handleSectionChange = useCallback((sectionId) => {
    // Change the active section FIRST (instant response)
    onSectionChange(sectionId);
    // Mark section as seen in background (fire-and-forget, don't block UI)
    markSectionSeen(sectionId).catch(() => {
      // Silently ignore badge update failures - non-critical
    });
  }, [markSectionSeen, onSectionChange]);
  
  // Sections that should show badges
  const badgeSections = ['users', 'kyc', 'card_requests', 'ledger', 'support'];
  
  const menuItems = [
    { id: 'overview', label: 'Overview', icon: 'home' },
    { id: 'users', label: 'Users', icon: 'users' },
    { id: 'kyc', label: 'KYC Queue', icon: 'clipboard' },
    { id: 'accounts', label: 'Accounts', icon: 'credit-card' },
    { id: 'card_requests', label: 'Card Requests', icon: 'credit-card' },
    { id: 'ledger', label: 'Transfers Queue', icon: 'repeat' },
    { id: 'support', label: 'Support Tickets', icon: 'message' },
    { id: 'audit', label: 'Audit Logs', icon: 'file-text' },
    { id: 'settings', label: 'Settings', icon: 'settings' }
  ];

  const getIcon = (iconName) => {
    const icons = {
      home: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>,
      users: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" /></svg>,
      clipboard: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" /></svg>,
      'credit-card': <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>,
      tool: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>,
      repeat: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>,
      message: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" /></svg>,
      'file-text': <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>,
      settings: <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" /><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" /></svg>
    };
    return icons[iconName] || icons.settings;
  };

  return (
    <div className="admin-sidebar">
      {/* Sidebar Header */}
      <div className="p-6 border-b border-gray-200 dark:border-gray-700">
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">
          <span>ecomm</span><span className="text-red-500">bx</span>
        </h1>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">Admin Portal</p>
      </div>

      {/* Navigation */}
      <nav className="py-4">
        {menuItems.map((item) => {
          const badgeCount = badgeSections.includes(item.id) ? getBadgeCount(item.id) : 0;
          
          return (
            <button
              key={item.id}
              onClick={() => handleSectionChange(item.id)}
              className={`sidebar-nav-item w-full relative ${
                activeSection === item.id ? 'sidebar-nav-item-active' : ''
              }`}
              data-testid={`admin-nav-${item.id}`}
            >
              {getIcon(item.icon)}
              <span>{item.label}</span>
              {isInitialized && <NotificationBadge count={badgeCount} />}
            </button>
          );
        })}
      </nav>

      {/* User Info at Bottom */}
      <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        <div className="text-xs text-gray-600 dark:text-gray-300 mb-2">
          <p className="font-medium text-gray-900 dark:text-white">{user?.email}</p>
          <p className="text-gray-500 dark:text-gray-400 mt-1">ECOMMBX</p>
        </div>
        <button
          onClick={logout}
          className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium"
          data-testid="admin-logout"
        >
          Logout
        </button>
      </div>
    </div>
  );
}

export function AdminLayout({ user, logout, children }) {
  return (
    <div className="admin-layout">
      <div className="admin-content">
        {/* Top Header */}
        <div className="header-bar border-b border-gray-200">
          <div className="px-8 h-full flex justify-between items-center">
            <h2 className="text-lg font-semibold text-gray-900">Admin Dashboard</h2>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">{user?.first_name} {user?.last_name}</span>
              <span className="badge badge-info ml-2">ECOMMBX</span>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="p-8">
          {children}
        </div>
      </div>
    </div>
  );
}
