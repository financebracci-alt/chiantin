/**
 * EU Currency Formatting Utility
 * 
 * Format: €24.650,00 (German/Italian/Spanish style)
 * - Dot (.) = thousands separator
 * - Comma (,) = decimal separator
 * 
 * This is the standard format used in EU retail banks.
 */

/**
 * Format cents to EU currency format
 * @param {number} cents - Amount in cents (e.g., 2465000 for €24,650.00)
 * @returns {string} Formatted string (e.g., "€24.650,00")
 */
export const formatCurrency = (cents) => {
  if (cents === null || cents === undefined || isNaN(cents)) {
    return '€0,00';
  }
  
  const euros = cents / 100;
  return formatEuroAmount(euros);
};

/**
 * Format euro amount to EU currency format
 * @param {number} euros - Amount in euros (e.g., 24650.00)
 * @returns {string} Formatted string (e.g., "€24.650,00")
 */
export const formatEuroAmount = (euros) => {
  if (euros === null || euros === undefined || isNaN(euros)) {
    return '€0,00';
  }
  
  // Use de-DE locale for EU formatting (dot for thousands, comma for decimals)
  const formatted = euros.toLocaleString('de-DE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
  
  return `€${formatted}`;
};

/**
 * Format number for display without euro sign (for use in charts, etc.)
 * @param {number} value - Amount in euros
 * @returns {string} Formatted string (e.g., "24.650,00")
 */
export const formatNumber = (value) => {
  if (value === null || value === undefined || isNaN(value)) {
    return '0,00';
  }
  
  return value.toLocaleString('de-DE', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
};

/**
 * Format cents amount for display (used in transaction lists)
 * Returns formatted number without euro sign
 * @param {number} cents - Amount in cents
 * @returns {string} Formatted string (e.g., "24.650,00")
 */
export const formatCentsToNumber = (cents) => {
  if (cents === null || cents === undefined || isNaN(cents)) {
    return '0,00';
  }
  
  const euros = cents / 100;
  return formatNumber(euros);
};

export default {
  formatCurrency,
  formatEuroAmount,
  formatNumber,
  formatCentsToNumber
};
