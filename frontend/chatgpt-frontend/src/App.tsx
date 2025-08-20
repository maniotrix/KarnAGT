import React from 'react';
import { BrowserRouter } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import { QueryProvider } from './providers/QueryProvider';
import { AppRoutes } from './routes';
import { useUiStore, useIsDarkMode } from './app/stores/uiStore';
import { useProxyLinkInterceptionSimple } from './hooks/useProxyLinkInterception';
import { X, CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { ENV } from './config/env';

// Toast Notifications Component
const ToastNotifications: React.FC = () => {
  const toasts = useUiStore(state => state.toasts);
  const removeToast = useUiStore(state => state.removeToast);
  const isDarkMode = useIsDarkMode();

  if (toasts.length === 0) return null;

  const getToastIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="h-5 w-5 text-green-500" />;
      case 'error':
        return <XCircle className="h-5 w-5 text-red-500" />;
      case 'warning':
        return <AlertCircle className="h-5 w-5 text-yellow-500" />;
      case 'info':
        return <Info className="h-5 w-5 text-blue-500" />;
      default:
        return <Info className="h-5 w-5 text-blue-500" />;
    }
  };

  const getToastStyles = (type: string) => {
    const baseStyles = `
      relative w-full max-w-sm sm:max-w-md lg:max-w-lg xl:max-w-xl
      bg-white dark:bg-gray-800 
      shadow-lg ring-1 ring-black ring-opacity-5 dark:ring-gray-700
      rounded-xl pointer-events-auto overflow-hidden
      transform transition-all duration-300 ease-out
    `;

    const borderStyles = {
      success: 'border-l-4 border-green-500',
      error: 'border-l-4 border-red-500',
      warning: 'border-l-4 border-yellow-500',
      info: 'border-l-4 border-blue-500',
    };

    return `${baseStyles} ${borderStyles[type as keyof typeof borderStyles] || borderStyles.info}`;
  };

  return (
    <div className="fixed top-4 right-4 z-50 space-y-3 max-w-screen-sm w-full px-4 sm:px-0">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, x: 300, scale: 0.95 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 300, scale: 0.95 }}
            whileHover={{ scale: 1.02 }}
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 30,
            }}
            className={getToastStyles(toast.type)}
          >
            <div className="p-4">
              <div className="flex items-start gap-3">
                {/* Icon */}
                <div className="flex-shrink-0 pt-0.5">
                  {getToastIcon(toast.type)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-gray-900 dark:text-white">
                    {toast.title}
                  </p>
                  {toast.message && (
                    <p className="mt-1 text-sm text-gray-600 dark:text-gray-300 break-words">
                      {toast.message}
                    </p>
                  )}
                </div>

                {/* Close Button */}
                <div className="flex-shrink-0">
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                    className="inline-flex rounded-md p-1.5 text-gray-400 hover:text-gray-600 dark:text-gray-500 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 dark:focus:ring-offset-gray-800 transition-colors"
                    onClick={() => removeToast(toast.id)}
                  >
                    <span className="sr-only">Dismiss</span>
                    <X className="h-4 w-4" />
                  </motion.button>
                </div>
              </div>
            </div>

            {/* Progress bar for auto-dismiss */}
            {toast.duration && toast.duration > 0 && (
              <motion.div
                initial={{ width: "100%" }}
                animate={{ width: "0%" }}
                transition={{ duration: toast.duration / 1000, ease: "linear" }}
                className={`h-1 ${
                  toast.type === 'success' ? 'bg-green-500' :
                  toast.type === 'error' ? 'bg-red-500' :
                  toast.type === 'warning' ? 'bg-yellow-500' :
                  'bg-blue-500'
                }`}
              />
            )}
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
};

// Main App Component with Providers and Router
const App: React.FC = () => {
  // Enable global proxy link interception with authentication
  useProxyLinkInterceptionSimple();

  // Google OAuth Client ID from configuration
  const googleClientId = ENV.GOOGLE_CLIENT_ID;

  return (
    <GoogleOAuthProvider clientId={googleClientId || ''}>
      <QueryProvider>
        <BrowserRouter>
          <AppRoutes />
          <ToastNotifications />
        </BrowserRouter>
      </QueryProvider>
    </GoogleOAuthProvider>
  );
};

export default App;
