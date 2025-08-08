import React from 'react';
import { Theme } from '../types';
import { getHeadingColor } from '../utils/themeUtils';

interface HeadingProps {
  children: React.ReactNode;
  theme: Theme;
  [key: string]: any;
}

export const H1Component: React.FC<HeadingProps> = ({ children, theme, ...props }) => (
  <h1 
    {...props} 
    className={`text-lg font-semibold mt-6 mb-3 first:mt-0 ${getHeadingColor(theme, 1)}`}
  >
    {children}
  </h1>
);

export const H2Component: React.FC<HeadingProps> = ({ children, theme, ...props }) => (
  <h2 
    {...props} 
    className={`text-base font-semibold mt-5 mb-2 ${getHeadingColor(theme, 2)}`}
  >
    {children}
  </h2>
);

export const H3Component: React.FC<HeadingProps> = ({ children, theme, ...props }) => (
  <h3 
    {...props} 
    className={`text-sm font-medium mt-4 mb-1.5 ${getHeadingColor(theme, 3)}`}
  >
    {children}
  </h3>
);

export const H4Component: React.FC<HeadingProps> = ({ children, theme, ...props }) => (
  <h4 
    {...props} 
    className={`text-sm font-medium mt-3 mb-1 ${getHeadingColor(theme, 4)}`}
  >
    {children}
  </h4>
);

export const H5Component: React.FC<HeadingProps> = ({ children, theme, ...props }) => (
  <h5 
    {...props} 
    className={`text-xs font-medium mt-3 mb-1 ${getHeadingColor(theme, 5)}`}
  >
    {children}
  </h5>
);

export const H6Component: React.FC<HeadingProps> = ({ children, theme, ...props }) => (
  <h6 
    {...props} 
    className={`text-xs font-medium mt-2 mb-1 ${getHeadingColor(theme, 6)}`}
  >
    {children}
  </h6>
);
