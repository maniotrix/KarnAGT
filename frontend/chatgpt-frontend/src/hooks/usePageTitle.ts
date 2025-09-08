import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

interface PageTitleConfig {
  [path: string]: string;
}

/**
 * Hook to dynamically update page titles based on route
 * Improves SEO and Google Analytics page title tracking
 */
export const usePageTitle = () => {
  const location = useLocation();

  useEffect(() => {
    // Map routes to specific page titles
    const titleMap: PageTitleConfig = {
      '/': 'KarnAGT - AI Agent',
      '/home': 'KarnAGT - AI Agent',
      '/about': 'About | KarnAGT - AI Agent',
      '/help': 'Help Center | KarnAGT - AI Agent',
      '/login': 'Sign In | KarnAGT - AI Agent',
      '/register': 'Sign Up | KarnAGT - AI Agent',
      '/terms': 'Terms & Conditions | KarnAGT',
      '/privacy-policy': 'Privacy Policy | KarnAGT',
    };

    // Get current path
    const currentPath = location.pathname;
    
    // Determine page title
    let pageTitle: string;
    
    if (titleMap[currentPath]) {
      // Exact route match
      pageTitle = titleMap[currentPath];
    } else if (currentPath.startsWith('/chat/')) {
      // Dynamic chat routes
      pageTitle = 'Chat | KarnAGT - AI Agent';
    } else {
      // Fallback for unknown routes
      pageTitle = 'KarnAGT - AI Agent';
    }

    // Update document title
    document.title = pageTitle;
    
    // Debug log in development
    if (process.env.NODE_ENV === 'development') {
      console.log(`📄 Page Title Updated: "${pageTitle}" for ${currentPath}`);
    }
  }, [location.pathname]);
};
