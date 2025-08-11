// Authenticated Download Utility
// Handles downloading files through authenticated proxy endpoints

import { ENV, buildApiUrl } from '../config/env';
import { authService } from '../services/authService';

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
    // Check authentication status using the new system
    if (!authService.isAuthenticated()) {
      console.error('❌ Not authenticated (no CSRF token cookie found)');
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

    // Make authenticated request to get redirect URL (don't follow automatically)
    const response = await fetch(fullUrl, {
      method: 'GET',
      credentials: 'include', // Send httpOnly cookies for authentication
      headers: {
        'Content-Type': 'application/json',
        // No CSRF token needed for GET requests
      },
      redirect: 'manual' // Get redirect URL manually to avoid CORS issue
    });

    console.log('✅ Response status:', response.status);

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

    // Backend returns 302 redirect with presigned URL in Location header
    if (response.status === 302) {
      const presignedUrl = response.headers.get('location');
      
      if (!presignedUrl) {
        console.error('❌ No redirect URL found in Location header');
        return { success: false, error: 'Failed to get download URL from server.' };
      }
      
      console.log('✅ Got presigned URL from redirect, opening in new tab');
      console.log('🔗 Presigned URL:', presignedUrl.substring(0, 100) + '...');
      
      // Open the presigned URL in new tab - no credentials needed, avoids CORS issue
      window.open(presignedUrl, '_blank');
      return { success: true };
    }

    console.error('❌ Unexpected response status:', response.status);
    return { success: false, error: `Server returned ${response.status}: ${response.statusText}` };

  } catch (error) {
    console.error('❌ Failed to get presigned URL:', error);
    console.error('❌ Original URL:', url);
    console.error('❌ Authenticated:', authService.isAuthenticated());
    
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