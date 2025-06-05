import { useChat } from '@ai-sdk/react';
import { useState, useCallback, useEffect } from 'react';
import { 
  ConversationResponse, 
  CustomChatOptions,
  AISDKMessage
} from '../types/chat';
import { chatApi } from '../services/chatApi';
import { useAuth } from '../contexts/AuthContext';

export function useCustomChat(options: CustomChatOptions = {}) {
  const { isAuthenticated, accessToken } = useAuth();
  const [conversation, setConversation] = useState<ConversationResponse | null>(null);
  const [tokenUsage, setTokenUsage] = useState({ total: 0, cost: 0, model: '' });
  const [backendError, setBackendError] = useState<string | null>(null);

  // AI SDK useChat with custom fetch
  const {
    messages,
    setMessages,
    input,
    setInput,
    handleSubmit: originalHandleSubmit,
    isLoading,
    error: aiError,
    stop,
    reload,
    append,
  } = useChat({
    api: '/api/chat', // This will be intercepted by our custom fetch
    fetch: chatApi.createAISDKFetch(),
    onResponse: (response) => {
      options.onStreamStart?.();
    },
    onFinish: (message, { usage, finishReason }) => {
      // Update token usage when streaming completes
      if (usage) {
        setTokenUsage(prev => ({
          total: prev.total + (usage.totalTokens || 0),
          cost: prev.cost + (usage.totalTokens || 0) * 0.002, // Estimated cost
          model: prev.model,
        }));
      }
      
      // Update conversation if available
      if (conversation) {
        setConversation(prev => prev ? {
          ...prev,
          message_count: prev.message_count + 1,
          total_tokens_used: prev.total_tokens_used + (usage?.totalTokens || 0),
          total_cost_usd: prev.total_cost_usd + ((usage?.totalTokens || 0) * 0.002),
          last_message_at: new Date().toISOString(),
        } : null);
      }
    },
    onError: (error) => {
      setBackendError(error.message);
      options.onError?.({
        type: 'error',
        error: error.message,
        message: 'Stream processing failed',
      });
    },
    body: {
      // Pass conversation ID to backend
      conversationId: options.conversationId,
      memoryEnabled: options.memoryEnabled ?? true,
    },
  });

  // Load conversation function (defined after useChat to access setMessages)
  const loadConversation = useCallback(async (conversationId: string) => {
    try {
      const conv = await chatApi.getConversation(conversationId);
      setConversation(conv);
      
      // Transform backend messages to AI SDK format
      if (conv.messages) {
        const aiMessages: AISDKMessage[] = conv.messages.map(msg => ({
          id: msg.message_id,
          role: msg.role,
          content: msg.content,
          createdAt: new Date(msg.created_at),
          // Backend-specific fields
          message_id: msg.message_id,
          parent_message_id: msg.parent_message_id,
          total_tokens: msg.total_tokens,
          cost_usd: msg.cost_usd,
          model_name: msg.model_name,
          attachments: msg.attachments,
          metadata: msg.metadata,
        }));
        
        // Set initial messages in AI SDK
        setMessages(aiMessages);
      }
      
      setTokenUsage({
        total: conv.total_tokens_used,
        cost: conv.total_cost_usd,
        model: conv.messages?.[0]?.model_name || 'gpt-4',
      });
    } catch (error) {
      setBackendError(error instanceof Error ? error.message : 'Failed to load conversation');
    }
  }, [setMessages]);

  // Initialize conversation if conversationId provided
  useEffect(() => {
    if (options.conversationId && isAuthenticated) {
      loadConversation(options.conversationId);
    }
  }, [options.conversationId, isAuthenticated, loadConversation]);

  // Custom submit handler
  const handleSubmit = useCallback(async (e?: React.FormEvent, submitOptions?: { 
    data?: any; 
    conversationId?: string; 
    memoryEnabled?: boolean;
    onConversationUpdate?: (conv: ConversationResponse) => void;
  }) => {
    if (!isAuthenticated || !accessToken) {
      setBackendError('Authentication required');
      return;
    }

    // Clear previous errors
    setBackendError(null);

    // If no conversation exists, create one
    if (!conversation && !submitOptions?.conversationId) {
      try {
        const newConv = await chatApi.createConversation({
          title: input.slice(0, 50) || 'New Chat',
          memory_config: {
            enabled: submitOptions?.memoryEnabled ?? true,
            max_turns: 10,
            summary_threshold: 8,
          },
        });
        setConversation(newConv);
        
        // Update options with new conversation ID
        if (submitOptions?.onConversationUpdate) {
          submitOptions.onConversationUpdate(newConv);
        }
      } catch (error) {
        setBackendError('Failed to create conversation');
        return;
      }
    }

    // Call AI SDK submit
    originalHandleSubmit(e, submitOptions);
  }, [isAuthenticated, accessToken, conversation, input, originalHandleSubmit]);

  // Create new conversation
  const createConversation = useCallback(async (title?: string) => {
    if (!isAuthenticated) return null;
    
    try {
      const newConv = await chatApi.createConversation({
        title: title || 'New Chat',
        memory_config: {
          enabled: options.memoryEnabled ?? true,
          max_turns: 10,
          summary_threshold: 8,
        },
      });
      setConversation(newConv);
      setMessages([]); // Clear previous messages
      setTokenUsage({ total: 0, cost: 0, model: 'gpt-4' });
      return newConv;
    } catch (error) {
      setBackendError('Failed to create conversation');
      return null;
    }
  }, [isAuthenticated, options.memoryEnabled, setMessages]);

  // Delete conversation
  const deleteConversation = useCallback(async (conversationId?: string) => {
    const idToDelete = conversationId || conversation?.conversation_id;
    if (!idToDelete) return false;
    
    try {
      await chatApi.deleteConversation(idToDelete);
      if (idToDelete === conversation?.conversation_id) {
        setConversation(null);
        setMessages([]);
        setTokenUsage({ total: 0, cost: 0, model: '' });
      }
      return true;
    } catch (error) {
      setBackendError('Failed to delete conversation');
      return false;
    }
  }, [conversation, setMessages]);

  // Share conversation
  const shareConversation = useCallback(async (conversationId?: string) => {
    const idToShare = conversationId || conversation?.conversation_id;
    if (!idToShare) return null;
    
    try {
      const result = await chatApi.shareConversation(idToShare);
      return result.share_url;
    } catch (error) {
      setBackendError('Failed to share conversation');
      return null;
    }
  }, [conversation]);

  // Get all conversations
  const getConversations = useCallback(async () => {
    if (!isAuthenticated) return [];
    
    try {
      return await chatApi.getConversations();
    } catch (error) {
      setBackendError('Failed to fetch conversations');
      return [];
    }
  }, [isAuthenticated]);

  // Combined error handling
  const error = backendError || aiError?.message || null;

  return {
    // AI SDK properties
    messages: messages as AISDKMessage[],
    input,
    setInput,
    isLoading,
    error,
    stop,
    reload,
    append,
    
    // Custom properties
    conversation,
    tokenUsage,
    isAuthenticated,
    
    // Custom methods
    handleSubmit,
    createConversation,
    deleteConversation,
    shareConversation,
    getConversations,
    loadConversation,
    
    // Utilities
    clearError: () => setBackendError(null),
    hasConversation: !!conversation,
    conversationId: conversation?.conversation_id || null,
  };
} 