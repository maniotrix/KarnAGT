import { useChat } from '@ai-sdk/react';
import { useState, useCallback, useEffect } from 'react';
import { 
  ConversationResponse, 
  CustomChatOptions,
  AISDKMessage
} from '../types/chat';
import { chatApi } from '../services/chatApi';
import { useCurrentUser, useAuthStatus } from '../app/hooks/auth/useAuth';

export function useCustomChat(options: CustomChatOptions = {}) {
  // Clean Architecture Integration
  const userQuery = useCurrentUser();
  const authStatus = useAuthStatus();
  const isAuthenticated = authStatus.data?.authenticated ?? false;
  const accessToken = userQuery.data ? 'mock-token' : null; // TODO: Implement proper token management
  const [conversation, setConversation] = useState<ConversationResponse | null>(null);
  const [tokenUsage, setTokenUsage] = useState({ total: 0, cost: 0, model: '' });
  const [error, setError] = useState<{ message: string } | null>(null);

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
      setError({ message: error.message });
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
      
      // Load the latest messages using the dedicated messages endpoint
      const { messages: recentMessages } = await chatApi.getMessages(conversationId, { 
        limit: 20, 
        offset: 0 
      });
      
      // Transform backend messages to AI SDK format
      const aiMessages: AISDKMessage[] = recentMessages.map(msg => ({
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
      
      setTokenUsage({
        total: conv.total_tokens_used,
        cost: conv.total_cost_usd,
        model: recentMessages[0]?.model_name || 'gpt-4',
      });
    } catch (error) {
      setError({ message: error instanceof Error ? error.message : 'Failed to load conversation' });
    }
  }, [setMessages]);

  // Load more messages (for pagination)
  const loadMoreMessages = useCallback(async (conversationId: string, offset: number = 0) => {
    console.log('loadMoreMessages called:', { conversationId, offset });
    try {
      const { messages: newMessages } = await chatApi.getMessages(conversationId, { 
        limit: 20, 
        offset 
      });
      
      console.log('API returned messages:', newMessages.length);
      
      // Transform backend messages to AI SDK format
      const aiMessages: AISDKMessage[] = newMessages.map(msg => ({
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
      
      // Prepend older messages to the beginning of the current messages
      // Ensure no duplicates by filtering out messages that already exist
      let uniqueMessagesCount = 0;
      setMessages(prev => {
        console.log('Adding messages:', { oldCount: prev.length, newCount: aiMessages.length });
        
        // Create a Set of existing message IDs for fast lookup
        const existingIds = new Set(prev.map(msg => msg.id));
        
        // Filter out any duplicates from the new messages
        const uniqueNewMessages = aiMessages.filter(msg => !existingIds.has(msg.id));
        uniqueMessagesCount = uniqueNewMessages.length;
        
        console.log('After deduplication:', { uniqueNewCount: uniqueNewMessages.length, duplicatesFiltered: aiMessages.length - uniqueNewMessages.length });
        
        return [...uniqueNewMessages, ...prev];
      });
      
      // Return the count of NEW unique messages loaded
      return uniqueMessagesCount;
    } catch (error) {
      console.error('loadMoreMessages error:', error);
      setError({ message: error instanceof Error ? error.message : 'Failed to load more messages' });
      return 0;
    }
  }, [setMessages]);

  // Initialize conversation if conversationId provided
  useEffect(() => {
    if (options.conversationId && isAuthenticated) {
      console.log('Loading conversation:', options.conversationId);
      loadConversation(options.conversationId);
    } else if (!options.conversationId) {
      // Clear conversation when switching to "new chat" mode
      console.log('Clearing conversation for new chat');
      setConversation(null);
      setMessages([]);
      setTokenUsage({ total: 0, cost: 0, model: '' });
      setError(null);
    }
  }, [options.conversationId, isAuthenticated, loadConversation, setMessages]);

  // Custom submit handler
  const handleSubmit = useCallback(async (e?: React.FormEvent, submitOptions?: { 
    data?: any; 
    conversationId?: string; 
    memoryEnabled?: boolean;
    onConversationUpdate?: (conv: ConversationResponse) => void;
  }) => {
    if (!isAuthenticated || !accessToken) {
      setError({ message: 'Authentication required' });
      return;
    }

    // Clear previous errors
    setError(null);

    // Strictly require conversation to exist - no automatic creation
    // Conversation creation is now handled by ChatApp component
    if (!conversation) {
      setError({ message: 'No conversation available. Conversation must be created first.' });
      return;
    }

    // Call AI SDK submit with existing conversation
    originalHandleSubmit(e, submitOptions);
  }, [isAuthenticated, accessToken, conversation, originalHandleSubmit]);

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
      setError({ message: 'Failed to create conversation' });
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
      setError({ message: 'Failed to delete conversation' });
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
      setError({ message: 'Failed to share conversation' });
      return null;
    }
  }, [conversation]);

  // Get all conversations
  const getConversations = useCallback(async () => {
    if (!isAuthenticated) return [];
    
    try {
      return await chatApi.getConversations();
    } catch (error) {
      setError({ message: 'Failed to fetch conversations' });
      return [];
    }
  }, [isAuthenticated]);

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
    loadMoreMessages,
    
    // Utilities
    clearError: () => setError(null),
    hasConversation: !!conversation,
    conversationId: conversation?.conversation_id || null,
  };
} 