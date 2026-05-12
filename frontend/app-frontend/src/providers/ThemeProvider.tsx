import React, { useEffect } from 'react';
import { useUiStore, useIsDarkMode } from '../app/stores/uiStore';

/**
 * ThemeProvider - Applies theme classes to document root
 * 
 * Features:
 * - Connects Zustand theme state to DOM
 * - Applies 'dark' class to <html> element for Tailwind
 * - Handles system preference detection
 * - SSR-safe implementation
 * - No flash of wrong theme on page load
 */

interface ThemeProviderProps {
  children: React.ReactNode;
}

export const ThemeProvider: React.FC<ThemeProviderProps> = ({ children }) => {
  const { theme } = useUiStore();
  const isDarkMode = useIsDarkMode();

  // Apply theme to document root
  useEffect(() => {
    const html = document.documentElement;
    
    // Remove existing theme classes
    html.classList.remove('light', 'dark');
    
    // Apply current theme class
    if (isDarkMode) {
      html.classList.add('dark');
    } else {
      html.classList.add('light');
    }
    
    // Store in data attribute for CSS targeting
    html.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    
  }, [isDarkMode]);

  // Listen for system preference changes when theme is 'system'
  useEffect(() => {
    if (theme !== 'system') return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
    
    const handleSystemChange = () => {
      // Force re-evaluation of isDarkMode when system preference changes
      const html = document.documentElement;
      html.classList.remove('light', 'dark');
      
      if (mediaQuery.matches) {
        html.classList.add('dark');
        html.setAttribute('data-theme', 'dark');
      } else {
        html.classList.add('light');
        html.setAttribute('data-theme', 'light');
      }
    };

    // Add listener for system preference changes
    mediaQuery.addEventListener('change', handleSystemChange);
    
    // Cleanup
    return () => mediaQuery.removeEventListener('change', handleSystemChange);
  }, [theme]);

  // Initial theme application to prevent flash
  useEffect(() => {
    // This ensures the theme is applied immediately on mount
    const html = document.documentElement;
    
    // Get the initial theme state
    const initialIsDark = useUiStore.getState().theme === 'dark' || 
      (useUiStore.getState().theme === 'system' && 
       window.matchMedia('(prefers-color-scheme: dark)').matches);
    
    if (initialIsDark) {
      html.classList.add('dark');
      html.setAttribute('data-theme', 'dark');
    } else {
      html.classList.add('light');
      html.setAttribute('data-theme', 'light');
    }
  }, []);

  return <>{children}</>;
};
