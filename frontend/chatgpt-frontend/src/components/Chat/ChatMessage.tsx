import React from 'react';
import { ChatMessage as ChatMessageType } from '../../types/chat';

interface ChatMessageProps {
  message: ChatMessageType;
  isStreaming?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  isStreaming = false 
}) => {
  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  
  return (
    <div className={`message ${message.role}`}>
      <div className="message-header">
        <div className="message-role">
          {isUser ? '👤 You' : '🤖 Assistant'}
        </div>
        {message.createdAt && (
          <div className="message-timestamp">
            {new Date(message.createdAt).toLocaleTimeString()}
          </div>
        )}
      </div>
      
      <div className="message-content">
        {message.content}
        {isStreaming && isAssistant && (
          <span className="streaming-cursor">|</span>
        )}
      </div>
      
      {/* Additional metadata for assistant messages */}
      {isAssistant && (message.cost || message.tokenUsage) && (
        <div className="message-metadata">
          {message.cost && (
            <span className="cost-info">💰 ${message.cost.toFixed(4)}</span>
          )}
          {message.tokenUsage && (
            <span className="token-info">
              🔢 {message.tokenUsage.total} tokens
            </span>
          )}
          {message.model && (
            <span className="model-info">🤖 {message.model}</span>
          )}
        </div>
      )}
    </div>
  );
}; 