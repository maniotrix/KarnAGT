import React from 'react';
import { Theme } from '../types';
import { getTextColor } from '../utils/themeUtils';

interface TextComponentProps {
  children: React.ReactNode;
  theme: Theme;
  [key: string]: any;
}

export const ParagraphComponent: React.FC<TextComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => (
  <p 
    {...props} 
    className={`text-sm leading-relaxed ${getTextColor(theme)}`}
  >
    {children}
  </p>
);

export const StrongComponent: React.FC<TextComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => (
  <strong 
    {...props} 
    className={`font-semibold ${
      theme === 'user' 
        ? 'text-blue-50' 
        : 'text-gray-900 dark:text-gray-100'
    }`}
  >
    {children}
  </strong>
);

export const EmComponent: React.FC<TextComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => (
  <em 
    {...props} 
    className={`italic ${getTextColor(theme)}`}
  >
    {children}
  </em>
);

export const BlockquoteComponent: React.FC<TextComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => (
  <blockquote 
    {...props} 
    className={`border-l-2 pl-3 py-2 my-3 text-sm italic ${
      theme === 'user' 
        ? 'border-blue-300 bg-blue-800/20 text-blue-100' 
        : 'border-gray-300 dark:border-gray-600 bg-gray-50/50 dark:bg-gray-800/40 text-gray-700 dark:text-gray-300'
    }`}
  >
    {children}
  </blockquote>
);

export const HrComponent: React.FC<{ theme: Theme; [key: string]: any }> = ({ 
  theme, 
  ...props 
}) => (
  <hr 
    {...props} 
    className={`my-4 border-t ${
      theme === 'user' 
        ? 'border-blue-400/40' 
        : 'border-gray-200 dark:border-gray-700'
    }`}
  />
);

export const ImgComponent: React.FC<{ 
  src?: string; 
  alt?: string; 
  theme: Theme; 
  [key: string]: any 
}> = ({ 
  src, 
  alt, 
  theme, 
  ...props 
}) => (
  <img 
    {...props}
    src={src}
    alt={alt}
    className={`max-w-full h-auto rounded-lg my-3 ${
      theme === 'user' 
        ? 'border border-blue-400/30' 
        : 'border border-gray-200 dark:border-gray-700 shadow-sm'
    }`}
  />
);
