// Image Management Store - Clean Architecture Application Layer
import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

export interface CachedImage {
  fileId: string;
  s3Key: string;
  filename: string;
  localPreviewUrl?: string; // blob URL from upload
  backendDisplayUrl?: string; // /api/v1/files/image/{fileId}
  isLoading: boolean;
  error?: string;
  cachedAt: number; // timestamp
  expiresAt: number; // timestamp
}

interface ImageStore {
  // State
  cachedImages: Record<string, CachedImage>; // fileId -> CachedImage
  
  // Actions
  addLocalImage: (fileId: string, s3Key: string, filename: string, localPreviewUrl: string) => void;
  updateImageUrls: (fileId: string, backendDisplayUrl: string, expiresAt?: number) => void;
  setImageLoading: (fileId: string, isLoading: boolean) => void;
  setImageError: (fileId: string, error: string) => void;
  getImage: (fileId: string) => CachedImage | null;
  isImageExpired: (fileId: string) => boolean;
  clearExpiredImages: () => void;
  removeImage: (fileId: string) => void;
  
  // Bulk operations
  addImagesFromUpload: (uploadFiles: Array<{ file_id: string; s3_key: string; preview?: string; file: File }>) => void;
  getImagesForStaging: (stagingFiles: Array<{ file_id: string; s3_key: string }>) => Array<{ fileId: string; filename: string; previewUrl: string }>;
}

const IMAGE_CACHE_DURATION = 24 * 60 * 60 * 1000; // 24 hours

export const useImageStore = create<ImageStore>()(
  persist(
    (set, get) => ({
      cachedImages: {},
      
      addLocalImage: (fileId, s3Key, filename, localPreviewUrl) => {
        const now = Date.now();
        set((state) => ({
          cachedImages: {
            ...state.cachedImages,
            [fileId]: {
              fileId,
              s3Key,
              filename,
              localPreviewUrl,
              isLoading: false,
              cachedAt: now,
              expiresAt: now + IMAGE_CACHE_DURATION,
            },
          },
        }));
      },
      
      updateImageUrls: (fileId, backendDisplayUrl, expiresAt) => {
        const now = Date.now();
        set((state) => ({
          cachedImages: {
            ...state.cachedImages,
            [fileId]: {
              ...state.cachedImages[fileId],
              backendDisplayUrl,
              isLoading: false,
              error: undefined,
              expiresAt: expiresAt || (now + IMAGE_CACHE_DURATION),
            },
          },
        }));
      },
      
      setImageLoading: (fileId, isLoading) => {
        set((state) => ({
          cachedImages: {
            ...state.cachedImages,
            [fileId]: {
              ...state.cachedImages[fileId],
              isLoading,
              error: isLoading ? undefined : state.cachedImages[fileId]?.error,
            },
          },
        }));
      },
      
      setImageError: (fileId, error) => {
        set((state) => ({
          cachedImages: {
            ...state.cachedImages,
            [fileId]: {
              ...state.cachedImages[fileId],
              isLoading: false,
              error,
            },
          },
        }));
      },
      
      getImage: (fileId) => {
        return get().cachedImages[fileId] || null;
      },
      
      isImageExpired: (fileId) => {
        const image = get().cachedImages[fileId];
        if (!image) return true;
        return Date.now() > image.expiresAt;
      },
      
      clearExpiredImages: () => {
        const now = Date.now();
        set((state) => {
          const newCachedImages = { ...state.cachedImages };
          Object.keys(newCachedImages).forEach((fileId) => {
            if (newCachedImages[fileId].expiresAt < now) {
              delete newCachedImages[fileId];
            }
          });
          return { cachedImages: newCachedImages };
        });
      },
      
      removeImage: (fileId) => {
        set((state) => {
          const newCachedImages = { ...state.cachedImages };
          delete newCachedImages[fileId];
          return { cachedImages: newCachedImages };
        });
      },
      
      addImagesFromUpload: (uploadFiles) => {
        const now = Date.now();
        set((state) => {
          const newCachedImages = { ...state.cachedImages };
          uploadFiles.forEach((file) => {
            if (file.file_id) {
              newCachedImages[file.file_id] = {
                fileId: file.file_id,
                s3Key: file.s3_key,
                filename: file.file.name,
                localPreviewUrl: file.preview,
                isLoading: false,
                cachedAt: now,
                expiresAt: now + IMAGE_CACHE_DURATION,
              };
            }
          });
          return { cachedImages: newCachedImages };
        });
      },
      
      getImagesForStaging: (stagingFiles) => {
        const state = get();
        return stagingFiles.map((staging) => {
          const cached = state.cachedImages[staging.file_id];
          return {
            fileId: staging.file_id,
            filename: cached?.filename || `image_${staging.file_id}`,
            previewUrl: cached?.localPreviewUrl || cached?.backendDisplayUrl || '',
          };
        }).filter(img => img.previewUrl); // Only return images with valid URLs
      },
    }),
    {
      name: 'image-cache-storage',
      storage: createJSONStorage(() => localStorage),
      // Only persist essential data, not blob URLs (they expire on browser refresh)
      partialize: (state) => ({
        cachedImages: Object.fromEntries(
          Object.entries(state.cachedImages).map(([id, img]) => [
            id,
            {
              ...img,
              localPreviewUrl: undefined, // Don't persist blob URLs
            },
          ])
        ),
      }),
    }
  )
); 