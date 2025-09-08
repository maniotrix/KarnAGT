import React from 'react';
import { GoogleLogin, CredentialResponse } from '@react-oauth/google';
import { useNavigate } from 'react-router-dom';
import { useGoogleLogin } from '../../app/hooks/auth/useAuth';

interface GoogleSignInButtonProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  onSuccess,
  onError,
}) => {
  const navigate = useNavigate();
  const googleLoginMutation = useGoogleLogin();

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    try {
      if (!credentialResponse.credential) {
        throw new Error('No Google credential received');
      }

      // Use the auth hook (same pattern as email/password login)
      const result = await googleLoginMutation.mutateAsync(credentialResponse.credential);
      
      console.log('✅ Google login successful:', result.user.getDisplayName());
      onSuccess?.();
      navigate('/'); // Redirect to home page
      
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Google login failed';
      console.error('🚨 Google login error:', errorMessage);
      onError?.(errorMessage);
    }
  };

  const handleGoogleError = () => {
    const errorMessage = 'Google authentication failed or was cancelled';
    console.error('🚨 Google auth error:', errorMessage);
    onError?.(errorMessage);
  };

  return (
    <div className="w-full relative">
      {googleLoginMutation.isPending && (
        <div className="absolute inset-0 bg-gray-50 bg-opacity-75 flex items-center justify-center z-10 rounded">
          <div className="text-fluid-sm text-gray-500">Signing in with Google...</div>
        </div>
      )}
      <GoogleLogin
        onSuccess={handleGoogleSuccess}
        onError={handleGoogleError}
        useOneTap={false}
        theme="outline"
        size="large"
        text="signin_with"
        shape="rectangular"
        width="100%"
      />
    </div>
  );
};
