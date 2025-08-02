// Authenticated Download Utility
// Handles downloading files through authenticated proxy endpoints

import { ENV, buildApiUrl } from '../config/env';

export interface DownloadResult {
  success: boolean;
  error?: string;
}

/**
 * Handle authenticated download for proxy URLs
 * Supports both redirect-based and blob-based downloads
 */
export async function handleAuthenticatedDownload(url: string): Promise<DownloadResult> {
  try {
    const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    
    if (!token) {
      console.error('❌ No authentication token found for download');
      return { success: false, error: 'Authentication required. Please log in.' };
    }

    console.log('🔗 Attempting authenticated download:', url);

    // Build the full URL - handle both relative and absolute URLs
    let fullUrl: string;
    
    if (url.startsWith('http://') || url.startsWith('https://')) {
      // Already absolute URL
      fullUrl = url;
    } else if (url.startsWith('/')) {
      // Relative URL starting with /
      fullUrl = buildApiUrl(url);
    } else {
      // Relative URL not starting with /
      fullUrl = buildApiUrl(`/${url}`);
    }
    
    console.log('🔗 Original URL:', url);
    console.log('🔗 Full URL for request:', fullUrl);

    // Make authenticated request to proxy endpoint
    // Use 'follow' to let browser handle the redirect automatically
    const response = await fetch(fullUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      redirect: 'follow' // Let browser follow redirects automatically
    });

    if (response.status === 401) {
      console.error('❌ Authentication failed for download');
      return { success: false, error: 'Authentication failed. Please log in again.' };
    }

    if (response.status === 404) {
      console.error('❌ File not found for download');
      return { success: false, error: 'File not found or no longer available.' };
    }

    if (response.status === 403) {
      console.error('❌ Access denied for download');
      return { success: false, error: 'Access denied. You do not have permission to download this file.' };
    }

    // Handle successful response (after redirect was followed automatically)
    if (response.ok) {
      console.log('✅ Got successful response from S3, downloading file');
      console.log('🔗 Final URL after redirect:', response.url);
      console.log('🔗 Content-Type:', response.headers.get('Content-Type'));
      console.log('🔗 Content-Disposition:', response.headers.get('Content-Disposition'));
      
      // Create blob from the file content
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      
      // Extract filename from Content-Disposition header if available
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'download';
      
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename[^;=\n]*=((['"]).*?\2|[^;\n]*)/);
        if (filenameMatch && filenameMatch[1]) {
          filename = filenameMatch[1].replace(/['"]/g, '');
        }
      }
      
      // Create download link
      const a = document.createElement('a');
      a.href = downloadUrl;
      a.download = filename;
      a.style.display = 'none';
      
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      
      // Clean up
      window.URL.revokeObjectURL(downloadUrl);
      
      console.log('✅ File download initiated:', filename);
      return { success: true };
    }

    console.error('❌ Unexpected response status:', response.status);
    return { success: false, error: `Server returned ${response.status}: ${response.statusText}` };

  } catch (error) {
    const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    console.error('❌ Download failed with error:', error);
    console.error('❌ Original URL:', url);
    console.error('❌ Token available:', !!token);
    
    if (error instanceof TypeError && error.message.includes('Failed to fetch')) {
      return { success: false, error: 'Network error. Please check your connection.' };
    }
    
    if (error instanceof TypeError && error.message.includes('Failed to parse URL')) {
      return { success: false, error: 'Invalid URL format. Please try again.' };
    }
    
    if (error instanceof TypeError && error.message.includes('CORS')) {
      return { success: false, error: 'CORS error. The file server may need CORS configuration.' };
    }
    
    return { 
      success: false, 
      error: error instanceof Error ? error.message : 'Unknown error occurred during download' 
    };
  }
}

// Note: Manual filename extraction removed - S3 presigned URLs handle this automatically
// through proper Content-Disposition headers set by the backend

/**
 * Check if a URL is a proxy URL that needs authentication
 */
export function isProxyUrl(url: string): boolean {
  if (!url) return false;
  
  // Handle both absolute and relative URLs
  const urlToCheck = url.startsWith('http') ? url : new URL(url, window.location.origin).pathname;
  
  return /\/api\/v1\/proxy\/(images|files|code-files)\//.test(urlToCheck);
}

/**
 * Extract file ID from proxy URL for logging/debugging
 */
export function extractFileIdFromProxyUrl(url: string): string | null {
  const match = url.match(/\/api\/v1\/proxy\/(?:images|files|code-files)\/([^?&#]+)/);
  return match ? match[1] : null;
}