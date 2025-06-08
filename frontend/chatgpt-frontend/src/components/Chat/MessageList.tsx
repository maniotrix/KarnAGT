import React, { useEffect, useRef, useState, useCallback } from 'react';
import { ChatMessage } from './ChatMessage';
import { Message } from '../../types/chat';


import { 
  MessageSquare, 
  Lightbulb, 
  Edit3, 
  Calculator, 
  Code,
  Loader2,
  ArrowDown,
  ArrowUp
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';



interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  className?: string;
  onLoadMore?: (offset: number) => Promise<number>;
  conversationId?: string;
  hasMoreMessages?: boolean;
  onScrollStateChange?: (shouldAutoScroll: boolean, scrollToBottom: () => void) => void;
}

const MessageListComponent: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  className = '',
  onLoadMore,
  conversationId,
  hasMoreMessages = false,
  onScrollStateChange
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const prevConversationIdRef = useRef(conversationId);
  
  // Simple scroll handler - only track if user is at bottom
  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    const { scrollTop, scrollHeight, clientHeight } = container;
    
    // Track if user is at bottom (for scroll button visibility)
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
    setIsAtBottom(isNearBottom);
  }, []);

  // Handle Load More button click
  const handleLoadMoreClick = useCallback(async () => {
    if (!onLoadMore || isLoadingMore || !hasMoreMessages) return;
    
    // Store current scroll position and height for restoration
    const container = messagesContainerRef.current;
    if (!container) return;
    
    const oldScrollHeight = container.scrollHeight;
    const oldScrollTop = container.scrollTop;
    
    setIsLoadingMore(true);
    
    try {
      await onLoadMore(messages.length);
      
      // Restore scroll position after new messages are loaded
      setTimeout(() => {
        if (container) {
          const newScrollHeight = container.scrollHeight;
          const heightDifference = newScrollHeight - oldScrollHeight;
          container.scrollTop = oldScrollTop + heightDifference;
        }
      }, 50);
    } catch (error) {
      console.error('Failed to load more messages:', error);
    } finally {
      setIsLoadingMore(false);
    }
  }, [onLoadMore, isLoadingMore, hasMoreMessages, messages.length]);

  // ONLY auto-scroll on conversation change or initial load
  useEffect(() => {
    const conversationChanged = prevConversationIdRef.current !== conversationId;
    
    if (conversationChanged && messages.length > 0) {
      // Scroll to bottom when conversation changes
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'auto' });
        setIsAtBottom(true);
      }, 100);
      
      prevConversationIdRef.current = conversationId;
    }
  }, [conversationId, messages.length]);

  // Expose scroll state to parent
  useEffect(() => {
    const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      setIsAtBottom(true);
    };
    
    // Show scroll button when: not at bottom OR (streaming and can scroll more)
    const shouldShowButton = !isAtBottom || (isLoading && !isAtBottom);
    onScrollStateChange?.(shouldShowButton, scrollToBottom);
  }, [isAtBottom, isLoading, onScrollStateChange]);

  // Attach scroll listener
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll, { passive: true });
      return () => container.removeEventListener('scroll', handleScroll);
    }
  }, [handleScroll]);

  // Welcome suggestions data
  const suggestions = [
    { icon: Lightbulb, text: 'Ask me anything', color: 'text-yellow-500' },
    { icon: Edit3, text: 'Help with writing', color: 'text-blue-500' },
    { icon: Calculator, text: 'Solve problems', color: 'text-green-500' },
    { icon: Code, text: 'Code assistance', color: 'text-purple-500' },
  ];

  if (messages.length === 0) {
    return (
      <div className={`flex flex-col items-center justify-center h-full p-8 ${className}`}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center max-w-2xl"
        >
          <div className="mb-6 p-4 bg-blue-100 dark:bg-blue-900 rounded-full inline-block">
            <MessageSquare className="w-12 h-12 text-blue-600 dark:text-blue-400" />
          </div>
          
          <h2 className="text-3xl font-bold text-gray-900 dark:text-white mb-4">
            Welcome to ChatGPT Clone
          </h2>
          
          <p className="text-gray-600 dark:text-gray-400 mb-8 text-lg">
            Start a conversation by typing a message below.
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
                  className="flex items-center space-x-3 p-4 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
                >
                  <Icon className={`w-5 h-5 ${suggestion.color}`} />
                  <span className="text-gray-700 dark:text-gray-300 font-medium">
                    {suggestion.text}
                  </span>
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className={`flex flex-col h-full overflow-hidden ${className}`}>
      {/* Messages Container */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto h-full"
      >
        <div className="flex flex-col space-y-4 p-4">
          {/* Load More Button - Always at top when more messages available */}
          <AnimatePresence>
            {hasMoreMessages && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="flex justify-center py-2"
              >
                <motion.button
                  onClick={handleLoadMoreClick}
                  disabled={isLoadingMore}
                  className="flex items-center space-x-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white rounded-full shadow-lg transition-all duration-200 hover:scale-105 disabled:scale-100 disabled:cursor-not-allowed"
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {isLoadingMore ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span className="text-sm font-medium">Loading...</span>
                    </>
                  ) : (
                    <>
                      <ArrowUp className="w-4 h-4" />
                      <span className="text-sm font-medium">Load More Messages</span>
                    </>
                  )}
                </motion.button>
              </motion.div>
            )}
          </AnimatePresence>

          <AnimatePresence initial={false}>
            {messages.map((message, index) => {
              // Determine if this message is currently being streamed
              const isLastMessage = index === messages.length - 1;
              const isStreamingThisMessage = isLoading && isLastMessage && message.role === 'assistant';
              
              return (
                <motion.div
                  key={`${message.role}-${index}`}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3 }}
                  layout
                >
                  <ChatMessage 
                    message={message} 
                    isStreaming={isStreamingThisMessage}
                  />
                </motion.div>
              );
            })}
          </AnimatePresence>

          {/* Typing Indicator - Only show when thinking (before streaming starts) */}
          <AnimatePresence>
            {(() => {
              // Show thinking indicator only when:
              // 1. isLoading is true (AI is processing)
              // 2. AND either no messages exist OR last message is not an incomplete assistant message
              const lastMessage = messages[messages.length - 1];
              const isStreamingResponse = isLoading && lastMessage?.role === 'assistant';
              const shouldShowThinking = isLoading && !isStreamingResponse;
              
              return shouldShowThinking;
            })() && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="flex items-center space-x-3 p-4"
              >
                <div className="w-8 h-8 bg-gray-200 dark:bg-gray-700 rounded-full flex items-center justify-center">
                  <MessageSquare className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                </div>
                <div className="flex space-x-1">
                  <motion.div
                    className="w-2 h-2 bg-gray-400 rounded-full"
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: 0 }}
                  />
                  <motion.div
                    className="w-2 h-2 bg-gray-400 rounded-full"
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: 0.2 }}
                  />
                  <motion.div
                    className="w-2 h-2 bg-gray-400 rounded-full"
                    animate={{ opacity: [0.4, 1, 0.4] }}
                    transition={{ duration: 1.5, repeat: Infinity, delay: 0.4 }}
                  />
                </div>
                <span className="text-sm text-gray-500 dark:text-gray-400">
                  AI is thinking...
                </span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Auto-scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>


    </div>
  );
};

// Export memoized version to prevent re-renders when input changes
export const MessageList = React.memo(MessageListComponent); 