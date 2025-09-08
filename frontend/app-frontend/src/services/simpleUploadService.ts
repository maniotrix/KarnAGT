import { ENV, API_ENDPOINTS, buildApiUrl } from '../config/env';
import { authService } from './authService';
import type { UploadFile, StagingUploadResponse } from '../types/upload';

class SimpleUploadService {
  constructor() {
    // URL building now handled by centralized buildApiUrl function
  }

  /**
   * Get headers for authenticated requests
   * Uses CSRF token instead of Authorization headers (httpOnly cookies system)
   */
  private getAuthHeaders(includeCsrf: boolean = false): HeadersInit {
    const headers: HeadersInit = {};

    // Add CSRF token for mutating operations
    if (includeCsrf) {
      const csrfToken = authService.getCSRFToken();
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }
    }

    return headers;
  }

  /**
   * Generate frontend thumbnail for immediate preview
   */
  async generateThumbnail(file: File, maxSize: number = 150): Promise<string> {
    return new Promise((resolve, reject) => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      const img = new Image();

      img.onload = () => {
        const { width, height } = this.calculateThumbnailSize(img.width, img.height, maxSize);
        canvas.width = width;
        canvas.height = height;
        
        if (ctx) {
          ctx.drawImage(img, 0, 0, width, height);
          resolve(canvas.toDataURL('image/jpeg', 0.7));
        } else {
          reject(new Error('Canvas context failed'));
        }
      };

      img.onerror = () => reject(new Error('Image load failed'));
      img.src = URL.createObjectURL(file);
    });
  }

  private calculateThumbnailSize(originalWidth: number, originalHeight: number, maxSize: number) {
    const aspectRatio = originalWidth / originalHeight;
    let width = maxSize;
    let height = maxSize;

    if (aspectRatio > 1) {
      height = maxSize / aspectRatio;
    } else {
      width = maxSize * aspectRatio;
    }

    return { width: Math.round(width), height: Math.round(height) };
  }

  /**
   * Validate image file
   */
  validateImageFile(file: File): { valid: boolean; error?: string } {
    const maxSize = 20 * 1024 * 1024; // 20MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];

    if (!allowedTypes.includes(file.type)) {
      return { valid: false, error: 'Invalid file type. Only JPEG, PNG, GIF, and WebP are supported.' };
    }

    if (file.size > maxSize) {
      return { valid: false, error: 'File size too large. Maximum size is 20MB.' };
    }

    return { valid: true };
  }

  /**
   * Simple upload - just shows uploading/complete status
   */
  async uploadToStaging(
    files: UploadFile[],
    onStatusChange?: (fileId: string, status: 'uploading' | 'success' | 'error', data?: any) => void
  ): Promise<UploadFile[]> {
    
    console.log('🚀 [SimpleUploadService] Starting upload for files:', files.map(f => f.name));
    
    // Mark all files as uploading
    files.forEach(file => {
      console.log(`📤 [SimpleUploadService] Marking file ${file.name} as uploading`);
      onStatusChange?.(file.id, 'uploading');
    });

    const formData = new FormData();
    files.forEach(uploadFile => {
      formData.append('files', uploadFile.file);
      console.log(`📎 [SimpleUploadService] Added file to FormData: ${uploadFile.file.name} (${uploadFile.file.size} bytes)`);
    });
    formData.append('max_concurrent_uploads', '5');

    // Authentication now handled by httpOnly cookies + CSRF
    const csrfToken = authService.getCSRFToken();
    console.log('🔐 [SimpleUploadService] CSRF token:', csrfToken ? `${csrfToken.substring(0, 20)}...` : 'MISSING');

    try {
      const uploadUrl = buildApiUrl(API_ENDPOINTS.AI_FILES.STAGING_BULK_UPLOAD);
      console.log('🌐 [SimpleUploadService] Upload URL:', uploadUrl);
      
      // Simple fetch - no progress tracking
      const response = await fetch(uploadUrl, {
        method: 'POST',
        credentials: 'include', // Send httpOnly cookies
        headers: this.getAuthHeaders(true), // ✅ CSRF required for POST
        body: formData,
      });

      console.log('📡 [SimpleUploadService] Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ [SimpleUploadService] Upload failed:', response.status, response.statusText, errorText);
        throw new Error(`Upload failed: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const result: StagingUploadResponse = await response.json();
      console.log('✅ [SimpleUploadService] Server response:', result);

      // Update files with server response - individual status per file
      // Extract staged files from new backend structure (staging_files.images, staging_files.vectors, etc.)
      const allStagedFiles: Array<{
        file_id: string;
        s3_key: string;
        filename: string;
        content_type: string;
        file_size: number;
      }> = [];
      if (result.staging_files) {
        const stagingFiles = result.staging_files;
        if (stagingFiles.images) allStagedFiles.push(...stagingFiles.images);
        if (stagingFiles.vectors) allStagedFiles.push(...stagingFiles.vectors);
        if (stagingFiles.unknown) allStagedFiles.push(...stagingFiles.unknown);
      }

      const updatedFiles = files.map(uploadFile => {
        // Check if this specific file succeeded  
        const stagedFile = allStagedFiles.find(sf => sf.filename === uploadFile.file.name);
        const failedFile = result.failed_files.find(ff => ff.filename === uploadFile.file.name);

        if (stagedFile) {
          console.log(`✅ [SimpleUploadService] File ${uploadFile.file.name} uploaded successfully:`, stagedFile);
          const updated = {
            ...uploadFile,
            status: 'success' as const,
            progress: 100,
            file_id: stagedFile.file_id,
            s3_key: stagedFile.s3_key,
          };
          
          onStatusChange?.(uploadFile.id, 'success', stagedFile);
          return updated;
          
        } else if (failedFile) {
          console.error(`❌ [SimpleUploadService] File ${uploadFile.file.name} failed:`, failedFile.error);
          const updated = {
            ...uploadFile,
            status: 'error' as const,
            progress: 0,
            error: failedFile.error,
          };
          
          onStatusChange?.(uploadFile.id, 'error', { error: failedFile.error });
          return updated;
          
        } else {
          // File not found in response (shouldn't happen)
          console.warn(`⚠️ [SimpleUploadService] File ${uploadFile.file.name} not found in server response`);
          const updated = {
            ...uploadFile,
            status: 'error' as const,
            error: 'Server response missing file status',
          };
          
          onStatusChange?.(uploadFile.id, 'error', { error: 'Server response missing file status' });
          return updated;
        }
      });

      console.log('🎉 [SimpleUploadService] Upload completed. Updated files:', updatedFiles);
      return updatedFiles;

    } catch (error) {
      console.error('💥 [SimpleUploadService] Upload error:', error);
      
      // Mark all files as error
      const errorFiles = files.map(file => {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed';
        console.error(`❌ [SimpleUploadService] Marking file ${file.name} as error: ${errorMessage}`);
        
        const updated = {
          ...file,
          status: 'error' as const,
          progress: 0,
          error: errorMessage,
        };
        
        onStatusChange?.(file.id, 'error', { error: updated.error });
        return updated;
      });

      return errorFiles;
    }
  }

  /**
   * Get staging files dictionary from successful upload files
   * Returns the format expected by the chat API
   */
  getStagingFilesForChat(uploadFiles: UploadFile[]): Record<string, any> {
    const successfulFiles = uploadFiles.filter(file => file.status === 'success' && file.file_id && file.s3_key);
    
    if (successfulFiles.length === 0) {
      return {};
    }

    // Convert to the format expected by chat API
    const stagingFiles: Record<string, any> = {
      images: successfulFiles.map(file => ({
        file_id: file.file_id!,
        s3_key: file.s3_key!,
        filename: file.name,
        content_type: file.type,
        file_size: file.size
      })),
      vectors: [],
      unknown: []
    };

    console.log('📋 [SimpleUploadService] Generated staging files for chat:', stagingFiles);
    return stagingFiles;
  }

  /**
   * Discard staged files  
   */
  async discardStagedFiles(fileIds: string[]): Promise<void> {
    console.log('🗑️ [SimpleUploadService] Discarding files from server:', fileIds);
    
    // Authentication now handled by httpOnly cookies + CSRF
    const csrfToken = authService.getCSRFToken();
    console.log('🔐 [SimpleUploadService] CSRF token:', csrfToken ? `${csrfToken.substring(0, 20)}...` : 'MISSING');

    if (fileIds.length === 1) {
      const url = buildApiUrl(API_ENDPOINTS.AI_FILES.STAGING_DISCARD(fileIds[0]));
      console.log('🌐 [SimpleUploadService] Single discard URL:', url);
      
      const response = await fetch(url, {
        method: 'DELETE',
        credentials: 'include', // Send httpOnly cookies
        headers: {
          ...this.getAuthHeaders(true), // ✅ CSRF required for DELETE
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ [SimpleUploadService] Single discard failed:', response.status, response.statusText, errorText);
        throw new Error(`Discard failed: ${response.status} ${response.statusText} - ${errorText}`);
      }
      
      console.log('✅ [SimpleUploadService] Single file discarded successfully');
    } else {
      const url = buildApiUrl(API_ENDPOINTS.AI_FILES.STAGING_BULK_DISCARD);
      console.log('🌐 [SimpleUploadService] Bulk discard URL:', url);
      
      const response = await fetch(url, {
        method: 'DELETE',
        credentials: 'include', // Send httpOnly cookies
        headers: {
          ...this.getAuthHeaders(true), // ✅ CSRF required for DELETE
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_ids: fileIds }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ [SimpleUploadService] Bulk discard failed:', response.status, response.statusText, errorText);
        throw new Error(`Bulk discard failed: ${response.status} ${response.statusText} - ${errorText}`);
      }
      
      console.log('✅ [SimpleUploadService] Bulk files discarded successfully');
    }
  }
}

export const simpleUploadService = new SimpleUploadService(); 