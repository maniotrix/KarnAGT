import { apiClient } from './api';
import type { UploadFile, StagingUploadResponse, UploadProgress, ImageDimensions } from '../types/upload';

class UploadService {
  private baseUrl: string;

  constructor() {
    this.baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  }

  /**
   * Generate a frontend thumbnail preview for immediate display
   */
  generateThumbnail(file: File, maxWidth: number = 150, maxHeight: number = 150): Promise<string> {
    return new Promise((resolve, reject) => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();

      img.onload = () => {
        // Calculate thumbnail dimensions while maintaining aspect ratio
        const { width: thumbWidth, height: thumbHeight } = this.calculateThumbnailSize(
          img.width,
          img.height,
          maxWidth,
          maxHeight
        );

        canvas.width = thumbWidth;
        canvas.height = thumbHeight;

        if (ctx) {
          ctx.drawImage(img, 0, 0, thumbWidth, thumbHeight);
          resolve(canvas.toDataURL('image/jpeg', 0.7));
        } else {
          reject(new Error('Failed to get canvas context'));
        }
      };

      img.onerror = () => reject(new Error('Failed to load image'));
      img.src = URL.createObjectURL(file);
    });
  }

  /**
   * Calculate thumbnail size maintaining aspect ratio
   */
  private calculateThumbnailSize(
    originalWidth: number,
    originalHeight: number,
    maxWidth: number,
    maxHeight: number
  ): ImageDimensions {
    const aspectRatio = originalWidth / originalHeight;

    let width = maxWidth;
    let height = maxHeight;

    if (aspectRatio > 1) {
      // Landscape
      height = maxWidth / aspectRatio;
    } else {
      // Portrait or square
      width = maxHeight * aspectRatio;
    }

    return {
      width: Math.round(width),
      height: Math.round(height),
    };
  }

  /**
   * Validate image file before upload
   */
  validateImageFile(file: File): { valid: boolean; error?: string } {
    const maxSize = 20 * 1024 * 1024; // 20MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

    if (!allowedTypes.includes(file.type)) {
      return {
        valid: false,
        error: 'Invalid file type. Only JPEG, PNG, GIF, and WebP are supported.',
      };
    }

    if (file.size > maxSize) {
      return {
        valid: false,
        error: 'File size too large. Maximum size is 20MB.',
      };
    }

    return { valid: true };
  }

  /**
   * Upload files to staging area with progress tracking
   */
  async uploadToStaging(
    files: UploadFile[],
    onProgress?: (fileId: string, progress: UploadProgress) => void,
    onFileComplete?: (fileId: string, result: UploadFile) => void
  ): Promise<UploadFile[]> {
    const formData = new FormData();
    
    // Add files to form data
    files.forEach((uploadFile) => {
      formData.append('files', uploadFile.file);
    });
    
    // Add additional parameters
    formData.append('max_concurrent_uploads', '5');

    try {
      const xhr = new XMLHttpRequest();

      // Set up progress tracking
      if (onProgress) {
        xhr.upload.addEventListener('progress', (event) => {
          if (event.lengthComputable) {
            const progress = {
              loaded: event.loaded,
              total: event.total,
              percentage: Math.round((event.loaded / event.total) * 100),
            };

            // Update progress for all files (bulk upload)
            files.forEach((file) => {
              onProgress(file.id, progress);
            });
          }
        });
      }

      const response = await new Promise<StagingUploadResponse>((resolve, reject) => {
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try {
              const result = JSON.parse(xhr.responseText);
              resolve(result);
            } catch (e) {
              reject(new Error('Invalid JSON response'));
            }
          } else {
            reject(new Error(`Upload failed: ${xhr.status} ${xhr.statusText}`));
          }
        };

        xhr.onerror = () => reject(new Error('Network error'));
        
        xhr.open('POST', `${this.baseUrl}/api/v1/ai-files/staging/bulk-upload`);
        
        // Get auth token from API client
        const authHeader = (apiClient as any).headers?.Authorization;
        if (authHeader) {
          xhr.setRequestHeader('Authorization', authHeader);
        }
        
        xhr.send(formData);
      });

      // Update upload files with backend response
      const updatedFiles: UploadFile[] = files.map((uploadFile) => {
        const stagedFile = response.staged_files.find(
          (sf) => sf.filename === uploadFile.file.name
        );
        
        const failedFile = response.failed_files.find(
          (ff) => ff.filename === uploadFile.file.name
        );

        if (stagedFile) {
          const updated = {
            ...uploadFile,
            status: 'success' as const,
            progress: 100,
            file_id: stagedFile.file_id,
            s3_key: stagedFile.s3_key,
            urls: {
              display: `${this.baseUrl}/api/v1/files/image/${stagedFile.file_id}`,
              api: `${this.baseUrl}/api/v1/files/image/${stagedFile.file_id}`,
            },
          };

          if (onFileComplete) {
            onFileComplete(uploadFile.id, updated);
          }

          return updated;
        } else if (failedFile) {
          const updated = {
            ...uploadFile,
            status: 'error' as const,
            progress: 0,
            error: failedFile.error,
          };

          if (onFileComplete) {
            onFileComplete(uploadFile.id, updated);
          }

          return updated;
        }

        return uploadFile;
      });

      return updatedFiles;
    } catch (error) {
      // Update all files to error state
      const errorFiles = files.map((file) => ({
        ...file,
        status: 'error' as const,
        progress: 0,
        error: error instanceof Error ? error.message : 'Upload failed',
      }));

      if (onFileComplete) {
        errorFiles.forEach((file) => {
          onFileComplete(file.id, file);
        });
      }

      return errorFiles;
    }
  }

  /**
   * Discard staged files
   */
  async discardStagedFiles(fileIds: string[]): Promise<void> {
    if (fileIds.length === 1) {
      // Single file discard
      await apiClient.request(`/api/v1/ai-files/staging/discard/${fileIds[0]}`, {
        method: 'DELETE',
      });
    } else {
      // Bulk discard
      await apiClient.request('/api/v1/ai-files/staging/bulk-discard', {
        method: 'DELETE',
        body: JSON.stringify({ file_ids: fileIds }),
      });
    }
  }
}

export const uploadService = new UploadService(); 