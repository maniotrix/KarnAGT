import React, { useState, useCallback, useEffect } from 'react';
import { useChat } from '../../hooks/useChat';
import { ConversationResponse } from '../../types/chat';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { ChatActions } from './ChatActions';

// Modern UI Libraries
import { Avatar, AvatarFallback, AvatarImage } from '@radix-ui/react-avatar';
import { Progress } from '@radix-ui/react-progress';
import { ScrollArea } from '@radix-ui/react-scroll-area';
import { Separator } from '@radix-ui/react-separator';

import { 
  User, 
  Bot, 
  Settings, 
  X, 
  AlertTriangle,
  Crown,
  MessageSquare,
  DollarSign,
  Zap,
  ArrowDown
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Clean Architecture - ONLY use these layers
import { useCurrentUser, useAuthStatus } from '../../app/hooks/auth/useAuth';
import { useUiStore } from '../../app/stores/uiStore';

interface ChatProps {
  conversationId?: string;
  onConversationChange?: (conversation: ConversationResponse | null) => void;
  onCreateConversationForMessage?: (messageContent: string) => Promise<ConversationResponse | null>;
  isCreatingConversation?: boolean;
  pendingMessage?: string | null;
  onPendingMessageSubmitted?: () => void;
}

export const Chat: React.FC<ChatProps> = ({ 
  conversationId, 
  onConversationChange,
  onCreateConversationForMessage,
  isCreatingConversation,
  pendingMessage,
  onPendingMessageSubmitted
}) => {
  // Clean Architecture Integration  
  const userQuery = useCurrentUser();
  const authStatus = useAuthStatus();
  const { theme } = useUiStore();
  const currentUser = userQuery.data;
  const isAuthenticated = authStatus.data?.authenticated ?? false;
  const [showActions, setShowActions] = useState(false);
  const [shouldShowScrollButton, setShouldShowScrollButton] = useState(false);
  const [scrollToBottomFn, setScrollToBottomFn] = useState<(() => void) | null>(null);

  // Calculate quota using clean architecture user data
  const calculateQuota = () => {
    if (!currentUser) return { used: 0, total: 20, percentage: 0 };
    
    const quota = currentUser.getMessageQuota();
    // This would normally come from a usage tracking service
    // For now, using mock data - this should be implemented in clean architecture
    const used = 15; // Mock usage - should come from usage repository
    
    return {
      used,
      total: quota.total,
      percentage: (used / quota.total) * 100
    };
  };
  
  const quota = calculateQuota();
  const isQuotaExceeded = quota.percentage >= 100;

  // ✅ Simple Chat Integration
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
    loadMoreMessages,
    hasMoreMessages,
  } = useChat({
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
    }
  });

  // Quota is already calculated above using clean architecture

  // Auto-submit pending message when conversation is loaded
  useEffect(() => {
    if (hasConversation && pendingMessage && pendingMessage.trim() && !isLoading) {
      // Set the input to the pending message and submit it
      setInput(pendingMessage);
      
      // Submit the message after a brief delay to ensure conversation is fully loaded
      const timer = setTimeout(() => {
        const syntheticEvent = new Event('submit', { bubbles: true, cancelable: true });
        handleSubmit(syntheticEvent as any);
        
        // Scroll to bottom after auto-submit
        setTimeout(() => {
          scrollToBottomFn?.();
        }, 100);
        
        // Clear the pending message
        onPendingMessageSubmitted?.();
      }, 100);
      
      return () => clearTimeout(timer);
    }
  }, [hasConversation, pendingMessage, isLoading, setInput, handleSubmit, onPendingMessageSubmitted, scrollToBottomFn]);

  // Handle message submission with quota check
  const handleMessageSubmit = async (e: React.FormEvent) => {
    if (isQuotaExceeded) {
      alert(`Quota exceeded! You've used ${quota.used}/${quota.total} messages. Please upgrade your plan.`);
      return;
    }

    // If we don't have a conversation, ask parent to create one
    if (!hasConversation && onCreateConversationForMessage && input.trim()) {
      // Parent will create conversation and navigate to proper URL
      // The message will be submitted after navigation completes
      await onCreateConversationForMessage(input.trim());
      return;
    }

    // We have a conversation, submit the message normally
    if (hasConversation) {
      handleSubmit(e);
      
      // ALWAYS scroll to bottom when user sends message
      setTimeout(() => {
        scrollToBottomFn?.();
      }, 100);
    }
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

  // Handle load more messages - memoized to prevent unnecessary re-renders
  const handleLoadMore = useCallback(async (offset: number): Promise<number> => {
    if (!conversation?.conversation_id) {
      console.log('No conversation ID available for loadMore');
      return 0;
    }
    console.log('Chat handleLoadMore called:', { conversationId: conversation.conversation_id, offset });
    return await loadMoreMessages(conversation.conversation_id, offset);
  }, [conversation?.conversation_id, loadMoreMessages]);

  // Handle scroll state changes from MessageList
  const handleScrollStateChange = useCallback((shouldShowButton: boolean, scrollToBottom: () => void) => {
    setShouldShowScrollButton(shouldShowButton);
    setScrollToBottomFn(() => scrollToBottom);
  }, []);

  // Show loading state during auth check
  if (!isAuthenticated) {
    return (
      <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
        <div className="flex flex-col items-center justify-center h-full text-center p-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex flex-col items-center space-y-4"
          >
            <div className="p-4 bg-blue-100 dark:bg-blue-900 rounded-full">
              <MessageSquare className="w-8 h-8 text-blue-600 dark:text-blue-400" />
            </div>
            <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
              Authentication Required
            </h2>
            <p className="text-gray-600 dark:text-gray-400 max-w-md">
              Please log in to start chatting with AI assistant.
            </p>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full overflow-hidden bg-gray-50 dark:bg-gray-900">
      {/* Chat Header */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex justify-between items-center px-4 py-2 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-sm flex-shrink-0"
      >
        <div className="flex-1">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            {conversation?.title || 'New Chat'}
          </h2>
          {conversation && (
            <div className="flex items-center space-x-4 mt-1 text-sm text-gray-500 dark:text-gray-400">
              <div className="flex items-center space-x-1">
                <MessageSquare className="w-4 h-4" />
                <span>{conversation.message_count} messages</span>
              </div>
              <div className="flex items-center space-x-1">
                <Zap className="w-4 h-4" />
                <span>{tokenUsage?.total || 0} tokens</span>
              </div>
              <div className="flex items-center space-x-1">
                <DollarSign className="w-4 h-4" />
                <span>~${(tokenUsage?.cost || 0).toFixed(4)}</span>
              </div>
            </div>
          )}
        </div>
      </motion.div>

      {/* Error Display */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="flex items-center justify-between bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200 px-4 py-3 mx-4 mt-2 rounded-lg flex-shrink-0"
          >
            <div className="flex items-center space-x-2">
              <AlertTriangle className="w-5 h-5" />
              <span>{typeof error === 'object' && error !== null ? error.message : String(error)}</span>
            </div>
            <button 
              onClick={clearError}
              className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-200 transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Quota Warning */}
      <AnimatePresence>
        {quota.percentage > 80 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className={`flex items-center justify-center px-4 py-3 mx-4 mt-2 rounded-lg flex-shrink-0 ${
              quota.percentage >= 100 
                ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-red-800 dark:text-red-200'
                : 'bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200'
            }`}
          >
            <AlertTriangle className="w-5 h-5 mr-2" />
            <span>
              {quota.percentage >= 100 
                ? `⚠️ Quota exceeded! Upgrade your ${currentUser?.subscriptionTier} plan to continue.`
                : `⚠️ Quota warning: ${quota.percentage.toFixed(0)}% used`
              }
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Content Area - This will grow and the inner MessageList will scroll */}
      <div className="flex-1 overflow-hidden min-h-0 relative">
        <MessageList
          messages={messages}
          isLoading={isLoading}
          onLoadMore={handleLoadMore}
          conversationId={conversation?.conversation_id}
          hasMoreMessages={hasMoreMessages}
          onScrollStateChange={handleScrollStateChange}
        />
        
        {/* Scroll to bottom button - Centered in chat area */}
        <AnimatePresence>
          {shouldShowScrollButton && messages.length > 0 && (
            <div className="absolute bottom-4 left-0 right-0 flex justify-center z-10">
              <motion.button
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                onClick={() => scrollToBottomFn?.()}
                className="p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-xl border-2 border-white dark:border-gray-800 transition-all duration-200 hover:scale-105"
              >
                <ArrowDown className="w-5 h-5" />
              </motion.button>
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* Chat Actions (conditionally rendered) */}
      {showActions && conversation && (
        <div className="px-4 pb-2 flex-shrink-0">
          <ChatActions
            onShare={handleShare}
            onDelete={handleDelete}
            onStop={stop}
            onRegenerate={() => console.log('Regenerate not implemented')}
            isStreaming={isLoading}
            canShare={!!conversation}
            canDelete={!!conversation}
          />
        </div>
      )}

      {/* Chat Input & Error Display */}
      <div className="border-t border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-4 flex-shrink-0">
        <ChatInput
          input={input}
          setInput={setInput}
          onSubmit={handleMessageSubmit}
          isLoading={isLoading || (isCreatingConversation ?? false)}
          disabled={isQuotaExceeded || (isCreatingConversation ?? false)}
          placeholder={
            (isCreatingConversation ?? false)
              ? "Creating conversation..."
              : isQuotaExceeded
              ? "Quota exceeded. Please upgrade your plan."
              : "Type your message..."
          }
        />
        {error && (
          <div className="mt-2 text-sm text-red-600 dark:text-red-400">
            Error: {typeof error === 'object' && error !== null ? error.message : String(error)}
          </div>
        )}
        {/* Stop generating button */}
        {isLoading && (
          <div className="mt-2 text-center">
            <button
              onClick={stop}
              className="px-4 py-2 text-sm bg-red-100 text-red-700 rounded-md hover:bg-red-200"
            >
              Stop generating
            </button>
          </div>
        )}
      </div>
    </div>
  );
}; 