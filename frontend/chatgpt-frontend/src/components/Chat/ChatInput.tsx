import React, { KeyboardEvent, FormEvent } from 'react';

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  input,
  setInput,
  onSubmit,
  isLoading,
  disabled = false,
  placeholder = "Type your message...",
}) => {
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && !isLoading && input.trim()) {
        onSubmit(e as any);
      }
    }
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!disabled && !isLoading && input.trim()) {
      onSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input-form">
      <div className="input-container">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isLoading}
          className="message-input"
          rows={1}
          style={{
            minHeight: '24px',
            maxHeight: '200px',
            resize: 'none',
            overflow: 'auto',
          }}
        />
        
        <button
          type="submit"
          disabled={disabled || isLoading || !input.trim()}
          className={`send-button ${isLoading ? 'loading' : ''}`}
          title={disabled ? "Input disabled" : isLoading ? "Sending..." : "Send message"}
        >
          {isLoading ? (
            <span className="loading-spinner">⏳</span>
          ) : (
            <span className="send-icon">➤</span>
          )}
        </button>
      </div>
      
      {/* Input hints */}
      <div className="input-hints">
        <span className="hint">Press Enter to send, Shift+Enter for new line</span>
        {disabled && (
          <span className="disabled-hint">Input disabled</span>
        )}
      </div>
    </form>
  );
}; 