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

export interface StagingUploadResponse {
  success: boolean;
  message: string;
  total_requested: number;
  successfully_staged: number;
  failed_uploads: number;
  staged_files: Array<{
    file_id: string;
    s3_key: string;
    filename: string;
    size: number;
    content_type: string;
    staged_at: string;
    expires_at: string;
  }>;
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