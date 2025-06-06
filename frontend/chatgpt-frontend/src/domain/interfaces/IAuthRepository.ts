// Repository Interface: Auth - Domain contract for authentication
import { User } from '../entities/User';
import { LoginRequest, RegisterRequest, TokenResponse, RefreshTokenResponse } from '../../types/auth';

export interface IAuthRepository {
  // Authentication
  login(credentials: LoginRequest): Promise<{ user: User; tokens: TokenResponse }>;
  register(userData: RegisterRequest): Promise<{ user: User; tokens: TokenResponse }>;
  logout(): Promise<void>;
  
  // Token management
  refreshToken(refreshToken: string): Promise<RefreshTokenResponse>;
  getStoredTokens(): { accessToken: string | null; refreshToken: string | null };
  storeTokens(accessToken: string, refreshToken: string): void;
  clearTokens(): void;
  
  // User management
  getCurrentUser(): Promise<User | null>;
  updateUser(user: User): Promise<User>;
  
  // Password management
  requestPasswordReset(email: string): Promise<void>;
  resetPassword(token: string, newPassword: string): Promise<void>;
  changePassword(currentPassword: string, newPassword: string): Promise<void>;
  
  // Email verification
  verifyEmail(token: string): Promise<void>;
  resendVerificationEmail(): Promise<void>;
  
  // Session management
  isAuthenticated(): boolean;
  getAuthHeaders(): Record<string, string>;
} 