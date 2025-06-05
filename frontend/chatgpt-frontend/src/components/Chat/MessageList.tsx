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
  
  // Use refs to avoid recreating handleScroll on every render
  const messagesLengthRef = useRef(messages.length);
  const isLoadingMoreRef = useRef(isLoadingMore);
  
  // Update refs when values change
  useEffect(() => {
    messagesLengthRef.current = messages.length;
  }, [messages.length]);
  
  useEffect(() => {
    isLoadingMoreRef.current = isLoadingMore;
  }, [isLoadingMore]);

  // Handle scroll for pagination
  const handleScroll = useCallback(async () => {
    if (!messagesContainerRef.current || !onLoadMore || !conversationId || !hasMoreMessages) {
      return;
    }
    
    const container = messagesContainerRef.current;
    const currentMessageCount = messagesLengthRef.current;
    const currentlyLoading = isLoadingMoreRef.current;
    
    // If user scrolled to top (within 100px), load more messages
    if (container.scrollTop <= 100 && !currentlyLoading) {
      setIsLoadingMore(true);
      
      try {
        const loadedCount = await onLoadMore(currentMessageCount);
        
        // If no new messages loaded, we've reached the end
        if (loadedCount === 0) {
          // hasMoreMessages should be managed by parent component
        }
      } catch (error) {
        console.error('Failed to load more messages:', error);
      } finally {
        setIsLoadingMore(false);
      }
    }
    
    // Determine if we should auto-scroll when new messages arrive
    const isNearBottom = container.scrollHeight - container.scrollTop - container.clientHeight < 100;
    setShouldAutoScroll(isNearBottom);
  }, [onLoadMore, conversationId, hasMoreMessages]);

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