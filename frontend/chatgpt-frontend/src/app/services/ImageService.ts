// Application Service: Image Service - Fetch images from backend with caching
import { ENV } from '../../config/env';

export interface ImageFetchResult {
  success: boolean;
  url?: string;
  error?: string;
  expiresAt?: number;
}

export class ImageService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  }

  /**
   * Fetch image display URL from backend with timeout
   */
  async fetchImageDisplayUrl(fileId: string, timeout: number = 10000): Promise<ImageFetchResult> {
    try {
      const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
      if (!token) {
        return { success: false, error: 'Authentication required' };
      }

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), timeout);

      const response = await fetch(`${this.baseUrl}/api/v1/files/images/${fileId}`, {
        method: 'HEAD', // Use HEAD to check if image exists without downloading
        headers: {
          'Authorization': `Bearer ${token}`,
        },
        signal: controller.signal,
      });

      clearTimeout(timeoutId);

      if (response.ok) {
        const displayUrl = `${this.baseUrl}/api/v1/files/images/${fileId}`;
        const expiresAt = Date.now() + (24 * 60 * 60 * 1000); // 24 hours
        
        return {
          success: true,
          url: displayUrl,
          expiresAt,
        };
      } else {
        return {
          success: false,
          error: `Backend returned ${response.status}: ${response.statusText}`,
        };
      }
    } catch (error) {
      if (error instanceof Error && error.name === 'AbortError') {
        return { success: false, error: 'Request timeout' };
      }
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error',
      };
    }
  }

  /**
   * Batch fetch multiple image URLs
   */
  async fetchMultipleImageUrls(fileIds: string[], timeout: number = 10000): Promise<Record<string, ImageFetchResult>> {
    const results: Record<string, ImageFetchResult> = {};
    
    // Use Promise.allSettled to handle individual failures
    const promises = fileIds.map(async (fileId) => {
      const result = await this.fetchImageDisplayUrl(fileId, timeout);
      return { fileId, result };
    });

    const settledResults = await Promise.allSettled(promises);
    
    settledResults.forEach((settled, index) => {
      const fileId = fileIds[index];
      if (settled.status === 'fulfilled') {
        results[fileId] = settled.value.result;
      } else {
        results[fileId] = {
          success: false,
          error: settled.reason instanceof Error ? settled.reason.message : 'Failed to fetch',
        };
      }
    });

    return results;
  }

  /**
   * Preload image to ensure it's actually accessible
   */
  async preloadImage(url: string, timeout: number = 5000): Promise<boolean> {
    return new Promise((resolve) => {
      const img = new Image();
      const timeoutId = setTimeout(() => {
        img.src = ''; // Cancel loading
        resolve(false);
      }, timeout);

      img.onload = () => {
        clearTimeout(timeoutId);
        resolve(true);
      };

      img.onerror = () => {
        clearTimeout(timeoutId);
        resolve(false);
      };

      img.src = url;
    });
  }
}

// Export singleton instance
export const imageService = new ImageService(); 