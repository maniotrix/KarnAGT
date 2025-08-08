import React from 'react';
import { Theme } from '../types';
import { getThemeStyles, getTableRowStyles } from '../utils/themeUtils';

interface TableComponentProps {
  children: React.ReactNode;
  theme: Theme;
  [key: string]: any;
}

export const TableComponent: React.FC<TableComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => {
  const styles = getThemeStyles(theme);
  
  return (
    <div className={`w-full overflow-x-auto not-prose ${styles.table.wrapper} my-4`} style={{ margin: '1rem 0' }}>
      <table 
        {...props} 
        className={`min-w-full border-collapse ${styles.table.table}`}
      >
        {children}
      </table>
    </div>
  );
};

export const TheadComponent: React.FC<TableComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => {
  const styles = getThemeStyles(theme);
  
  return (
    <thead {...props} className={styles.table.headerRow}>
      {children}
    </thead>
  );
};

export const ThComponent: React.FC<TableComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => {
  const styles = getThemeStyles(theme);
  
  return (
    <th 
      {...props} 
      className={`px-3 py-2 text-left text-xs font-medium ${styles.table.headerCell}`}
    >
      {children}
    </th>
  );
};

export const TbodyComponent: React.FC<TableComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => (
  <tbody {...props}>
    {children}
  </tbody>
);

export const TrComponent: React.FC<TableComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => {
  const styles = getThemeStyles(theme);
  const rowStyles = getTableRowStyles(theme);
  
  return (
    <tr 
      {...props} 
      className={`transition-colors duration-150 ${styles.table.bodyRowHover} ${rowStyles}`}
    >
      {children}
    </tr>
  );
};

export const TdComponent: React.FC<TableComponentProps> = ({ 
  children, 
  theme, 
  ...props 
}) => {
  const styles = getThemeStyles(theme);
  
  return (
    <td 
      {...props} 
      className={`px-3 py-2 text-xs leading-relaxed ${styles.table.bodyCell}`}
    >
      {children}
    </td>
  );
};
