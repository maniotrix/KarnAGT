import React from 'react';
import { GoogleLogin, CredentialResponse } from '@react-oauth/google';
import { authService } from '../../services/authService';
import { useNavigate } from 'react-router-dom';

interface GoogleSignInButtonProps {
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

export const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
  onSuccess,
  onError,
}) => {
  const navigate = useNavigate();

  const handleGoogleSuccess = async (credentialResponse: CredentialResponse) => {
    try {
      if (!credentialResponse.credential) {
        throw new Error('No Google credential received');
      }

      // Send Google ID token to our backend
      const result = await authService.googleLogin(credentialResponse.credential);

      if (result.success) {
        console.log('✅ Google login successful:', result.message);
        onSuccess?.();
        navigate('/'); // Redirect to home page
      } else {
        throw new Error(result.message || 'Google login failed');
      }
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
    <div className="w-full">
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
