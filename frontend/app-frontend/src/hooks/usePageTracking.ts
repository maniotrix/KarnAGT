import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

/**
 * Hook to track page views with Google Analytics for client-side navigation
 * Automatically sends pageview events when route changes occur with safety features
 */
export const usePageTracking = () => {
  const location = useLocation();
  const lastTrackedPath = useRef<string>('');
  const isInitialRender = useRef<boolean>(true);

  useEffect(() => {
    // Safety checks
    if (typeof window === 'undefined') return; // SSR safety
    if (!window.gtag) {
      // GA script not loaded - warn in development only
      if (process.env.NODE_ENV === 'development') {
        console.warn('🔍 GA tracking skipped: gtag not available');
      }
      return;
    }

    const currentPath = location.pathname + location.search;
    
    // Prevent duplicate tracking (safety against rapid navigation)
    if (lastTrackedPath.current === currentPath) {
      return;
    }

    // Skip initial render tracking (page already tracked by GA script)
    if (isInitialRender.current) {
      isInitialRender.current = false;
      lastTrackedPath.current = currentPath;
      return;
    }

    try {
      // Sanitize path for privacy (remove sensitive params)
      const sanitizedPath = sanitizePath(currentPath);
      
      // Send pageview event with error handling
      window.gtag('config', 'G-VR48JWQDKG', {
        page_path: sanitizedPath,
        page_title: document.title,
        // Privacy-safe custom dimensions
        custom_map: {
          dimension1: 'spa_navigation'
        }
      });
      
      lastTrackedPath.current = currentPath;
      
      // Log only in development
      if (process.env.NODE_ENV === 'development') {
        console.log(`🔍 GA Tracked: ${sanitizedPath}`);
      }
      
    } catch (error) {
      // Fail silently in production, warn in development
      if (process.env.NODE_ENV === 'development') {
        console.error('🔍 GA tracking error:', error);
      }
    }
  }, [location]);
};

/**
 * Sanitize path for privacy and security
 * Removes sensitive IDs, tokens, and personal info from both path and query params
 */
const sanitizePath = (path: string): string => {
  try {
    const url = new URL(path, 'https://dummy.com');
    let sanitizedPath = url.pathname;
    
    // PRIVACY: Sanitize sensitive path segments
    sanitizedPath = sanitizedPath
      // API ENDPOINTS: Completely sanitize all API paths to protect system architecture
      .replace(/\/api\/.*$/gi, '/api/[ENDPOINT]')
      // Chat conversation IDs: /chat/uuid -> /chat/[ID]
      .replace(/\/chat\/[a-f0-9\-]{36}/gi, '/chat/[ID]')
      .replace(/\/chat\/[a-f0-9\-]{32}/gi, '/chat/[ID]')
      .replace(/\/chat\/[a-z0-9\-]{20,}/gi, '/chat/[ID]')
      // User IDs: /user/123 -> /user/[ID]  
      .replace(/\/user\/[a-z0-9\-]{8,}/gi, '/user/[ID]')
      // Document/File IDs: /doc/abc123 -> /doc/[ID]
      .replace(/\/doc\/[a-z0-9\-]{8,}/gi, '/doc/[ID]')
      .replace(/\/file\/[a-z0-9\-]{8,}/gi, '/file/[ID]')
      // Generic ID patterns: /anything/long-id -> /anything/[ID]
      .replace(/\/([^\/]+)\/[a-f0-9\-]{16,}/gi, '/$1/[ID]')
      // Email addresses in paths
      .replace(/\/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, '/[EMAIL]');
    
    // Remove sensitive query parameters
    const sensitiveParams = [
      'token', 'access_token', 'refresh_token', 'jwt',
      'key', 'api_key', 'password', 'pwd', 'pass',
      'email', 'mail', 'phone', 'tel', 'mobile',
      'id', 'user_id', 'userId', 'conversation_id', 'conversationId',
      'session', 'sessionId', 'auth', 'authorization'
    ];
    
    sensitiveParams.forEach(param => {
      if (url.searchParams.has(param)) {
        url.searchParams.set(param, '[REDACTED]');
      }
    });
    
    // Return privacy-safe path
    return sanitizedPath + url.search;
    
  } catch (error) {
    // Fallback: sanitize obvious patterns even if URL parsing fails
    let fallbackPath = path.split('?')[0];
    fallbackPath = fallbackPath.replace(/\/chat\/[a-f0-9\-]{20,}/gi, '/chat/[ID]');
    return fallbackPath;
  }
};

// TypeScript declaration for gtag (add to vite-env.d.ts if needed)
declare global {
  interface Window {
    gtag: (...args: any[]) => void;
    dataLayer: any[];
  }
}
