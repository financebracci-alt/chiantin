/**
 * CopyButton - Reusable copy-to-clipboard button component
 * 
 * Provides consistent copy functionality across the admin panel:
 * - Shows "Copied!" feedback for 2 seconds
 * - Prevents multiple clicks during animation
 * - Consistent styling and accessibility
 */
import React, { useState, useCallback } from 'react';

export const CopyButton = ({ 
  value, 
  label = 'Copy', 
  copiedLabel = 'Copied!',
  className = '',
  iconOnly = false,
  size = 'sm', // 'xs', 'sm', 'md'
  onCopy = null
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(async (e) => {
    e.stopPropagation();
    if (copied || !value) return;
    
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      onCopy?.(value);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  }, [copied, value, onCopy]);

  const sizeClasses = {
    xs: 'text-xs px-1.5 py-0.5',
    sm: 'text-xs px-2 py-1',
    md: 'text-sm px-3 py-1.5'
  };

  const iconSizes = {
    xs: 'w-3 h-3',
    sm: 'w-3.5 h-3.5',
    md: 'w-4 h-4'
  };

  const CopyIcon = () => (
    <svg className={iconSizes[size]} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
    </svg>
  );

  const CheckIcon = () => (
    <svg className={iconSizes[size]} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
    </svg>
  );

  if (iconOnly) {
    return (
      <button
        onClick={handleCopy}
        disabled={!value || copied}
        className={`inline-flex items-center justify-center p-1 rounded transition-colors ${
          copied 
            ? 'text-green-600 bg-green-50' 
            : 'text-gray-400 hover:text-gray-600 hover:bg-gray-100'
        } disabled:opacity-50 ${className}`}
        title={copied ? copiedLabel : `${label}: ${value}`}
        data-testid="copy-btn"
      >
        {copied ? <CheckIcon /> : <CopyIcon />}
      </button>
    );
  }

  return (
    <button
      onClick={handleCopy}
      disabled={!value || copied}
      className={`inline-flex items-center gap-1 rounded transition-colors ${sizeClasses[size]} ${
        copied 
          ? 'bg-green-100 text-green-700' 
          : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
      } disabled:opacity-50 ${className}`}
      title={copied ? copiedLabel : `${label}: ${value}`}
      data-testid="copy-btn"
    >
      {copied ? <CheckIcon /> : <CopyIcon />}
      <span>{copied ? copiedLabel : label}</span>
    </button>
  );
};

/**
 * ActionButton - Standardized admin action button with loading state
 * 
 * Features:
 * - Loading spinner during action
 * - Double-click prevention
 * - Consistent styling
 * - Disabled state handling
 */
export const ActionButton = ({
  onClick,
  loading = false,
  disabled = false,
  variant = 'default', // 'default', 'primary', 'danger', 'success'
  size = 'sm', // 'xs', 'sm', 'md'
  children,
  className = '',
  title = '',
  testId = ''
}) => {
  const [isProcessing, setIsProcessing] = useState(false);

  const handleClick = async (e) => {
    e.stopPropagation();
    if (isProcessing || disabled || loading) return;
    
    setIsProcessing(true);
    try {
      await onClick?.(e);
    } finally {
      setIsProcessing(false);
    }
  };

  const isDisabled = disabled || loading || isProcessing;
  const showSpinner = loading || isProcessing;

  const sizeClasses = {
    xs: 'text-xs px-2 py-0.5',
    sm: 'text-xs px-2.5 py-1',
    md: 'text-sm px-3 py-1.5'
  };

  const variantClasses = {
    default: 'btn-text',
    primary: 'bg-red-600 text-white rounded hover:bg-red-700',
    danger: 'bg-red-100 text-red-700 rounded hover:bg-red-200',
    success: 'bg-green-100 text-green-700 rounded hover:bg-green-200',
    secondary: 'bg-gray-100 text-gray-700 rounded hover:bg-gray-200'
  };

  return (
    <button
      onClick={handleClick}
      disabled={isDisabled}
      className={`inline-flex items-center gap-1.5 transition-colors ${sizeClasses[size]} ${variantClasses[variant]} disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
      title={title}
      data-testid={testId}
    >
      {showSpinner && (
        <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
      {children}
    </button>
  );
};

/**
 * EmptyState - Standardized empty state component
 */
export const EmptyState = ({
  icon = null,
  title = 'No results found',
  description = '',
  action = null,
  className = ''
}) => {
  const DefaultIcon = () => (
    <svg className="w-12 h-12 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
    </svg>
  );

  return (
    <div className={`flex flex-col items-center justify-center py-12 px-4 ${className}`}>
      {icon || <DefaultIcon />}
      <h3 className="mt-4 text-sm font-medium text-gray-900">{title}</h3>
      {description && <p className="mt-1 text-sm text-gray-500 text-center max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
};

/**
 * FilterChip - Show active filter state
 */
export const FilterChip = ({
  label,
  value,
  onClear,
  className = ''
}) => {
  if (!value) return null;
  
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 text-xs rounded-full ${className}`}>
      <span className="font-medium">{label}:</span>
      <span>{value}</span>
      {onClear && (
        <button
          onClick={onClear}
          className="ml-0.5 hover:bg-blue-100 rounded-full p-0.5"
          title="Clear filter"
        >
          <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </span>
  );
};

/**
 * ClearFiltersButton - Clear all filters button
 */
export const ClearFiltersButton = ({
  onClick,
  hasActiveFilters = false,
  className = ''
}) => {
  if (!hasActiveFilters) return null;
  
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 px-2 py-1 text-xs text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition-colors ${className}`}
      title="Clear all filters"
    >
      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
      </svg>
      Clear filters
    </button>
  );
};

export default {
  CopyButton,
  ActionButton,
  EmptyState,
  FilterChip,
  ClearFiltersButton
};
