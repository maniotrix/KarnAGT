import { Theme, ThemeStyles } from '../types';

export const getThemeStyles = (theme: Theme): ThemeStyles => {
  switch (theme) {
    case 'user':
      return {
        codeBlock: 'bg-gray-50 dark:bg-gray-800 rounded-md p-2 overflow-x-auto border border-gray-200 dark:border-gray-700 max-w-full',
        inlineCode: 'bg-blue-900/20 px-1 py-0.5 rounded border border-blue-400/20',
        link: 'text-blue-200 hover:text-blue-100 underline',
        table: {
          wrapper: 'border border-blue-200 dark:border-blue-800 rounded-lg overflow-hidden',
          table: 'bg-white dark:bg-gray-900',
          headerRow: 'bg-blue-50 dark:bg-blue-900/30 border-b border-blue-200 dark:border-blue-700',
          headerCell: 'text-gray-900 dark:text-blue-100',
          bodyRowHover: 'hover:bg-blue-50/60 dark:hover:bg-blue-900/20',
          bodyCell: 'text-gray-900 dark:text-blue-100 border-b border-gray-200 dark:border-blue-800/40'
        }
      };
    case 'assistant':
    default:
      return {
        codeBlock: 'bg-gray-50 dark:bg-gray-800 rounded-md p-2 overflow-x-auto border border-gray-200 dark:border-gray-700 max-w-full',
        inlineCode: 'bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded',
        link: 'text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline',
        table: {
          wrapper: 'border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden',
          table: 'bg-white dark:bg-gray-900',
          headerRow: 'bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700',
          headerCell: 'text-gray-900 dark:text-gray-100',
          bodyRowHover: 'hover:bg-gray-50 dark:hover:bg-gray-800/50',
          bodyCell: 'text-gray-900 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700'
        }
      };
  }
};

export const getTextColor = (theme: Theme): string => {
  switch (theme) {
    case 'user':
      return 'text-blue-100';
    case 'assistant':
    default:
      return 'text-gray-800 dark:text-gray-200';
  }
};

export const getHeadingColor = (theme: Theme, level: number = 1): string => {
  const baseColors = {
    user: ['text-blue-100', 'text-blue-100', 'text-blue-100', 'text-blue-200', 'text-blue-200', 'text-blue-300'],
    assistant: [
      'text-gray-900 dark:text-gray-100',
      'text-gray-900 dark:text-gray-100', 
      'text-gray-900 dark:text-gray-100',
      'text-gray-800 dark:text-gray-200',
      'text-gray-700 dark:text-gray-300',
      'text-gray-600 dark:text-gray-400'
    ]
  };
  
  const colors = theme === 'user' ? baseColors.user : baseColors.assistant;
  return colors[Math.min(level - 1, colors.length - 1)] || colors[colors.length - 1];
};

export const getFocusRingStyles = (theme: Theme): string => {
  return theme === 'user'
    ? 'focus-visible:ring-blue-300'
    : 'focus-visible:ring-blue-500 focus-visible:ring-offset-white dark:focus-visible:ring-offset-gray-900';
};

export const getTableRowStyles = (theme: Theme): string => {
  return theme === 'user'
    ? 'even:bg-blue-50/30 dark:even:bg-blue-950/20'
    : 'even:bg-gray-50/50 dark:even:bg-gray-800/30';
};
