import React, { useState } from 'react';
import { Message, ToolExecution } from '../../types/chat';
import { ToolExecutionDropdown } from './ToolExecutionDropdown';

// Markdown Support
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';

// Modern UI Libraries  
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@radix-ui/react-tooltip';
import { 
  Copy,
  Check,
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

  // Show tool dropdown when thinking OR when tools exist for this message
  const shouldShowToolDropdown = isThinking || messageTools.length > 0;

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="p-2 sm:p-4 rounded-lg group hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
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
                    // Custom styling for code blocks
                    pre: ({ children, ...props }) => (
                      <pre {...props} className="bg-gray-100 dark:bg-gray-900 rounded-lg p-3 overflow-x-auto">
                        {children}
                      </pre>
                    ),
                    // Custom styling for inline code
                    code: ({ children, className, ...props }) => {
                      const isInline = !className;
                      return (
                        <code 
                          {...props} 
                          className={`${className || ''} ${
                            isInline 
                              ? 'bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-sm' 
                              : ''
                          }`}
                        >
                          {children}
                        </code>
                      );
                    }
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            </div>
          )}

          {/* Action Buttons - Only show when there's content */}
          {message.content && (
            <div className="flex items-center gap-1 mt-1 sm:mt-2 justify-start">
              {/* Copy Button */}
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
                <TooltipContent side="bottom">
                  <p>{copied ? 'Copied!' : 'Copy message'}</p>
                </TooltipContent>
              </Tooltip>
            </div>
          )}


        </div>
      </motion.div>
    </TooltipProvider>
  );
}; 