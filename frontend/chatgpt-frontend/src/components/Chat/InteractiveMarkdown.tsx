import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';

// Code Block Components
import { CodeComponent, PreBlock } from './CodeBlock';

// Interactive Components
import { ActionButton, QuickForm, CodeRunner, DataFetcher } from './InteractiveComponents';

interface InteractiveMarkdownProps {
  content: string;
  className?: string;
  theme?: 'light' | 'dark' | 'user' | 'assistant';
}

export const InteractiveMarkdown: React.FC<InteractiveMarkdownProps> = ({ 
  content, 
  className = '',
  theme = 'assistant'
}) => {
  // Theme-specific styling
  const getCodeBlockStyles = () => {
    switch (theme) {
      case 'user':
        return 'bg-blue-700 rounded-md p-2 overflow-x-auto border border-blue-600 max-w-full';
      case 'assistant':
      default:
        return 'bg-gray-50 dark:bg-gray-800 rounded-md p-2 overflow-x-auto border border-gray-200 dark:border-gray-700 max-w-full';
    }
  };

  const getInlineCodeStyles = () => {
    switch (theme) {
      case 'user':
        return 'bg-blue-800 px-1 py-0.5 rounded text-sm';
      case 'assistant':
      default:
        return 'bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-sm';
    }
  };

  const getLinkStyles = () => {
    switch (theme) {
      case 'user':
        return 'text-blue-200 hover:text-blue-100 underline';
      case 'assistant':
      default:
        return 'text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline';
    }
  };

  const getTableStyles = () => {
    switch (theme) {
      case 'user':
        return {
          wrapper: 'border border-blue-200 dark:border-blue-800 rounded-lg overflow-hidden',
          table: 'bg-white dark:bg-gray-900',
          headerRow: 'bg-blue-50 dark:bg-blue-900/30 border-b border-blue-200 dark:border-blue-700',
          headerCell: 'text-gray-900 dark:text-blue-100',
          bodyRowHover: 'hover:bg-blue-50/60 dark:hover:bg-blue-900/20',
          bodyCell: 'text-gray-900 dark:text-blue-100 border-b border-gray-200 dark:border-blue-800/40'
        };
      case 'assistant':
      default:
        return {
          wrapper: 'border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden',
          table: 'bg-white dark:bg-gray-900',
          headerRow: 'bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700',
          headerCell: 'text-gray-900 dark:text-gray-100',
          bodyRowHover: 'hover:bg-gray-50 dark:hover:bg-gray-800/50',
          bodyCell: 'text-gray-900 dark:text-gray-200 border-b border-gray-200 dark:border-gray-700'
        };
    }
  };

  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // Enhanced pre blocks with copy button
          pre: ({ children, ...props }) => (
            <PreBlock {...props} className={getCodeBlockStyles()}>
              {children}
            </PreBlock>
          ),
          // Enhanced code with copy functionality
          code: ({ children, className, inline, ...props }: any) => {
            if (inline) {
              // True inline code (like `code` in text) - add inline styling and copy button
              return (
                <CodeComponent 
                  {...props} 
                  className={getInlineCodeStyles()}
                  inline={true}
                >
                  {children}
                </CodeComponent>
              );
            } else {
              // Code inside pre blocks - just render plain code element
              // The PreBlock wrapper will handle the copy functionality
              return (
                <code 
                  {...props} 
                  className={className}
                >
                  {children}
                </code>
              );
            }
          },
          // Custom link handling
          a: ({ href, children, ...props }) => {
            const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'));
            const isProxyUrl = href && /\/api\/v1\/proxy\/(images|files|code-files)\//.test(href);
            
            return (
              <a 
                {...props}
                href={href}
                target={isExternal && !isProxyUrl ? '_blank' : undefined}
                rel={isExternal && !isProxyUrl ? 'noopener noreferrer' : undefined}
                className={getLinkStyles()}
              >
                {children}
              </a>
            );
          },
          // Professional table with clean design
          table: ({ children, ...props }) => {
            const styles = getTableStyles();
            return (
              <div className={`w-full overflow-x-auto not-prose ${styles.wrapper} my-4`} style={{ margin: '1rem 0' }}>
                <table 
                  {...props} 
                  className={`min-w-full border-collapse ${styles.table}`}
                >
                  {children}
                </table>
              </div>
            );
          },
          // Clean table headers
          thead: ({ children, ...props }) => {
            const styles = getTableStyles();
            return (
              <thead {...props} className={styles.headerRow}>
                {children}
              </thead>
            );
          },
          th: ({ children, ...props }) => {
            const styles = getTableStyles();
            return (
              <th 
                {...props} 
                className={`px-3 py-2 text-left text-xs font-medium ${styles.headerCell}`}
              >
                {children}
              </th>
            );
          },
          // Table body with zebra striping
          tbody: ({ children, ...props }) => (
            <tbody {...props}>
              {children}
            </tbody>
          ),
          tr: ({ children, ...props }) => {
            const styles = getTableStyles();            
            return (
              <tr 
                {...props} 
                className={`transition-colors duration-150 ${styles.bodyRowHover} ${
                  theme === 'user' 
                    ? 'even:bg-blue-50/30 dark:even:bg-blue-950/20' 
                    : 'even:bg-gray-50/50 dark:even:bg-gray-800/30'
                }`}
              >
                {children}
              </tr>
            );
          },
          td: ({ children, ...props }) => {
            const styles = getTableStyles();
            return (
              <td 
                {...props} 
                className={`px-3 py-2 text-xs leading-relaxed ${styles.bodyCell}`}
              >
                {children}
              </td>
            );
          },
          // Interactive Components - These can be used in markdown
          ...({
            ActionButton: (props: any) => <ActionButton {...props} />,
            QuickForm: (props: any) => <QuickForm {...props} />,
            CodeRunner: (props: any) => <CodeRunner {...props} />,
            DataFetcher: (props: any) => <DataFetcher {...props} />,
          } as any),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};