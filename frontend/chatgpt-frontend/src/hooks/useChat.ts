import { useState, useCallback, useEffect, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { 
  Message,
  ChatOptions,
  ConversationResponse,
  MessageResponse,
  StreamMessage
} from '../types/chat';
import { chatApi } from '../services/chatApi';
import { useCurrentUser, useAuthStatus } from '../app/hooks/auth/useAuth';
import { chatKeys } from '../app/hooks/chat';
import { API_ENDPOINTS, buildApiUrl, ENV } from '../config/env';

export function useChat(options: ChatOptions = {}) {
  // Auth state
  const userQuery = useCurrentUser();
  const authStatus = useAuthStatus();
  const isAuthenticated = authStatus.data?.authenticated ?? false;
  const queryClient = useQueryClient();

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [conversation, setConversation] = useState<ConversationResponse | null>(null);
  const [tokenUsage, setTokenUsage] = useState({ total: 0, cost: 0, model: '' });
  
  // Refs for SSE management
  const eventSourceRef = useRef<EventSource | null>(null);
  const currentStreamingMessageRef = useRef<Message | null>(null);

  // Transform backend message to frontend format
  const transformBackendMessage = useCallback((msg: MessageResponse): Message => ({
    id: msg.message_id,
    role: msg.role,
    content: msg.content,
    createdAt: new Date(msg.created_at),
    message_id: msg.message_id,
    parent_message_id: msg.parent_message_id,
    total_tokens: msg.total_tokens,
    cost_usd: msg.cost_usd,
    model_name: msg.model_name,
    attachments: msg.attachments,
    metadata: msg.metadata,
  }), []);

  // Load conversation
  const loadConversation = useCallback(async (conversationId: string) => {
    try {
      const conv = await chatApi.getConversation(conversationId);
      setConversation(conv);
      
      // Load messages - the API returns { messages: MessageResponse[], pagination: any }
      const { messages: recentMessages } = await chatApi.getMessages(conversationId, { 
        limit: 20, 
        offset: 0 
      });
      
      // Transform and set messages
      const chatMessages = recentMessages.map(transformBackendMessage);
      setMessages(chatMessages);
      
      // Update token usage
      setTokenUsage({
        total: conv.total_tokens_used,
        cost: conv.total_cost_usd,
        model: recentMessages[0]?.model_name || 'gpt-4',
      });
    } catch (error) {
      setError(error instanceof Error ? error : new Error('Failed to load conversation'));
    }
  }, [transformBackendMessage]);

  // Load more messages (pagination)
  const loadMoreMessages = useCallback(async (conversationId: string, offset: number = 0) => {
    try {
      const { messages: newMessages } = await chatApi.getMessages(conversationId, { 
        limit: 20, 
        offset 
      });
      
      const chatMessages = newMessages.map(transformBackendMessage);
      
      // Prepend older messages, avoiding duplicates
      let uniqueNewMessagesCount = 0;
      setMessages(prev => {
        const existingIds = new Set(prev.map(msg => msg.id));
        const uniqueNewMessages = chatMessages.filter(msg => !existingIds.has(msg.id));
        uniqueNewMessagesCount = uniqueNewMessages.length;
        return [...uniqueNewMessages, ...prev];
      });
      
      return uniqueNewMessagesCount;
    } catch (error) {
      setError(error instanceof Error ? error : new Error('Failed to load more messages'));
      return 0;
    }
  }, [transformBackendMessage]);

  // Initialize conversation
  useEffect(() => {
    if (options.conversationId && isAuthenticated) {
      loadConversation(options.conversationId);
    } else if (!options.conversationId) {
      // Clear state for new chat
      setConversation(null);
      setMessages([]);
      setTokenUsage({ total: 0, cost: 0, model: '' });
      setError(null);
    }
  }, [options.conversationId, isAuthenticated, loadConversation]);

  // Stop streaming
  const stop = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setIsLoading(false);
  }, []);

  // Send message with SSE streaming
  const sendMessage = useCallback(async (content: string, conversationId: string) => {
    if (!content.trim() || !conversationId) return;

    setError(null);
    setIsLoading(true);
    
    // Add user message immediately
    const userMessage: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      createdAt: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    
    // Create assistant message placeholder
    const assistantMessage: Message = {
      id: `assistant-${Date.now()}`,
      role: 'assistant',
      content: '',
      createdAt: new Date(),
    };
    
    currentStreamingMessageRef.current = assistantMessage;
    setMessages(prev => [...prev, assistantMessage]);
    
    try {
      // Prepare stream message
      const streamMessage: StreamMessage = {
        conversation_id: conversationId,
        content,
        role: 'user',
        include_memory: options.memoryEnabled ?? true,
        stream_mode: 'text',
        attachments: [],
        metadata: {},
      };

      // Use fetch with SSE response handling
      const url = buildApiUrl(API_ENDPOINTS.CHAT.STREAM_MESSAGE(conversationId));
      const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        body: JSON.stringify(streamMessage),
      });

      if (!response.ok) {
        throw new Error(`Stream request failed: ${response.statusText}`);
      }

      options.onStreamStart?.();

      // Read SSE stream
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (!reader) {
        throw new Error('No response body');
      }

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          setIsLoading(false);
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the last incomplete line in the buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.trim() === '') continue;
          
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            
            if (data === '[DONE]') {
              setIsLoading(false);
              options.onStreamEnd?.({
                type: 'end',
                message: currentStreamingMessageRef.current as any,
                conversation: conversation as any
              });
              queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
              continue;
            }

            try {
              const event = JSON.parse(data);
              
              switch (event.type) {
                case 'token':
                  // Update assistant message content
                  if (currentStreamingMessageRef.current && event.data?.content) {
                    const token = event.data.content;
                    options.onTokenUpdate?.({
                      type: 'token',
                      content: token,
                      message_id: currentStreamingMessageRef.current.id
                    });
                    
                    setMessages(prev => prev.map(msg => 
                      msg.id === currentStreamingMessageRef.current?.id
                        ? { ...msg, content: msg.content + token }
                        : msg
                    ));
                  }
                  break;
                  
                case 'completion':
                  // Update message with final metadata
                  if (currentStreamingMessageRef.current && event.data) {
                    const finalData = event.data;
                    setMessages(prev => prev.map(msg => 
                      msg.id === currentStreamingMessageRef.current?.id
                        ? {
                            ...msg,
                            message_id: finalData.message_id || msg.message_id,
                            total_tokens: finalData.usage?.total_tokens,
                            cost_usd: finalData.cost_usd,
                            model_name: finalData.model_name,
                          }
                        : msg
                    ));
                    
                    // Update token usage
                    if (finalData.usage) {
                      setTokenUsage(prev => ({
                        total: prev.total + (finalData.usage.total_tokens || 0),
                        cost: prev.cost + (finalData.cost_usd || 0),
                        model: finalData.model_name || prev.model,
                      }));
                    }
                    
                    // Update conversation
                    if (conversation) {
                      setConversation(prev => prev ? {
                        ...prev,
                        message_count: prev.message_count + 2, // user + assistant
                        total_tokens_used: prev.total_tokens_used + (finalData.usage?.total_tokens || 0),
                        total_cost_usd: prev.total_cost_usd + (finalData.cost_usd || 0),
                        last_message_at: new Date().toISOString(),
                      } : null);
                    }
                  }
                  break;
                  
                case 'error':
                  setError(new Error(event.data?.error || 'Stream error'));
                  options.onError?.(event.data?.error || 'Stream error');
                  break;
                  
                case 'end':
                case 'stream_end':
                  setIsLoading(false);
                  options.onStreamEnd?.({
                    type: 'end',
                    message: currentStreamingMessageRef.current as any,
                    conversation: conversation as any
                  });
                  queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
                  break;
              }
            } catch (error) {
              console.error('Failed to parse SSE data:', error, 'Raw data:', data);
            }
          }
        }
      }
    } catch (error) {
      setError(error instanceof Error ? error : new Error('Failed to send message'));
      setIsLoading(false);
    } finally {
      currentStreamingMessageRef.current = null;
    }
  }, [conversation, options, queryClient]);

  // Handle submit
  const handleSubmit = useCallback(async (e?: React.FormEvent) => {
    e?.preventDefault();
    
    if (!isAuthenticated) {
      setError(new Error('Authentication required'));
      return;
    }

    if (!conversation) {
      setError(new Error('No conversation available'));
      return;
    }

    if (input.trim()) {
      await sendMessage(input, conversation.conversation_id);
      setInput('');
    }
  }, [isAuthenticated, conversation, input, sendMessage]);

  // Append message (for programmatic sending)
  const append = useCallback(async (message: { content: string; role?: 'user' | 'assistant' }) => {
    if (!conversation) return;
    
    const content = message.content;
    const role = message.role || 'user';
    
    if (role === 'user') {
      await sendMessage(content, conversation.conversation_id);
    }
  }, [conversation, sendMessage]);

  // Create conversation
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
      setMessages([]);
      setTokenUsage({ total: 0, cost: 0, model: 'gpt-4' });
      return newConv;
    } catch (error) {
      setError(new Error('Failed to create conversation'));
      return null;
    }
  }, [isAuthenticated, options.memoryEnabled]);

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
      setError(new Error('Failed to delete conversation'));
      return false;
    }
  }, [conversation]);

  // Share conversation
  const shareConversation = useCallback(async (conversationId?: string) => {
    const idToShare = conversationId || conversation?.conversation_id;
    if (!idToShare) return null;
    
    try {
      const result = await chatApi.shareConversation(idToShare);
      return result.share_url;
    } catch (error) {
      setError(new Error('Failed to share conversation'));
      return null;
    }
  }, [conversation]);

  // Get all conversations
  const getConversations = useCallback(async () => {
    if (!isAuthenticated) return [];
    
    try {
      return await chatApi.getConversations();
    } catch (error) {
      setError(new Error('Failed to fetch conversations'));
      return [];
    }
  }, [isAuthenticated]);

  // Reload last message
  const reload = useCallback(async () => {
    if (!conversation || messages.length < 2) return;
    
    // Remove last assistant message
    const lastUserMessage = messages[messages.length - 2];
    if (lastUserMessage.role !== 'user') return;
    
    setMessages(prev => prev.slice(0, -1));
    await sendMessage(lastUserMessage.content, conversation.conversation_id);
  }, [conversation, messages, sendMessage]);

  return {
    // State
    messages,
    input,
    setInput,
    isLoading,
    error,
    conversation,
    tokenUsage,
    isAuthenticated,
    
    // Actions
    handleSubmit,
    append,
    stop,
    reload,
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