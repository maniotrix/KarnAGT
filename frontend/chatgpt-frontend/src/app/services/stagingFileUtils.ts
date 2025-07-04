// Staging File Utilities - Convert between frontend and backend formats
import type { UploadFile } from '../../types/upload';

/**
 * Convert successful upload files to staging files dictionary format
 * Returns the format expected by the chat API
 */
export function convertUploadFilesToStagingFiles(uploadFiles: UploadFile[]): Record<string, any> {
  const successfulFiles = uploadFiles.filter(file => 
    file.status === 'success' && file.file_id && file.s3_key
  );
  
  if (successfulFiles.length === 0) {
    return {};
  }

  // For now, all uploaded files are treated as images
  // In the future, we could add logic to categorize files
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

  return stagingFiles;
}

/**
 * Extract file IDs from staging files dictionary for cleanup
 */
export function extractFileIdsFromStagingFiles(stagingFiles: Record<string, any>): string[] {
  const fileIds: string[] = [];
  
  for (const category of ['images', 'vectors', 'unknown']) {
    if (Array.isArray(stagingFiles[category])) {
      for (const file of stagingFiles[category]) {
        if (file.file_id) {
          fileIds.push(file.file_id);
        }
      }
    }
  }
  
  return fileIds;
}

/**
 * Check if staging files dictionary has any files
 */
export function hasStagingFiles(stagingFiles?: Record<string, any>): boolean {
  if (!stagingFiles) return false;
  
  return Object.keys(stagingFiles).some(key => 
    Array.isArray(stagingFiles[key]) && stagingFiles[key].length > 0
  );
}

/**
 * Count total files in staging files dictionary
 */
export function countStagingFiles(stagingFiles?: Record<string, any>): number {
  if (!stagingFiles) return 0;
  
  let totalFiles = 0;
  for (const category of ['images', 'vectors', 'unknown']) {
    if (Array.isArray(stagingFiles[category])) {
      totalFiles += stagingFiles[category].length;
    }
  }
  
  return totalFiles;
}

/**
 * Validate staging files dictionary format
 */
export function validateStagingFiles(stagingFiles?: Record<string, any>): { valid: boolean; error?: string } {
  if (!stagingFiles) return { valid: true };
  
  try {
    for (const category of ['images', 'vectors', 'unknown']) {
      if (stagingFiles[category] && !Array.isArray(stagingFiles[category])) {
        return { valid: false, error: `${category} must be an array` };
      }
      
      if (Array.isArray(stagingFiles[category])) {
        for (const file of stagingFiles[category]) {
          if (!file.file_id || !file.s3_key) {
            return { valid: false, error: `Invalid file data in ${category}` };
          }
        }
      }
    }
    
    return { valid: true };
  } catch (error) {
    return { valid: false, error: 'Invalid staging files format' };
  }
} 