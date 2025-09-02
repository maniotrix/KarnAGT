import React, { useEffect } from 'react';
import { BrowserRouter } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { QueryProvider } from './providers/QueryProvider';
import { ThemeProvider } from './providers/ThemeProvider';
import { AppRoutes } from './routes';
import { useProxyLinkInterceptionSimple } from './hooks/useProxyLinkInterception';
import { ToastNotifications } from './components/ui/ToastNotifications';
import { ENV } from './config/env';
import { initViewportUtils } from './utils/viewport';



// Main App Component with Providers and Router
const App: React.FC = () => {
  // Enable global proxy link interception with authentication
  useProxyLinkInterceptionSimple();

  // Initialize viewport utilities for mobile compatibility
  useEffect(() => {
    initViewportUtils();
  }, []);

  // Google OAuth Client ID from configuration
  const googleClientId = ENV.GOOGLE_CLIENT_ID;

  return (
    <ThemeProvider>
      <GoogleOAuthProvider clientId={googleClientId || ''}>
        <QueryProvider>
          <BrowserRouter>
            <AppRoutes />
            <ToastNotifications />
          </BrowserRouter>
        </QueryProvider>
      </GoogleOAuthProvider>
    </ThemeProvider>
  );
};

export default App;
