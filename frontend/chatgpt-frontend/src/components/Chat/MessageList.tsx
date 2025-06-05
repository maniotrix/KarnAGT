import React, { useEffect, useRef } from 'react';
import { ChatMessage } from './ChatMessage';
import { AISDKMessage } from '../../types/chat';

interface MessageListProps {
  messages: AISDKMessage[];
  isLoading: boolean;
  className?: string;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  className = 'message-list'
}) => {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

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
    <div className={className}>
      <div className="messages-list">
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