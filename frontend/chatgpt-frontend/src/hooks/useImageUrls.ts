import { useState, useCallback } from 'react';
import { buildApiUrl, ENV } from '../config/env';

interface ImageUrls {
  display: string;
  thumbnail: string;
  expires_at: string;
}

interface ImageUrlCache {
  [fileId: string]: {
    urls: ImageUrls;
    cachedAt: number;
    expiresAt: number;
  };
}

// Global cache shared across components (24-hour TTL)
const globalImageCache: ImageUrlCache = {};
const CACHE_TTL = 23 * 60 * 60 * 1000; // 23 hours (before 24h presigned URL expires)

/**
 * Hook for on-demand image URL generation following 2025 industry standards
 * 
 * - Saves metadata only in messages (no permanent URLs)
 * - Generates presigned URLs only when needed
 * - Caches URLs globally to avoid repeated API calls
 * - Automatically handles expiration and refresh
 */
export function useImageUrls() {
  const [loading, setLoading] = useState<{[fileId: string]: boolean}>({});
  const [errors, setErrors] = useState<{[fileId: string]: string}>({});

  const getCachedUrl = useCallback((fileId: string): ImageUrls | null => {
    const cached = globalImageCache[fileId];
    if (!cached) return null;

    // Check if cache is still valid
    const now = Date.now();
    if (now > cached.expiresAt) {
      delete globalImageCache[fileId];
      return null;
    }

    return cached.urls;
  }, []);

  const generateUrls = useCallback(async (fileIds: string[]): Promise<{[fileId: string]: ImageUrls}> => {
    if (!fileIds.length) return {};

    // Filter out already cached URLs
    const uncachedFileIds = fileIds.filter(id => {
      const cached = globalImageCache[id];
      if (!cached) return true;
      
      // Check if cache is still valid
      const now = Date.now();
      if (now > cached.expiresAt) {
        delete globalImageCache[id];
        return true;
      }
      
      return false;
    });
    
    if (!uncachedFileIds.length) {
      // Return cached URLs
      const result: {[fileId: string]: ImageUrls} = {};
      fileIds.forEach(id => {
        const cached = globalImageCache[id];
        if (cached) result[id] = cached.urls;
      });
      return result;
    }

    // Set loading state
    const loadingState: {[fileId: string]: boolean} = {};
    uncachedFileIds.forEach(id => { loadingState[id] = true; });
    setLoading(prev => ({ ...prev, ...loadingState }));

    try {
      const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
      const response = await fetch(
        buildApiUrl('/api/v1/files/images/bulk-presigned-urls'),
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ file_ids: uncachedFileIds }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to generate URLs: ${response.statusText}`);
      }

      const data = await response.json();
      const now = Date.now();
      const results: {[fileId: string]: ImageUrls} = {};

      // Cache successful results
      Object.entries(data.urls).forEach(([fileId, urlData]: [string, any]) => {
        if (urlData.display) {
          const urls: ImageUrls = {
            display: urlData.display,
            thumbnail: urlData.thumbnail || urlData.display,
            expires_at: urlData.expires_at,
          };

          // Cache with TTL
          globalImageCache[fileId] = {
            urls,
            cachedAt: now,
            expiresAt: now + CACHE_TTL,
          };

          results[fileId] = urls;
        } else if (urlData.error) {
          setErrors(prev => ({ ...prev, [fileId]: urlData.error }));
        }
      });

      // Include previously cached URLs
      fileIds.forEach(id => {
        if (!results[id]) {
          const cached = globalImageCache[id];
          if (cached) results[id] = cached.urls;
        }
      });

      return results;

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error';
      const errorState: {[fileId: string]: string} = {};
      uncachedFileIds.forEach(id => { errorState[id] = errorMessage; });
      setErrors(prev => ({ ...prev, ...errorState }));
      throw error;

    } finally {
      // Clear loading state
      const clearLoadingState: {[fileId: string]: boolean} = {};
      uncachedFileIds.forEach(id => { clearLoadingState[id] = false; });
      setLoading(prev => ({ ...prev, ...clearLoadingState }));
    }
  }, []); // Removed getCachedUrl dependency and inlined the logic

  const getUrl = useCallback(async (fileId: string): Promise<string | null> => {
    // First check cache
    const cached = globalImageCache[fileId];
    if (cached) {
      const now = Date.now();
      if (now <= cached.expiresAt) {
        return cached.urls.display;
      } else {
        delete globalImageCache[fileId];
      }
    }
    
    // Generate URL if not cached - inline the API call to avoid circular dependency
    setLoading(prev => ({ ...prev, [fileId]: true }));
    
    try {
      const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
      const response = await fetch(
        buildApiUrl('/api/v1/files/images/bulk-presigned-urls'),
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`,
          },
          body: JSON.stringify({ file_ids: [fileId] }),
        }
      );

      if (!response.ok) {
        throw new Error(`Failed to generate URL: ${response.statusText}`);
      }

      const data = await response.json();
      const urlData = data.urls[fileId];
      
      if (urlData?.display) {
        const urls: ImageUrls = {
          display: urlData.display,
          thumbnail: urlData.thumbnail || urlData.display,
          expires_at: urlData.expires_at,
        };

        // Cache with TTL
        const now = Date.now();
        globalImageCache[fileId] = {
          urls,
          cachedAt: now,
          expiresAt: now + CACHE_TTL,
        };

        return urls.display;
      }
      
      return null;
    } catch (error) {
      setErrors(prev => ({ ...prev, [fileId]: error instanceof Error ? error.message : 'Unknown error' }));
      return null;
    } finally {
      setLoading(prev => ({ ...prev, [fileId]: false }));
    }
  }, []);

  const isLoading = useCallback((fileId: string): boolean => {
    return loading[fileId] || false;
  }, [loading]);

  const getError = useCallback((fileId: string): string | null => {
    return errors[fileId] || null;
  }, [errors]);

  const hasError = useCallback((fileId: string): boolean => {
    return !!errors[fileId];
  }, [errors]);

  return {
    getCachedUrl,
    generateUrls,
    getUrl,
    isLoading,
    getError,
    hasError,
  };
} 