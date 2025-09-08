import type { FileCategory, FileTypeInfo } from '../services/universalUploadService';

export interface UploadFile {
  id: string;
  file: File;
  name: string;
  size: number;
  type: string;
  preview?: string; // Frontend-generated thumbnail URL
  status: 'pending' | 'uploading' | 'success' | 'error';
  progress: number;
  error?: string;
  // File categorization
  fileCategory?: FileCategory;
  fileTypeInfo?: FileTypeInfo;
  // From backend response
  file_id?: string;
  s3_key?: string;
  urls?: {
    display: string;
    api: string;
    thumbnail_small?: string;
    thumbnail_medium?: string;
    thumbnail_large?: string;
  };
}

export interface StagingFileInfo {
  file_id: string;
  s3_key: string;
  filename: string;
  content_type: string;
  file_size: number;
}

export interface StagingFileCollection {
  images: StagingFileInfo[];
  vectors: StagingFileInfo[];
  unknown: StagingFileInfo[];
}

export interface StagingUploadResponse {
  success: boolean;
  message: string;
  total_requested: number;
  successfully_staged: number;
  failed_uploads: number;
  staging_files: StagingFileCollection;
  failed_files: Array<{
    filename: string;
    error: string;
  }>;
  total_size_bytes: number;
  upload_duration_seconds: number;
}

export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

export interface ImageDimensions {
  width: number;
  height: number;
} 