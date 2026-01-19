// App Context - Language and Theme Management
import React, { createContext, useContext, useState, useEffect } from 'react';
import { translations } from '../translations';

// Language Context
const LanguageContext = createContext();

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    const saved = localStorage.getItem('atlas_language');
    return saved || 'en';
  });

  useEffect(() => {
    localStorage.setItem('atlas_language', language);
    document.documentElement.lang = language;
  }, [language]);

  const t = (key) => {
    return translations[language]?.[key] || translations['en']?.[key] || key;
  };

  return (
    <LanguageContext.Provider value={{ language, setLanguage, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
}

// Theme Context
const ThemeContext = createContext();

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    const saved = localStorage.getItem('atlas_theme');
    if (saved) return saved;
    // Check system preference
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return 'dark';
    }
    return 'light';
  });

  useEffect(() => {
    localStorage.setItem('atlas_theme', theme);
    
    // Apply theme class to document
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [theme]);

  const toggleTheme = () => {
    setTheme(prev => prev === 'light' ? 'dark' : 'light');
  };

  const isDark = theme === 'dark';

  return (
    <ThemeContext.Provider value={{ theme, setTheme, toggleTheme, isDark }}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
}

// Combined App Provider
export function AppProvider({ children }) {
  return (
    <LanguageProvider>
      <ThemeProvider>
        {children}
      </ThemeProvider>
    </LanguageProvider>
  );
}
