// Statements Component
import React, { useState } from 'react';
import api from '../api';
import { useLanguage, useTheme } from '../contexts/AppContext';

export function StatementDownload({ accountId }) {
  const { t } = useLanguage();
  const { isDark } = useTheme();
  const [downloading, setDownloading] = useState(false);
  const [selectedMonth, setSelectedMonth] = useState('');
  const [selectedYear, setSelectedYear] = useState(new Date().getFullYear());

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 5 }, (_, i) => currentYear - i);
  
  const getMonths = () => [
    { value: 1, label: t('january') },
    { value: 2, label: t('february') },
    { value: 3, label: t('march') },
    { value: 4, label: t('april') },
    { value: 5, label: t('may') },
    { value: 6, label: t('june') },
    { value: 7, label: t('july') },
    { value: 8, label: t('august') },
    { value: 9, label: t('september') },
    { value: 10, label: t('october') },
    { value: 11, label: t('november') },
    { value: 12, label: t('december') }
  ];

  const handleDownload = async () => {
    if (!selectedMonth) {
      alert(t('pleaseSelectMonth'));
      return;
    }

    setDownloading(true);

    try {
      const response = await api.get(
        `/accounts/${accountId}/statement/${selectedYear}/${selectedMonth}`,
        { responseType: 'blob' }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `statement_${selectedYear}_${selectedMonth.toString().padStart(2, '0')}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(err.response?.data?.detail || t('failedToDownloadStatement'));
    } finally {
      setDownloading(false);
    }
  };

  return (
    <div className={`rounded-lg shadow p-6 ${isDark ? 'bg-gray-800' : 'bg-white'}`}>
      <h3 className={`text-lg font-semibold mb-4 ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('downloadStatement')}</h3>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('year')}</label>
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(parseInt(e.target.value))}
            className={`w-full px-3 py-2 border rounded-md ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'border-gray-300'}`}
            data-testid="statement-year"
          >
            {years.map(year => (
              <option key={year} value={year}>{year}</option>
            ))}
          </select>
        </div>
        <div>
          <label className={`block text-sm font-medium mb-2 ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>{t('month')}</label>
          <select
            value={selectedMonth}
            onChange={(e) => setSelectedMonth(e.target.value)}
            className={`w-full px-3 py-2 border rounded-md ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'border-gray-300'}`}
            data-testid="statement-month"
          >
            <option value="">{t('selectMonth')}</option>
            {getMonths().map(month => (
              <option key={month.value} value={month.value}>{month.label}</option>
            ))}
          </select>
        </div>
      </div>
      <button
        onClick={handleDownload}
        disabled={downloading || !selectedMonth}
        className="mt-4 w-full py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
        data-testid="download-statement"
      >
        {downloading ? t('generatingPdf') : t('downloadPdfStatement')}
      </button>
    </div>
  );
}
