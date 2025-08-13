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
import { authService } from '../../services/authService';

export class AuthRepository implements IAuthRepository {
  // Note: Headers are now handled by AuthService with httpOnly cookies + CSRF
  // This method kept for interface compatibility but deprecated

  // Authentication methods
  async login(credentials: LoginRequest): Promise<{ user: User; tokens: TokenResponse }> {
    console.log('🔐 AuthRepository.login delegating to AuthService');
    
    const tokens = await authService.login(credentials);
    const user = User.fromProfile(tokens.user);
    
    console.log('🔐 Login successful via AuthService:', { userId: user.userId, email: user.email });
    
    return { user, tokens };
  }

  async register(userData: RegisterRequest): Promise<{ user: User; tokens: TokenResponse }> {
    console.log('🔐 AuthRepository.register delegating to AuthService');
    
    const tokens = await authService.register(userData);
    const user = User.fromProfile(tokens.user);
    
    return { user, tokens };
  }

  async logout(): Promise<void> {
    console.log('🔐 AuthRepository.logout delegating to AuthService');
    await authService.logout();
  }

  // Token management
  async refreshToken(_refreshToken: string): Promise<RefreshTokenResponse> {
    console.log('🔐 AuthRepository.refreshToken delegating to AuthService (ignoring parameter - using httpOnly cookies)');
    return authService.refreshTokens();
  }

  getStoredTokens(): { accessToken: string | null; refreshToken: string | null } {
    console.warn('⚠️ getStoredTokens deprecated - tokens are now in httpOnly cookies');
    return authService.getStoredTokens();
  }

  storeTokens(accessToken: string, refreshToken: string): void {
    console.warn('⚠️ storeTokens deprecated - tokens are now in httpOnly cookies');
    authService.storeTokens(accessToken, refreshToken);
  }

  clearTokens(): void {
    console.warn('⚠️ clearTokens deprecated - use logout() instead');
    authService.clearTokens();
  }

  // User management
  async getCurrentUser(): Promise<User | null> {
    try {
      console.log('🔐 AuthRepository.getCurrentUser delegating to AuthService');
      const profile = await authService.getCurrentUser();
      return User.fromProfile(profile);
    } catch (error) {
      console.log('🔐 getCurrentUser failed:', error);
      return null; // Not authenticated
    }
  }

  async updateUser(user: User): Promise<User> {
    console.log('🔐 AuthRepository.updateUser delegating to AuthService');
    const profile = user.toProfile();
    const updatedProfile = await authService.updateUser(profile);
    return User.fromProfile(updatedProfile);
  }

  // Password management
  async requestPasswordReset(email: string): Promise<void> {
    console.log('🔐 AuthRepository.requestPasswordReset delegating to AuthService');
    await authService.forgotPassword(email);
  }

  async resetPassword(token: string, newPassword: string): Promise<void> {
    console.log('🔐 AuthRepository.resetPassword delegating to AuthService');
    await authService.resetPassword(token, newPassword);
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    console.log('🔐 AuthRepository.changePassword delegating to AuthService');
    await authService.changePassword(currentPassword, newPassword);
  }

  // Email verification
  async verifyEmail(token: string): Promise<void> {
    console.log('🔐 AuthRepository.verifyEmail delegating to AuthService');
    await authService.verifyEmail(token);
  }

  async resendVerificationEmail(): Promise<void> {
    console.log('🔐 AuthRepository.resendVerificationEmail delegating to AuthService');
    await authService.resendVerificationEmail();
  }

  // Session management
  isAuthenticated(): boolean {
    return authService.isAuthenticated();
  }

  getAuthHeaders(): Record<string, string> {
    console.warn('⚠️ getAuthHeaders deprecated - using httpOnly cookies + CSRF');
    const csrfToken = authService.getCSRFToken();
    return {
      'Content-Type': 'application/json',
      ...(csrfToken && { 'X-CSRF-Token': csrfToken }),
    };
  }



  // Additional helper methods for legacy compatibility
  async getAuthStatus(): Promise<{ authenticated: boolean; user?: User }> {
    const status = await authService.getAuthStatus();
    return {
      authenticated: status.authenticated,
      user: status.user ? User.fromProfile(status.user) : undefined
    };
  }

  // Store user profile for backwards compatibility
  storeUserProfile(_user: User): void {
    console.warn('⚠️ storeUserProfile deprecated - user profile managed by httpOnly cookies');
  }

  // Store full token response for backwards compatibility
  storeTokenResponse(_tokenResponse: TokenResponse): void {
    console.warn('⚠️ storeTokenResponse deprecated - tokens managed by httpOnly cookies');
  }
} 