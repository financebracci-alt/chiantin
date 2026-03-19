// Spending Insights Component
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';
import api from '../api';
import { useLanguage, useTheme } from '../contexts/AppContext';
import { formatCurrency, formatNumber, formatEuroAmount } from '../utils/currency';

export function SpendingInsights() {
  const [searchParams] = useSearchParams();
  const [data, setData] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  // Check URL params for period (e.g., from "View full breakdown" link)
  const initialPeriod = searchParams.get('period') || '30';
  const [period, setPeriod] = useState(initialPeriod);
  const { t } = useLanguage();
  const { isDark } = useTheme();

  useEffect(() => {
    fetchInsights();
  }, [period]);

  const fetchInsights = async () => {
    try {
      // Build API URL based on period selection
      let url;
      if (period === 'this_month') {
        // Use period=this_month for exact same calculation as Overview
        url = '/insights/spending?period=this_month';
      } else {
        // Use days parameter for rolling periods
        url = `/insights/spending?days=${period}`;
      }
      
      const response = await api.get(url);
      const responseData = response.data;
      
      if (responseData.categories) {
        // New format from backend
        const chartData = Object.entries(responseData.categories).map(([category, amount]) => ({
          name: category.replace(/_/g, ' '),
          value: amount / 100,
          amount: amount
        }));
        setData(chartData);
        setTotal(responseData.total || 0);
      } else {
        // Legacy format (direct object)
        const chartData = Object.entries(responseData).map(([category, amount]) => ({
          name: category.replace(/_/g, ' '),
          value: amount / 100,
          amount: amount
        }));
        setData(chartData);
        setTotal(chartData.reduce((sum, item) => sum + item.amount, 0));
      }
    } catch (err) {
      console.error(err);
      setData([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  };

  const COLORS = ['#D32F2F', '#F57C00', '#FBC02D', '#388E3C', '#1976D2', '#7B1FA2'];

  return (
    <div className={`rounded-xl p-6 ${isDark ? 'bg-gray-800 border border-gray-700' : 'bg-white shadow-sm border border-gray-200'}`} data-testid="spending-insights-card">
      <div className="flex justify-between items-center mb-4">
        <h3 className={`text-lg font-semibold ${isDark ? 'text-white' : 'text-gray-900'}`}>{t('spendingBreakdown')}</h3>
        <select 
          value={period} 
          onChange={(e) => setPeriod(e.target.value)} 
          className={`px-3 py-2 rounded-lg border text-sm font-medium ${isDark ? 'bg-gray-700 border-gray-600 text-white' : 'bg-white border-gray-300 text-gray-700'}`}
          data-testid="spending-period-select"
        >
          <option value="this_month">{t('thisMonth') || 'This Month'}</option>
          <option value={7}>{t('last7Days')}</option>
          <option value={30}>{t('last30Days')}</option>
          <option value={90}>{t('last90Days')}</option>
        </select>
      </div>

      {loading ? (
        <div className={`h-64 rounded-lg animate-pulse ${isDark ? 'bg-gray-700' : 'bg-gray-100'}`}></div>
      ) : total === 0 ? (
        <div className="text-center py-12" data-testid="spending-empty-state">
          <div className={`text-5xl mb-4 ${isDark ? 'text-gray-600' : 'text-gray-400'}`}>📊</div>
          <p className={`font-medium ${isDark ? 'text-gray-300' : 'text-gray-600'}`}>{t('noSpendingThisPeriod')}</p>
          <p className={`text-sm mt-1 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>{t('spendingDataWillAppear')}</p>
        </div>
      ) : (
        <div>
          <div className="mb-6">
            <p className={`text-sm mb-1 ${isDark ? 'text-gray-400' : 'text-gray-600'}`}>{t('totalSpending')}</p>
            <p className={`text-3xl font-bold ${isDark ? 'text-white' : 'text-gray-900'}`} data-testid="insights-total">{formatCurrency(total)}</p>
          </div>
          
          {data.length > 0 && (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={data}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {data.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value) => formatEuroAmount(value)} 
                    contentStyle={{ 
                      backgroundColor: isDark ? '#1f2937' : '#ffffff',
                      border: `1px solid ${isDark ? '#374151' : '#e5e7eb'}`,
                      borderRadius: '8px',
                      color: isDark ? '#ffffff' : '#111827'
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>

              <div className="mt-6 space-y-2" data-testid="spending-categories-list">
                {data.map((item, idx) => (
                  <div key={idx} className={`flex justify-between items-center text-sm ${isDark ? 'text-gray-300' : 'text-gray-700'}`}>
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[idx % COLORS.length] }}></div>
                      <span>{item.name}</span>
                    </div>
                    <span className="font-semibold">{formatEuroAmount(item.value)}</span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}
