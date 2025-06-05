import React from 'react';

interface ChatActionsProps {
  messageCount: number;
  onClearChat: () => void;
  onReload?: () => void;
  status: 'ready' | 'submitted' | 'streaming' | 'error';
  error?: Error | null;
}

export const ChatActions: React.FC<ChatActionsProps> = ({
  messageCount,
  onClearChat,
  onReload,
  status,
  error
}) => {
  return (
    <div className="chat-actions">
      {/* Error Display */}
      {error && (
        <div className="error-container">
          <div className="error-message">
            ❌ Error: {error.message}
          </div>
          {onReload && (
            <button onClick={onReload} className="retry-button">
              🔄 Retry
            </button>
          )}
        </div>
      )}

      {/* Status and Actions */}
      <div className="actions-row">
        <div className="status-info">
          <span className={`status-indicator ${status}`}>
            {status === 'ready' && '✅'}
            {status === 'submitted' && '⏳'}
            {status === 'streaming' && '🔄'}
            {status === 'error' && '❌'}
          </span>
          <span className="status-text">
            {status === 'ready' && 'Ready'}
            {status === 'submitted' && 'Sending...'}
            {status === 'streaming' && 'Streaming...'}
            {status === 'error' && 'Error'}
          </span>
        </div>

        <div className="action-buttons">
          <span className="message-count">
            {messageCount} message{messageCount !== 1 ? 's' : ''}
          </span>
          
          <button
            onClick={onClearChat}
            className="clear-button"
            disabled={messageCount === 0}
            title="Clear all messages"
          >
            🗑️ Clear Chat
          </button>
        </div>
      </div>
    </div>
  );
}; 