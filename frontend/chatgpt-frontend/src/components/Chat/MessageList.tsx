import React, { useEffect, useRef } from 'react';
import { ChatMessage } from './ChatMessage';
import { ChatMessage as ChatMessageType } from '../../types/chat';

interface MessageListProps {
  messages: ChatMessageType[];
  isLoading: boolean;
  status: 'ready' | 'submitted' | 'streaming' | 'error';
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  isLoading,
  status
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
    <div className="messages-container">
      <div className="messages-list">
        {messages.map((message, index) => (
          <ChatMessage
            key={message.id}
            message={message}
            isStreaming={
              index === messages.length - 1 && 
              message.role === 'assistant' && 
              (status === 'streaming' || status === 'submitted')
            }
          />
        ))}
        
        {/* Loading indicator for new assistant message */}
        {isLoading && status === 'submitted' && (
          <div className="message assistant loading">
            <div className="message-header">
              <div className="message-role">🤖 Assistant</div>
            </div>
            <div className="message-content">
              <div className="typing-indicator">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}; 