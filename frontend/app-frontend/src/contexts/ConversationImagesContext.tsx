import React, { createContext, useContext, ReactNode } from 'react';
import { Message } from '../types/chat';
import { useConversationImages } from '../hooks/useConversationImages';

interface ConversationImagesContextValue {
  // Image URL getters
  getImageUrl: (fileId: string) => string | null;
  getThumbnailUrl: (fileId: string) => string | null;
  hasImage: (fileId: string) => boolean;
  
  // Query state
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  
  // Debug info
  totalImages: number;
  fileIds: string[];
}

const ConversationImagesContext = createContext<ConversationImagesContextValue | null>(null);

interface ConversationImagesProviderProps {
  children: ReactNode;
  messages: Message[];
  conversationId?: string;
}

/**
 * 🎯 CONVERSATION IMAGES PROVIDER
 * 
 * This provider fetches ALL image URLs for a conversation in a single API call
 * and makes them available to all child components via React Context.
 * 
 * This is the correct architectural approach that eliminates:
 * ❌ Multiple API requests from individual components
 * ❌ Race conditions and timing issues
 * ❌ Complex batching and coordination logic
 * 
 * Benefits:
 * ✅ Single API call per conversation
 * ✅ Clean separation of concerns
 * ✅ Follows React best practices
 * ✅ Perfect performance characteristics
 */
export function ConversationImagesProvider({ 
  children, 
  messages, 
  conversationId 
}: ConversationImagesProviderProps) {
  const conversationImages = useConversationImages(messages, conversationId);
  
  const contextValue: ConversationImagesContextValue = {
    getImageUrl: conversationImages.getImageUrl,
    getThumbnailUrl: conversationImages.getThumbnailUrl,
    hasImage: conversationImages.hasImage,
    isLoading: conversationImages.isLoading,
    isError: conversationImages.isError,
    error: conversationImages.error,
    totalImages: conversationImages.totalImages,
    fileIds: conversationImages.fileIds,
  };

  return (
    <ConversationImagesContext.Provider value={contextValue}>
      {children}
    </ConversationImagesContext.Provider>
  );
}

/**
 * Hook to access conversation images from any child component
 * 
 * @returns Image URLs and helper functions
 * @throws Error if used outside of ConversationImagesProvider
 */
export function useConversationImagesContext(): ConversationImagesContextValue {
  const context = useContext(ConversationImagesContext);
  
  if (!context) {
    throw new Error(
      'useConversationImagesContext must be used within a ConversationImagesProvider. ' +
      'Make sure to wrap your conversation components with <ConversationImagesProvider>.'
    );
  }
  
  return context;
}

/**
 * 🧪 DEBUG: Hook to inspect image context state (for development)
 * Use this in development to see what images are available
 */
export function useDebugConversationImages() {
  const context = useConversationImagesContext();
  
  // Uncomment the useEffect below for debugging
  // React.useEffect(() => {
  //   console.log('🖼️ Conversation Images Debug:', {
  //     totalImages: context.totalImages,
  //     fileIds: context.fileIds,
  //     isLoading: context.isLoading,
  //     isError: context.isError,
  //     hasImages: context.fileIds.length > 0,
  //   });
  // }, [context]);
  
  return context;
} 