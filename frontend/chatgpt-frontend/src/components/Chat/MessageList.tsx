import React, { useEffect, useRef, useState, useCallback } from 'react';
import { ChatMessage } from './ChatMessage';
import { AISDKMessage } from '../../types/chat';

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
  className = 'message-list',
  onLoadMore,
  conversationId,
  hasMoreMessages = true
}) => {
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

  if (messages.length === 0) {
    return (
      <div className="messages-container empty">
        <div className="welcome-message">
          <h2>Welcome to ChatGPT Clone</h2>
          <p>Start a conversation by typing a message below.</p>
          <div className="welcome-suggestions">
            <div className="suggestion">💡 Ask me anything</div>
            <div className="suggestion">📝 Help with writing</div>
            <div className="suggestion">🧮 Solve problems</div>
            <div className="suggestion">💻 Code assistance</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={className} ref={messagesContainerRef}>
      <div className="messages-list">
        {/* Loading indicator for loading more messages */}
        {isLoadingMore && (
          <div className="loading-more-indicator">
            <div className="loading-more-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className="loading-more-text">Loading more messages...</span>
          </div>
        )}
        
        {messages.map((message, index) => (
          <ChatMessage
            key={message.id}
            message={message}
            isStreaming={
              index === messages.length - 1 && 
              message.role === 'assistant' && 
              isLoading
            }
          />
        ))}
        
        {/* Loading indicator for new assistant message */}
        {isLoading && (
          <div className="typing-indicator">
            <div className="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <span className="typing-text">AI is typing...</span>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}; 