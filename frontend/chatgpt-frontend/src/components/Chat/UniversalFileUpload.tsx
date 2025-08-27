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
import {
  FaFilePdf,
  FaFileWord,
  FaFileExcel,
  FaFilePowerpoint,
  FaFileCsv,
  FaFileCode,
  FaFileAlt
} from 'react-icons/fa';
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
  addFiles: (files: File[]) => void;
  openFileDialog: () => void;
}

const UniversalFileUploadComponent = forwardRef<UniversalFileUploadRef, UniversalFileUploadProps>(({
  onFilesSelected,
  onUploadComplete,
  onError,
  maxFiles = 10,
  disabled = false,
  acceptedTypes = 'all',
}, ref) => {
  console.log('📎 [UniversalFileUpload] KEYSTROKE - Component render started:', {
    timestamp: new Date().toISOString(),
    maxFiles,
    disabled,
    acceptedTypes,
    hasOnFilesSelected: !!onFilesSelected,
    hasOnUploadComplete: !!onUploadComplete,
    hasOnError: !!onError,
  });

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
    addFiles: (files: File[]) => addFiles(files),
    openFileDialog: () => fileInputRef.current?.click(),
  }), [files, clearFiles, getFilesByCategory, addFiles]);

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

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusIcon = (file: UploadFile) => {
    switch (file.status) {
      case 'error':
        return <AlertCircle className="w-3 h-3 text-white" />;
      case 'uploading':
        return <Loader2 className="w-4 h-4 text-white animate-spin" />;
      default:
        return null; // No icon for success or pending
    }
  };

  const getStatusColor = (file: UploadFile) => {
    // Use neutral card styling; rely on overlays/badges for state feedback
    return 'border-gray-300 bg-white';
  };

  const getBrandedFileIcon = (fileName: string) => {
    const extension = fileName.split('.').pop()?.toLowerCase() || '';
    
    const iconMap: Record<string, { Icon: React.ComponentType<{ className?: string }>; color: string }> = {
      // PDF
      pdf: { Icon: FaFilePdf, color: 'text-red-600' },
      
      // Microsoft Word
      doc: { Icon: FaFileWord, color: 'text-blue-600' },
      docx: { Icon: FaFileWord, color: 'text-blue-600' },
      
      // Microsoft Excel
      xls: { Icon: FaFileExcel, color: 'text-green-600' },
      xlsx: { Icon: FaFileExcel, color: 'text-green-600' },
      
      // Microsoft PowerPoint
      ppt: { Icon: FaFilePowerpoint, color: 'text-orange-600' },
      pptx: { Icon: FaFilePowerpoint, color: 'text-orange-600' },
      
      // CSV
      csv: { Icon: FaFileCsv, color: 'text-emerald-600' },
      
      // Code/Data files
      json: { Icon: FaFileCode, color: 'text-yellow-600' },
      xml: { Icon: FaFileCode, color: 'text-purple-600' },
      
      // Text files
      txt: { Icon: FaFileAlt, color: 'text-gray-600' },
    };

    return iconMap[extension] || { Icon: FaFileAlt, color: 'text-gray-600' };
  };

  const getFileIcon = (file: UploadFile) => {
    if (file.fileCategory === 'image') {
      return <ImageIcon className="w-4 h-4" />;
    } else if (file.fileCategory === 'document') {
      const { Icon, color } = getBrandedFileIcon(file.name);
      return <Icon className={`w-4 h-4 ${color}`} />;
    } else {
      const { Icon, color } = getBrandedFileIcon(file.name);
      return <Icon className={`w-4 h-4 ${color}`} />;
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
        <div className="w-full h-full flex items-center justify-center bg-gray-100">
          <div className="text-gray-500">
            {getFileIcon(file)}
          </div>
        </div>
      );
    }
  };

  return (
    <div className={`flex items-center gap-3 overflow-x-auto ${files.length > 0 ? 'py-3 px-2' : ''}`}>
      {/* File thumbnails */}
      {files.map((file) => (
        <div
          key={file.id}
          className="group relative shrink-0"
          onClick={handleFileContainerClick}
        >
          {/* Thumbnail container with clipped content */}
          <div className={`relative w-12 h-12 rounded-lg overflow-hidden border-2 ${getStatusColor(file)}`}>
            {renderFileThumbnail(file)}
            
            {/* Uploading overlay - centered translucent badge, slightly larger than error */}
            {file.status === 'uploading' && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-6 h-6 rounded-full bg-black/40 backdrop-blur-[1px] flex items-center justify-center">
                  {getStatusIcon(file)}
                </div>
              </div>
            )}

            {/* Progress indicator */}
            {file.status === 'uploading' && (
              <div className="absolute bottom-0 left-0 right-0 h-1 bg-blue-500"></div>
            )}

            {/* Error indicator - centered translucent badge (no outer padding changes, cross button untouched) */}
            {file.status === 'error' && (
              <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                <div className="w-5 h-5 rounded-full bg-red-500/70 backdrop-blur-[1px] flex items-center justify-center">
                  {getStatusIcon(file)}
                </div>
              </div>
            )}
          </div>

          {/* Remove button */}
          <button
            type="button"
            onClick={(e) => {
              e.preventDefault();
              e.stopPropagation();
              console.log('❌ [UniversalFileUpload] Remove button clicked for file:', file.id, file.name);
              removeFile(file.id);
            }}
            className="absolute -top-2 -right-2 w-6 h-6 min-w-6 min-h-6 bg-red-500 text-white rounded-full flex items-center justify-center hover:bg-red-600 transition-colors shadow-md focus:outline-none focus:ring-2 focus:ring-red-300 active:scale-95 flex-shrink-0"
            title={"Remove file: " + file.name}
            aria-label={"Remove file: " + file.name}
          >
            <X className="w-3 h-3" />
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

UniversalFileUploadComponent.displayName = 'UniversalFileUpload';

// 🚀 Export with memo to prevent re-renders when parent (ChatInput) re-renders
const UniversalFileUpload = React.memo(UniversalFileUploadComponent);
UniversalFileUpload.displayName = 'UniversalFileUpload'; 
export { UniversalFileUpload };