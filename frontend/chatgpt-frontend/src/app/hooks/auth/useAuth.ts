// Auth Query Hook - TanStack Query integration with Clean Architecture
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AuthRepository } from '../../../infrastructure/repositories/AuthRepository';
import { LoginUser, RegisterUser } from '../../use-cases/auth';
import type { LoginUserRequest, RegisterUserRequest } from '../../use-cases/auth';

// Repository instance (in real app, this would be injected via DI)
const authRepository = new AuthRepository();
const loginUseCase = new LoginUser(authRepository);
const registerUseCase = new RegisterUser(authRepository);

// Query keys
export const authKeys = {
  all: ['auth'] as const,
  user: () => [...authKeys.all, 'user'] as const,
  status: () => [...authKeys.all, 'status'] as const,
} as const;

// Get current user query
export function useCurrentUser() {
  return useQuery({
    queryKey: authKeys.user(),
    queryFn: () => authRepository.getCurrentUser(),
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: (failureCount, error: any) => {
      // Don't retry on 401 (unauthorized)
      if (error?.message?.includes('401') || error?.status === 401) {
        return false;
      }
      return failureCount < 2;
    },
  });
}

// Auth status query
export function useAuthStatus() {
  return useQuery({
    queryKey: authKeys.status(),
    queryFn: () => authRepository.getAuthStatus(),
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}

// Login mutation
export function useLogin() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (credentials: LoginUserRequest) => loginUseCase.execute(credentials),
    onSuccess: (data) => {
      // Update user cache immediately
      queryClient.setQueryData(authKeys.user(), data.user);
      queryClient.setQueryData(authKeys.status(), { 
        authenticated: true, 
        user: data.user 
      });
      
      // Invalidate and refetch related queries
      queryClient.invalidateQueries({ queryKey: authKeys.all });
    },
    onError: () => {
      // Clear auth data on login failure
      queryClient.setQueryData(authKeys.user(), null);
      queryClient.setQueryData(authKeys.status(), { authenticated: false });
    },
  });
}

// Register mutation
export function useRegister() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (userData: RegisterUserRequest) => registerUseCase.execute(userData),
    onSuccess: (data) => {
      // Update user cache immediately
      queryClient.setQueryData(authKeys.user(), data.user);
      queryClient.setQueryData(authKeys.status(), { 
        authenticated: true, 
        user: data.user 
      });
      
      // Invalidate and refetch related queries
      queryClient.invalidateQueries({ queryKey: authKeys.all });
    },
    onError: () => {
      // Clear auth data on registration failure
      queryClient.setQueryData(authKeys.user(), null);
      queryClient.setQueryData(authKeys.status(), { authenticated: false });
    },
  });
}

// Logout mutation
export function useLogout() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => authRepository.logout(),
    onSuccess: () => {
      // Disable fetching for auth queries
      queryClient.setQueryDefaults(authKeys.user(), {
        enabled: false,
      });
      queryClient.setQueryDefaults(authKeys.status(), {
        enabled: false,
      });
      
      // Set data as null instead of just clearing cache
      queryClient.setQueryData(authKeys.user(), null);
      queryClient.setQueryData(authKeys.status(), { authenticated: false });
      
      // Then clear all cached data
      queryClient.clear();
    },
    onError: () => {
      // Same approach for error case
      queryClient.setQueryDefaults(authKeys.user(), {
        enabled: false,
      });
      queryClient.setQueryDefaults(authKeys.status(), {
        enabled: false,
      });
      queryClient.setQueryData(authKeys.user(), null);
      queryClient.setQueryData(authKeys.status(), { authenticated: false });
      queryClient.clear();
    },
  });
}

// Refresh token mutation
export function useRefreshToken() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (refreshToken: string) => authRepository.refreshToken(refreshToken),
    onSuccess: () => {
      // Invalidate user data to refetch with new token
      queryClient.invalidateQueries({ queryKey: authKeys.all });
    },
  });
} 