import React, { useState, useCallback, useEffect, useRef } from 'react';
import { ChatMessage } from './ChatMessage';
import { Message, ToolExecution } from '../../types/chat';

import { 
  Lightbulb, 
  Edit3, 
  Calculator, 
  Code,
  Loader2,
  ArrowUp
} from 'lucide-react';
import Logo from '../ui/Logo';
import { motion, AnimatePresence } from 'framer-motion';



interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  className?: string;
  onLoadMore?: (offset: number) => Promise<number>;
  conversationId?: string;
  hasMoreMessages?: boolean;
  onEdit?: (messageId: string, newContent: string) => Promise<boolean>;
  messageToolExecutions?: Map<string, ToolExecution[]>;
  onScrollFunctionReady?: (scrollToBottom: (behavior?: 'auto' | 'smooth') => void) => void;
}

const MessageListComponent: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  className = '',
  onLoadMore,
  conversationId,
  hasMoreMessages = false,
  onEdit,
  messageToolExecutions = new Map(),
  onScrollFunctionReady
}) => {
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [showScrollButton, setShowScrollButton] = useState(false);
  
  // Refs for pure native implementation
  const containerRef = useRef<HTMLDivElement>(null);
  const bottomElementRef = useRef<HTMLDivElement>(null);
  
  // Pure browser scroll function
  const scrollToBottom = useCallback((behavior: 'auto' | 'smooth' = 'smooth') => {
    bottomElementRef.current?.scrollIntoView({ behavior });
  }, []);
  
  // Expose scroll function to parent
  useEffect(() => {
    if (onScrollFunctionReady) {
      onScrollFunctionReady(scrollToBottom);
    }
  }, [onScrollFunctionReady, scrollToBottom]);
  
  // Pure browser visibility detection - no manual config needed
  useEffect(() => {
    if (!bottomElementRef.current) return;
    
    const observer = new IntersectionObserver(
      ([entry]) => {
        // Show button when bottom is NOT visible
        setShowScrollButton(!entry.isIntersecting && messages.length > 0);
      },
      { threshold: 1.0 } // Exactly at bottom - pure browser decision
    );
    
    observer.observe(bottomElementRef.current);
    return () => observer.disconnect();
  }, [messages.length]);

  // Manual triggers only - no auto-scroll on content change
  
  // Conversation change auto-scroll
  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom('auto'); // Instant scroll on conversation switch
    }
  }, [conversationId, scrollToBottom]);

  // Initial scroll on mount
  useEffect(() => {
    if (messages.length > 0) {
      scrollToBottom('auto'); // Instant scroll on first load
    }
  }, [messages.length > 0, scrollToBottom]);

  // Simple Load More handler
  const handleLoadMoreClick = useCallback(async () => {
    if (!onLoadMore || isLoadingMore || !hasMoreMessages) return;
    
    setIsLoadingMore(true);
    try {
      await onLoadMore(messages.length);
    } catch (error) {
      console.error('Failed to load more messages:', error);
    } finally {
      setIsLoadingMore(false);
    }
  }, [onLoadMore, isLoadingMore, hasMoreMessages, messages.length]);

  // Welcome suggestions data
  const suggestions = [
    { icon: Lightbulb, text: 'Ask me anything', color: 'text-yellow-500' },
    { icon: Edit3, text: 'Writing / Data Analysis', color: 'text-blue-500' },
    { icon: Calculator, text: 'Solve problems', color: 'text-green-500' },
    { icon: Code, text: 'Code assistance', color: 'text-purple-500' },
  ];

  if (messages.length === 0) {
    return (
      <div className={`flex flex-col h-full overflow-hidden ${className}`}>
        <div className="flex-1 overflow-y-auto mobile-scroll-container" 
             style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'contain' }}>
          <div className="flex flex-col items-center justify-center min-h-full p-4 sm:p-8">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center max-w-2xl"
            >
              <div className="mb-6 flex justify-center">
                <Logo size="2xl" backgroundVariant="theme" />
              </div>
              
              <h2 className="text-fluid-lg font-bold text-gray-900 dark:text-white mb-4">
                Welcome to KarnAGT
              </h2>
              
              <p className="text-gray-600 dark:text-gray-400 mb-8 text-fluid-sm">
                Start a conversation by typing a message below.
              </p>
              {/* Capability one-liner – wraps gracefully on smaller screens */}
              <p className="text-gray-500 dark:text-gray-400 mb-10 text-fluid-xs flex flex-wrap justify-center gap-x-2 gap-y-1">
                <span className="whitespace-nowrap">💻 <span className="font-medium">Run code</span></span>
                <span className="hidden sm:inline">|</span>
                <span className="whitespace-nowrap">🌐 <span className="font-medium">Search web</span></span>
                <span className="hidden sm:inline">|</span>
                <span className="whitespace-nowrap">📄 <span className="font-medium">Upload and Query docs</span></span>
                <span className="hidden sm:inline">|</span>
                <span className="whitespace-nowrap">📁 <span className="font-medium">Generate files</span></span>
                <span className="hidden sm:inline">|</span>
                <span className="whitespace-nowrap">🧠 <span className="font-medium">Save to memory</span></span>
              </p>
              <div className="grid grid-cols-2 gap-4 max-w-lg mx-auto">
            {suggestions.map((suggestion, index) => {
              const Icon = suggestion.icon;
              return (
                <motion.div
                  key={index}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.1 }}
                  className="flex items-center space-x-2 sm:space-x-3 p-3 sm:p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
                >
                  <Icon className={`w-6 h-6 sm:w-5 sm:h-5 ${suggestion.color}`} />
                  <span className="text-gray-700 dark:text-gray-300 font-medium">
                    {suggestion.text}
                  </span>
                </motion.div>
              );
            })}
              </div>
            </motion.div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full overflow-hidden ${className} relative`}>
      {/* Pure native scroll container - no custom event handlers */}
      <div 
        ref={containerRef}
        className="flex-1 h-full overflow-y-auto mobile-scroll-container"
        style={{ WebkitOverflowScrolling: 'touch', overscrollBehavior: 'contain' }}
      >
        <div className="flex flex-col space-y-4 px-2 py-4 sm:px-6">
          {/* Load More Button - Always at top when more messages available */}
          {hasMoreMessages && (
            <div className="flex justify-center py-2">
              <button
                onClick={handleLoadMoreClick}
                disabled={isLoadingMore}
                className="flex items-center space-x-2 px-4 py-2 bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 disabled:bg-blue-400 dark:disabled:bg-blue-600 text-white rounded-full shadow-lg transition-colors disabled:cursor-not-allowed"
              >
                {isLoadingMore ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span className="text-fluid-sm font-medium">Loading...</span>
                  </>
                ) : (
                  <>
                    <ArrowUp className="w-4 h-4" />
                    <span className="text-fluid-sm font-medium">Load More Messages</span>
                  </>
                )}
              </button>
            </div>
          )}

          {/* Messages - No animations for better performance */}
          {messages.map((message, index) => {
            // Determine if this message is currently being streamed
            const isLastMessage = index === messages.length - 1;
            const isStreamingThisMessage = isLoading && isLastMessage && message.role === 'assistant';
            
            // Create a more stable key
            const messageKey = message.id || `${conversationId}-${message.role}-${index}`;
            
            // Pass tool execution data to ChatMessage
            const messageTools = messageToolExecutions.get(message.id) || [];
            const shouldShowThinking = isLoading && isLastMessage && message.role === 'assistant';
            
            // Get latest user message for assistant messages
            const latestUserMessage = message.role === 'assistant' && index > 0 
              ? (() => {
                  // Find the most recent user message before this assistant message
                  for (let i = index - 1; i >= 0; i--) {
                    if (messages[i].role === 'user') {
                      return messages[i];
                    }
                  }
                  return undefined;
                })()
              : undefined;
            
            // Get assistant content for progressive messaging detection
            const assistantContent = message.role === 'assistant' ? message.content : undefined;
            
            return (
              <div key={messageKey} className="mb-4">
                <ChatMessage 
                  message={message} 
                  isStreaming={isStreamingThisMessage}
                  onEdit={onEdit}
                  messageTools={messageTools}
                  isThinking={shouldShowThinking}
                  userMessage={latestUserMessage}
                  assistantContent={assistantContent}
                />
              </div>
            );
          })}
          
          {/* Pure native bottom marker - IntersectionObserver target */}
          <div ref={bottomElementRef} className="h-1" />
        </div>
      </div>
      
      {/* Pure native button visibility - no complex props needed */}
      {showScrollButton && (
        <div className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-10">
          <button
            onClick={() => scrollToBottom('smooth')}
            className="p-3 bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 text-white rounded-full shadow-xl border-2 border-white dark:border-gray-800 transition-colors"
          >
            <ArrowUp className="w-5 h-5 rotate-180" />
          </button>
        </div>
      )}
    </div>
  );
};

// Export memoized version to prevent re-renders when input changes
export const MessageList = React.memo(MessageListComponent); 