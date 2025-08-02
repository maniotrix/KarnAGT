// Authenticated Download Utility
// Handles downloading files through authenticated proxy endpoints

import { ENV, buildApiUrl } from '../config/env';

export interface DownloadResult {
  success: boolean;
  error?: string;
}

/**
 * Handle authenticated redirect for proxy URLs
 * Gets presigned URL and opens it in a new tab - lets browser handle file naturally
 */
export async function handleAuthenticatedDownload(url: string): Promise<DownloadResult> {
  try {
    const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    
    if (!token) {
      console.error('❌ No authentication token found');
      return { success: false, error: 'Authentication required. Please log in.' };
    }

    console.log('🔗 Getting presigned URL for:', url);

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

    // Make authenticated request and follow the redirect to get the presigned URL
    const response = await fetch(fullUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      redirect: 'follow' // Follow redirects to get final presigned URL
    });

    console.log('✅ Response status:', response.status);
    console.log('✅ Final URL:', response.url);

    if (response.status === 401) {
      console.error('❌ Authentication failed');
      return { success: false, error: 'Authentication failed. Please log in again.' };
    }

    if (response.status === 404) {
      console.error('❌ File not found');
      return { success: false, error: 'File not found or no longer available.' };
    }

    if (response.status === 403) {
      console.error('❌ Access denied');
      return { success: false, error: 'Access denied. You do not have permission to access this file.' };
    }

    // If we get a successful response, the final URL is our presigned URL
    if (response.ok) {
      const presignedUrl = response.url; // This is the final URL after redirect
      
      console.log('✅ Got presigned URL, opening in new tab');
      console.log('🔗 Presigned URL:', presignedUrl);
      
      // Open the presigned URL in a new tab - browser handles the rest!
      window.open(presignedUrl, '_blank');
      return { success: true };
    }

    console.error('❌ Unexpected response status:', response.status);
    return { success: false, error: `Server returned ${response.status}: ${response.statusText}` };

  } catch (error) {
    const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    console.error('❌ Failed to get presigned URL:', error);
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
      error: error instanceof Error ? error.message : 'Unknown error occurred while accessing file' 
    };
  }
}

// Note: No download logic needed - we just open the presigned URL in a new tab
// The browser handles file display/download naturally based on Content-Type

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