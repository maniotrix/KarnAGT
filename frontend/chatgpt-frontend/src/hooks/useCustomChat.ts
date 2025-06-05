import { useChat } from '@ai-sdk/react';
import { useCallback } from 'react';
import { ChatConfig, ChatMessage } from '../types/chat';

export const useCustomChat = (config: ChatConfig = {}) => {
  const {
    apiUrl = '/api/chat',
    enableCostTracking = true,
    maxMessages = 100,
    ...aiSdkOptions
  } = config;

  const chat = useChat({
    api: apiUrl,
    onError: (error) => {
      console.error('Chat error:', error);
      config.onError?.(error);
    },
    onFinish: (message, options) => {
      if (enableCostTracking) {
        console.log('Token usage:', options.usage);
      }
      config.onFinish?.(message, options);
    },
    onResponse: async (response) => {
      console.log('Response status:', response.status);
      config.onResponse?.(response);
    },
    ...aiSdkOptions,
  });

  // Custom methods extending AI SDK functionality
  const clearChat = useCallback(() => {
    chat.setMessages([]);
  }, [chat.setMessages]);

  const getMessageCount = useCallback(() => {
    return chat.messages.length;
  }, [chat.messages.length]);

  const canSendMessage = useCallback(() => {
    return chat.input.trim().length > 0 && 
           chat.status === 'ready' && 
           chat.messages.length < maxMessages;
  }, [chat.input, chat.status, chat.messages.length, maxMessages]);

  // Transform messages to our custom format
  const messages: ChatMessage[] = chat.messages.map(msg => ({
    ...msg,
    // Add our custom properties if available from backend response
  }));

  return {
    // AI SDK properties
    messages,
    input: chat.input,
    isLoading: chat.isLoading,
    error: chat.error,
    status: chat.status,
    
    // AI SDK methods
    handleInputChange: chat.handleInputChange,
    handleSubmit: chat.handleSubmit,
    setInput: chat.setInput,
    stop: chat.stop,
    reload: chat.reload,
    append: chat.append,
    
    // Custom methods
    clearChat,
    getMessageCount,
    canSendMessage,
  };
}; 