/**
 * 🚨 DEPRECATED: Use ConversationImagesProvider + useConversationImagesContext instead
 * 
 * This file is kept for reference but should not be used in new code.
 * The new conversation-level approach eliminates multiple API requests.
 */

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { buildApiUrl, ENV } from '../config/env';

interface ImageUrls {
  display: string;
  thumbnail: string;
  expires_at: string;
}

interface BulkUrlResponse {
  urls: Record<string, ImageUrls>;
}

/**
 * 🎯 CLEAN SOLUTION: Normalized Query Keys + TanStack Query Deduplication
 * 
 * Problem: Multiple components requesting different file subsets = multiple API calls
 * Solution: Normalize all requests to use the same query pattern that TanStack Query can deduplicate
 * 
 * ✅ Zero delays, zero timeouts, zero race conditions
 * ✅ TanStack Query handles deduplication automatically  
 * ✅ Simple, predictable, follows React Query patterns
 * ✅ One API call per unique file set (naturally cached)
 */

// Cache key factory - simple and consistent
const imageUrlKeys = {
  all: ['imageUrls'] as const,
  files: (fileIds: string[]) => [...imageUrlKeys.all, 'files', fileIds.sort()] as const,
};

// Fetch function for bulk URL generation
const fetchBulkImageUrls = async (fileIds: string[]): Promise<Record<string, ImageUrls>> => {
  if (!fileIds.length) return {};

  console.log('🌐 API CALL: Fetching URLs for', fileIds.length, 'files:', fileIds);
  
  const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
  const response = await fetch(
    buildApiUrl('/api/v1/files/images/bulk-presigned-urls'),
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
      },
      body: JSON.stringify({ file_ids: fileIds }),
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to fetch image URLs: ${response.status} ${response.statusText}`);
  }

  const data: BulkUrlResponse = await response.json();
  return data.urls || {};
};

/**
 * Hook for getting image URLs with automatic TanStack Query deduplication
 * 
 * @param fileIds Array of file IDs to get URLs for
 * @returns Query result with image URLs and helper functions
 */
export function useImageUrls(fileIds: string[] = []) {
  const normalizedFileIds = fileIds.filter(Boolean).sort();
  
  const query = useQuery({
    queryKey: imageUrlKeys.files(normalizedFileIds),
    queryFn: () => fetchBulkImageUrls(normalizedFileIds),
    enabled: normalizedFileIds.length > 0,
    
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

  // Helper functions for easy access
  const getUrl = (fileId: string): string | null => {
    const urls = query.data;
    return urls?.[fileId]?.display || null;
  };

  const getThumbnail = (fileId: string): string | null => {
    const urls = query.data;
    return urls?.[fileId]?.thumbnail || null;
  };

  const isFileLoading = (fileId: string): boolean => {
    return query.isLoading && normalizedFileIds.includes(fileId);
  };

  const hasFileError = (fileId: string): boolean => {
    return query.isError && normalizedFileIds.includes(fileId);
  };

  const getFileError = (fileId: string): string | null => {
    if (!hasFileError(fileId)) return null;
    return query.error instanceof Error ? query.error.message : 'Unknown error';
  };

  return {
    // Raw data
    imageUrls: query.data || {},
    
    // Helper functions
    getUrl,
    getThumbnail,
    
    // State helpers
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
    
    // Per-file helpers
    isFileLoading,
    hasFileError,
    getFileError,
    
    // Actions
    refetch: query.refetch,
    
    // Debug info
    queryKey: imageUrlKeys.files(normalizedFileIds),
  };
}

/**
 * Hook for getting a single image URL (convenience wrapper)
 * 
 * @param fileId Single file ID to get URL for
 * @returns Simple object with url, loading, and error states
 */
export function useImageUrl(fileId: string | null) {
  const result = useImageUrls(fileId ? [fileId] : []);
  
  return {
    url: fileId ? result.getUrl(fileId) : null,
    thumbnail: fileId ? result.getThumbnail(fileId) : null,
    isLoading: result.isLoading,
    isError: result.isError,
    error: result.error,
    refetch: result.refetch,
  };
}

/**
 * 🧪 TESTING: Function to check how TanStack Query deduplication works
 * 
 * Usage in console:
 * ```
 * import { debugQueryDeduplication } from './useImageUrls';
 * debugQueryDeduplication();
 * ```
 */
export function debugQueryDeduplication() {
  console.log('🔍 Testing TanStack Query deduplication:');
  console.log('Key for ["img1", "img2"]:', imageUrlKeys.files(['img1', 'img2']));
  console.log('Key for ["img2", "img1"]:', imageUrlKeys.files(['img2', 'img1'])); // Should be same
  console.log('Key for ["img1"]:', imageUrlKeys.files(['img1']));
  console.log('Key for ["img3"]:', imageUrlKeys.files(['img3']));
} 