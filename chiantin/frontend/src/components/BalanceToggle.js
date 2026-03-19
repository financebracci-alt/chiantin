/**
 * BalanceToggle Component
 * 
 * Professional banking-style toggle button for showing/hiding balance.
 * Uses Eye/EyeOff icons following industry standards (N26, Revolut, Chase).
 */

import React from 'react';
import { Eye, EyeOff } from 'lucide-react';

export const BalanceToggle = ({ isVisible, onToggle, isDark = false, size = 'default', className = '' }) => {
  const sizeClasses = {
    small: 'w-8 h-8',
    default: 'w-10 h-10',
    large: 'w-12 h-12'
  };

  const iconSizes = {
    small: 16,
    default: 20,
    large: 24
  };

  return (
    <button
      type="button"
      onClick={onToggle}
      className={`
        ${sizeClasses[size]}
        inline-flex items-center justify-center
        rounded-full
        transition-all duration-200
        ${isDark 
          ? 'bg-gray-700 hover:bg-gray-600 text-gray-300 hover:text-white' 
          : 'bg-gray-100 hover:bg-gray-200 text-gray-600 hover:text-gray-900'}
        focus:outline-none focus:ring-2 focus:ring-offset-2
        ${isDark ? 'focus:ring-gray-500' : 'focus:ring-gray-400'}
        ${className}
      `}
      aria-label={isVisible ? 'Hide balance' : 'Show balance'}
      data-testid="balance-visibility-toggle"
      title={isVisible ? 'Hide balance' : 'Show balance'}
    >
      {isVisible ? (
        <Eye size={iconSizes[size]} />
      ) : (
        <EyeOff size={iconSizes[size]} />
      )}
    </button>
  );
};

export default BalanceToggle;
