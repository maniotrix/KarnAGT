import React, { useState } from 'react';
import { useCustomChat } from '../../hooks/useCustomChat';
import { useAuth } from '../../contexts/AuthContext';
import { ConversationResponse } from '../../types/chat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { ChatActions } from './ChatActions';
import './Chat.css';

interface ChatProps {
  conversationId?: string;
  onConversationChange?: (conversation: ConversationResponse | null) => void;
}

export const Chat: React.FC<ChatProps> = ({ 
  conversationId, 
  onConversationChange 
}) => {
  const { user, isAuthenticated, checkQuota } = useAuth();
  const [showActions, setShowActions] = useState(false);

  // Initialize custom chat with backend integration
  const {
    messages,
    input,
    setInput,
    isLoading,
    error,
    conversation,
    tokenUsage,
    handleSubmit,
    createConversation,
    deleteConversation,
    shareConversation,
    stop,
    clearError,
    hasConversation,
  } = useCustomChat({
    conversationId,
    memoryEnabled: true,
    onConversationUpdate: onConversationChange,
    onStreamStart: () => {
      setShowActions(false); // Hide actions during streaming
    },
    onStreamEnd: (data) => {
      console.log('Stream completed:', data);
      setShowActions(true); // Show actions after completion
    },
    onError: (error) => {
      console.error('Chat error:', error);
    },
  });

  // Check quota before allowing messages
  const quota = checkQuota();
  const isQuotaExceeded = quota.percentage >= 100;

  // Handle conversation creation for new chats
  const handleNewConversation = async () => {
    const newConv = await createConversation();
    if (newConv && onConversationChange) {
      onConversationChange(newConv);
    }
  };

  // Handle message submission with quota check
  const handleMessageSubmit = async (e: React.FormEvent) => {
    if (isQuotaExceeded) {
      alert(`Quota exceeded! You've used ${quota.used}/${quota.total} messages. Please upgrade your plan.`);
      return;
    }

    if (!hasConversation) {
      await handleNewConversation();
    }
    
    handleSubmit(e);
  };

  // Handle share conversation
  const handleShare = async () => {
    if (!conversation) return;
    
    try {
      const shareUrl = await shareConversation();
      if (shareUrl) {
        navigator.clipboard.writeText(shareUrl);
        alert('Share link copied to clipboard!');
      }
    } catch (error) {
      console.error('Failed to share conversation:', error);
    }
  };

  // Handle delete conversation
  const handleDelete = async () => {
    if (!conversation) return;
    
    if (window.confirm('Are you sure you want to delete this conversation?')) {
      const success = await deleteConversation();
      if (success && onConversationChange) {
        onConversationChange(null);
      }
    }
  };

  // Show loading state during auth check
  if (!isAuthenticated) {
    return (
      <div className="chat-container">
        <div className="chat-auth-required">
          <h2>Authentication Required</h2>
          <p>Please log in to start chatting.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="chat-container">
      {/* Chat Header */}
      <div className="chat-header">
        <div className="chat-title">
          <h2>{conversation?.title || 'New Chat'}</h2>
          {conversation && (
            <div className="chat-meta">
              <span className="message-count">{conversation.message_count} messages</span>
              <span className="token-usage">{tokenUsage?.total || 0} tokens</span>
              <span className="cost">~${(tokenUsage?.cost || 0).toFixed(4)}</span>
            </div>
          )}
        </div>
        
        {/* User Info & Quota */}
        <div className="chat-user-info">
          <div className="user-details">
            <span className="user-name">{user?.full_name || user?.email}</span>
            <span className="subscription-tier">{user?.subscription_tier}</span>
          </div>
          <div className="quota-info">
            <div className="quota-bar">
              <div 
                className="quota-fill" 
                style={{ width: `${Math.min(quota.percentage, 100)}%` }}
              />
            </div>
            <span className="quota-text">
              {quota.used}/{quota.total} messages
            </span>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="chat-error">
          <span>{error}</span>
          <button onClick={clearError} className="error-close">×</button>
        </div>
      )}

      {/* Quota Warning */}
      {quota.percentage > 80 && (
        <div className={`quota-warning ${quota.percentage >= 100 ? 'quota-exceeded' : ''}`}>
          {quota.percentage >= 100 
            ? `⚠️ Quota exceeded! Upgrade your ${user?.subscription_tier} plan to continue.`
            : `⚠️ Quota warning: ${quota.percentage.toFixed(0)}% used`
          }
        </div>
      )}

      {/* Messages */}
      <MessageList 
        messages={messages} 
        isLoading={isLoading}
        className="chat-messages"
      />

      {/* Chat Actions */}
      {showActions && hasConversation && (
        <ChatActions
          onShare={handleShare}
          onDelete={handleDelete}
          onStop={stop}
          onRegenerate={() => console.log('Regenerate not implemented')}
          isStreaming={isLoading}
          canShare={!!conversation}
          canDelete={!!conversation}
        />
      )}

      {/* Input */}
      <ChatInput
        input={input}
        setInput={setInput}
        onSubmit={handleMessageSubmit}
        isLoading={isLoading}
        disabled={isQuotaExceeded}
        placeholder={
          isQuotaExceeded 
            ? "Quota exceeded - please upgrade your plan"
            : hasConversation 
              ? "Type your message..." 
              : "Start a new conversation..."
        }
      />
    </div>
  );
}; 