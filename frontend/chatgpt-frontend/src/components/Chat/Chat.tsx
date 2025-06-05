import React from 'react';
import { useCustomChat } from '../../hooks/useCustomChat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { ChatActions } from './ChatActions';
import { ChatConfig } from '../../types/chat';

interface ChatProps {
  config?: ChatConfig;
  className?: string;
}

export const Chat: React.FC<ChatProps> = ({ 
  config = {}, 
  className = '' 
}) => {
  const {
    messages,
    input,
    isLoading,
    error,
    status,
    handleInputChange,
    handleSubmit,
    stop,
    reload,
    clearChat,
    getMessageCount,
    canSendMessage
  } = useCustomChat(config);

  const isStreaming = status === 'streaming' || status === 'submitted';

  return (
    <div className={`chat-container ${className}`}>
      {/* Header */}
      <header className="chat-header">
        <h1>ChatGPT Clone</h1>
        <div className="chat-info">
          <span className="model-info">🤖 GPT-4</span>
          <span className="status-badge" data-status={status}>
            {status}
          </span>
        </div>
      </header>

      {/* Main Chat Area */}
      <main className="chat-main">
        <MessageList
          messages={messages}
          isLoading={isLoading}
          status={status}
        />
      </main>

      {/* Input Area */}
      <footer className="chat-footer">
        <ChatInput
          input={input}
          onInputChange={handleInputChange}
          onSubmit={handleSubmit}
          onStop={stop}
          canSend={canSendMessage()}
          isStreaming={isStreaming}
          disabled={status === 'error'}
        />
        
        <ChatActions
          messageCount={getMessageCount()}
          onClearChat={clearChat}
          onReload={reload}
          status={status}
          error={error}
        />
      </footer>
    </div>
  );
}; 