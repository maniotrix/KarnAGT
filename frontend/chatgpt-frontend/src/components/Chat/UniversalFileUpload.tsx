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

interface UniversalFileUploadProps {
  onFilesSelected?: (files: UploadFile[]) => void;
  onUploadComplete?: (files: UploadFile[]) => void;
  onError?: (error: string) => void;
  maxFiles?: number;
  compact?: boolean;
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
  compact = false,
  disabled = false,
  acceptedTypes = 'all',
}, ref) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

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
    const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    const user = localStorage.getItem(ENV.USER_PROFILE_KEY);
    console.log('🔐 [UniversalFileUpload] Auth status check:');
    console.log('   - Token exists:', !!token);
    console.log('   - Token preview:', token ? `${token.substring(0, 20)}...` : 'NONE');
    console.log('   - User profile exists:', !!user);
    if (user) {
      try {
        const userObj = JSON.parse(user);
        console.log('   - User ID:', userObj.user_id || 'MISSING');
        console.log('   - Username:', userObj.username || 'MISSING');
      } catch (e) {
        console.log('   - User profile parse error:', e);
      }
    }
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

  const handleDragOver = (event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(true);
  };

  const handleDragLeave = (event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);
  };

  const handleDrop = (event: React.DragEvent) => {
    event.preventDefault();
    event.stopPropagation();
    setIsDragOver(false);
    
    const droppedFiles = Array.from(event.dataTransfer.files);
    console.log('🎯 [UniversalFileUpload] Files dropped:', droppedFiles.map(f => f.name));
    
    if (droppedFiles.length > 0) {
      console.log('🚀 [UniversalFileUpload] Calling addFiles with dropped files');
      addFiles(droppedFiles);
    }
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

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        {/* Compact upload button */}
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

        {/* File thumbnails for compact view */}
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
  }

  const { images, documents, unknown } = getFilesByCategory();

  return (
    <div className="w-full">
      {/* Upload Area */}
      <div
        className={`relative border-2 border-dashed rounded-lg p-6 transition-colors ${
          isDragOver
            ? 'border-blue-400 bg-blue-50'
            : disabled
            ? 'border-gray-200 bg-gray-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={(e) => {
          e.stopPropagation();
          console.log('📂 [UniversalFileUpload] Upload area clicked (prevented bubbling)');
        }}
      >
        <div className="text-center">
          <div className="mb-4">
            <FileIcon className="w-12 h-12 text-gray-400 mx-auto" />
          </div>
          
          <div className="mb-4">
            <button
              type="button"
              onClick={handleFileDialogClick}
              disabled={disabled}
              className={`inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                disabled
                  ? 'bg-gray-100 text-gray-400 cursor-not-allowed'
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              <Plus className="w-4 h-4" />
              Choose Files
            </button>
          </div>
          
          <p className="text-sm text-gray-500">
            or drag and drop files here
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {acceptedTypes === 'images' 
              ? 'Images: PNG, JPEG, GIF, WebP • Max 20MB each'
              : acceptedTypes === 'documents'
              ? 'Documents: PDF, Word, Excel, PowerPoint, Text • Max 50MB each'
              : 'Images (20MB) & Documents (50MB) • Up to ' + maxFiles + ' files'
            }
          </p>
        </div>

        {/* Upload Progress */}
        {isUploading && (
          <div className="absolute inset-0 bg-white bg-opacity-90 flex items-center justify-center">
            <div className="text-center">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin mx-auto mb-2" />
              <p className="text-sm text-gray-600">Uploading files...</p>
            </div>
          </div>
        )}
      </div>

      {/* File List */}
      {files.length > 0 && (
        <div className="mt-4 space-y-2">
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-700">
              Uploaded Files ({files.length})
              {images.length > 0 && (
                <span className="ml-2 text-blue-600">{images.length} images</span>
              )}
              {documents.length > 0 && (
                <span className="ml-2 text-green-600">{documents.length} documents</span>
              )}
              {unknown.length > 0 && (
                <span className="ml-2 text-gray-600">{unknown.length} unknown</span>
              )}
            </h4>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={handleClearFiles}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                Clear All
              </button>
              {files.some(f => f.status === 'success') && (
                <button
                  type="button"
                  onClick={handleDiscardStagedFiles}
                  className="text-xs text-red-500 hover:text-red-700"
                >
                  Discard Staged
                </button>
              )}
            </div>
          </div>

          <div className="max-h-48 overflow-y-auto space-y-2">
            {files.map((file) => (
              <div
                key={file.id}
                className={`flex items-center gap-3 p-3 rounded-lg border ${getStatusColor(file)}`}
                onClick={handleFileContainerClick}
              >
                {/* Thumbnail */}
                <div className="w-12 h-12 rounded-lg overflow-hidden bg-gray-100 flex-shrink-0">
                  {renderFileThumbnail(file)}
                </div>

                {/* File Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    {getFileIcon(file)}
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {file.name}
                    </p>
                    {file.fileTypeInfo && (
                      <span className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded">
                        {file.fileTypeInfo.displayName}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500">
                    {formatFileSize(file.size)}
                    {file.file_id && (
                      <span className="ml-2 text-blue-600">
                        ID: {file.file_id}
                      </span>
                    )}
                  </p>
                  {file.error && (
                    <p className="text-xs text-red-600 mt-1">{file.error}</p>
                  )}
                </div>

                {/* Status */}
                <div className="flex items-center gap-2">
                  {getStatusIcon(file)}
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      console.log('🗑️ [UniversalFileUpload] Trash button clicked for file:', file.id, file.name);
                      removeFile(file.id);
                    }}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                    title="Remove"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>

                {/* Progress Bar */}
                {file.status === 'uploading' && (
                  <div className="absolute bottom-0 left-0 right-0 h-1 bg-gray-200 rounded-b-lg">
                    <div 
                      className="h-full bg-blue-500 rounded-b-lg transition-all duration-300"
                      style={{ width: `${file.progress}%` }}
                    />
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

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