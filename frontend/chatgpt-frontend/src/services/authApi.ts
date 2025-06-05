// Authentication API service matching backend/app/api/v1/endpoints/auth.py
import { 
  LoginRequest, 
  RegisterRequest, 
  TokenResponse, 
  RefreshTokenResponse,
  PasswordResetResponse,
  UserProfile 
} from '../types/auth';
import { API_ENDPOINTS, buildApiUrl, ENV } from '../config/env';

class AuthApiService {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  // POST /api/v1/auth/login
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.LOGIN), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Login failed');
    }

    return response.json();
  }

  // POST /api/v1/auth/register
  async register(data: RegisterRequest): Promise<TokenResponse> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.REGISTER), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Registration failed');
    }

    return response.json();
  }

  // POST /api/v1/auth/refresh
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

  // GET /api/v1/auth/me
  async getCurrentUser(): Promise<UserProfile> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.ME), {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Failed to get user profile');
    }

    return response.json();
  }

  // POST /api/v1/auth/logout
  async logout(): Promise<void> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.LOGOUT), {
      method: 'POST',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Logout failed');
    }
  }

  // POST /api/v1/auth/forgot-password
  async forgotPassword(email: string): Promise<PasswordResetResponse> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.FORGOT_PASSWORD), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Password reset request failed');
    }

    return response.json();
  }

  // POST /api/v1/auth/reset-password
  async resetPassword(token: string, newPassword: string): Promise<PasswordResetResponse> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.RESET_PASSWORD), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, new_password: newPassword }),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.message || 'Password reset failed');
    }

    return response.json();
  }

  // GET /api/v1/auth/status
  async getAuthStatus(): Promise<{ authenticated: boolean; user?: UserProfile }> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.AUTH.STATUS), {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      return { authenticated: false };
    }

    const data = await response.json();
    return { authenticated: true, user: data };
  }

  // Storage helpers
  storeTokens(tokenResponse: TokenResponse): void {
    localStorage.setItem(ENV.ACCESS_TOKEN_KEY, tokenResponse.access_token);
    localStorage.setItem(ENV.REFRESH_TOKEN_KEY, tokenResponse.refresh_token);
    localStorage.setItem(ENV.USER_PROFILE_KEY, JSON.stringify(tokenResponse.user));
  }

  getStoredTokens(): { accessToken: string | null; refreshToken: string | null; user: UserProfile | null } {
    const accessToken = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    const refreshToken = localStorage.getItem(ENV.REFRESH_TOKEN_KEY);
    const userStr = localStorage.getItem(ENV.USER_PROFILE_KEY);
    const user = userStr ? JSON.parse(userStr) : null;

    return { accessToken, refreshToken, user };
  }

  clearTokens(): void {
    localStorage.removeItem(ENV.ACCESS_TOKEN_KEY);
    localStorage.removeItem(ENV.REFRESH_TOKEN_KEY);
    localStorage.removeItem(ENV.USER_PROFILE_KEY);
  }
}

export const authApi = new AuthApiService(); 