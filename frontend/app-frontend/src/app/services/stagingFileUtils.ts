// Staging File Utilities - Convert between frontend and backend formats
import type { UploadFile } from '../../types/upload';
import { universalUploadService } from '../../services/universalUploadService';

/**
 * Convert successful upload files to staging files dictionary format
 * Returns the format expected by the chat API with proper categorization
 */
export function convertUploadFilesToStagingFiles(uploadFiles: UploadFile[]): Record<string, any> {
  const successfulFiles = uploadFiles.filter(file => 
    file.status === 'success' && file.file_id && file.s3_key
  );
  
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
    const category = universalUploadService.categorizeFile(file.file);
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

  console.log('📋 [stagingFileUtils] Generated staging files:', stagingFiles);
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