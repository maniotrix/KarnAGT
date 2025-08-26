import React, { useRef, useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { 
  FileIcon, 
  X, 
  Upload, 
  CheckCircle, 
  AlertCircle, 
  Loader2,
  Trash2,
  Plus,
  Image as ImageIcon,
  FileText,
  File
} from 'lucide-react';
import { useUniversalFileUpload } from '../../hooks/useUniversalFileUpload';
import type { UploadFile } from '../../types/upload';
import { ENV } from '../../config/env';
import { authService } from '../../services/authService';

interface UniversalFileUploadProps {
  onFilesSelected?: (files: UploadFile[]) => void;
  onUploadComplete?: (files: UploadFile[]) => void;
  onError?: (error: string) => void;
  maxFiles?: number;
  disabled?: boolean;
  acceptedTypes?: 'all' | 'images' | 'documents';
}

export interface UniversalFileUploadRef {
  getSuccessfulFiles: () => UploadFile[];
  getFileCount: () => number;
  clearFiles: () => void;
  getFilesByCategory: () => { images: UploadFile[]; documents: UploadFile[]; unknown: UploadFile[] };
}

export const UniversalFileUpload = forwardRef<UniversalFileUploadRef, UniversalFileUploadProps>(({
  onFilesSelected,
  onUploadComplete,
  onError,
  maxFiles = 10,
  disabled = false,
  acceptedTypes = 'all',
}, ref) => {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const {
    files,
    isUploading,
    addFiles,
    removeFile,
    clearFiles,
    discardStagedFiles,
    getFilesByCategory,
  } = useUniversalFileUpload({
    maxFiles,
    autoUpload: true,
    onUploadComplete: (successfulFiles) => {
      onUploadComplete?.(successfulFiles);
      onFilesSelected?.(files);
    },
    onUploadError: onError,
  });

  // Debug authentication status
  useEffect(() => {
    const isAuth = authService.isAuthenticated();
    const csrfToken = authService.getCSRFToken();
    console.log('🔐 [UniversalFileUpload] Auth status check:');
    console.log('   - Authenticated (has CSRF cookie):', isAuth);
    console.log('   - CSRF token preview:', csrfToken ? `${csrfToken.substring(0, 20)}...` : 'NONE');
    console.log('   - ℹ️ Note: Auth via httpOnly cookies, user profile fetched from API & cached in TanStack Query');
  }, []);

  // Expose methods to parent component
  useImperativeHandle(ref, () => ({
    getSuccessfulFiles: () => files.filter(f => f.status === 'success'),
    getFileCount: () => files.filter(f => f.status === 'success').length,
    clearFiles: () => clearFiles(),
    getFilesByCategory: () => getFilesByCategory(),
  }), [files, clearFiles, getFilesByCategory]);

  // Notify parent when files change
  useEffect(() => {
    const successfulCount = files.filter(f => f.status === 'success').length;
    console.log('📁 [UniversalFileUpload] Notifying parent of file changes. Successful files:', successfulCount);
    onFilesSelected?.(files);
  }, [files, onFilesSelected]);

  // Get accepted file types for input
  const getAcceptedTypes = () => {
    switch (acceptedTypes) {
      case 'images':
        return 'image/*';
      case 'documents':
        return '.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.json,.xml';
      default:
        return 'image/*,.pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.csv,.json,.xml';
    }
  };

  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(event.target.files || []);
    console.log('📁 [UniversalFileUpload] File input changed, selected files:', selectedFiles.map(f => f.name));
    
    if (selectedFiles.length > 0) {
      console.log('🚀 [UniversalFileUpload] Calling addFiles with selected files');
      addFiles(selectedFiles);
    }
    // Reset input value to allow selecting the same file again
    event.target.value = '';
  };

  // Safeguard function for clear/discard buttons
  const handleClearFiles = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('🧹 [UniversalFileUpload] Clear All button clicked');
    clearFiles();
  };

  const handleDiscardStagedFiles = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('🗑️ [UniversalFileUpload] Discard Staged button clicked');
    discardStagedFiles();
  };

  // Safeguard for file container clicks (prevent any bubbling)
  const handleFileContainerClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    // Don't prevent default here as it might interfere with text selection
    console.log('📁 [UniversalFileUpload] File container clicked (prevented bubbling)');
  };

  const openFileDialog = () => {
    console.log('🖱️ [UniversalFileUpload] Open file dialog clicked, disabled:', disabled);
    if (!disabled) {
      console.log('📂 [UniversalFileUpload] Opening file dialog');
      fileInputRef.current?.click();
    }
  };

  const handleFileDialogClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('🖱️ [UniversalFileUpload] File dialog button clicked');
    openFileDialog();
  };

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusIcon = (file: UploadFile) => {
    switch (file.status) {
      case 'success':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-500" />;
      case 'uploading':
        return <Loader2 className="w-4 h-4 text-blue-500 animate-spin" />;
      default:
        return <Upload className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (file: UploadFile) => {
    switch (file.status) {
      case 'success':
        return 'border-green-200 bg-green-50';
      case 'error':
        return 'border-red-200 bg-red-50';
      case 'uploading':
        return 'border-blue-200 bg-blue-50';
      default:
        return 'border-gray-200 bg-gray-50';
    }
  };

  const getFileIcon = (file: UploadFile) => {
    if (file.fileCategory === 'image') {
      return <ImageIcon className="w-4 h-4" />;
    } else if (file.fileCategory === 'document') {
      return <FileText className="w-4 h-4" />;
    } else {
      return <File className="w-4 h-4" />;
    }
  };

  const renderFileThumbnail = (file: UploadFile) => {
    if (file.fileCategory === 'image' && file.preview) {
      return (
        <img
          src={file.preview}
          alt={file.name}
          className="w-full h-full object-cover"
        />
      );
    } else {
      return (
        <div className="w-full h-full flex flex-col items-center justify-center bg-gray-100">
          {getFileIcon(file)}
          <span className="text-xs text-gray-600 mt-1 truncate max-w-full px-1">
            {file.fileTypeInfo?.icon || '📄'}
          </span>
        </div>
      );
    }
  };

  return (
    <div className="flex items-center gap-2">
      {/* Upload button */}
      <button
        type="button"
        onClick={handleFileDialogClick}
        disabled={disabled}
        className={`flex items-center justify-center w-8 h-8 rounded-lg border-2 border-dashed transition-colors ${
          disabled
            ? 'border-gray-200 text-gray-400 cursor-not-allowed'
            : 'border-gray-300 text-gray-600 hover:border-blue-400 hover:text-blue-600'
        }`}
        title="Upload files"
      >
        <FileIcon className="w-4 h-4" />
      </button>

      {/* File thumbnails */}
      {files.map((file) => (
        <div
          key={file.id}
          className={`relative w-8 h-8 rounded-lg overflow-hidden border-2 ${getStatusColor(file)}`}
          onClick={handleFileContainerClick}
        >
          {renderFileThumbnail(file)}
          
          {/* Status overlay */}
          <div className="absolute inset-0 flex items-center justify-center bg-black bg-opacity-40">
            {getStatusIcon(file)}
          </div>

          {/* Progress indicator */}
          {file.status === 'uploading' && (
            <div className="absolute bottom-0 left-0 right-0 h-1 bg-blue-500"></div>
          )}

          {/* Remove button */}
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              console.log('❌ [UniversalFileUpload] Remove button clicked for file:', file.id, file.name);
              removeFile(file.id);
            }}
            className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors"
            title="Remove file"
          >
            <X className="w-2 h-2" />
          </button>
        </div>
      ))}

      <input
        ref={fileInputRef}
        type="file"
        accept={getAcceptedTypes()}
        multiple
        onChange={handleFileSelect}
        className="hidden"
      />
    </div>
  );
});

UniversalFileUpload.displayName = 'UniversalFileUpload'; 