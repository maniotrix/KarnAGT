import React from 'react';
import { Route, Routes, Navigate } from 'react-router-dom';
import { ChatApp } from '../components/Chat/ChatApp';
import { AuthForm } from '../components/Auth/AuthForm';
import { useCurrentUser } from '../app/hooks/auth';
import { AppLoading } from '../components/common/AppLoading';
import { ErrorPage } from '../components/common/ErrorPage';

// Protected route component that redirects to login if user is not authenticated
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const { data: user, isLoading, error } = useCurrentUser();

  if (isLoading) {
    return <AppLoading />;
  }

  if (error) {
    return <ErrorPage 
      title="Authentication Error" 
      message="There was a problem verifying your authentication. Please try logging in again."
      showLoginButton={true}
    />;
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

// Routes configuration
export const AppRoutes = () => {
  return (
    <Routes>
      {/* Auth routes */}
      <Route path="/login" element={<AuthForm />} />
      <Route path="/register" element={<AuthForm isRegisterMode={true} />} />
      
      {/* Protected routes */}
      <Route 
        path="/" 
        element={
          <ProtectedRoute>
            <ChatApp />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/chat/:conversationId" 
        element={
          <ProtectedRoute>
            <ChatApp />
          </ProtectedRoute>
        } 
      />
      
      {/* Error page */}
      <Route path="/error" element={<ErrorPage />} />
      
      {/* Catch-all route - redirect to root */}
      <Route path="*" element={<Navigate to="/error" replace />} />
    </Routes>
  );
}; 