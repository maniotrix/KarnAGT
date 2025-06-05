import React, { useRef, useEffect } from 'react';

interface ChatInputProps {
  input: string;
  onInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSubmit: (e: React.FormEvent) => void;
  onStop: () => void;
  canSend: boolean;
  isStreaming: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  input,
  onInputChange,
  onSubmit,
  onStop,
  canSend,
  isStreaming,
  disabled = false,
  placeholder = "Type your message here..."
}) => {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [input]);

  // Focus on mount
  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (canSend) {
        onSubmit(e);
      }
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (canSend) {
      onSubmit(e);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="chat-input-form">
      <div className="input-container">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={onInputChange}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled || isStreaming}
          rows={1}
          className="message-input"
          maxLength={4000}
        />
        
        <div className="input-actions">
          {isStreaming ? (
            <button
              type="button"
              onClick={onStop}
              className="stop-button"
              title="Stop generation"
            >
              ⏹️
            </button>
          ) : (
            <button
              type="submit"
              disabled={!canSend || disabled}
              className="send-button"
              title="Send message (Enter)"
            >
              📤
            </button>
          )}
        </div>
      </div>
      
      {/* Character count */}
      <div className="input-footer">
        <span className="char-count">
          {input.length}/4000
        </span>
        <span className="input-hint">
          Press Enter to send, Shift+Enter for new line
        </span>
      </div>
    </form>
  );
}; 