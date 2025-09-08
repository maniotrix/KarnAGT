import { useState, useCallback, useRef, useEffect } from 'react';
import { universalUploadService } from '../services/universalUploadService';
import type { UploadFile } from '../types/upload';

export interface UseUniversalFileUploadOptions {
  maxFiles?: number;
  autoUpload?: boolean;
  onUploadComplete?: (files: UploadFile[]) => void;
  onUploadError?: (error: string) => void;
}

export interface UseUniversalFileUploadReturn {
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
  getFilesByCategory: () => { images: UploadFile[]; documents: UploadFile[]; unknown: UploadFile[] };
}

export const useUniversalFileUpload = (options: UseUniversalFileUploadOptions = {}): UseUniversalFileUploadReturn => {
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
    console.log('📁 [useUniversalFileUpload] Adding files:', newFiles.map(f => f.name));
    
    // Validate file count
    if (files.length + newFiles.length > maxFiles) {
      console.warn(`⚠️ [useUniversalFileUpload] Too many files: ${files.length + newFiles.length} > ${maxFiles}`);
      onUploadError?.(`Maximum ${maxFiles} files allowed`);
      return;
    }

    const validFiles: UploadFile[] = [];
    
    for (const file of newFiles) {
      console.log(`🔍 [useUniversalFileUpload] Processing file: ${file.name} (${file.size} bytes, ${file.type})`);
      
      // Validate file based on type
      const validation = universalUploadService.validateFile(file);
      if (!validation.valid) {
        console.error(`❌ [useUniversalFileUpload] File validation failed for ${file.name}: ${validation.error}`);
        onUploadError?.(validation.error || 'Invalid file');
        continue;
      }

      // Get file type info
      const fileTypeInfo = universalUploadService.getFileTypeInfo(file);
      console.log(`📋 [useUniversalFileUpload] File type: ${fileTypeInfo.displayName} (${fileTypeInfo.category})`);

      // Generate preview thumbnail for images only
      let preview: string | undefined;
      try {
        if (fileTypeInfo.category === 'image') {
          console.log(`🖼️ [useUniversalFileUpload] Generating thumbnail for ${file.name}`);
          preview = await universalUploadService.generateThumbnail(file);
        }
      } catch (error) {
        console.warn('Failed to generate thumbnail for', file.name, error);
      }
      
      const uploadFile: UploadFile = {
        id: generateFileId(),
        file,
        name: file.name,
        size: file.size,
        type: file.type,
        preview,
        status: 'pending',
        progress: 0,
        fileCategory: fileTypeInfo.category,
        fileTypeInfo,
      };
      
      validFiles.push(uploadFile);
    }

    if (validFiles.length === 0) {
      return;
    }

    setFiles(prev => [...prev, ...validFiles]);

    console.log(`✅ [useUniversalFileUpload] Added ${validFiles.length} valid files`);
    
    // Auto-upload will be triggered by useEffect when files change
  }, [files.length, maxFiles, onUploadError, generateFileId]);

  const removeFile = useCallback(async (fileId: string) => {
    console.log('🗑️ [useUniversalFileUpload] removeFile called with fileId:', fileId);
    console.log('🗑️ [useUniversalFileUpload] Current files before removal:', files.map(f => ({ id: f.id, name: f.name })));
    
    // Find the file to check if it needs to be discarded from server
    const fileToRemove = files.find(f => f.id === fileId);
    if (fileToRemove && fileToRemove.status === 'success' && fileToRemove.file_id) {
      console.log('🗑️ [useUniversalFileUpload] File was uploaded, discarding from server:', fileToRemove.file_id);
      try {
        await universalUploadService.discardStagedFiles([fileToRemove.file_id]);
        console.log('✅ [useUniversalFileUpload] File discarded from server successfully');
      } catch (error) {
        console.error('❌ [useUniversalFileUpload] Failed to discard file from server:', error);
        onUploadError?.('Failed to remove file from server');
      }
    }
    
    setFiles(prev => {
      const filtered = prev.filter(f => f.id !== fileId);
      console.log('🗑️ [useUniversalFileUpload] Files after removal:', filtered.map(f => ({ id: f.id, name: f.name })));
      return filtered;
    });
  }, [files, onUploadError]);

  const uploadFiles = useCallback(async () => {
    const pendingFiles = files.filter(f => f.status === 'pending');
    
    console.log(`📤 [useUniversalFileUpload] Starting upload for ${pendingFiles.length} pending files`);
    
    if (pendingFiles.length === 0) {
      console.log('ℹ️ [useUniversalFileUpload] No pending files to upload');
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

      // Upload all files at once with status tracking
      const uploadResults = await universalUploadService.uploadToStaging(
        pendingFiles,
        (fileId: string, status: 'uploading' | 'success' | 'error', data?: any) => {
          setFiles(prev => prev.map(f => 
            f.id === fileId 
              ? { 
                  ...f, 
                  status,
                  progress: status === 'success' ? 100 : status === 'error' ? 0 : f.progress,
                  file_id: data?.file_id || f.file_id,
                  s3_key: data?.s3_key || f.s3_key,
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
        console.log('🚀 [useUniversalFileUpload] Auto-upload triggered by useEffect for', pendingFiles.length, 'pending files');
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
      await universalUploadService.discardStagedFiles(fileIds);
      
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

  const getFilesByCategory = useCallback(() => {
    const images = files.filter(f => f.fileCategory === 'image');
    const documents = files.filter(f => f.fileCategory === 'document');
    const unknown = files.filter(f => f.fileCategory === 'unknown');
    
    return { images, documents, unknown };
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
    getFilesByCategory,
  };
}; 