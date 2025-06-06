import React, { useEffect, useRef, useState, useCallback } from 'react';
import { ChatMessage } from './ChatMessage';
import { AISDKMessage } from '../../types/chat';

// Modern UI Libraries
import { ScrollArea } from '@radix-ui/react-scroll-area';
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

// Clean Architecture Integration
import { useUiStore } from '../../app/stores/uiStore';

interface MessageListProps {
  messages: AISDKMessage[];
  isLoading: boolean;
  className?: string;
  onLoadMore?: (offset: number) => Promise<number>;
  conversationId?: string;
  hasMoreMessages?: boolean;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  className = '',
  onLoadMore,
  conversationId,
  hasMoreMessages = true
}) => {
  // Clean Architecture Integration
  const { theme } = useUiStore();
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messagesContainerRef = useRef<HTMLDivElement>(null);
  const [isLoadingMore, setIsLoadingMore] = useState(false);
  const [shouldAutoScroll, setShouldAutoScroll] = useState(true);
  const [noMoreMessages, setNoMoreMessages] = useState(false);
  const [isInitialLoad, setIsInitialLoad] = useState(true);
  
  // Use refs to avoid recreating handleScroll on every render
  const messagesLengthRef = useRef(messages.length);
  const isLoadingMoreRef = useRef(isLoadingMore);
  const loadingRequestRef = useRef(false); // Immediate synchronous loading flag
  
  // Track current conversation ID to detect switches
  const currentConversationIdRef = useRef(conversationId);
  
  // Refs for scroll position preservation
  const scrollHeightBeforeLoadRef = useRef(0);
  const scrollTopBeforeLoadRef = useRef(0);
  const shouldPreserveScrollRef = useRef(false);
  
  // Reset state when conversation changes
  useEffect(() => {
    if (currentConversationIdRef.current !== conversationId) {
      console.log('Conversation changed, resetting scroll state:', {
        from: currentConversationIdRef.current,
        to: conversationId
      });
      
      // Reset all scroll-related state
      setIsLoadingMore(false);
      setNoMoreMessages(false);
      setIsInitialLoad(true);
      setShouldAutoScroll(true);
      
      // Reset refs
      loadingRequestRef.current = false;
      isLoadingMoreRef.current = false;
      shouldPreserveScrollRef.current = false;
      
      // Update conversation ID ref
      currentConversationIdRef.current = conversationId;
    }
  }, [conversationId]);
  
  // Update refs when values change
  useEffect(() => {
    messagesLengthRef.current = messages.length;
  }, [messages.length]);
  
  useEffect(() => {
    isLoadingMoreRef.current = isLoadingMore;
    // Also sync the immediate loading flag with state
    if (!isLoadingMore) {
      loadingRequestRef.current = false;
    }
  }, [isLoadingMore]);

  // Preserve scroll position after new messages are loaded
  useEffect(() => {
    if (shouldPreserveScrollRef.current && messagesContainerRef.current) {
      const container = messagesContainerRef.current;
      const heightDifference = container.scrollHeight - scrollHeightBeforeLoadRef.current;
      
      console.log('Preserving scroll position:', {
        oldScrollHeight: scrollHeightBeforeLoadRef.current,
        newScrollHeight: container.scrollHeight,
        heightDifference,
        oldScrollTop: scrollTopBeforeLoadRef.current,
        newScrollTop: scrollTopBeforeLoadRef.current + heightDifference
      });
      
      // Adjust scroll position by the height of newly added content
      container.scrollTop = scrollTopBeforeLoadRef.current + heightDifference;
      
      // Reset the flag
      shouldPreserveScrollRef.current = false;
    }
  }, [messages.length]); // Trigger when messages array changes

  // Handle initial load - auto scroll to bottom and disable load more during initial scroll
  useEffect(() => {
    if (messages.length > 0 && isInitialLoad) {
      // Auto-scroll to bottom on initial load
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
        // Allow load more after initial scroll is complete
        setTimeout(() => {
          setIsInitialLoad(false);
        }, 1000);
      }, 100);
    }
  }, [messages.length, isInitialLoad]);

  // Handle scroll for pagination
  const handleScroll = useCallback(async () => {
    // BLOCK all load more logic during initial load/auto-scroll
    if (isInitialLoad || !messagesContainerRef.current || !onLoadMore || !conversationId || !hasMoreMessages || noMoreMessages) {
      return;
    }
    
    const container = messagesContainerRef.current;
    const currentMessageCount = messagesLengthRef.current;
    const currentlyLoading = isLoadingMoreRef.current;
    
    // ONLY trigger when user explicitly scrolls to the VERY TOP (within 5px)
    // Use synchronous ref check to prevent race conditions
    if (container.scrollTop <= 5 && !currentlyLoading && !loadingRequestRef.current) {
      console.log('Scroll triggered loadMore with offset:', currentMessageCount);
      
      // Store current scroll position and height BEFORE loading
      scrollHeightBeforeLoadRef.current = container.scrollHeight;
      scrollTopBeforeLoadRef.current = container.scrollTop;
      shouldPreserveScrollRef.current = true;
      
      console.log('Storing scroll position before load:', {
        scrollHeight: scrollHeightBeforeLoadRef.current,
        scrollTop: scrollTopBeforeLoadRef.current
      });
      
      // Set synchronous flag immediately to prevent duplicate calls
      loadingRequestRef.current = true;
      setIsLoadingMore(true);
      
      try {
        const loadedCount = await onLoadMore(currentMessageCount);
        
        if (loadedCount === 0) {
          // No more messages available - stop future requests
          setNoMoreMessages(true);
          shouldPreserveScrollRef.current = false; // Don't preserve if no new messages
        }
        // Note: Scroll position preservation happens in useEffect above
        
      } catch (error) {
        console.error('Failed to load more messages:', error);
        shouldPreserveScrollRef.current = false; // Don't preserve on error
      } finally {
        // Reset both state and synchronous flag
        setIsLoadingMore(false);
        loadingRequestRef.current = false;
      }
    }
    
    // Determine if we should auto-scroll when new messages arrive (only after initial load)
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
    setShouldAutoScroll(isNearBottom);
  }, [onLoadMore, conversationId, hasMoreMessages, noMoreMessages, isInitialLoad]);

  // Add scroll listener
  useEffect(() => {
    const container = messagesContainerRef.current;
    if (container) {
      container.addEventListener('scroll', handleScroll);
      return () => {
        container.removeEventListener('scroll', handleScroll);
      };
    }
  }, [handleScroll]);

  // Auto-scroll to bottom when new messages arrive (only if user is near bottom)
  useEffect(() => {
    if (shouldAutoScroll) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isLoading, shouldAutoScroll]);

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
    <div className={`flex flex-col h-full ${className}`}>
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

      {/* Messages Container with Radix ScrollArea */}
      <ScrollArea className="flex-1">
        <div
          ref={messagesContainerRef}
          className="flex flex-col space-y-4 p-4"
        >
          <AnimatePresence initial={false}>
            {messages.map((message, index) => (
              <motion.div
                key={message.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                layout
              >
                <ChatMessage message={message} />
              </motion.div>
            ))}
          </AnimatePresence>

          {/* Typing Indicator */}
          <AnimatePresence>
            {isLoading && (
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
      </ScrollArea>

      {/* Scroll to bottom button */}
      <AnimatePresence>
        {!shouldAutoScroll && messages.length > 0 && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            onClick={() => messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })}
            className="absolute bottom-20 right-6 p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-lg transition-colors"
          >
            <ArrowDown className="w-5 h-5" />
          </motion.button>
        )}
      </AnimatePresence>
    </div>
  );
}; 