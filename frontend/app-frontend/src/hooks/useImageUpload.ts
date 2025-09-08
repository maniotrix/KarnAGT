import { useState, useCallback, useRef, useEffect } from 'react';
import { simpleUploadService } from '../services/simpleUploadService';
import type { UploadFile } from '../types/upload';

export interface UseImageUploadOptions {
  maxFiles?: number;
  autoUpload?: boolean;
  onUploadComplete?: (files: UploadFile[]) => void;
  onUploadError?: (error: string) => void;
}

export interface UseImageUploadReturn {
  // State
  files: UploadFile[];
  isUploading: boolean;
  
  // Actions
  addFiles: (newFiles: File[]) => Promise<void>;
  removeFile: (fileId: string) => void;
  uploadFiles: () => Promise<void>;
  clearFiles: () => void;
  discardStagedFiles: () => Promise<void>;
  
  // Utilities
  getSuccessfulUploads: () => UploadFile[];
  getFailedUploads: () => UploadFile[];
  getFileIds: () => string[];
}

export const useImageUpload = (options: UseImageUploadOptions = {}): UseImageUploadReturn => {
  const {
    maxFiles = 10,
    autoUpload = true,
    onUploadComplete,
    onUploadError,
  } = options;

  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const fileIdCounter = useRef(0);

  const generateFileId = useCallback(() => {
    fileIdCounter.current += 1;
    return `file_${Date.now()}_${fileIdCounter.current}`;
  }, []);

  const addFiles = useCallback(async (newFiles: File[]) => {
    console.log('📁 [useImageUpload] Adding files:', newFiles.map(f => f.name));
    
    // Validate file count
    if (files.length + newFiles.length > maxFiles) {
      console.warn(`⚠️ [useImageUpload] Too many files: ${files.length + newFiles.length} > ${maxFiles}`);
      onUploadError?.(`Maximum ${maxFiles} files allowed`);
      return;
    }

    const validFiles: UploadFile[] = [];
    
    for (const file of newFiles) {
      console.log(`🔍 [useImageUpload] Processing file: ${file.name} (${file.size} bytes, ${file.type})`);
      
      // Validate file
      const validation = simpleUploadService.validateImageFile(file);
      if (!validation.valid) {
        console.error(`❌ [useImageUpload] File validation failed for ${file.name}: ${validation.error}`);
        onUploadError?.(validation.error || 'Invalid file');
        continue;
      }

      // Generate preview thumbnail
      try {
        console.log(`🖼️ [useImageUpload] Generating thumbnail for ${file.name}`);
        const preview = await simpleUploadService.generateThumbnail(file);
        
        const uploadFile: UploadFile = {
          id: generateFileId(),
          file,
          name: file.name,
          size: file.size,
          type: file.type,
          preview,
          status: 'pending',
          progress: 0,
        };
        
        validFiles.push(uploadFile);
      } catch (error) {
        console.warn('Failed to generate thumbnail for', file.name, error);
        
        const uploadFile: UploadFile = {
          id: generateFileId(),
          file,
          name: file.name,
          size: file.size,
          type: file.type,
          status: 'pending',
          progress: 0,
        };
        
        validFiles.push(uploadFile);
      }
    }

    if (validFiles.length === 0) {
      return;
    }

    setFiles(prev => [...prev, ...validFiles]);

    console.log(`✅ [useImageUpload] Added ${validFiles.length} valid files`);
    
    // Auto-upload will be triggered by useEffect when files change
    // No need to call upload here - let React handle the state update cycle
  }, [files.length, maxFiles, onUploadError, generateFileId]);

  const removeFile = useCallback(async (fileId: string) => {
    console.log('🗑️ [useImageUpload] removeFile called with fileId:', fileId);
    console.log('🗑️ [useImageUpload] Current files before removal:', files.map(f => ({ id: f.id, name: f.name })));
    
    // Find the file to check if it needs to be discarded from server
    const fileToRemove = files.find(f => f.id === fileId);
    if (fileToRemove && fileToRemove.status === 'success' && fileToRemove.file_id) {
      console.log('🗑️ [useImageUpload] File was uploaded, discarding from server:', fileToRemove.file_id);
      try {
        await simpleUploadService.discardStagedFiles([fileToRemove.file_id]);
        console.log('✅ [useImageUpload] File discarded from server successfully');
      } catch (error) {
        console.error('❌ [useImageUpload] Failed to discard file from server:', error);
        onUploadError?.('Failed to remove file from server');
      }
    }
    
    setFiles(prev => {
      const filtered = prev.filter(f => f.id !== fileId);
      console.log('🗑️ [useImageUpload] Files after removal:', filtered.map(f => ({ id: f.id, name: f.name })));
      return filtered;
    });
  }, [files, onUploadError]);

  const uploadFiles = useCallback(async () => {
    const pendingFiles = files.filter(f => f.status === 'pending');
    
    console.log(`📤 [useImageUpload] Starting upload for ${pendingFiles.length} pending files`);
    
    if (pendingFiles.length === 0) {
      console.log('ℹ️ [useImageUpload] No pending files to upload');
      return;
    }

    setIsUploading(true);

    try {
      // Update files to uploading state
      setFiles(prev => prev.map(f => 
        pendingFiles.some(pf => pf.id === f.id)
          ? { ...f, status: 'uploading' }
          : f
      ));

      // Upload all files at once with simple status tracking
      const uploadResults = await simpleUploadService.uploadToStaging(
        pendingFiles,
        (fileId: string, status: 'uploading' | 'success' | 'error', data?: any) => {
          setFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { 
                  ...f, 
                  status,
                  progress: status === 'success' ? 100 : status === 'error' ? 0 : f.progress,
                  file_id: data?.file_id || f.file_id,
                  error: data?.error || f.error
                }
              : f
          ));
        }
      );

      const successful = uploadResults.filter(f => f.status === 'success');
      
      if (successful.length > 0) {
        onUploadComplete?.(successful);
      }

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed';
      onUploadError?.(errorMessage);
      
      // Update all pending files to error state
      setFiles(prev => prev.map(f => 
        pendingFiles.some(pf => pf.id === f.id)
          ? { ...f, status: 'error', error: errorMessage, progress: 0 }
          : f
      ));
    } finally {
      setIsUploading(false);
    }
  }, [files, onUploadComplete, onUploadError]);

  // Auto-upload effect - triggers when files change and autoUpload is enabled
  useEffect(() => {
    if (autoUpload && !isUploading) {
      const pendingFiles = files.filter(f => f.status === 'pending');
      if (pendingFiles.length > 0) {
        console.log('🚀 [useImageUpload] Auto-upload triggered by useEffect for', pendingFiles.length, 'pending files');
        uploadFiles();
      }
    }
  }, [files, autoUpload, isUploading, uploadFiles]);

  const clearFiles = useCallback(() => {
    setFiles([]);
  }, []);

  const discardStagedFiles = useCallback(async () => {
    const stagedFiles = files.filter(f => f.status === 'success' && f.file_id);
    
    if (stagedFiles.length === 0) {
      return;
    }

    try {
      const fileIds = stagedFiles.map(f => f.file_id!);
      await simpleUploadService.discardStagedFiles(fileIds);
      
      // Remove discarded files from state
      setFiles(prev => prev.filter(f => !stagedFiles.some(sf => sf.id === f.id)));
    } catch (error) {
      onUploadError?.(
        error instanceof Error ? error.message : 'Failed to discard files'
      );
    }
  }, [files, onUploadError]);

  const getSuccessfulUploads = useCallback(() => {
    return files.filter(f => f.status === 'success');
  }, [files]);

  const getFailedUploads = useCallback(() => {
    return files.filter(f => f.status === 'error');
  }, [files]);

  const getFileIds = useCallback(() => {
    return files.filter(f => f.file_id).map(f => f.file_id!);
  }, [files]);

  return {
    // State
    files,
    isUploading,
    
    // Actions
    addFiles,
    removeFile,
    uploadFiles,
    clearFiles,
    discardStagedFiles,
    
    // Utilities
    getSuccessfulUploads,
    getFailedUploads,
    getFileIds,
  };
}; 