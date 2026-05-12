import React from 'react';
import { Theme } from '../types';

interface ListComponentProps {
  children: React.ReactNode;
  theme: Theme;
  [key: string]: any;
}

export const UlComponent: React.FC<ListComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => (
  <ul 
    {...props} 
    className={`list-disc pl-5 my-2 space-y-1 ${
      theme === 'user' 
        ? 'text-blue-100 marker:text-blue-300' 
        : 'text-gray-800 dark:text-gray-200 marker:text-gray-500 dark:marker:text-gray-300'
    }`}
  >
    {children}
  </ul>
);

export const OlComponent: React.FC<ListComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => (
  <ol 
    {...props} 
    className={`list-decimal pl-5 my-2 space-y-1 ${
      theme === 'user' 
        ? 'text-blue-100 marker:text-blue-300' 
        : 'text-gray-800 dark:text-gray-200 marker:text-gray-500 dark:marker:text-gray-300'
    }`}
  >
    {children}
  </ol>
);

export const LiComponent: React.FC<ListComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => (
  <li 
    {...props} 
    className=""
  >
    {children}
  </li>
);
