// App Context - Language and Theme Management
import React, { createContext, useContext, useState, useEffect } from 'react';
import translations from '../translations';

// Language Context
const LanguageContext = createContext(null);

export function LanguageProvider({ children }) {
  const [language, setLanguage] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('atlas_language');
      return saved || 'en';
    }
    return 'en';
  });

  useEffect(() => {
    localStorage.setItem('atlas_language', language);
    document.documentElement.lang = language;
  }, [language]);

  const t = (key) => {
    // Ensure we always have a valid translation
    const value = translations[language]?.[key] || translations['en']?.[key] || key;
    // Log if we're falling back to the key itself (shouldn't happen)
    if (value === key && process.env.NODE_ENV === 'development') {
      console.warn(`Missing translation for key: ${key}`);
    }
    return value;
  };

  const value = { language, setLanguage, t };

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage() {
  const context = useContext(LanguageContext);
  if (!context) {
    // Return default values if not wrapped in provider
    return {
      language: 'en',
      setLanguage: () => {},
      t: (key) => translations['en']?.[key] || key
    };
  }
  return context;
}

// Theme Context
const ThemeContext = createContext(null);

export function ThemeProvider({ children }) {
  const [theme, setTheme] = useState(() => {
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('atlas_theme');
      if (saved) return saved;
      if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        return 'dark';
      }
    }
    return 'light';
  });

  useEffect(() => {
    localStorage.setItem('atlas_theme', theme);
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

  const value = { theme, setTheme, toggleTheme, isDark };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
}

export function useTheme() {
  const context = useContext(ThemeContext);
  if (!context) {
    // Return default values if not wrapped in provider
    return {
      theme: 'light',
      setTheme: () => {},
      toggleTheme: () => {},
      isDark: false
    };
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
