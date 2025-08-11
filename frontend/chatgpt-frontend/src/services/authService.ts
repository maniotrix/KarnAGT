// Centralized Authentication Service for httpOnly Cookie + CSRF System
import { 
  LoginRequest, 
  RegisterRequest, 
  TokenResponse, 
  RefreshTokenResponse,
  PasswordResetResponse,
  UserProfile,
  AuthState
} from '../types/auth';
import { API_ENDPOINTS, buildApiUrl, ENV } from '../config/env';

/**
 * Centralized authentication service that works with httpOnly cookies + CSRF
 * This replaces the scattered auth logic across AuthRepository, authApi, etc.
 */
class AuthService {
  private csrfToken: string | null = null;

  constructor() {
    // Initialize CSRF token from cookie if available
    this.csrfToken = this.getCSRFTokenFromCookie();
  }

  /**
   * Get CSRF token from cookie (not httpOnly)
   */
  private getCSRFTokenFromCookie(): string | null {
    const cookies = document.cookie.split(';');
    const csrfCookie = cookies.find(cookie => 
      cookie.trim().startsWith(`${ENV.COOKIE_NAMES.CSRF_TOKEN}=`)
    );
    return csrfCookie ? csrfCookie.split('=')[1].trim() : null;
  }

  /**
   * Get headers for API requests
   */
  private getHeaders(includeCsrf: boolean = false): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add CSRF token for mutating operations
    if (includeCsrf && this.csrfToken) {
      headers['X-CSRF-Token'] = this.csrfToken;
    }

    return headers;
  }

  /**
   * Make authenticated request with proper cookie handling
   */
  private async makeRequest<T>(
    url: string,
    options: RequestInit = {},
    includeCsrf: boolean = false
  ): Promise<T> {
    const response = await fetch(buildApiUrl(url), {
      ...options,
      credentials: 'include', // Critical: This sends httpOnly cookies
      headers: {
        ...this.getHeaders(includeCsrf),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Request failed' }));
      throw new Error(error.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // ===========================================
  // Authentication Methods
  // ===========================================

  /**
   * Login user - backend sets httpOnly cookies
   */
  async login(credentials: LoginRequest): Promise<TokenResponse> {
    console.log('🔐 AuthService.login:', { email: credentials.email });
    
    const response = await this.makeRequest<TokenResponse>(
      API_ENDPOINTS.AUTH.LOGIN,
      {
        method: 'POST',
        body: JSON.stringify(credentials),
      },
      true // ✅ CSRF required for login POST
    );

    // Update CSRF token from response
    if (response.csrf_token) {
      this.csrfToken = response.csrf_token;
    } else {
      // Fallback: read from cookie
      this.csrfToken = this.getCSRFTokenFromCookie();
    }

    console.log('🔐 Login successful, CSRF token updated');
    return response;
  }

  /**
   * Register user - backend sets httpOnly cookies
   */
  async register(userData: RegisterRequest): Promise<TokenResponse> {
    console.log('🔐 AuthService.register:', { email: userData.email });
    
    // Clean up optional fields: convert empty strings to null for backend validation
    const cleanedData = {
      ...userData,
      full_name: userData.full_name?.trim() || null,
      username: userData.username?.trim() || null,
    };
    
    console.log('🔐 AuthService.register cleaned data:', cleanedData);
    
    const response = await this.makeRequest<TokenResponse>(
      API_ENDPOINTS.AUTH.REGISTER,
      {
        method: 'POST',
        body: JSON.stringify(cleanedData),
      },
      false // ❌ CSRF NOT required for registration (public endpoint)
    );

    // Update CSRF token from response
    if (response.csrf_token) {
      this.csrfToken = response.csrf_token;
    } else {
      this.csrfToken = this.getCSRFTokenFromCookie();
    }

    console.log('🔐 Registration successful, CSRF token updated');
    return response;
  }

  /**
   * Logout user - backend clears httpOnly cookies
   */
  async logout(): Promise<void> {
    console.log('🔐 AuthService.logout');
    
    await this.makeRequest(
      API_ENDPOINTS.AUTH.LOGOUT,
      {
        method: 'POST',
        body: JSON.stringify({}), // Empty body
      },
      true // Include CSRF token
    );

    // Clear local CSRF token
    this.csrfToken = null;
    console.log('🔐 Logout successful, CSRF token cleared');
  }

  /**
   * Refresh tokens - backend reads from httpOnly cookies
   */
  async refreshTokens(): Promise<RefreshTokenResponse> {
    console.log('🔐 AuthService.refreshTokens');
    
    const response = await this.makeRequest<RefreshTokenResponse>(
      API_ENDPOINTS.AUTH.REFRESH,
      {
        method: 'POST',
        body: JSON.stringify({}), // Empty body - backend reads from cookies
      },
      true // ✅ CSRF required for refresh POST
    );

    // Update CSRF token from response
    if (response.csrf_token) {
      this.csrfToken = response.csrf_token;
      console.log('🔐 Token refresh successful, CSRF token updated');
    }

    return response;
  }

  // ===========================================
  // User Profile Methods
  // ===========================================

  /**
   * Get current user profile
   */
  async getCurrentUser(): Promise<UserProfile> {
    console.log('🔐 AuthService.getCurrentUser');
    
    return this.makeRequest<UserProfile>(API_ENDPOINTS.AUTH.ME, {
      method: 'GET',
    });
  }

  /**
   * Update user profile
   */
  async updateUser(updates: Partial<UserProfile>): Promise<UserProfile> {
    console.log('🔐 AuthService.updateUser');
    
    return this.makeRequest<UserProfile>(
      API_ENDPOINTS.AUTH.ME,
      {
        method: 'PUT',
        body: JSON.stringify(updates),
      },
      true // Include CSRF token
    );
  }

  // ===========================================
  // Password Management
  // ===========================================

  /**
   * Request password reset
   */
  async forgotPassword(email: string): Promise<PasswordResetResponse> {
    console.log('🔐 AuthService.forgotPassword');
    
    return this.makeRequest<PasswordResetResponse>(
      API_ENDPOINTS.AUTH.FORGOT_PASSWORD,
      {
        method: 'POST',
        body: JSON.stringify({ email }),
      },
      true // ✅ CSRF required for password reset POST
    );
  }

  /**
   * Reset password with token
   */
  async resetPassword(token: string, newPassword: string): Promise<PasswordResetResponse> {
    console.log('🔐 AuthService.resetPassword');
    
    return this.makeRequest<PasswordResetResponse>(
      API_ENDPOINTS.AUTH.RESET_PASSWORD,
      {
        method: 'POST',
        body: JSON.stringify({ token, new_password: newPassword }),
      },
      true // ✅ CSRF required for password reset POST
    );
  }

  /**
   * Change password (authenticated user)
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    console.log('🔐 AuthService.changePassword');
    
    await this.makeRequest(
      API_ENDPOINTS.AUTH.CHANGE_PASSWORD,
      {
        method: 'POST',
        body: JSON.stringify({ 
          current_password: currentPassword, 
          new_password: newPassword 
        }),
      },
      true // ✅ CSRF required for password change POST
    );
  }

  // ===========================================
  // Email Verification
  // ===========================================

  /**
   * Verify email with token
   */
  async verifyEmail(token: string): Promise<void> {
    console.log('🔐 AuthService.verifyEmail');
    
    await this.makeRequest(
      API_ENDPOINTS.AUTH.VERIFY_EMAIL,
      {
        method: 'POST',
        body: JSON.stringify({ token }),
      },
      true // ✅ CSRF required for email verification POST
    );
  }

  /**
   * Resend verification email
   */
  async resendVerificationEmail(): Promise<void> {
    console.log('🔐 AuthService.resendVerificationEmail');
    
    await this.makeRequest(
      API_ENDPOINTS.AUTH.RESEND_VERIFICATION,
      {
        method: 'POST',
      },
      true // ✅ CSRF required for resend POST
    );
  }

  // ===========================================
  // Session Management
  // ===========================================

  /**
   * Check authentication status
   */
  async getAuthStatus(): Promise<{ authenticated: boolean; user?: UserProfile }> {
    try {
      const user = await this.getCurrentUser();
      return { authenticated: true, user };
    } catch (error) {
      console.log('🔐 Not authenticated:', error);
      return { authenticated: false };
    }
  }

  /**
   * Check if user appears to be authenticated (has CSRF token cookie)
   */
  isAuthenticated(): boolean {
    return !!this.getCSRFTokenFromCookie();
  }

  /**
   * Get current CSRF token for external use
   */
  getCSRFToken(): string | null {
    return this.csrfToken || this.getCSRFTokenFromCookie();
  }

  // ===========================================
  // Legacy Token Methods (for backward compatibility)
  // ===========================================

  /**
   * @deprecated Tokens are now in httpOnly cookies
   */
  storeTokens(_accessToken: string, _refreshToken: string): void {
    console.warn('⚠️ storeTokens is deprecated - tokens are now in httpOnly cookies');
  }

  /**
   * @deprecated Tokens are now in httpOnly cookies
   */
  getStoredTokens(): { accessToken: null; refreshToken: null } {
    console.warn('⚠️ getStoredTokens is deprecated - tokens are now in httpOnly cookies');
    return { accessToken: null, refreshToken: null };
  }

  /**
   * @deprecated Tokens are now in httpOnly cookies
   */
  clearTokens(): void {
    console.warn('⚠️ clearTokens is deprecated - use logout() instead');
    // Clear CSRF token
    this.csrfToken = null;
  }
}

// Export singleton instance
export const authService = new AuthService();
export default authService;
