import { useQuery } from '@tanstack/react-query';
import { buildApiUrl, ENV } from '../config/env';
import { Message } from '../types/chat';

interface ImageUrls {
  display: string;
  thumbnail: string;
  expires_at: string;
}

interface BulkUrlResponse {
  urls: Record<string, ImageUrls>;
}

/**
 * 🎯 CONVERSATION-LEVEL IMAGE FETCHING
 * 
 * This hook fetches ALL image URLs for a conversation in a single API call.
 * This is the correct architectural approach that eliminates multiple API requests.
 * 
 * Benefits:
 * ✅ Single API call per conversation
 * ✅ No race conditions or timing issues  
 * ✅ Perfect for React Context pattern
 * ✅ Follows data hoisting best practices
 * ✅ Better performance than component-level fetching
 */

// Extract all file IDs from conversation messages
function extractFileIdsFromMessages(messages: Message[]): string[] {
  const fileIds = new Set<string>();
  
  messages.forEach((message) => {
    // Check attachments field  
    if (message.attachments?.length) {
      message.attachments.forEach(attachment => {
        if (typeof attachment === 'object' && attachment?.file_id) {
          fileIds.add(attachment.file_id);
        } else if (typeof attachment === 'string') {
          fileIds.add(attachment);
        }
      });
    }
    
    // Check localImages field (for new uploads)
    if (message.localImages?.length) {
      message.localImages.forEach(img => {
        if (img.fileId) {
          fileIds.add(img.fileId);
        }
      });
    }
  });
  
  return Array.from(fileIds).sort(); // Sort for consistent cache keys
}

// Fetch function for bulk URL generation
const fetchBulkImageUrls = async (fileIds: string[]): Promise<Record<string, ImageUrls>> => {
  if (!fileIds.length) return {};

  console.log('🌐 API CALL: Fetching URLs for', fileIds.length, 'files:', fileIds);
  
  const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
  const response = await fetch(buildApiUrl('/api/v1/files/images/bulk-presigned-urls'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    },
    body: JSON.stringify({ file_ids: fileIds }),
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch image URLs: ${response.status} ${response.statusText}`);
  }

  const data: BulkUrlResponse = await response.json();
  return data.urls || {};
};

/**
 * Hook to fetch all image URLs for a conversation
 * Use this at the conversation level and provide URLs via React Context
 * 
 * @param messages All messages in the conversation
 * @param conversationId Unique identifier for the conversation
 * @returns Query result with all image URLs for the conversation
 */
export function useConversationImages(messages: Message[], conversationId?: string) {
  const fileIds = extractFileIdsFromMessages(messages);
  
  const query = useQuery({
    queryKey: ['conversationImages', conversationId, fileIds],
    queryFn: () => fetchBulkImageUrls(fileIds),
    enabled: fileIds.length > 0,
    
    // Cache for 20 hours (URLs expire in 24 hours)
    staleTime: 20 * 60 * 60 * 1000, // 20 hours - data stays fresh
    gcTime: 24 * 60 * 60 * 1000, // 24 hours - keep in cache
    
    // Background refetch when URLs are about to expire
    refetchInterval: 22 * 60 * 60 * 1000, // 22 hours
    refetchIntervalInBackground: true,
    
    // Retry configuration
    retry: 2,
    retryDelay: 1000,
  });

  // Helper functions for components to use
  const getImageUrl = (fileId: string): string | null => {
    return query.data?.[fileId]?.display || null;
  };

  const getThumbnailUrl = (fileId: string): string | null => {
    return query.data?.[fileId]?.thumbnail || null;
  };

  const hasImage = (fileId: string): boolean => {
    return !!query.data?.[fileId];
  };

  return {
    // All image URLs for the conversation
    imageUrls: query.data || {},
    
    // Helper functions
    getImageUrl,
    getThumbnailUrl,
    hasImage,
    
    // Query state
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    refetch: query.refetch,
    
    // Debug info
    totalImages: fileIds.length,
    fileIds,
  };
} 