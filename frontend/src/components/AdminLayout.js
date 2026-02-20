// Professional Admin Layout with Sidebar
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

// Session-based notification badge manager
// Baselines are stored in sessionStorage and reset on login/logout
const BADGE_BASELINE_KEY = 'admin_badge_baselines';
const BADGE_SESSION_KEY = 'admin_badge_session_id';

function useBadgeManager(apiUrl, token) {
  const [counts, setCounts] = useState({
    kyc_pending: 0,
    transfers_pending: 0,
    card_requests_pending: 0,
    tickets_unread: 0,
    users_pending: 0
  });
  const [baselines, setBaselines] = useState(null);
  const [isInitialized, setIsInitialized] = useState(false);
  const fetchIntervalRef = useRef(null);

  // Generate a unique session ID on login
  const getSessionId = useCallback(() => {
    let sessionId = sessionStorage.getItem(BADGE_SESSION_KEY);
    if (!sessionId) {
      sessionId = `admin_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem(BADGE_SESSION_KEY, sessionId);
    }
    return sessionId;
  }, []);

  // Load baselines from sessionStorage
  const loadBaselines = useCallback(() => {
    const stored = sessionStorage.getItem(BADGE_BASELINE_KEY);
    if (stored) {
      try {
        return JSON.parse(stored);
      } catch (e) {
        return null;
      }
    }
    return null;
  }, []);

  // Save baselines to sessionStorage
  const saveBaselines = useCallback((newBaselines) => {
    sessionStorage.setItem(BADGE_BASELINE_KEY, JSON.stringify(newBaselines));
    setBaselines(newBaselines);
  }, []);

  // Fetch current counts from API
  const fetchCounts = useCallback(async () => {
    if (!apiUrl || !token) return null;
    try {
      const response = await fetch(`${apiUrl}/api/v1/admin/notification-counts`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        return await response.json();
      }
    } catch (error) {
      console.error('[BadgeManager] Error fetching counts:', error);
    }
    return null;
  }, [apiUrl, token]);

  // Initialize baselines on first load (session start)
  const initializeBaselines = useCallback(async () => {
    const sessionId = getSessionId();
    const storedBaselines = loadBaselines();
    
    // Check if we already have baselines for this session
    if (storedBaselines && storedBaselines._sessionId === sessionId) {
      setBaselines(storedBaselines);
      setIsInitialized(true);
      return;
    }
    
    // New session - fetch current counts and use as baselines
    const currentCounts = await fetchCounts();
    if (currentCounts) {
      const newBaselines = {
        ...currentCounts,
        _sessionId: sessionId,
        _timestamp: Date.now()
      };
      saveBaselines(newBaselines);
      setCounts(currentCounts);
      setIsInitialized(true);
    }
  }, [getSessionId, loadBaselines, saveBaselines, fetchCounts]);

  // Poll for new counts periodically
  const startPolling = useCallback(() => {
    if (fetchIntervalRef.current) {
      clearInterval(fetchIntervalRef.current);
    }
    
    fetchIntervalRef.current = setInterval(async () => {
      const newCounts = await fetchCounts();
      if (newCounts) {
        setCounts(newCounts);
      }
    }, 30000); // Poll every 30 seconds
  }, [fetchCounts]);

  // Mark a section as "seen" - update baseline to current count
  const markSectionSeen = useCallback((sectionKey) => {
    if (!baselines || !counts) return;
    
    const countKey = {
      'kyc': 'kyc_pending',
      'ledger': 'transfers_pending',
      'card_requests': 'card_requests_pending',
      'support': 'tickets_unread',
      'users': 'users_pending'
    }[sectionKey];
    
    if (countKey && counts[countKey] !== undefined) {
      const newBaselines = {
        ...baselines,
        [countKey]: counts[countKey]
      };
      saveBaselines(newBaselines);
    }
  }, [baselines, counts, saveBaselines]);

  // Calculate badge number for a section
  const getBadgeCount = useCallback((sectionKey) => {
    if (!baselines || !isInitialized) return 0;
    
    const countKey = {
      'kyc': 'kyc_pending',
      'ledger': 'transfers_pending',
      'card_requests': 'card_requests_pending',
      'support': 'tickets_unread',
      'users': 'users_pending'
    }[sectionKey];
    
    if (!countKey) return 0;
    
    const current = counts[countKey] || 0;
    const baseline = baselines[countKey] || 0;
    
    return Math.max(0, current - baseline);
  }, [baselines, counts, isInitialized]);

  // Initialize on mount
  useEffect(() => {
    if (apiUrl && token) {
      initializeBaselines();
    }
  }, [apiUrl, token, initializeBaselines]);

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

  // Refresh counts immediately
  const refresh = useCallback(async () => {
    const newCounts = await fetchCounts();
    if (newCounts) {
      setCounts(newCounts);
    }
  }, [fetchCounts]);

  return {
    getBadgeCount,
    markSectionSeen,
    refresh,
    isInitialized
  };
}

// Badge component
function NotificationBadge({ count }) {
  if (count <= 0) return null;
  
  const displayCount = count > 99 ? '99+' : count;
  
  return (
    <span 
      className="absolute right-2 top-1/2 -translate-y-1/2 min-w-[20px] h-5 px-1.5 flex items-center justify-center bg-red-500 text-white text-xs font-semibold rounded-full"
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
  
  const { getBadgeCount, markSectionSeen, isInitialized } = useBadgeManager(apiUrl, token);
  
  // Handle section change - mark as seen and then change section
  const handleSectionChange = useCallback((sectionId) => {
    markSectionSeen(sectionId);
    onSectionChange(sectionId);
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
        <h1 className="text-lg font-semibold text-gray-900 dark:text-white">ecommbx</h1>
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
          onClick={() => {
            // Clear badge baselines on logout
            sessionStorage.removeItem(BADGE_BASELINE_KEY);
            sessionStorage.removeItem(BADGE_SESSION_KEY);
            logout();
          }}
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
