// Repository Implementation: Auth - Clean architecture data access
import { IAuthRepository } from '../../domain/interfaces/IAuthRepository';
import { User } from '../../domain/entities/User';
import { 
  LoginRequest, 
  RegisterRequest, 
  TokenResponse, 
  RefreshTokenResponse,
  PasswordResetResponse,
  UserProfile 
} from '../../types/auth';
import { API_ENDPOINTS, buildApiUrl, ENV } from '../../config/env';

export class AuthRepository implements IAuthRepository {
  private getPrivateHeaders(): HeadersInit {
    const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  // Authentication methods
  async login(credentials: LoginRequest): Promise<{ user: User; tokens: TokenResponse }> {
    console.log('🔐 AuthRepository.login called with:', { email: credentials.email, hasPassword: !!credentials.password });
    
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.LOGIN), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });

    console.log('🔐 Login response status:', response.status);
    console.log('🔐 Login response headers:', Object.fromEntries(response.headers.entries()));

    if (!response.ok) {
      const error = await response.json();
      console.error('🔐 Login failed with error:', error);
      throw new Error(error.message || 'Login failed');
    }

    const tokens: TokenResponse = await response.json();
    console.log('🔐 Login successful, got tokens:', { hasAccessToken: !!tokens.access_token, user: tokens.user?.email });
    
    const user = User.fromProfile(tokens.user);
    console.log('🔐 User entity created:', { userId: user.userId, email: user.email });
    
    return { user, tokens };
  }

  async register(userData: RegisterRequest): Promise<{ user: User; tokens: TokenResponse }> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.REGISTER), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Registration failed');
    }

    const tokens: TokenResponse = await response.json();
    const user = User.fromProfile(tokens.user);
    
    return { user, tokens };
  }

  async logout(): Promise<void> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.LOGOUT), {
      method: 'POST',
      headers: this.getPrivateHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Logout failed');
    }

    this.clearTokens();
  }

  // Token management
  async refreshToken(refreshToken: string): Promise<RefreshTokenResponse> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.REFRESH), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Token refresh failed');
    }

    return response.json();
  }

  getStoredTokens(): { accessToken: string | null; refreshToken: string | null } {
    const accessToken = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    const refreshToken = localStorage.getItem(ENV.REFRESH_TOKEN_KEY);
    return { accessToken, refreshToken };
  }

  storeTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem(ENV.ACCESS_TOKEN_KEY, accessToken);
    localStorage.setItem(ENV.REFRESH_TOKEN_KEY, refreshToken);
  }

  clearTokens(): void {
    localStorage.removeItem(ENV.ACCESS_TOKEN_KEY);
    localStorage.removeItem(ENV.REFRESH_TOKEN_KEY);
    localStorage.removeItem(ENV.USER_PROFILE_KEY);
  }

  // User management
  async getCurrentUser(): Promise<User | null> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.ME), {
      method: 'GET',
      headers: this.getPrivateHeaders(),
    });

    if (!response.ok) {
      if (response.status === 401) {
        return null; // Not authenticated
      }
      const error = await response.json();
      throw new Error(error.message || 'Failed to get user profile');
    }

    const profile: UserProfile = await response.json();
    return User.fromProfile(profile);
  }

  async updateUser(user: User): Promise<User> {
    const profile = user.toProfile();
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.ME), {
      method: 'PUT',
      headers: this.getPrivateHeaders(),
      body: JSON.stringify(profile),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to update user');
    }

    const updatedProfile: UserProfile = await response.json();
    return User.fromProfile(updatedProfile);
  }

  // Password management
  async requestPasswordReset(email: string): Promise<void> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.FORGOT_PASSWORD), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Password reset request failed');
    }
  }

  async resetPassword(token: string, newPassword: string): Promise<void> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.RESET_PASSWORD), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Password reset failed');
    }
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.CHANGE_PASSWORD), {
      method: 'POST',
      headers: this.getPrivateHeaders(),
      body: JSON.stringify({ 
        current_password: currentPassword, 
        new_password: newPassword 
      }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Password change failed');
    }
  }

  // Email verification
  async verifyEmail(token: string): Promise<void> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.VERIFY_EMAIL), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Email verification failed');
    }
  }

  async resendVerificationEmail(): Promise<void> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.RESEND_VERIFICATION), {
      method: 'POST',
      headers: this.getPrivateHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to resend verification email');
    }
  }

  // Session management
  isAuthenticated(): boolean {
    const { accessToken } = this.getStoredTokens();
    return !!accessToken;
  }

  getAuthHeaders(): Record<string, string> {
    const { accessToken } = this.getStoredTokens();
    return {
      'Content-Type': 'application/json',
      ...(accessToken && { Authorization: `Bearer ${accessToken}` }),
    };
  }



  // Additional helper methods for legacy compatibility
  async getAuthStatus(): Promise<{ authenticated: boolean; user?: User }> {
    try {
      const user = await this.getCurrentUser();
      return { authenticated: !!user, user: user || undefined };
    } catch (error) {
      return { authenticated: false };
    }
  }

  // Store user profile for backwards compatibility
  storeUserProfile(user: User): void {
    localStorage.setItem(ENV.USER_PROFILE_KEY, JSON.stringify(user.toProfile()));
  }

  // Store full token response for backwards compatibility
  storeTokenResponse(tokenResponse: TokenResponse): void {
    this.storeTokens(tokenResponse.access_token, tokenResponse.refresh_token);
    const user = User.fromProfile(tokenResponse.user);
    this.storeUserProfile(user);
  }
} 