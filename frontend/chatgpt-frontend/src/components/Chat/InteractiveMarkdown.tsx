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
        return 'bg-blue-700 rounded-md p-2 overflow-x-auto border border-blue-600';
      case 'assistant':
      default:
        return 'bg-gray-50 dark:bg-gray-800 rounded-md p-2 overflow-x-auto border border-gray-200 dark:border-gray-700';
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
          code: ({ children, className, ...props }) => {
            const isInline = !className;
            return (
              <CodeComponent 
                {...props} 
                className={`${className || ''} ${
                  isInline ? getInlineCodeStyles() : ''
                }`}
                inline={isInline}
              >
                {children}
              </CodeComponent>
            );
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