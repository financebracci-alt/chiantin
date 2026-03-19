/**
 * Balance Visibility Hook
 * 
 * Manages the visibility state of account balances across the application.
 * State is stored in sessionStorage for security (resets on login/browser close).
 * Default state: HIDDEN for privacy and security.
 */

import { useState, useEffect } from 'react';

const STORAGE_KEY = 'balance_visibility_state';

/**
 * Format number in EU style: dot for thousands, comma for decimals
 * e.g., 24650.00 -> "24.650,00"
 */
const formatEU = (amount) => {
  return amount.toLocaleString('de-DE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
};

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
 * Format balance for display in EU format
 * If hidden: shows "€ •••••"
 * If visible: shows actual amount formatted (e.g., "€24.650,00")
 */
export const formatBalance = (cents, isVisible, currency = '€') => {
  if (!isVisible) {
    return `${currency} •••••`;
  }
  
  // Convert cents to euros and format in EU style
  const amount = cents / 100;
  return `${currency}${formatEU(amount)}`;
};

/**
 * Format amount only (no currency symbol) in EU format
 * Used in contexts where currency is displayed separately
 */
export const formatAmount = (cents, isVisible) => {
  if (!isVisible) {
    return '•••••';
  }
  
  const amount = cents / 100;
  return formatEU(amount);
};
