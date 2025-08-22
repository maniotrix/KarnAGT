import React, { useEffect, useRef, useState, useCallback } from 'react';
import { ChatMessage } from './ChatMessage';
import { Message, ToolExecution } from '../../types/chat';


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
  onEdit?: (messageId: string, newContent: string) => Promise<boolean>;
  messageToolExecutions?: Map<string, ToolExecution[]>;
}

const MessageListComponent: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  className = '',
  onLoadMore,
  conversationId,
  hasMoreMessages = false,
  onScrollStateChange,
  onEdit,
  messageToolExecutions = new Map()
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
    
    // console.log('[DEBUG] Scroll values:', { 
    //   scrollTop, 
    //   scrollHeight, 
    //   clientHeight, 
    //   diff: scrollHeight - scrollTop - clientHeight,
    //   isAtBottom 
    // });
    
    // Track if user is at bottom (for scroll button visibility)
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
    // console.log('[DEBUG] Setting isAtBottom:', isNearBottom);
    setIsAtBottom(isNearBottom);
  }, [isAtBottom]);

  // Ref callback to attach scroll listener when element is available
  const setMessagesContainerRef = useCallback((element: HTMLDivElement | null) => {
    // Remove listener from old element
    if (messagesContainerRef.current) {
      // console.log('[DEBUG] Removing old scroll listener');
      messagesContainerRef.current.removeEventListener('scroll', handleScroll);
    }
    
    // Set new ref
    messagesContainerRef.current = element;
    
    // Attach listener to new element
    if (element) {
      // console.log('[DEBUG] Attaching scroll listener to new element');
      element.addEventListener('scroll', handleScroll, { passive: true });
      // console.log('[DEBUG] Scroll listener attached successfully');
    }
  }, [handleScroll]);

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

  // Check scroll position when content changes (during streaming)
  useEffect(() => {
    if (isLoading && messagesContainerRef.current) {
      // console.log('[DEBUG] Content changed during streaming, checking scroll position');
      handleScroll(); // Manually trigger scroll position check
    }
  }, [messages, isLoading, handleScroll]);

  // Expose scroll state to parent
  useEffect(() => {
    const scrollToBottom = () => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
      setIsAtBottom(true);
    };
    
    // Show scroll button when user is not at bottom
    const shouldShowButton = !isAtBottom;
    // console.log('[DEBUG] Scroll button visibility:', { isAtBottom, isLoading, shouldShowButton });
    onScrollStateChange?.(shouldShowButton, scrollToBottom);
  }, [isAtBottom, onScrollStateChange]);

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
            Welcome to KarnAGT
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
        ref={setMessagesContainerRef}
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
              
              // Create a more stable key - use message ID if available, fallback to index
              const messageKey = message.id || `${conversationId}-${message.role}-${index}`;
              
              // Pass tool execution data to ChatMessage
              const messageTools = messageToolExecutions.get(message.id) || [];
              // Show thinking state when AI is working on the last assistant message
              const shouldShowThinking = isLoading && isLastMessage && message.role === 'assistant';
              
              return (
                <motion.div
                  key={messageKey}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -20 }}
                  transition={{ duration: 0.3, ease: "easeOut" }}
                >
                  <ChatMessage 
                    message={message} 
                    isStreaming={isStreamingThisMessage}
                    onEdit={onEdit}
                    messageTools={messageTools}
                    isThinking={shouldShowThinking}
                  />
                </motion.div>
              );
            })}
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