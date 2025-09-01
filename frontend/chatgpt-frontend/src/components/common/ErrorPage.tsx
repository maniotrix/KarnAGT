import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle } from 'lucide-react';
import Logo from '../ui/Logo';

interface ErrorPageProps {
  title?: string;
  message?: string;
  showLoginButton?: boolean;
}

export const ErrorPage: React.FC<ErrorPageProps> = ({
  title = 'Something went wrong',
  message = 'We encountered an error while processing your request.',
  showLoginButton = false
}) => {
  const navigate = useNavigate();
  
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-8 md:p-12 lg:p-16">
      <div className="max-w-md w-full text-center bg-white rounded-lg shadow-sm p-8 md:p-10">
        {/* Brand Logo */}
        <div className="flex justify-center mb-6">
          <Logo size="xl" variant="full" />
        </div>
        
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-red-100 text-red-600 rounded-full">
            <AlertTriangle className="h-10 w-10" />
          </div>
        </div>
        
        <h1 className="text-2xl font-bold text-gray-900 mb-3">
          {title}
        </h1>
        
        <p className="text-gray-600 mb-6">
          {message}
        </p>
        
        <div className="flex flex-col space-y-2 sm:flex-row sm:space-y-0 sm:space-x-3 justify-center">
          {showLoginButton ? (
            <>
              <button
                onClick={() => navigate('/login')}
                className="px-5 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 transition-colors"
              >
                Go to Login
              </button>
              
              <button
                onClick={() => navigate('/register')}
                className="px-5 py-2 bg-green-600 text-white font-medium rounded-md hover:bg-green-700 transition-colors"
              >
                Create Account
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => navigate('/')}
                className="px-5 py-2 bg-blue-600 text-white font-medium rounded-md hover:bg-blue-700 transition-colors"
              >
                Go to Home
              </button>
              
              <button
                onClick={() => navigate(-1)}
                className="px-5 py-2 bg-gray-200 text-gray-800 font-medium rounded-md hover:bg-gray-300 transition-colors"
              >
                Go Back
              </button>
            </>
          )}
        </div>
        
        {/* Subtle branding footer */}
        <div className="mt-8 pt-6 border-t border-gray-200">
          <p className="text-sm text-gray-500">
            Having trouble? Contact KarnAGT support for assistance.
          </p>
        </div>
      </div>
    </div>
  );
}; 