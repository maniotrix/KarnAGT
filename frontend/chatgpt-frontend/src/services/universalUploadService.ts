import { apiClient } from './api';
import { ENV, API_ENDPOINTS, buildApiUrl } from '../config/env';
import type { UploadFile, StagingUploadResponse } from '../types/upload';

export type FileCategory = 'image' | 'document' | 'unknown';

export interface FileTypeInfo {
  category: FileCategory;
  displayName: string;
  icon: string;
}

class UniversalUploadService {
  constructor() {
    // URL building handled by centralized buildApiUrl function
  }

  /**
   * Categorize file based on type
   */
  categorizeFile(file: File): FileCategory {
    const imageTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'];
    const documentTypes = [
      // PDF documents
      'application/pdf',
      // Word documents  
      'application/msword',                                                                    // .doc
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',             // .docx
      // Excel spreadsheets
      'application/vnd.ms-excel',                                                             // .xls
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',                   // .xlsx
      // PowerPoint presentations
      'application/vnd.ms-powerpoint',                                                        // .ppt
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',           // .pptx
      // Text files
      'text/plain',                                                                           // .txt
      'text/csv',                                                                             // .csv
      'text/tab-separated-values',                                                            // .tsv
      'text/markdown',                                                                        // .md
      // Markup files
      'application/xml',                                                                      // .xml
      'text/xml',                                                                             // .xml
      'text/html',                                                                            // .html
      // JSON files
      'application/json',                                                                     // .json
      // OpenDocument formats
      'application/vnd.oasis.opendocument.text',                                             // .odt
      // Org mode and reStructuredText
      'text/x-org',                                                                          // .org
      'text/x-rst',                                                                          // .rst
      // Email formats
      'application/vnd.ms-outlook',                                                          // .msg
      'message/rfc822',                                                                      // .eml
      'application/mbox',                                                                    // .mbox
      // Jupyter notebooks
      'application/x-ipynb+json',                                                            // .ipynb
      // Korean word processor
      'application/x-hwp',                                                                   // .hwp
      // Rich text and other formats
      'application/rtf',                                                                      // .rtf
      'application/epub+zip'                                                                  // .epub
    ];

    if (imageTypes.includes(file.type)) {
      return 'image';
    } else if (documentTypes.includes(file.type)) {
      return 'document';
    } else {
      return 'unknown';
    }
  }

  /**
   * Get file type information
   */
  getFileTypeInfo(file: File): FileTypeInfo {
    const category = this.categorizeFile(file);
    
    switch (category) {
      case 'image':
        return {
          category: 'image',
          displayName: 'Image',
          icon: '🖼️'
        };
      case 'document':
        return {
          category: 'document',
          displayName: 'Document',
          icon: '📄'
        };
      default:
        return {
          category: 'unknown',
          displayName: 'Unknown',
          icon: '❓'
        };
    }
  }

  /**
   * Generate thumbnail for images
   */
  async generateThumbnail(file: File, maxSize: number = 150): Promise<string> {
    // Only generate thumbnails for images
    if (this.categorizeFile(file) !== 'image') {
      throw new Error('Thumbnails only supported for images');
    }

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
   * Validate file based on type
   */
  validateFile(file: File): { valid: boolean; error?: string } {
    const category = this.categorizeFile(file);
    
    switch (category) {
      case 'image':
        return this.validateImageFile(file);
      case 'document':
        return this.validateDocumentFile(file);
      default:
        return { valid: false, error: 'Unsupported file type' };
    }
  }

  /**
   * Validate image file
   */
  private validateImageFile(file: File): { valid: boolean; error?: string } {
    const maxSize = 20 * 1024 * 1024; // 20MB
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml'];

    if (!allowedTypes.includes(file.type)) {
      return { valid: false, error: 'Invalid image type. Only JPEG, PNG, GIF, WebP, and SVG are supported.' };
    }

    if (file.size > maxSize) {
      return { valid: false, error: 'Image size too large. Maximum size is 20MB.' };
    }

    return { valid: true };
  }

  /**
   * Validate document file
   */
  private validateDocumentFile(file: File): { valid: boolean; error?: string } {
    const maxSize = 50 * 1024 * 1024; // 50MB for documents
    const allowedTypes = [
      // PDF documents
      'application/pdf',
      // Word documents  
      'application/msword',                                                                    // .doc
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',             // .docx
      // Excel spreadsheets
      'application/vnd.ms-excel',                                                             // .xls
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',                   // .xlsx
      // PowerPoint presentations
      'application/vnd.ms-powerpoint',                                                        // .ppt
      'application/vnd.openxmlformats-officedocument.presentationml.presentation',           // .pptx
      // Text files
      'text/plain',                                                                           // .txt
      'text/csv',                                                                             // .csv
      'text/tab-separated-values',                                                            // .tsv
      'text/markdown',                                                                        // .md
      // Markup files
      'application/xml',                                                                      // .xml
      'text/xml',                                                                             // .xml
      'text/html',                                                                            // .html
      // JSON files
      'application/json',                                                                     // .json
      // OpenDocument formats
      'application/vnd.oasis.opendocument.text',                                             // .odt
      // Org mode and reStructuredText
      'text/x-org',                                                                          // .org
      'text/x-rst',                                                                          // .rst
      // Email formats
      'application/vnd.ms-outlook',                                                          // .msg
      'message/rfc822',                                                                      // .eml
      'application/mbox',                                                                    // .mbox
      // Jupyter notebooks
      'application/x-ipynb+json',                                                            // .ipynb
      // Korean word processor
      'application/x-hwp',                                                                   // .hwp
      // Rich text and other formats
      'application/rtf',                                                                      // .rtf
      'application/epub+zip'                                                                  // .epub
    ];

    if (!allowedTypes.includes(file.type)) {
      return { 
        valid: false, 
        error: 'Invalid document type. Supported formats: PDF, Word (.doc/.docx), Excel (.xls/.xlsx), PowerPoint (.ppt/.pptx), text files (.txt/.csv/.tsv/.md), markup files (.html/.xml), JSON (.json), OpenDocument (.odt), org-mode (.org), reStructuredText (.rst), email files (.eml/.msg/.mbox), Jupyter notebooks (.ipynb), Korean HWP (.hwp), RTF, and EPUB.' 
      };
    }

    if (file.size > maxSize) {
      return { valid: false, error: 'Document size too large. Maximum size is 50MB.' };
    }

    return { valid: true };
  }

  /**
   * Upload files to staging with proper categorization
   */
  async uploadToStaging(
    files: UploadFile[],
    onStatusChange?: (fileId: string, status: 'uploading' | 'success' | 'error', data?: any) => void
  ): Promise<UploadFile[]> {
    
    console.log('🚀 [UniversalUploadService] Starting upload for files:', files.map(f => f.name));
    
    // Mark all files as uploading
    files.forEach(file => {
      console.log(`📤 [UniversalUploadService] Marking file ${file.name} as uploading`);
      onStatusChange?.(file.id, 'uploading');
    });

    const formData = new FormData();
    files.forEach(uploadFile => {
      formData.append('files', uploadFile.file);
      console.log(`📎 [UniversalUploadService] Added file to FormData: ${uploadFile.file.name} (${uploadFile.file.size} bytes, ${uploadFile.file.type})`);
    });
    formData.append('max_concurrent_uploads', '5');

    // Get authentication token
    const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    const authHeader = token ? `Bearer ${token}` : '';
    console.log('🔐 [UniversalUploadService] Auth token:', token ? `${token.substring(0, 20)}...` : 'MISSING');

    try {
      const uploadUrl = buildApiUrl(API_ENDPOINTS.AI_FILES.STAGING_BULK_UPLOAD);
      console.log('🌐 [UniversalUploadService] Upload URL:', uploadUrl);
      
      const response = await fetch(uploadUrl, {
        method: 'POST',
        headers: {
          'Authorization': authHeader,
        },
        body: formData,
      });

      console.log('📡 [UniversalUploadService] Response status:', response.status, response.statusText);

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ [UniversalUploadService] Upload failed:', response.status, response.statusText, errorText);
        throw new Error(`Upload failed: ${response.status} ${response.statusText} - ${errorText}`);
      }

      const result: StagingUploadResponse = await response.json();
      console.log('✅ [UniversalUploadService] Server response:', result);

      // Extract all staged files from organized backend structure
      const allStagedFiles: Array<{
        file_id: string;
        s3_key: string;
        filename: string;
        content_type: string;
        file_size: number;
      }> = [];

      if (result.staging_files) {
        const stagingFiles = result.staging_files;
        // Images go to images category (img_* IDs)
        if (stagingFiles.images) allStagedFiles.push(...stagingFiles.images);
        // Documents go to vectors category (file_* IDs)
        if (stagingFiles.vectors) allStagedFiles.push(...stagingFiles.vectors);
        // Unknown files
        if (stagingFiles.unknown) allStagedFiles.push(...stagingFiles.unknown);
      }

      // Update files with server response
      const updatedFiles = files.map(uploadFile => {
        const stagedFile = allStagedFiles.find(sf => sf.filename === uploadFile.file.name);
        const failedFile = result.failed_files?.find(ff => ff.filename === uploadFile.file.name);

        if (stagedFile) {
          console.log(`✅ [UniversalUploadService] File ${uploadFile.file.name} uploaded successfully:`, stagedFile);
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
          console.error(`❌ [UniversalUploadService] File ${uploadFile.file.name} failed:`, failedFile.error);
          const updated = {
            ...uploadFile,
            status: 'error' as const,
            progress: 0,
            error: failedFile.error,
          };
          
          onStatusChange?.(uploadFile.id, 'error', { error: failedFile.error });
          return updated;
          
        } else {
          console.warn(`⚠️ [UniversalUploadService] File ${uploadFile.file.name} not found in server response`);
          const updated = {
            ...uploadFile,
            status: 'error' as const,
            error: 'Server response missing file status',
          };
          
          onStatusChange?.(uploadFile.id, 'error', { error: 'Server response missing file status' });
          return updated;
        }
      });

      console.log('🎉 [UniversalUploadService] Upload completed. Updated files:', updatedFiles);
      return updatedFiles;

    } catch (error) {
      console.error('💥 [UniversalUploadService] Upload error:', error);
      
      // Mark all files as error
      const errorFiles = files.map(file => {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed';
        console.error(`❌ [UniversalUploadService] Marking file ${file.name} as error: ${errorMessage}`);
        
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
   * Returns the format expected by the chat API with proper categorization
   */
  getStagingFilesForChat(uploadFiles: UploadFile[]): Record<string, any> {
    const successfulFiles = uploadFiles.filter(file => file.status === 'success' && file.file_id && file.s3_key);
    
    if (successfulFiles.length === 0) {
      return {};
    }

    // Properly categorize files based on their original type
    const stagingFiles: Record<string, any> = {
      images: [],
      vectors: [],
      unknown: []
    };

    successfulFiles.forEach(file => {
      const category = this.categorizeFile(file.file);
      const fileData = {
        file_id: file.file_id!,
        s3_key: file.s3_key!,
        filename: file.name,
        content_type: file.type,
        file_size: file.size
      };

      if (category === 'image') {
        stagingFiles.images.push(fileData);
      } else if (category === 'document') {
        stagingFiles.vectors.push(fileData);
      } else {
        stagingFiles.unknown.push(fileData);
      }
    });

    console.log('📋 [UniversalUploadService] Generated staging files for chat:', stagingFiles);
    return stagingFiles;
  }

  /**
   * Discard staged files (supports both img_* and file_* IDs)
   */
  async discardStagedFiles(fileIds: string[]): Promise<void> {
    console.log('🗑️ [UniversalUploadService] Discarding files from server:', fileIds);
    
    const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    const authHeader = token ? `Bearer ${token}` : '';
    console.log('🔐 [UniversalUploadService] Discard auth header:', authHeader ? `${authHeader.substring(0, 30)}...` : 'MISSING');

    if (fileIds.length === 1) {
      const url = buildApiUrl(API_ENDPOINTS.AI_FILES.STAGING_DISCARD(fileIds[0]));
      console.log('🌐 [UniversalUploadService] Single discard URL:', url);
      
      const response = await fetch(url, {
        method: 'DELETE',
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ [UniversalUploadService] Single discard failed:', response.status, response.statusText, errorText);
        throw new Error(`Discard failed: ${response.status} ${response.statusText} - ${errorText}`);
      }
      
      console.log('✅ [UniversalUploadService] Single file discarded successfully');
    } else {
      const url = buildApiUrl(API_ENDPOINTS.AI_FILES.STAGING_BULK_DISCARD);
      console.log('🌐 [UniversalUploadService] Bulk discard URL:', url);
      
      const response = await fetch(url, {
        method: 'DELETE',
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ file_ids: fileIds }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('❌ [UniversalUploadService] Bulk discard failed:', response.status, response.statusText, errorText);
        throw new Error(`Bulk discard failed: ${response.status} ${response.statusText} - ${errorText}`);
      }
      
      console.log('✅ [UniversalUploadService] Bulk files discarded successfully');
    }
  }
}

export const universalUploadService = new UniversalUploadService(); 