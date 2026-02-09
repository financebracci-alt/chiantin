/**
 * Balance Visibility Hook
 * 
 * Manages the visibility state of account balances across the application.
 * State is stored in sessionStorage for security (resets on login/browser close).
 * Default state: HIDDEN for privacy and security.
 */

import { useState, useEffect } from 'react';

const STORAGE_KEY = 'balance_visibility_state';

export const useBalanceVisibility = () => {
  // Default to HIDDEN (false = hidden, true = visible)
  // Check sessionStorage on mount
  const [isBalanceVisible, setIsBalanceVisible] = useState(() => {
    try {
      const stored = sessionStorage.getItem(STORAGE_KEY);
      // Default to false (hidden) if nothing stored
      return stored === null ? false : JSON.parse(stored);
    } catch {
      return false; // Default to hidden on error
    }
  });

  // Persist state changes to sessionStorage
  useEffect(() => {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(isBalanceVisible));
    } catch (error) {
      console.error('Failed to save balance visibility state:', error);
    }
  }, [isBalanceVisible]);

  // Toggle function
  const toggleBalanceVisibility = () => {
    setIsBalanceVisible(prev => !prev);
  };

  return {
    isBalanceVisible,
    toggleBalanceVisibility
  };
};

/**
 * Format balance for display
 * If hidden: shows "€ •••.••"
 * If visible: shows actual amount formatted
 */
export const formatBalance = (cents, isVisible, currency = '€') => {
  if (!isVisible) {
    return `${currency} •••.••`;
  }
  
  // Convert cents to euros and format
  const amount = (cents / 100).toFixed(2);
  return `${currency}${amount}`;
};

/**
 * Format amount only (no currency symbol)
 * Used in contexts where currency is displayed separately
 */
export const formatAmount = (cents, isVisible) => {
  if (!isVisible) {
    return '•••.••';
  }
  
  return (cents / 100).toFixed(2);
};
