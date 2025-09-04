import React, { useState, useRef, useEffect } from 'react';
import { Message, ToolExecution } from '../../types/chat';
import { ToolExecutionDropdown } from './ToolExecutionDropdown';

// Interactive Markdown Component
import { InteractiveMarkdown } from './InteractiveMarkdown/InteractiveMarkdown';

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
  const bubbleRef = useRef<HTMLDivElement>(null);
  const [minHeight, setMinHeight] = useState<number | null>(null);
  const didInitialScrollRef = useRef(false);

  // Calculate streaming space once when streaming starts (delay to allow viewport + scroll settle)
  useEffect(() => {
    if ((isStreaming || isThinking) && !message.content && bubbleRef.current && minHeight === null) {
      const calc = () => {
        const bubble = bubbleRef.current as HTMLDivElement | null;
        if (!bubble) return;
        const container = bubble.closest('.mobile-scroll-container') as HTMLDivElement | null;
        if (!container) return;

        try {
          // Use viewport height for robust floor/cap
          const vh = (window as any).visualViewport?.height || window.innerHeight;

          // Measure in viewport coordinates to avoid scroll math
          const containerRect = container.getBoundingClientRect();
          const bubbleRect = bubble.getBoundingClientRect();

          // Visible space from bubble top to container bottom
          const spaceToBottom = Math.max(0, containerRect.bottom - bubbleRect.top);

          // Subtract small padding to avoid tight fit
          const available = Math.max(0, spaceToBottom - 24);

          // Clamp between 50% and 70% of viewport height
          const floor = Math.round(vh * 0.5);
          const cap = Math.round(vh * 0.7);
          const minHeightPx = Math.max(floor, Math.min(available, cap));

          setMinHeight(minHeightPx);
        } catch (error) {
          console.warn('Error calculating streaming space:', error);
          const fallbackVh = (window as any).visualViewport?.height || window.innerHeight || 600;
          setMinHeight(Math.round(fallbackVh * 0.5)); // Fallback to 50vh
        }
      };

      // Defer until after blur/scroll-to-bottom/layout settle
      requestAnimationFrame(() => setTimeout(calc, 50));
    }

    // Reset when streaming ends
    if (!isStreaming && !isThinking) {
      setMinHeight(null);
    }
  }, [isStreaming, isThinking, message.content, minHeight]);

  const handleCopy = async () => {
    try {
      // Modern Clipboard API (preferred)
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(message.content);
      } else {
        // Fallback for older browsers or non-HTTPS contexts
        const textArea = document.createElement('textarea');
        textArea.value = message.content;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        textArea.remove();
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy message:', error);
      // Still show copied state even if there was an error
      // User might have manually copied the text
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Show tool dropdown when thinking OR when tools exist (timer shows total time for any AI response)
  const shouldShowToolDropdown = isThinking || messageTools.length > 0;

  // Check if content is empty (accounting for whitespace)
  const hasEmptyContent = !message.content || message.content.trim() === '';

  // Show spacer only when streaming/thinking
  const shouldShowSpacer = (isStreaming || isThinking) && minHeight !== null;

  // One-time scroll to reveal spacer/stream area after minHeight is applied
  useEffect(() => {
    if (shouldShowSpacer && !message.content && bubbleRef.current && !didInitialScrollRef.current) {
      requestAnimationFrame(() => {
        try {
          bubbleRef.current?.scrollIntoView({ block: 'end', behavior: 'auto' });
        } catch {}
      });
      didInitialScrollRef.current = true;
    }
    if (!isStreaming && !isThinking) {
      didInitialScrollRef.current = false;
    }
  }, [shouldShowSpacer, isStreaming, isThinking, message.content]);

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="px-3 py-2 sm:px-4 sm:py-3 md:px-6 md:py-4 rounded-lg group hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
      >
        {/* Message Content */}
        <div 
          ref={bubbleRef}
          className="flex flex-col w-full min-w-0 items-start"
          style={{
            minHeight: shouldShowSpacer ? `${minHeight}px` : undefined
          }}
        >


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
            <div className="px-3 py-2 sm:px-4 sm:py-3 md:px-5 md:py-4 rounded-2xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 w-full min-w-0">
              <div className="prose prose-fluid max-w-none prose-gray dark:prose-invert text-gray-900 dark:text-white overflow-hidden">
                <InteractiveMarkdown 
                  content={message.content}
                  theme="assistant"
                  className="break-words"
                />
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
                        <span className="font-medium">Cancelled</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent 
                      side="top" 
                      align="center"
                      className="max-w-xs px-2 py-1 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 rounded-md shadow-lg"
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
                        <span className="font-medium">No response</span>
                      </div>
                    </TooltipTrigger>
                    <TooltipContent 
                      side="top" 
                      align="center"
                      className="max-w-xs px-2 py-1 bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 rounded-md shadow-lg"
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
                      className="p-2 rounded-lg opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 min-h-[44px] min-w-[44px] flex items-center justify-center"
                    >
                      {copied ? (
                        <Check className="w-3 h-3 text-green-600 dark:text-green-400" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent 
                    side="top" 
                    align="center"
                    className="max-w-xs px-2 py-1 text-xs bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 rounded-md shadow-lg"
                  >
                    <p>{copied ? 'Copied!' : 'Copy message'}</p>
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
          )}

          {/* 🎯 MOBILE UX: Flex spacer - shrinks as content grows */}
          {shouldShowSpacer && (
            <div 
              className="pointer-events-none flex-1"
              style={{ minHeight: '20px' }}
            />
          )}

        </div>
      </motion.div>
    </TooltipProvider>
  );
}; 