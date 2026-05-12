import React from 'react';
import { Sun, Moon, Monitor } from 'lucide-react';
import { useUiStore, Theme } from '../../app/stores/uiStore';

/**
 * ThemeToggle - Modern theme switching component
 * 
 * Features:
 * - Cycle through Light → Dark → System modes
 * - Keyboard accessible
 * - Visual icons for each theme
 * - Smooth transitions
 * - Mobile-friendly touch targets
 */

interface ThemeToggleProps {
  /** Show labels next to icons */
  showLabels?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Layout variant */
  variant?: 'button' | 'dropdown';
  /** Custom className */
  className?: string;
}

export const ThemeToggle: React.FC<ThemeToggleProps> = ({ 
  showLabels = false, 
  size = 'md', 
  variant = 'button',
  className = '' 
}) => {
  const { theme, setTheme } = useUiStore();

  const themes: { value: Theme; label: string; icon: React.ReactNode }[] = [
    { value: 'light', label: 'Light', icon: <Sun className="w-4 h-4" /> },
    { value: 'dark', label: 'Dark', icon: <Moon className="w-4 h-4" /> },
    { value: 'system', label: 'System', icon: <Monitor className="w-4 h-4" /> },
  ];

  const currentTheme = themes.find(t => t.value === theme) || themes[0];

  const cycleTheme = () => {
    const currentIndex = themes.findIndex(t => t.value === theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    setTheme(themes[nextIndex].value);
  };

  const sizeClasses = {
    sm: 'h-8 px-2 text-sm',
    md: 'h-10 px-3 text-sm',
    lg: 'h-12 px-4 text-base'
  };

  if (variant === 'dropdown') {
    return (
      <div className="relative inline-block text-left">
        <select
          value={theme}
          onChange={(e) => setTheme(e.target.value as Theme)}
          className={`
            ${sizeClasses[size]}
            bg-white dark:bg-gray-800 
            border border-gray-300 dark:border-gray-600 
            text-gray-900 dark:text-gray-100
            rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            cursor-pointer transition-colors
            ${className}
          `}
          aria-label="Select theme"
        >
          {themes.map(({ value, label }) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>
    );
  }

  return (
    <button
      onClick={cycleTheme}
      className={`
        ${sizeClasses[size]}
        inline-flex items-center justify-center gap-2
        bg-white dark:bg-gray-800 
        border border-gray-300 dark:border-gray-600 
        text-gray-700 dark:text-gray-300
        rounded-lg transition-all duration-200
        hover:bg-gray-50 dark:hover:bg-gray-700
        hover:border-gray-400 dark:hover:border-gray-500
        focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
        active:scale-95
        ${className}
      `}
      aria-label={`Current theme: ${currentTheme.label}. Click to cycle to next theme.`}
      title={`Switch theme (currently ${currentTheme.label})`}
    >
      <span className="transition-transform duration-200 group-hover:scale-110">
        {currentTheme.icon}
      </span>
      {showLabels && (
        <span className="font-medium">
          {currentTheme.label}
        </span>
      )}
    </button>
  );
};

/**
 * ThemeToggleGroup - Alternative horizontal toggle group
 */
export const ThemeToggleGroup: React.FC<{ className?: string }> = ({ className = '' }) => {
  const { theme, setTheme } = useUiStore();

  const themes: { value: Theme; label: string; icon: React.ReactNode }[] = [
    { value: 'light', label: 'Light', icon: <Sun className="w-4 h-4" /> },
    { value: 'dark', label: 'Dark', icon: <Moon className="w-4 h-4" /> },
    { value: 'system', label: 'System', icon: <Monitor className="w-4 h-4" /> },
  ];

  return (
    <div 
      className={`
        inline-flex rounded-lg border border-gray-200 dark:border-gray-700 
        bg-white dark:bg-gray-800 p-1 
        ${className}
      `}
      role="group"
      aria-label="Theme selection"
    >
      {themes.map(({ value, label, icon }) => (
        <button
          key={value}
          onClick={() => setTheme(value)}
          className={`
            flex items-center justify-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium
            transition-all duration-200 min-w-[80px]
            ${theme === value
              ? 'bg-blue-500 text-white shadow-sm' 
              : 'text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700'
            }
          `}
          aria-pressed={theme === value}
          title={`Switch to ${label} theme`}
        >
          {icon}
          <span className="hidden sm:inline">{label}</span>
        </button>
      ))}
    </div>
  );
};
