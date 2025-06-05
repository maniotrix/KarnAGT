import React from 'react';

interface ChatActionsProps {
  onShare: () => void;
  onDelete: () => void;
  onStop: () => void;
  onRegenerate: () => void;
  isStreaming: boolean;
  canShare: boolean;
  canDelete: boolean;
}

export const ChatActions: React.FC<ChatActionsProps> = ({
  onShare,
  onDelete,
  onStop,
  onRegenerate,
  isStreaming,
  canShare,
  canDelete,
}) => {
  return (
    <div className="chat-actions">
      {/* Stop streaming button (only show when streaming) */}
      {isStreaming && (
        <button
          onClick={onStop}
          className="action-button stop-button"
          title="Stop generation"
        >
          <span className="action-icon">⏹️</span>
          Stop
        </button>
      )}
      
      {/* Regenerate button (only when not streaming) */}
      {!isStreaming && (
        <button
          onClick={onRegenerate}
          className="action-button regenerate-button"
          title="Regenerate response"
        >
          <span className="action-icon">🔄</span>
          Regenerate
        </button>
      )}
      
      {/* Share button */}
      {canShare && (
        <button
          onClick={onShare}
          className="action-button share-button"
          title="Share conversation"
        >
          <span className="action-icon">📤</span>
          Share
        </button>
      )}
      
      {/* Delete button */}
      {canDelete && (
        <button
          onClick={onDelete}
          className="action-button delete-button"
          title="Delete conversation"
        >
          <span className="action-icon">🗑️</span>
          Delete
        </button>
      )}
    </div>
  );
}; 