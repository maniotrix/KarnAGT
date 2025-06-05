// Authentication context with JWT and quota management
import React, { 
  createContext, 
  useContext, 
  useReducer, 
  useEffect, 
  useCallback,
  ReactNode 
} from 'react';
import { 
  AuthContextType, 
  AuthState, 
  LoginRequest, 
  RegisterRequest, 
  UserProfile 
} from '../types/auth';
import { authApi } from '../services/authApi';

// Auth reducer
type AuthAction =
  | { type: 'AUTH_START' }
  | { type: 'AUTH_SUCCESS'; payload: { user: UserProfile; accessToken: string; refreshToken: string } }
  | { type: 'AUTH_ERROR'; payload: string }
  | { type: 'AUTH_LOGOUT' }
  | { type: 'AUTH_INIT_COMPLETE' }
  | { type: 'CLEAR_ERROR' }
  | { type: 'UPDATE_USER'; payload: Partial<UserProfile> }
  | { type: 'TOKEN_REFRESH'; payload: { accessToken: string } };

const initialState: AuthState = {
  user: null,
  accessToken: null,
  refreshToken: null,
  isAuthenticated: false,
  isLoading: true, // Start loading to check stored tokens
  isInitialized: false, // Not initialized yet
  error: null,
};

function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'AUTH_START':
      return { ...state, isLoading: true, error: null };
    case 'AUTH_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        accessToken: action.payload.accessToken,
        refreshToken: action.payload.refreshToken,
        isAuthenticated: true,
        isLoading: false,
        isInitialized: true,
        error: null,
      };
    case 'AUTH_ERROR':
      return {
        ...state,
        user: null,
        accessToken: null,
        refreshToken: null,
        isAuthenticated: false,
        isLoading: false,
        isInitialized: true,
        error: action.payload,
      };
    case 'AUTH_LOGOUT':
      return {
        ...initialState,
        isLoading: false,
        isInitialized: true,
      };
    case 'AUTH_INIT_COMPLETE':
      return {
        ...state,
        isLoading: false,
        isInitialized: true,
      };
    case 'CLEAR_ERROR':
      return { ...state, error: null };
    case 'UPDATE_USER':
      return {
        ...state,
        user: state.user ? { ...state.user, ...action.payload } : null,
      };
    case 'TOKEN_REFRESH':
      return {
        ...state,
        accessToken: action.payload.accessToken,
      };
    default:
      return state;
  }
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Initialize auth on app start
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const { accessToken, refreshToken, user } = authApi.getStoredTokens();
        
        if (accessToken && refreshToken && user) {
          // Validate token with backend
          try {
            const status = await authApi.getAuthStatus();
            if (status.authenticated && status.user) {
              dispatch({
                type: 'AUTH_SUCCESS',
                payload: {
                  user: status.user,
                  accessToken,
                  refreshToken,
                },
              });
              return;
            }
          } catch (error) {
            console.log('Token validation failed, trying refresh...');
          }
          
          // Token invalid, try refresh
          try {
            const refreshResponse = await authApi.refreshToken(refreshToken);
            // Get fresh user data
            const userResponse = await authApi.getCurrentUser();
            authApi.storeTokens({
              ...refreshResponse,
              user: userResponse,
              refresh_token: refreshToken,
              token_type: 'bearer'
            } as any);
            
            dispatch({
              type: 'AUTH_SUCCESS',
              payload: {
                user: userResponse,
                accessToken: refreshResponse.access_token,
                refreshToken,
              },
            });
          } catch (refreshError) {
            console.error('Token refresh failed:', refreshError);
            // Refresh failed, clear tokens
            authApi.clearTokens();
            dispatch({ type: 'AUTH_LOGOUT' });
          }
        } else {
          // No stored tokens
          dispatch({ type: 'AUTH_INIT_COMPLETE' });
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
        authApi.clearTokens();
        dispatch({ type: 'AUTH_LOGOUT' });
      }
    };

    initializeAuth();
  }, []);



  // Define logout first to avoid dependency issues
  const logout = useCallback(async () => {
    try {
      if (state.accessToken) {
        await authApi.logout();
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      authApi.clearTokens();
      dispatch({ type: 'AUTH_LOGOUT' });
    }
  }, [state.accessToken]);

  // Auto-refresh token before expiry
  useEffect(() => {
    if (!state.refreshToken) return;

    const refreshInterval = setInterval(async () => {
      try {
        const refreshResponse = await authApi.refreshToken(state.refreshToken!);
        dispatch({
          type: 'TOKEN_REFRESH',
          payload: { accessToken: refreshResponse.access_token },
        });
      } catch (error) {
        console.error('Token refresh failed:', error);
        logout();
      }
    }, 14 * 60 * 1000); // Refresh every 14 minutes

    return () => clearInterval(refreshInterval);
  }, [state.refreshToken, logout]);

  const login = async (credentials: LoginRequest) => {
    dispatch({ type: 'AUTH_START' });
    try {
      const response = await authApi.login(credentials);
      authApi.storeTokens(response);
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: {
          user: response.user,
          accessToken: response.access_token,
          refreshToken: response.refresh_token,
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Login failed';
      dispatch({ type: 'AUTH_ERROR', payload: message });
      throw error;
    }
  };

  const register = async (data: RegisterRequest) => {
    dispatch({ type: 'AUTH_START' });
    try {
      // Clean up the data - remove empty optional fields
      const cleanData: RegisterRequest = {
        email: data.email,
        password: data.password,
        confirm_password: data.confirm_password,
        ...(data.full_name && data.full_name.trim() && { full_name: data.full_name.trim() }),
        ...(data.username && data.username.trim() && { username: data.username.trim() }),
      };
      
      const response = await authApi.register(cleanData);
      authApi.storeTokens(response);
      dispatch({
        type: 'AUTH_SUCCESS',
        payload: {
          user: response.user,
          accessToken: response.access_token,
          refreshToken: response.refresh_token,
        },
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Registration failed';
      dispatch({ type: 'AUTH_ERROR', payload: message });
      throw error;
    }
  };



  const refreshAuth = async () => {
    if (!state.refreshToken) {
      throw new Error('No refresh token available');
    }
    
    try {
      const response = await authApi.refreshToken(state.refreshToken);
      dispatch({
        type: 'TOKEN_REFRESH',
        payload: { accessToken: response.access_token },
      });
    } catch (error) {
      logout();
      throw error;
    }
  };

  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  const updateUser = (userUpdate: Partial<UserProfile>) => {
    dispatch({ type: 'UPDATE_USER', payload: userUpdate });
  };

  // Quota checking based on user subscription tier
  const checkQuota = () => {
    if (!state.user) {
      return { used: 0, total: 0, percentage: 0 };
    }

    // These match your backend quota limits
    const quotaLimits = {
      free: 100,
      pro: 1000,
      enterprise: 10000,
    };

    const total = quotaLimits[state.user.subscription_tier];
    // In a real app, you'd get this from the user profile or a separate endpoint
    const used = 0; // This would come from your backend user profile
    const percentage = (used / total) * 100;

    return { used, total, percentage };
  };

  const contextValue: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    refreshAuth,
    clearError,
    updateUser,
    checkQuota,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
} 