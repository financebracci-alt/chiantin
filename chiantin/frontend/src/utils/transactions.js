/**
 * Transaction Display Utility
 * 
 * Professional banking-style transaction display:
 * - Credits (money IN): +€X.XXX,XX in GREEN
 * - Debits (money OUT): -€X.XXX,XX in RED
 * - Status badges with professional colors
 */

/**
 * Transaction status configuration for professional banking display
 * 
 * Status types:
 * - POSTED/COMPLETED: Transaction finalized (green badge)
 * - PENDING: Awaiting processing (amber/yellow badge)
 * - SUBMITTED: Sent for processing (amber/yellow badge)  
 * - PROCESSING: Being processed (blue badge)
 * - REJECTED/FAILED: Transaction failed (red badge)
 * - CANCELLED: Transaction cancelled (gray badge)
 * - REVERSED: Transaction reversed (purple badge)
 */
export const TRANSACTION_STATUS = {
  POSTED: {
    label: 'posted',
    bgClass: 'bg-green-50 border-green-200',
    textClass: 'text-green-700',
    darkBgClass: 'dark:bg-green-900/30 dark:border-green-800',
    darkTextClass: 'dark:text-green-400'
  },
  COMPLETED: {
    label: 'completed',
    bgClass: 'bg-green-50 border-green-200',
    textClass: 'text-green-700',
    darkBgClass: 'dark:bg-green-900/30 dark:border-green-800',
    darkTextClass: 'dark:text-green-400'
  },
  PENDING: {
    label: 'pending',
    bgClass: 'bg-amber-50 border-amber-200',
    textClass: 'text-amber-700',
    darkBgClass: 'dark:bg-amber-900/30 dark:border-amber-800',
    darkTextClass: 'dark:text-amber-400'
  },
  SUBMITTED: {
    label: 'submitted',
    bgClass: 'bg-amber-50 border-amber-200',
    textClass: 'text-amber-700',
    darkBgClass: 'dark:bg-amber-900/30 dark:border-amber-800',
    darkTextClass: 'dark:text-amber-400'
  },
  PROCESSING: {
    label: 'processing',
    bgClass: 'bg-blue-50 border-blue-200',
    textClass: 'text-blue-700',
    darkBgClass: 'dark:bg-blue-900/30 dark:border-blue-800',
    darkTextClass: 'dark:text-blue-400'
  },
  REJECTED: {
    label: 'rejected',
    bgClass: 'bg-red-50 border-red-200',
    textClass: 'text-red-700',
    darkBgClass: 'dark:bg-red-900/30 dark:border-red-800',
    darkTextClass: 'dark:text-red-400'
  },
  FAILED: {
    label: 'failed',
    bgClass: 'bg-red-50 border-red-200',
    textClass: 'text-red-700',
    darkBgClass: 'dark:bg-red-900/30 dark:border-red-800',
    darkTextClass: 'dark:text-red-400'
  },
  CANCELLED: {
    label: 'cancelled',
    bgClass: 'bg-gray-100 border-gray-200',
    textClass: 'text-gray-600',
    darkBgClass: 'dark:bg-gray-700 dark:border-gray-600',
    darkTextClass: 'dark:text-gray-400'
  },
  REVERSED: {
    label: 'reversed',
    bgClass: 'bg-purple-50 border-purple-200',
    textClass: 'text-purple-700',
    darkBgClass: 'dark:bg-purple-900/30 dark:border-purple-800',
    darkTextClass: 'dark:text-purple-400'
  }
};

/**
 * Get status badge classes for a transaction status
 * @param {string} status - Transaction status (POSTED, PENDING, etc.)
 * @param {boolean} isDark - Whether dark mode is enabled
 * @returns {string} Tailwind CSS classes for the badge
 */
export const getStatusBadgeClasses = (status, isDark = false) => {
  const statusUpper = status?.toUpperCase() || 'POSTED';
  const config = TRANSACTION_STATUS[statusUpper] || TRANSACTION_STATUS.POSTED;
  
  const baseClasses = 'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border';
  
  if (isDark) {
    return `${baseClasses} ${config.darkBgClass} ${config.darkTextClass} border-transparent`;
  }
  
  return `${baseClasses} ${config.bgClass} ${config.textClass}`;
};

/**
 * Determine if a transaction is a credit (money coming IN)
 * @param {object} transaction - Transaction object
 * @returns {boolean} True if credit, false if debit
 */
export const isTransactionCredit = (transaction) => {
  const creditTypes = ['TOP_UP', 'CREDIT', 'REFUND', 'INTEREST', 'DEPOSIT', 'INCOMING_TRANSFER'];
  return creditTypes.includes(transaction.transaction_type) || 
         transaction.direction === 'CREDIT' ||
         transaction.type === 'CREDIT';
};

/**
 * Get amount display classes based on credit/debit
 * @param {boolean} isCredit - Whether the transaction is a credit
 * @returns {string} Tailwind CSS classes for the amount
 */
export const getAmountClasses = (isCredit) => {
  return isCredit 
    ? 'text-green-600 dark:text-green-400' 
    : 'text-red-600 dark:text-red-400';
};

/**
 * Format transaction amount with +/- prefix and EU currency format
 * @param {number} cents - Amount in cents
 * @param {boolean} isCredit - Whether this is a credit (money IN)
 * @returns {string} Formatted amount string (e.g., "+€5.566,00" or "-€250,00")
 */
export const formatTransactionAmount = (cents, isCredit) => {
  const euros = (cents || 0) / 100;
  const formatted = euros.toLocaleString('de-DE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
  
  const prefix = isCredit ? '+' : '-';
  return `${prefix}€${formatted}`;
};

export default {
  TRANSACTION_STATUS,
  getStatusBadgeClasses,
  isTransactionCredit,
  getAmountClasses,
  formatTransactionAmount
};
