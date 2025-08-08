import React from 'react';
import { Theme } from '../types';
import { getThemeStyles, getFocusRingStyles } from '../utils/themeUtils';

interface LinkComponentProps {
  href?: string;
  children: React.ReactNode;
  theme: Theme;
  [key: string]: any;
}

export const LinkComponent: React.FC<LinkComponentProps> = ({ 
  href, 
  children, 
  theme, 
  ...props 
}) => {
  const styles = getThemeStyles(theme);
  const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'));
  const isProxyUrl = href && /\/api\/v1\/proxy\/(images|files|code-files)\//.test(href);
  const shouldOpenNewTab = isExternal && !isProxyUrl;

  return (
    <a 
      {...props}
      href={href}
      target={shouldOpenNewTab ? '_blank' : undefined}
      rel={shouldOpenNewTab ? 'noopener noreferrer' : undefined}
      className={`${styles.link} underline-offset-2 hover:underline-offset-1 transition-all duration-150 focus-visible:ring-2 focus-visible:ring-offset-1 ${getFocusRingStyles(theme)} break-words`}
    >
      {children}
      {shouldOpenNewTab && (
        <span 
          className={`ml-1 inline-block text-xs ${
            theme === 'user' 
              ? 'text-blue-200' 
              : 'text-gray-500 dark:text-gray-400'
          }`}
          aria-label="Opens in new tab"
        >
          ↗
        </span>
      )}
    </a>
  );
};
