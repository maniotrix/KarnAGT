import React, { useState } from 'react';
import { Message, ToolExecution } from '../../types/chat';
import { ToolExecutionDropdown } from './ToolExecutionDropdown';

// Markdown Support
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';

// Code Block Components
import { CodeComponent, PreBlock } from './CodeBlock';

// Modern UI Libraries  
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@radix-ui/react-tooltip';
import { 
  Copy,
  Check,
  AlertTriangle,
  FileQuestion,
} from 'lucide-react';
import { motion } from 'framer-motion';



interface AssistantMessageProps {
  message: Message;
  isStreaming?: boolean;
  messageTools?: ToolExecution[];
  isThinking?: boolean;
}

export const AssistantMessage: React.FC<AssistantMessageProps> = ({ 
  message, 
  isStreaming = false,
  messageTools = [],
  isThinking = false
}) => {
  // Copy functionality
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy message:', error);
    }
  };

  // Show tool dropdown when thinking OR when tools exist (timer shows total time for any AI response)
  const shouldShowToolDropdown = isThinking || messageTools.length > 0;

  // Check if content is empty (accounting for whitespace)
  const hasEmptyContent = !message.content || message.content.trim() === '';

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="px-2 py-2 sm:px-4 sm:py-3 rounded-lg group hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      >
        {/* Message Content */}
        <div className="flex flex-col w-full min-w-0 items-start">


          {/* Tool Execution Dropdown - Part of assistant message, below header */}
          {shouldShowToolDropdown && (
            <div className="mb-2 sm:mb-3 w-full">
              <ToolExecutionDropdown 
                tools={messageTools}
                isThinking={isThinking}
                isStreaming={isStreaming}
              />
            </div>
          )}

          {/* Message Bubble - Only show when there's content */}
          {message.content && (
            <div className="px-3 py-2 sm:px-4 sm:py-3 rounded-2xl max-w-none bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700">
              <div className="prose prose-sm max-w-none prose-gray dark:prose-invert text-gray-900 dark:text-white">
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    // Enhanced pre blocks with copy button
                    pre: ({ children, ...props }) => (
                      <PreBlock {...props} className="bg-gray-50 dark:bg-gray-800 rounded-md p-2 overflow-x-auto border border-gray-200 dark:border-gray-700">
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
                            isInline 
                              ? 'bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-sm' 
                              : ''
                          }`}
                          inline={isInline}
                        >
                          {children}
                        </CodeComponent>
                      );
                    },
                    // Custom link handling - open external links in new tab
                    a: ({ href, children, ...props }) => {
                      const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'));
                      const isProxyUrl = href && /\/api\/v1\/proxy\/(images|files|code-files)\//.test(href);
                      
                      return (
                        <a 
                          {...props}
                          href={href}
                          target={isExternal && !isProxyUrl ? '_blank' : undefined}
                          rel={isExternal && !isProxyUrl ? 'noopener noreferrer' : undefined}
                          className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline"
                        >
                          {children}
                        </a>
                      );
                    }
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Compact Status & Actions - Only render when needed */}
          {(message.status === 'cancelled' || hasEmptyContent || message.content) && (
            <div className="flex items-center justify-between mt-1 sm:mt-2">
              {/* Status Indicators - Compact mobile design */}
              <div className="flex items-center gap-1">
                {/* Cancelled Status */}
                {message.status === 'cancelled' && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300 border border-orange-200 dark:border-orange-800">
                        <AlertTriangle className="w-3 h-3" />
                        <span className="text-xs font-medium">Cancelled</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent 
                      side="top" 
                      align="center"
                      className="max-w-xs px-2 py-1 text-xs bg-gray-900 text-white rounded-md shadow-lg"
                    >
                      <p>AI response was cancelled</p>
                    </TooltipContent>
                  </Tooltip>
                )}

                {/* Empty Content Status - Only show for completed messages */}
                {hasEmptyContent && !isStreaming && !isThinking && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 border border-yellow-200 dark:border-yellow-800">
                        <FileQuestion className="w-3 h-3" />
                        <span className="text-xs font-medium">No response</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent 
                      side="top" 
                      align="center"
                      className="max-w-xs px-2 py-1 text-xs bg-gray-900 text-white rounded-md shadow-lg"
                    >
                      <p>AI response is empty</p>
                    </TooltipContent>
                  </Tooltip>
                )}
              </div>

              {/* Copy Button - Only show when there's content */}
              {message.content && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={handleCopy}
                      className="p-1 sm:p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400"
                    >
                      {copied ? (
                        <Check className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
                      ) : (
                        <Copy className="w-2.5 h-2.5 sm:w-3 sm:h-3" />
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent 
                    side="top" 
                    align="center"
                    className="max-w-xs px-2 py-1 text-xs bg-gray-900 text-white rounded-md shadow-lg"
                  >
                    <p>{copied ? 'Copied!' : 'Copy message'}</p>
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
          )}


        </div>
      </motion.div>
    </TooltipProvider>
  );
}; 