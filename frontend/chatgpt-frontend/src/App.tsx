import React from 'react';
import { QueryProvider } from './providers/QueryProvider';
import { AuthForm } from './components/auth/AuthForm';
import { ChatApp } from './components/chat/ChatApp';
import { useCurrentUser } from './app/hooks/auth';
import { useUiStore } from './app/stores/uiStore';
import { Loader2 } from 'lucide-react';

// Loading Component
const AppLoading: React.FC = () => (
  <div className="min-h-screen bg-gray-50 flex items-center justify-center">
    <div className="text-center">
      <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
      <p className="text-gray-600">Initializing...</p>
    </div>
  </div>
);

// Toast Notifications Component
const ToastNotifications: React.FC = () => {
  const toasts = useUiStore(state => state.toasts);
  const removeToast = useUiStore(state => state.removeToast);

  if (toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map(toast => (
        <div
          key={toast.id}
          className={`
            max-w-md w-full bg-white shadow-lg rounded-lg pointer-events-auto overflow-hidden
            ${toast.type === 'success' ? 'border-l-4 border-green-400' : ''}
            ${toast.type === 'error' ? 'border-l-4 border-red-400' : ''}
            ${toast.type === 'info' ? 'border-l-4 border-blue-400' : ''}
            ${toast.type === 'warning' ? 'border-l-4 border-yellow-400' : ''}
          `}
        >
          <div className="p-4">
            <div className="flex items-start">
              <div className="flex-shrink-0">
                {toast.type === 'success' && (
                  <div className="w-5 h-5 rounded-full bg-green-100 flex items-center justify-center">
                    <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  </div>
                )}
                {toast.type === 'error' && (
                  <div className="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center">
                    <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                  </div>
                )}
                {toast.type === 'info' && (
                  <div className="w-5 h-5 rounded-full bg-blue-100 flex items-center justify-center">
                    <div className="w-2 h-2 bg-blue-400 rounded-full"></div>
                  </div>
                )}
                {toast.type === 'warning' && (
                  <div className="w-5 h-5 rounded-full bg-yellow-100 flex items-center justify-center">
                    <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
                  </div>
                )}
              </div>
              <div className="ml-3 w-0 flex-1">
                <p className="text-sm font-medium text-gray-900">
                  {toast.title}
                </p>
                {toast.message && (
                  <p className="mt-1 text-sm text-gray-500">
                    {toast.message}
                  </p>
                )}
              </div>
              <div className="ml-4 flex-shrink-0 flex">
                <button
                  className="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none"
                  onClick={() => removeToast(toast.id)}
                >
                  <span className="sr-only">Close</span>
                  <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
                  </svg>
                </button>
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};

// Main App Content Component
const AppContent: React.FC = () => {
  const { data: user, isLoading, error } = useCurrentUser();

  // Show loading state
  if (isLoading) {
    return <AppLoading />;
  }

  // Show error state (could be network error, etc.)
  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="text-red-600 mb-4">
            <svg className="h-12 w-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 15.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h2 className="text-xl font-semibold text-gray-900 mb-2">Connection Error</h2>
          <p className="text-gray-600 mb-4">Unable to connect to the server. Please try again.</p>
          <button
            onClick={() => window.location.reload()}
            className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Show appropriate component based on auth state
  return user ? <ChatApp /> : <AuthForm />;
};

// Main App Component with Providers
const App: React.FC = () => {
  return (
    <QueryProvider>
      <AppContent />
      <ToastNotifications />
    </QueryProvider>
  );
};

export default App;
