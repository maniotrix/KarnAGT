// Hook for loading message images with caching and timeout
import { useEffect, useState } from 'react';
import { useImageStore } from '../app/stores';
import { imageService } from '../app/services';
import { Message } from '../types/chat';

export interface MessageImageState {
  loading: boolean;
  error?: string;
  images: Array<{
    fileId: string;
    filename: string;
    previewUrl: string;
    isLoading?: boolean;
    error?: string;
  }>;
}

/**
 * Hook to load images for a message with caching and timeout handling
 * Used when conversations are refreshed/re-rendered to ensure images are available
 */
export function useMessageImages(message: Message): MessageImageState {
  const [loadingState, setLoadingState] = useState<{ loading: boolean; error?: string }>({
    loading: false
  });
  
  const { 
    getImage, 
    isImageExpired, 
    updateImageUrls, 
    setImageLoading, 
    setImageError 
  } = useImageStore();

  useEffect(() => {
    const loadImagesForMessage = async () => {
      if (!message.stagingImages?.length) {
        return;
      }

      const imagesToLoad: string[] = [];
      const currentImages = message.stagingImages.map(img => {
        const cached = getImage(img.fileId);
        
        // Check if we need to load this image
        if (!cached || (!cached.localPreviewUrl && !cached.backendDisplayUrl)) {
          imagesToLoad.push(img.fileId);
          return {
            fileId: img.fileId,
            filename: img.filename,
            previewUrl: img.previewUrl || '',
            isLoading: true,
          };
        }
        
        // Check if cached image is expired and needs refresh
        if (cached.backendDisplayUrl && isImageExpired(img.fileId)) {
          imagesToLoad.push(img.fileId);
          return {
            fileId: img.fileId,
            filename: cached.filename,
            previewUrl: cached.localPreviewUrl || cached.backendDisplayUrl,
            isLoading: true,
          };
        }
        
        // Use cached image (not expired)
        return {
          fileId: img.fileId,
          filename: cached.filename,
          previewUrl: cached.localPreviewUrl || cached.backendDisplayUrl || img.previewUrl,
          isLoading: false,
        };
      });

      // If no images need loading, we're done
      if (imagesToLoad.length === 0) {
        setLoadingState({ loading: false });
        return;
      }

      console.log(`🔄 Loading ${imagesToLoad.length} images for message ${message.message_id}`);
      setLoadingState({ loading: true });

      // Mark images as loading in store
      imagesToLoad.forEach(fileId => setImageLoading(fileId, true));

      try {
        // Fetch images with timeout
        const fetchResults = await imageService.fetchMultipleImageUrls(imagesToLoad, 10000);
        
        // Update store with results
        Object.entries(fetchResults).forEach(([fileId, result]) => {
          if (result.success && result.url) {
            updateImageUrls(fileId, result.url, result.expiresAt);
            console.log(`✅ Loaded image for message: ${fileId}`);
          } else {
            setImageError(fileId, result.error || 'Failed to load image');
            console.error(`❌ Failed to load image for message: ${fileId}`, result.error);
          }
        });

        setLoadingState({ loading: false });
        
      } catch (error) {
        console.error('❌ Failed to load images for message:', error);
        setLoadingState({ 
          loading: false, 
          error: error instanceof Error ? error.message : 'Failed to load images' 
        });
        
        // Mark all as error in store
        imagesToLoad.forEach(fileId => setImageError(fileId, 'Network error'));
      }
    };

    loadImagesForMessage();
  }, [message.message_id, message.stagingImages, getImage, isImageExpired, updateImageUrls, setImageLoading, setImageError]);

  // Build current image state
  const images = message.stagingImages?.map(img => {
    const cached = getImage(img.fileId);
    return {
      fileId: img.fileId,
      filename: cached?.filename || img.filename,
      previewUrl: cached?.localPreviewUrl || cached?.backendDisplayUrl || img.previewUrl,
      isLoading: cached?.isLoading || false,
      error: cached?.error,
    };
  }) || [];

  return {
    loading: loadingState.loading,
    error: loadingState.error,
    images,
  };
}

/**
 * Hook to preload images for multiple messages (for conversation view)
 */
export function useConversationImages(messages: Message[]) {
  const [loadingCount, setLoadingCount] = useState(0);
  const [errorCount, setErrorCount] = useState(0);
  
  const { 
    getImage, 
    isImageExpired, 
    updateImageUrls, 
    setImageLoading, 
    setImageError,
    clearExpiredImages 
  } = useImageStore();

  useEffect(() => {
    const loadAllImages = async () => {
      // Clear expired images first
      clearExpiredImages();
      
      // Collect all images that need loading
      const imagesToLoad: string[] = [];
      
      messages.forEach(message => {
        message.stagingImages?.forEach(img => {
          const cached = getImage(img.fileId);
          
          if (!cached || (!cached.localPreviewUrl && !cached.backendDisplayUrl) || 
              (cached.backendDisplayUrl && isImageExpired(img.fileId))) {
            imagesToLoad.push(img.fileId);
          }
        });
      });

      if (imagesToLoad.length === 0) {
        setLoadingCount(0);
        setErrorCount(0);
        return;
      }

      console.log(`🔄 Loading ${imagesToLoad.length} images for conversation`);
      setLoadingCount(imagesToLoad.length);
      setErrorCount(0);

      // Mark as loading
      imagesToLoad.forEach(fileId => setImageLoading(fileId, true));

      try {
        // Batch fetch with timeout
        const fetchResults = await imageService.fetchMultipleImageUrls(imagesToLoad, 15000);
        
        let successCount = 0;
        let failCount = 0;
        
        // Process results
        Object.entries(fetchResults).forEach(([fileId, result]) => {
          if (result.success && result.url) {
            updateImageUrls(fileId, result.url, result.expiresAt);
            successCount++;
          } else {
            setImageError(fileId, result.error || 'Failed to load');
            failCount++;
          }
        });

        setLoadingCount(0);
        setErrorCount(failCount);
        
        console.log(`✅ Conversation images loaded: ${successCount} success, ${failCount} failed`);
        
      } catch (error) {
        console.error('❌ Failed to load conversation images:', error);
        setLoadingCount(0);
        setErrorCount(imagesToLoad.length);
        
        imagesToLoad.forEach(fileId => setImageError(fileId, 'Network error'));
      }
    };

    loadAllImages();
  }, [messages.length, clearExpiredImages, getImage, isImageExpired, updateImageUrls, setImageLoading, setImageError]);

  return {
    loadingCount,
    errorCount,
    isLoading: loadingCount > 0,
    hasErrors: errorCount > 0,
  };
} 