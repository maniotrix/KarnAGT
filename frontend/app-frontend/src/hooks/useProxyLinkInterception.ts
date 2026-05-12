// Proxy Link Interception Hook
// Global event delegation hook for intercepting authenticated proxy URL clicks

import { useEffect, useRef } from 'react';
import { handleAuthenticatedDownload, isProxyUrl, extractFileIdFromProxyUrl } from '../utils/authenticatedDownload';
import { useToast } from '../app/stores/uiStore';
import { isLikelyMobile } from '../utils/device';

export interface ProxyLinkInterceptionOptions {
  /** Enable debug logging */
  debug?: boolean;
  /** Custom URL patterns to match (in addition to default proxy patterns) */
  customPatterns?: RegExp[];
  /** Callback fired when a proxy link is intercepted */
  onInterception?: (url: string, fileId: string | null) => void;
  /** Callback fired when download succeeds */
  onDownloadSuccess?: (url: string) => void;
  /** Callback fired when download fails */
  onDownloadError?: (url: string, error: string) => void;
}

/**
 * Hook for intercepting clicks on authenticated proxy URLs using event delegation
 * 
 * This hook adds a global click listener that:
 * 1. Detects clicks on links that match proxy URL patterns
 * 2. Prevents default navigation
 * 3. Handles authenticated download instead
 * 
 * Usage:
 * ```tsx
 * function App() {
 *   useProxyLinkInterception(); // Enable globally
 *   return <YourApp />;
 * }
 * ```
 */
export function useProxyLinkInterception(options: ProxyLinkInterceptionOptions = {}) {
  const {
    debug = false,
    customPatterns = [],
    onInterception,
    onDownloadSuccess,
    onDownloadError
  } = options;

  const isHandlingRef = useRef(false); // Prevent concurrent handling

  useEffect(() => {
    const handleGlobalClick = async (event: Event) => {
      // Prevent concurrent handling
      if (isHandlingRef.current) return;

      try {
        // Find the closest anchor element
        const target = (event.target as Element)?.closest('a[href]') as HTMLAnchorElement;
        if (!target) return;

        const href = target.getAttribute('href');
        if (!href) return;

        if (debug) {
          console.log('🔗 [ProxyInterception] Found link:', {
            href,
            isAbsolute: href.startsWith('http'),
            targetElement: target.tagName,
            eventType: event.type
          });
        }

        // Check if it matches proxy URL patterns or custom patterns
        const matchesProxy = isProxyUrl(href);
        const matchesCustom = customPatterns.some(pattern => pattern.test(href));

        if (!matchesProxy && !matchesCustom) {
          if (debug) {
            console.log('🔗 [ProxyInterception] Not a proxy URL, ignoring:', href);
          }
          return;
        }

        // This is a proxy URL - intercept it!
        event.preventDefault();
        event.stopPropagation();

        const fileId = extractFileIdFromProxyUrl(href);
        
        if (debug) {
          console.log('🔗 [ProxyInterception] Intercepted proxy link:', {
            href,
            fileId,
            targetElement: target,
            eventType: event.type,
            isAbsolute: href.startsWith('http')
          });
        }

        // Call interception callback
        onInterception?.(href, fileId);

        // Set handling flag
        isHandlingRef.current = true;

        try {
          // Handle the authenticated download
          const result = await handleAuthenticatedDownload(href);

          if (result.success) {
            if (debug) {
              console.log('✅ [ProxyInterception] Proxy link successfully opened for download in new tab:', href);
            }
            
            onDownloadSuccess?.(href);
          } else {
            if (debug) {
              console.error('❌ [ProxyInterception] Proxy link failed to open for download in new tab:', href, result.error);
            }
            
            onDownloadError?.(href, result.error || 'Unknown error');
          }
        } catch (error) {
          const errorMessage = error instanceof Error ? error.message : 'Unexpected error occurred';
          
          if (debug) {
            console.error('❌ [ProxyInterception] Exception during download:', error);
          }
          
          onDownloadError?.(href, errorMessage);
        } finally {
          // Clear handling flag
          isHandlingRef.current = false;
        }

      } catch (error) {
        if (debug) {
          console.error('❌ [ProxyInterception] Exception in click handler:', error);
        }
        isHandlingRef.current = false;
      }
    };

    if (debug) {
      console.log('🔗 [ProxyInterception] Hook initialized, adding global click listener');
    }

    // Add event listener in capture phase to intercept before other handlers
    document.addEventListener('click', handleGlobalClick, true);

    // Cleanup function
    return () => {
      if (debug) {
        console.log('🔗 [ProxyInterception] Hook cleanup, removing global click listener');
      }
      document.removeEventListener('click', handleGlobalClick, true);
      isHandlingRef.current = false;
    };
  }, [debug, customPatterns, onInterception, onDownloadSuccess, onDownloadError]);

  // Return some useful utilities
  return {
    isProxyUrl,
    extractFileIdFromProxyUrl,
    handleAuthenticatedDownload
  };
}

// Using the proper device detection utility instead of simple width check

/**
 * Simplified hook version with sensible defaults for most use cases
 * Includes mobile-aware toast notifications for download success/failure
 */
export function useProxyLinkInterceptionSimple() {
  const toast = useToast();
  
  return useProxyLinkInterception({
    debug: process.env.NODE_ENV === 'development',
    onDownloadSuccess: (url) => {
      const isMobile = isLikelyMobile();
      
      if (isMobile) {
        // Mobile: File goes to download manager automatically
        toast.success('Download Started', 'File sent to downloads');
      } else {
        // Desktop: Opens in new tab
        toast.success('Download Started', 'Opening file in new tab');
      }
    },
    onDownloadError: (url, error) => {
      const isMobile = isLikelyMobile();
      
      if (isMobile) {
        // Mobile: Simple, clear error messages
        const mobileError = error?.includes('Authentication') ? 'Please log in first' :
                           error?.includes('404') ? 'File not found' :
                           error?.includes('403') ? 'Access denied' :
                           'Unable to download file';
        toast.error('Download Failed', mobileError);
      } else {
        // Desktop: More detailed error
        toast.error('Download Failed', error || 'Unable to download file');
      }
    },
    onInterception: (url, fileId) => {
      if (process.env.NODE_ENV === 'development') {
        console.log('🔗 Intercepted download link:', { url, fileId });
      }
    }
  });
}

/**
 * Hook version with enhanced logging for debugging
 */
export function useProxyLinkInterceptionDebug() {
  return useProxyLinkInterception({
    debug: true,
    onInterception: (url, fileId) => {
      console.log('🔗 [DEBUG] Proxy link intercepted:', { url, fileId });
    },
    onDownloadSuccess: (url) => {
      console.log('✅ [DEBUG] Download successful:', url);
    },
    onDownloadError: (url, error) => {
      console.error('❌ [DEBUG] Download failed:', { url, error });
    }
  });
}