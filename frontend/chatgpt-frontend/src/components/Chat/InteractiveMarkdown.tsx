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
          pre: ({ children, node, ...props }) => (
            <PreBlock {...props} className={getCodeBlockStyles()}>
              {children}
            </PreBlock>
          ),
          // Enhanced code with copy functionality
          code: ({ children, className, inline, node, ...props }: any) => {
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
          // Enhanced link handling with external indicators
          a: ({ href, children, node, ...props }) => {
            const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'));
            const isProxyUrl = href && /\/api\/v1\/proxy\/(images|files|code-files)\//.test(href);
            const shouldOpenNewTab = isExternal && !isProxyUrl;
            
            return (
              <a 
                {...props}
                href={href}
                target={shouldOpenNewTab ? '_blank' : undefined}
                rel={shouldOpenNewTab ? 'noopener noreferrer' : undefined}
                className={`${getLinkStyles()} underline-offset-2 hover:underline-offset-1 transition-all duration-150 focus-visible:ring-2 focus-visible:ring-offset-1 ${
                  theme === 'user' 
                    ? 'focus-visible:ring-blue-300' 
                    : 'focus-visible:ring-blue-500 focus-visible:ring-offset-white dark:focus-visible:ring-offset-gray-900'
                } break-words`}
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
          },
          // Professional table with clean design
          table: ({ children, node, ...props }) => {
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
          thead: ({ children, node, ...props }) => {
            const styles = getTableStyles();
            return (
              <thead {...props} className={styles.headerRow}>
                {children}
              </thead>
            );
          },
          th: ({ children, node, ...props }) => {
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
          tbody: ({ children, node, ...props }) => (
            <tbody {...props}>
              {children}
            </tbody>
          ),
          tr: ({ children, node, ...props }) => {
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
          td: ({ children, node, ...props }) => {
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
          // Professional heading hierarchy
          h1: ({ children, node, ...props }) => (
            <h1 
              {...props} 
              className={`text-lg font-semibold mt-6 mb-3 first:mt-0 ${
                theme === 'user' 
                  ? 'text-blue-100' 
                  : 'text-gray-900 dark:text-gray-100'
              }`}
            >
              {children}
            </h1>
          ),
          h2: ({ children, node, ...props }) => (
            <h2 
              {...props} 
              className={`text-base font-semibold mt-5 mb-2 ${
                theme === 'user' 
                  ? 'text-blue-100' 
                  : 'text-gray-900 dark:text-gray-100'
              }`}
            >
              {children}
            </h2>
          ),
          h3: ({ children, node, ...props }) => (
            <h3 
              {...props} 
              className={`text-sm font-medium mt-4 mb-1.5 ${
                theme === 'user' 
                  ? 'text-blue-100' 
                  : 'text-gray-900 dark:text-gray-100'
              }`}
            >
              {children}
            </h3>
          ),
          h4: ({ children, node, ...props }) => (
            <h4 
              {...props} 
              className={`text-sm font-medium mt-3 mb-1 ${
                theme === 'user' 
                  ? 'text-blue-200' 
                  : 'text-gray-800 dark:text-gray-200'
              }`}
            >
              {children}
            </h4>
          ),
          h5: ({ children, node, ...props }) => (
            <h5 
              {...props} 
              className={`text-xs font-medium mt-3 mb-1 ${
                theme === 'user' 
                  ? 'text-blue-200' 
                  : 'text-gray-700 dark:text-gray-300'
              }`}
            >
              {children}
            </h5>
          ),
          h6: ({ children, node, ...props }) => (
            <h6 
              {...props} 
              className={`text-xs font-medium mt-2 mb-1 ${
                theme === 'user' 
                  ? 'text-blue-300' 
                  : 'text-gray-600 dark:text-gray-400'
              }`}
            >
              {children}
            </h6>
          ),
          // Professional blockquotes
          blockquote: ({ children, node, ...props }) => (
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
          ),
          // Simple list styling that handles nesting properly
          ul: ({ children, node, ...props }) => (
            <ul 
              {...props} 
              className={`list-disc pl-5 my-2 space-y-1 text-sm ${
                theme === 'user' 
                  ? 'text-blue-100 marker:text-blue-300' 
                  : 'text-gray-800 dark:text-gray-200 marker:text-gray-500 dark:marker:text-gray-300'
              }`}
            >
              {children}
            </ul>
          ),
          ol: ({ children, node, ...props }) => (
            <ol 
              {...props} 
              className={`list-decimal pl-5 my-2 space-y-1 text-sm ${
                theme === 'user' 
                  ? 'text-blue-100 marker:text-blue-300' 
                  : 'text-gray-800 dark:text-gray-200 marker:text-gray-500 dark:marker:text-gray-300'
              }`}
            >
              {children}
            </ol>
          ),
          li: ({ children, node, ...props }) => (
            <li 
              {...props} 
              className="leading-relaxed"
            >
              {children}
            </li>
          ),
          // Enhanced images
          img: ({ src, alt, node, ...props }) => (
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
          ),
          // Professional horizontal rules
          hr: ({ node, ...props }) => (
            <hr 
              {...props} 
              className={`my-4 border-t ${
                theme === 'user' 
                  ? 'border-blue-400/40' 
                  : 'border-gray-200 dark:border-gray-700'
              }`}
            />
          ),
          // Enhanced inline formatting
          strong: ({ children, node, ...props }) => (
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
          ),
          em: ({ children, node, ...props }) => (
            <em 
              {...props} 
              className={`italic ${
                theme === 'user' 
                  ? 'text-blue-100' 
                  : 'text-gray-800 dark:text-gray-200'
              }`}
            >
              {children}
            </em>
          ),
          // Proper paragraph spacing (minimal when in lists)
          p: ({ children, node, ...props }) => (
            <p 
              {...props} 
              className={`text-sm leading-relaxed ${
                theme === 'user' 
                  ? 'text-blue-100' 
                  : 'text-gray-800 dark:text-gray-200'
              }`}
            >
              {children}
            </p>
          ),
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