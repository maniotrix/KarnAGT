// Authentication types matching backend/app/models/schemas/auth_schemas.py

export type SubscriptionTier = 'free' | 'pro' | 'enterprise';

// Exact UserProfile from your backend/app/models/schemas/auth_schemas.py line 155
export interface UserProfile {
  id: number;
  user_id: string;
  email: string;
  username?: string;
  full_name?: string;
  avatar_url?: string;
  bio?: string;
  subscription_tier: SubscriptionTier;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login_at?: string;
}

// Exact UserLogin from your backend line 47
export interface LoginRequest {
  email: string;
  password: string;
  remember_me?: boolean;
}

// Exact UserRegister from your backend line 13
export interface RegisterRequest {
  email: string;
  password: string;
  confirm_password: string;
  full_name?: string;
  username?: string;
}

// Exact TokenResponse from your backend line 52
export interface TokenResponse {
  success: boolean;
  message: string;
  timestamp: string;
  access_token: string;
  refresh_token: string;
  token_type: string; // "bearer"
  expires_in: number;
  user: UserProfile;
  csrf_token?: string; // CSRF token for frontend use (httpOnly cookies system)
}

// Exact TokenRefresh from your backend line 64
export interface RefreshTokenRequest {
  refresh_token: string;
}

// Exact TokenRefreshResponse from your backend line 69
export interface RefreshTokenResponse {
  success: boolean;
  message: string;
  timestamp: string;
  access_token: string;
  expires_in: number;
  csrf_token?: string; // CSRF token for frontend use (httpOnly cookies system)
}

// Exact PasswordReset from your backend line 74
export interface PasswordResetRequest {
  email: string;
}

export interface PasswordResetResponse {
  success: boolean;
  message: string;
  timestamp: string;
}

// Frontend auth state
export interface AuthState {
  user: UserProfile | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  isInitialized: boolean; // Track if auth initialization is complete
  error: string | null;
}

export interface AuthContextType extends AuthState {
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  refreshAuth: () => Promise<void>;
  clearError: () => void;
  updateUser: (user: Partial<UserProfile>) => void;
  checkQuota: () => { used: number; total: number; percentage: number };
} 