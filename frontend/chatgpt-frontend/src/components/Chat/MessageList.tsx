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
  ArrowDown
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

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  className = '',
  onLoadMore,
  conversationId,
  hasMoreMessages = true,
  onScrollStateChange
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const isLoadingMoreRef = useRef(false);
  const prevConversationIdRef = useRef(conversationId);
  
  // Simple scroll handler - just track if user is at bottom and handle load more
  const handleScroll = useCallback(() => {
    if (!messagesContainerRef.current) return;
    
    const container = messagesContainerRef.current;
    const { scrollTop, scrollHeight, clientHeight } = container;
    
    // Track if user is at bottom (for scroll button visibility)
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
    setIsAtBottom(isNearBottom);
    
    // Load more when scrolled to top
    if (scrollTop <= 10 && onLoadMore && !isLoadingMoreRef.current) {
      isLoadingMoreRef.current = true;
      setIsLoadingMore(true);
      
      onLoadMore(messages.length)
        .then(() => {
          // Keep user near top after loading
          setTimeout(() => {
            if (messagesContainerRef.current) {
              messagesContainerRef.current.scrollTop = 100;
            }
          }, 50);
        })
        .catch(console.error)
        .finally(() => {
          setIsLoadingMore(false);
          isLoadingMoreRef.current = false;
        });
    }
  }, [onLoadMore, messages.length]);

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
      {/* Load More Indicator */}
      <AnimatePresence>
        {isLoadingMore && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center justify-center py-4 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700"
          >
            <Loader2 className="w-5 h-5 animate-spin text-blue-600 dark:text-blue-400 mr-2" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Loading more messages...
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Messages Container */}
      <div
        ref={messagesContainerRef}
        className="flex-1 overflow-y-auto h-full"
      >
        <div className="flex flex-col space-y-4 p-4">
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