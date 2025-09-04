import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle, XCircle, AlertCircle, Info } from 'lucide-react';
import { useUiStore } from '../../app/stores/uiStore';

/**
 * Mobile-optimized Toast Notifications Component
 * 
 * Features:
 * - Responsive sizing: smaller on mobile, larger on desktop
 * - Safe area considerations for modern mobile devices
 * - Optimized spacing and positioning
 * - Touch-friendly close buttons
 * - Proper animations and transitions
 */
export const ToastNotifications: React.FC = () => {
  const toasts = useUiStore(state => state.toasts);
  const removeToast = useUiStore(state => state.removeToast);

  if (toasts.length === 0) return null;

  const getToastIcon = (type: string) => {
    switch (type) {
      case 'success':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-red-500" />;
      case 'warning':
        return <AlertCircle className="h-4 w-4 text-yellow-500" />;
      case 'info':
        return <Info className="h-4 w-4 text-blue-500" />;
      default:
        return <Info className="h-4 w-4 text-blue-500" />;
    }
  };

  const getToastStyles = (type: string) => {
    // Mobile-first responsive design
    const baseStyles = `
      relative w-full 
      max-w-xs sm:max-w-sm md:max-w-md lg:max-w-lg
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
    <div className="fixed top-4 z-50 
                    space-y-2 sm:space-y-3
                    max-w-xs sm:max-w-sm md:max-w-md w-full 
                    px-2 sm:px-4 md:px-0
                    left-1/2 -translate-x-1/2
                    sm:left-auto sm:translate-x-0 sm:right-4
                    safe-area-inset-top safe-area-inset-right">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <motion.div
            key={toast.id}
            initial={{ opacity: 0, y: -50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -50, scale: 0.95 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }} // Better for mobile touch
            transition={{
              type: "spring",
              stiffness: 300,
              damping: 30,
            }}
            className={getToastStyles(toast.type)}
          >
            {/* Toast Content */}
            <div className="p-2 sm:p-3">
              <div className="flex items-start gap-2">
                {/* Icon */}
                <div className="flex-shrink-0">
                  {getToastIcon(toast.type)}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0">
                  <p className="text-fluid-xs font-semibold text-gray-900 dark:text-white leading-tight">
                    {toast.title}
                  </p>
                  {toast.message && (
                    <p className="mt-0.5 text-fluid-xs text-gray-600 dark:text-gray-300 break-words leading-tight">
                      {toast.message}
                    </p>
                  )}
                </div>

                {/* Close Button - Touch optimized */}
                <div className="flex-shrink-0">
                  <motion.button
                    whileHover={{ scale: 1.1 }}
                    whileTap={{ scale: 0.95 }}
                    className="inline-flex rounded-md p-1 sm:p-1.5 
                              text-gray-400 hover:text-gray-600 
                              dark:text-gray-500 dark:hover:text-gray-300 
                              hover:bg-gray-100 dark:hover:bg-gray-700 
                              focus:outline-none focus:ring-2 focus:ring-offset-2 
                              focus:ring-indigo-500 dark:focus:ring-offset-gray-800 
                              transition-colors
                              min-h-[40px] min-w-[40px] sm:min-h-[auto] sm:min-w-[auto]" // Reduced from 44px to 40px for mobile
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
