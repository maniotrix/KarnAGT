import React from 'react';
import { AISDKMessage } from '../../types/chat';

interface ChatMessageProps {
  message: AISDKMessage;
  isStreaming?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  isStreaming = false 
}) => {
  const formatTime = (date: Date | string) => {
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`message ${message.role}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '🤖'}
      </div>
      
      <div className="message-content">
        <div className="message-header">
          <span className="message-role">
            {isUser ? 'You' : 'Assistant'}
          </span>
          <span className="message-time">
            {formatTime(message.createdAt || new Date())}
          </span>
          {isStreaming && isAssistant && (
            <span className="streaming-indicator">●</span>
          )}
        </div>
        
        <div className="message-text">
          {message.content}
        </div>
        
        {/* Backend-specific metadata */}
        {(message.total_tokens || message.cost_usd || message.model_name) && (
          <div className="message-meta">
            {message.model_name && (
              <span className="model">Model: {message.model_name}</span>
            )}
            {message.total_tokens && (
              <span className="tokens">Tokens: {message.total_tokens}</span>
            )}
            {message.cost_usd && (
              <span className="cost">Cost: ${message.cost_usd.toFixed(4)}</span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}; 