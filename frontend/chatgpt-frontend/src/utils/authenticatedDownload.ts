// Authenticated Download Utility
// Handles downloading files through authenticated proxy endpoints

import { ENV, buildApiUrl } from '../config/env';
import { authService } from '../services/authService';

export interface DownloadResult {
  success: boolean;
  error?: string;
}

/**
 * Handle authenticated download for proxy URLs
 * Opens URL directly in new tab - browser handles auth & redirect automatically
 */
export async function handleAuthenticatedDownload(url: string): Promise<DownloadResult> {
  try {
    // Check authentication status
    if (!authService.isAuthenticated()) {
      console.error('❌ Not authenticated (no CSRF token cookie found)');
      return { success: false, error: 'Authentication required. Please log in.' };
    }

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
    
    console.log('🔗 Opening authenticated URL in new tab:', fullUrl);
    
    // Open URL directly in new tab - browser handles everything automatically:
    // 1. Browser sends cookies automatically in navigation request
    // 2. Backend authenticates user via httpOnly cookies  
    // 3. Backend returns 302 redirect to presigned URL
    // 4. Browser automatically follows redirect in same new tab
    // 5. File downloads/displays in the new tab
    // 6. Any errors (401, 404, 403) are shown to user in the new tab
    window.open(fullUrl, '_blank');
    
    return { success: true };
    
  } catch (error) {
    console.error('❌ Failed to open download link:', error);
    return { success: false, error: 'Failed to open download link.' };
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