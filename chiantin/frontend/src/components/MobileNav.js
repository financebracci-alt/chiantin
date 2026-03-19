// Mobile Bottom Navigation
import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export function MobileBottomTabs() {
  const navigate = useNavigate();
  const location = useLocation();

  const tabs = [
    { path: '/dashboard', label: 'Home', icon: 'home' },
    { path: '/transactions', label: 'Accounts', icon: 'wallet' },
    { path: '/support', label: 'Activity', icon: 'activity' },
    { path: '/profile', label: 'Profile', icon: 'user' }
  ];

  const getIcon = (name, isActive) => {
    const color = isActive ? '#D32F2F' : '#9E9E9E';
    const icons = {
      home: <svg className="w-6 h-6" fill="none" stroke={color} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>,
      wallet: <svg className="w-6 h-6" fill="none" stroke={color} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 10h18M7 15h1m4 0h1m-7 4h12a3 3 0 003-3V8a3 3 0 00-3-3H6a3 3 0 00-3 3v8a3 3 0 003 3z" /></svg>,
      activity: <svg className="w-6 h-6" fill="none" stroke={color} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>,
      user: <svg className="w-6 h-6" fill="none" stroke={color} viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" /></svg>
    };
    return icons[name];
  };

  return (
    <div className="bottom-tabs md:hidden">
      {tabs.map(tab => {
        const isActive = location.pathname === tab.path;
        return (
          <button
            key={tab.path}
            onClick={() => navigate(tab.path)}
            className={`bottom-tab ${isActive ? 'bottom-tab-active' : ''}`}
            data-testid={`mobile-tab-${tab.label.toLowerCase()}`}
          >
            {getIcon(tab.icon, isActive)}
            <span className="mt-1">{tab.label}</span>
          </button>
        );
      })}
    </div>
  );
}
