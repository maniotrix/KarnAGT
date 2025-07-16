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
import { imageService, hasStagingFiles } from '../app/services';

export function useChat(options: ChatOptions = {}) {
  // Auth state
  const userQuery = useCurrentUser();
  const authStatus = useAuthStatus();
  const isAuthenticated = authStatus.data?.authenticated ?? false;
  const queryClient = useQueryClient();

  // Image handling is now managed directly in message data

  // Chat state
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [conversation, setConversation] = useState<ConversationResponse | null>(null);
  const [tokenUsage, setTokenUsage] = useState({ total: 0, cost: 0, model: '' });
  
  // Pagination state
  const [paginationInfo, setPaginationInfo] = useState<{
    hasNext: boolean;
    hasPrev: boolean;
    total: number;
    currentlyLoaded: number;
  }>({
    hasNext: false,
    hasPrev: false,
    total: 0,
    currentlyLoaded: 0
  });
  
  // Stream state for stop functionality
  const [currentStreamId, setCurrentStreamId] = useState<string | null>(null);
  
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
    vector_file_references: msg.vector_file_references,  // Add vector_file_references mapping
    metadata: msg.metadata,
  }), []);

  // Load conversation
  const loadConversation = useCallback(async (conversationId: string) => {
    try {
      const conv = await chatApi.getConversation(conversationId);
      setConversation(conv);
      
      // Load messages - the API returns { messages: MessageResponse[], pagination: any }
      const { messages: recentMessages, pagination } = await chatApi.getMessages(conversationId, { 
        limit: 20, 
        offset: 0 
      });
      
      // Transform and set messages
      const chatMessages = recentMessages.map(transformBackendMessage);
      setMessages(chatMessages);
      
      // Update pagination info
      setPaginationInfo({
        hasNext: pagination?.has_next || false,
        hasPrev: pagination?.has_prev || false,
        total: pagination?.total || chatMessages.length,
        currentlyLoaded: chatMessages.length
      });
      
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
      const { messages: newMessages, pagination } = await chatApi.getMessages(conversationId, { 
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
      
      // Update pagination info
      setPaginationInfo(prev => ({
        hasNext: pagination?.has_next || false,
        hasPrev: pagination?.has_prev || false,
        total: pagination?.total || prev.total,
        currentlyLoaded: prev.currentlyLoaded + uniqueNewMessagesCount
      }));
      
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
      setPaginationInfo({
        hasNext: false,
        hasPrev: false,
        total: 0,
        currentlyLoaded: 0
      });
      setError(null);
    }
  }, [options.conversationId, isAuthenticated, loadConversation]);

  // Extract stream_id from SSE events - exactly like the test file does
  const extractStreamIdFromSSE = useCallback((data: string): string | null => {
    if (!data || data === '[DONE]' || data === '') {
      return null;
    }
    
    try {
      const event = JSON.parse(data);
      
      // Look for stream_id in various event types (as shown in test file)
      if ('stream_id' in event) {
        return event.stream_id;
      }
      
      // Also check nested data
      if ('data' in event && typeof event.data === 'object' && event.data !== null && 'stream_id' in event.data) {
        return event.data.stream_id;
      }
      
      return null;
    } catch (error) {
      return null;
    }
  }, []);

  // Stop streaming - updated to use backend stream cancellation API
  const stop = useCallback(async () => {
    console.log('Stop called - currentStreamId:', currentStreamId);
    
    // Cancel backend stream if we have a stream ID
    if (currentStreamId) {
      try {
        const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
        const response = await fetch(buildApiUrl(API_ENDPOINTS.CHAT.CANCEL_STREAM(currentStreamId)), {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(token && { Authorization: `Bearer ${token}` }),
          },
        });
        
        if (response.status === 200) {
          console.log('✅ Stream cancelled successfully');
        } else if (response.status === 410) {
          console.log('✅ Stream already completed (410 - expected for fast streams)');
        } else if (response.status === 404) {
          console.log('⚠️ Stream not found (may have already ended)');
        } else {
          console.error('❌ Stream cancellation failed:', response.status);
        }
      } catch (error) {
        console.error('❌ Stream cancellation error:', error);
      }
    }
    
    // Clean up EventSource (legacy support)
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    
    // Update state
    setIsLoading(false);
    setCurrentStreamId(null);
  }, [currentStreamId]);

  // Send message with SSE streaming
  const sendMessage = useCallback(async (content: string, conversationId: string, stagingFiles: Record<string, any> = {}, imageData: Array<{ fileId: string; filename: string; file: File; blobUrl: string; s3Key: string }> = []) => {
    if (!conversationId) {
      console.error('❌ No conversation ID provided');
      return;
    }

    console.log('📤 Sending message with staging files:', stagingFiles);
    console.log('📤 Sending message with image data:', imageData);
    
    // Extract document data from staging files for immediate display
    const documentData = stagingFiles.vectors ? stagingFiles.vectors.map((doc: any) => ({
      fileId: doc.file_id,
      filename: doc.filename,
      file: null, // Not available in staging files
      s3Key: doc.s3_key,
    })) : [];
    
    console.log('📤 Extracted document data:', documentData);
    
    // STEP 1: Create user message with actual image and document data for immediate display
    const userMessage: Message = {
      id: `temp_${Date.now()}`,
      message_id: `temp_${Date.now()}`,
      role: 'user',
      content,
      createdAt: new Date(),
      // Store actual image data for immediate display
      localImages: imageData.length > 0 ? imageData : undefined,
      // Store actual document data for immediate display
      localDocuments: documentData.length > 0 ? documentData : undefined,
    };

    // STEP 2: Add to UI immediately with actual image data
    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setError(null);
    setIsLoading(true);

    options.onStreamStart?.();
    
    try {
      // STEP 3: Prepare stream message for backend
      const streamMessage: StreamMessage = {
        conversation_id: conversationId,
        content,
        role: 'user',
        include_memory: options.memoryEnabled ?? true,
        stream_mode: 'text',
        attachments: [],
        metadata: {},
        staging_files: stagingFiles, // Send staging files to backend
      };

      console.log('🔍 DEBUG: Prepared StreamMessage object:', streamMessage);

      // STEP 4: Start streaming to backend
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

      // STEP 5: Process stream response
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      if (!reader) {
        throw new Error('No response body');
      }

      console.log('🌊 Stream started...');
      
      let assistantMessage: Message | null = null;
      let assistantContent = '';
      
      while (true) {
        const { done, value } = await reader.read();
        
        if (done) {
          console.log('✅ Stream completed');
          break;
        }

        buffer += decoder.decode(value, { stream: true });
        
        while (buffer.includes('\n')) {
          const lineIndex = buffer.indexOf('\n');
          const line = buffer.substring(0, lineIndex);
          buffer = buffer.substring(lineIndex + 1);
          
          if (line.trim() === '') continue;
          
          if (line.startsWith('data: ')) {
            const data = line.substring(6);
            
            if (data === '[DONE]') {
              console.log('✅ Stream completed with [DONE]');
              break;
            }
            
            if (data === '') continue;
            
            try {
              const parsed = JSON.parse(data);
              
              // Handle different event types
              if (parsed.type === 'token' && parsed.data?.content) {
                const token = parsed.data.content;
                assistantContent += token;
                
                // Update or create assistant message
                if (!assistantMessage) {
                  assistantMessage = {
                    id: `temp_assistant_${Date.now()}`,
                    message_id: `temp_assistant_${Date.now()}`,
                    role: 'assistant',
                    content: assistantContent,
                    createdAt: new Date(),
                  };
                  
                  setMessages(prev => [...prev, assistantMessage!]);
                } else {
                  // Update existing assistant message
                  assistantMessage.content = assistantContent;
                  
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessage!.id 
                      ? { ...assistantMessage! }
                      : msg
                  ));
                }
                
                // Call token callback if exists
                if (options.onTokenUpdate) {
                  options.onTokenUpdate({ type: 'token', content: token, message_id: assistantMessage.message_id || '' });
                }
              } else if (parsed.type === 'completion' 
                                    || parsed.type === 'end' 
                                    || parsed.type === 'cancelled' 
                                    || parsed.type === 'stream_end'
                                    || parsed.type === 'stream_cancelled') {
                console.log(`✅ Stream ended with ${parsed.type} event`);
                
                // Handle both nested and direct message data formats for compatibility
                let finalMessage = null;
                if (parsed.data?.message) {
                  // Nested format: parsed.data.message.message_id
                  finalMessage = parsed.data.message;
                } else if (parsed.data?.message_id) {
                  // Direct format: parsed.data.message_id (used in stream_end)
                  finalMessage = parsed.data;
                }
                
                if (finalMessage && assistantMessage) {
                  assistantMessage.message_id = finalMessage.message_id;
                  
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessage!.id
                      ? { ...assistantMessage! }
                      : msg
                  ));
                }
                
                // CRITICAL FIX: Update user message ID from backend (even for cancelled streams)
                if (parsed.data?.user_message_id) {
                  setMessages(prev => prev.map(msg => 
                    msg.id === userMessage.id
                      ? { ...msg, message_id: parsed.data.user_message_id }
                      : msg
                  ));
                  console.log(`✅ Updated user message ID from ${parsed.type}:`, parsed.data.user_message_id);
                }
                
                // Log if stream was cancelled
                if (parsed.data?.was_cancelled) {
                  console.log('⚠️ Stream was cancelled, but message IDs updated for edit functionality');
                }
                
                break;
              }
            } catch (parseError) {
              console.warn('⚠️ Failed to parse SSE data:', data, parseError);
            }
          }
        }
      }

      // STEP 6: Update user message with final backend message ID if available
      // The localImages will remain for display, backend attachments will be available on refresh
      
    } catch (error) {
      console.error('❌ Error in sendMessage:', error);
      setError(error as Error);
      
      // Create proper StreamErrorEvent for callback
      if (options.onError) {
        options.onError({
          type: 'error',
          error: error instanceof Error ? error.message : 'Unknown error',
          message: error instanceof Error ? error.message : 'Unknown error'
        });
      }
      
      // Remove the temporary user message on error
      setMessages(prev => prev.filter(msg => msg.id !== userMessage.id));
    } finally {
      setIsLoading(false);
    }
  }, [options, setMessages, setInput, setError, setIsLoading]);

  // Handle submit
  const handleSubmit = useCallback(async (e?: React.FormEvent | (React.FormEvent & { stagingFiles?: Record<string, any>; imageData?: Array<{ fileId: string; filename: string; file: File; blobUrl: string; s3Key: string }> })) => {
    console.log('🔍 DEBUG: handleSubmit called in useChat');
    console.log('🔍 DEBUG: Event object:', e);
    console.log('🔍 DEBUG: Event type:', typeof e);
    console.log('🔍 DEBUG: Event keys:', e ? Object.keys(e) : 'no event');
    
    e?.preventDefault();
    
    if (!isAuthenticated) {
      setError(new Error('Authentication required'));
      return;
    }

    if (!conversation) {
      setError(new Error('No conversation available'));
      return;
    }

    // Extract staging files and image data from custom event if present
    const stagingFiles = (e as any)?.stagingFiles || {};
    const imageData = (e as any)?.imageData || [];
    console.log('🔍 DEBUG: Extracted stagingFiles from event:', stagingFiles);
    console.log('🔍 DEBUG: Extracted imageData from event:', imageData);
    console.log('🔍 DEBUG: stagingFiles type:', typeof stagingFiles);
    console.log('🔍 DEBUG: stagingFiles keys:', Object.keys(stagingFiles));
    console.log('🔍 DEBUG: imageData length:', imageData.length);
    
    // Validate that we have either content or staging files using utility function
    const hasFiles = hasStagingFiles(stagingFiles);
    
    if (!input.trim() && !hasFiles) {
      setError(new Error('Message must have content or images'));
      return;
    }

    const messageToSend = input.trim();
    console.log('🔍 DEBUG: Message to send:', messageToSend);
    console.log('🔍 DEBUG: Conversation ID:', conversation.conversation_id);
    console.log('🔍 DEBUG: About to call sendMessage with staging files:', stagingFiles);
    console.log('🔍 DEBUG: About to call sendMessage with image data:', imageData);
    
    // Clear input IMMEDIATELY when user submits
    setInput('');
    
    await sendMessage(messageToSend, conversation.conversation_id, stagingFiles, imageData);
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
      setPaginationInfo({
        hasNext: false,
        hasPrev: false,
        total: 0,
        currentlyLoaded: 0
      });
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

  // Edit message with streaming support
  const editMessage = useCallback(async (messageId: string, newContent: string) => {
    if (!conversation || !newContent.trim()) return false;
    
    try {
      setError(null);
      
      // Find the message being edited
      const messageIndex = messages.findIndex(msg => msg.message_id === messageId);
      if (messageIndex === -1) {
        throw new Error('Message not found');
      }
      
      const originalMessage = messages[messageIndex];
      if (originalMessage.role !== 'user') {
        throw new Error('Can only edit user messages');
      }
      
      // STEP 1: Immediately update the edited message and clear everything after it
      // This gives instant visual feedback to the user
      setMessages(prev => {
        const updatedMessages = [...prev];
        
        // Update the edited message content
        updatedMessages[messageIndex] = {
          ...updatedMessages[messageIndex],
          content: newContent.trim()
        };
        
        // Remove all messages after the edited one
        return updatedMessages.slice(0, messageIndex + 1);
      });
      
      // STEP 2: Set loading state and prepare for streaming
      setIsLoading(true);
      
      // Create assistant message placeholder for streaming
      const assistantMessage: Message = {
        id: `assistant-edit-${Date.now()}`,
        role: 'assistant',
        content: '',
        createdAt: new Date(),
      };
      
      currentStreamingMessageRef.current = assistantMessage;
      setMessages(prev => [...prev, assistantMessage]);
      
      // STEP 3: Start streaming edit
      const streamResponse = await chatApi.editMessage(
        conversation.conversation_id,
        messageId,
        newContent.trim()
      );
      
      // STEP 4: Process the streaming response
      const reader = streamResponse.body?.getReader();
      if (!reader) {
        throw new Error('Failed to get stream reader');
      }
      
      const decoder = new TextDecoder();
      let buffer = '';
      let streamIdCaptured = false;
      
      try {
        console.log('🌊 Edit stream started, waiting for stream_id...');
        
        while (true) {
          const { done, value } = await reader.read();
          
          if (done) {
            setIsLoading(false);
            setCurrentStreamId(null);
            break;
          }
          
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';
          
          for (const line of lines) {
            if (!line.trim()) continue;
            
            if (line.startsWith('data: ')) {
              const data = line.slice(6).trim();
              
              // Try to capture stream_id from this event (critical for stop button)
              if (!streamIdCaptured) {
                const extractedStreamId = extractStreamIdFromSSE(data);
                if (extractedStreamId) {
                  setCurrentStreamId(extractedStreamId);
                  streamIdCaptured = true;
                  console.log('🎯 EDIT STREAM_ID CAPTURED:', extractedStreamId);
                }
              }
              
              if (data === '[DONE]') {
                break;
              }
              
              try {
                const event = JSON.parse(data);
                console.log('Edit stream event:', event);
                
                switch (event.type) {
                  case 'stream_start':
                    console.log('Edit stream started');
                    options.onStreamStart?.();
                    break;
                    
                  case 'token':
                    if (event.data?.content && currentStreamingMessageRef.current) {
                      setMessages(prev => {
                        const updated = [...prev];
                        const lastIndex = updated.length - 1;
                        if (lastIndex >= 0 && updated[lastIndex].id === currentStreamingMessageRef.current?.id) {
                          updated[lastIndex] = {
                            ...updated[lastIndex],
                            content: updated[lastIndex].content + event.data.content
                          };
                        }
                        return updated;
                      });
                    }
                    break;
                    
                  case 'completion':
                  case 'stream_end':
                    if (event.data && currentStreamingMessageRef.current) {
                      // Final update with complete message data
                      setMessages(prev => {
                        const updated = [...prev];
                        const lastIndex = updated.length - 1;
                        if (lastIndex >= 0 && updated[lastIndex].id === currentStreamingMessageRef.current?.id) {
                          updated[lastIndex] = {
                            ...updated[lastIndex],
                            message_id: event.data.message_id || updated[lastIndex].id,
                            total_tokens: event.data.total_tokens,
                            cost_usd: event.data.cost_usd,
                            model_name: event.data.model_name,
                          };
                        }
                        return updated;
                      });
                      
                      // Update conversation metadata
                      if (conversation && event.data) {
                        setConversation(prev => prev ? {
                          ...prev,
                          total_tokens_used: prev.total_tokens_used + (event.data.total_tokens || 0),
                          total_cost_usd: prev.total_cost_usd + (event.data.cost_usd || 0),
                          last_message_at: new Date().toISOString(),
                        } : null);
                      }
                      
                      // Update token usage
                      if (event.data) {
                        setTokenUsage(prev => ({
                          total: prev.total + (event.data.total_tokens || 0),
                          cost: prev.cost + (event.data.cost_usd || 0),
                          model: event.data.model_name || prev.model,
                        }));
                      }
                    }
                    
                    setIsLoading(false);
                    setCurrentStreamId(null);
                    options.onStreamEnd?.({
                      type: 'end',
                      message: currentStreamingMessageRef.current as any,
                      conversation: conversation as any
                    });
                    // Invalidate queries to refresh conversation list
                    queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
                    break;
                    
                  case 'error':
                    throw new Error(event.data?.error || 'Stream error occurred');
                }
              } catch (parseError) {
                console.error('Failed to parse edit stream event:', parseError, 'Raw data:', data);
              }
            }
          }
        }
      } finally {
        reader.releaseLock();
        currentStreamingMessageRef.current = null;
      }
      
      // Invalidate queries to refresh conversation list
      queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
      
      return true;
    } catch (error) {
      setError(error instanceof Error ? error : new Error('Failed to edit message'));
      setIsLoading(false);
      setCurrentStreamId(null);
      
      // Remove the placeholder assistant message on error
      if (currentStreamingMessageRef.current) {
        setMessages(prev => 
          prev.filter(msg => msg.id !== currentStreamingMessageRef.current?.id)
        );
        currentStreamingMessageRef.current = null;
      }
      
      return false;
    }
  }, [conversation, messages, queryClient, options, extractStreamIdFromSSE, currentStreamId]);

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
    
    // Pagination
    hasMoreMessages: paginationInfo.hasNext,
    paginationInfo,
    
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
    editMessage,
    
    // Utilities
    clearError: () => setError(null),
    hasConversation: !!conversation,
    conversationId: conversation?.conversation_id || null,
  };
} 