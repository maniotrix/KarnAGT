// AuthForm - Modern Auth Component using React Hook Form + Zod + Tailwind
import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useLogin, useRegister, useCurrentUser } from '../../app/hooks/auth';
import { useToast } from '../../app/stores/uiStore';
import { Eye, EyeOff, User, Mail, Lock, Loader2 } from 'lucide-react';
import { useNavigate, Link } from 'react-router-dom';
import { GoogleSignInButton } from './GoogleSignInButton';

// Zod validation schemas
const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
});

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z
    .string()
    .min(8, 'Password must be at least 8 characters')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/\d/, 'Password must contain at least one number'),
  confirmPassword: z.string().min(1, 'Please confirm your password'),
  fullName: z.string().optional(),
  username: z
    .string()
    .optional()
    .refine(
      (val) => !val || (val.length >= 3 && /^[a-zA-Z0-9_-]+$/.test(val)),
      'Username must be at least 3 characters and contain only letters, numbers, hyphens, and underscores'
    ),
}).refine((data) => data.password === data.confirmPassword, {
  message: "Passwords don't match",
  path: ["confirmPassword"],
});

type LoginForm = z.infer<typeof loginSchema>;
type RegisterForm = z.infer<typeof registerSchema>;

// Update the component interface to accept isRegisterMode
interface AuthFormProps {
  isRegisterMode?: boolean;
}

export const AuthForm: React.FC<AuthFormProps> = ({ isRegisterMode = false }) => {
  const [isLoginMode, setIsLoginMode] = useState(!isRegisterMode);
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const navigate = useNavigate();
  const toast = useToast();
  const loginMutation = useLogin();
  const registerMutation = useRegister();
  const { data: user } = useCurrentUser();

  // React Hook Form setup with proper typing
  const form = useForm<any>({
    resolver: zodResolver(isLoginMode ? loginSchema : registerSchema),
    mode: 'onChange',
  });

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      navigate('/');
    }
  }, [user, navigate]);

  // Sync the login/register mode with the prop
  useEffect(() => {
    setIsLoginMode(!isRegisterMode);
  }, [isRegisterMode]);

  const { register, handleSubmit, formState: { errors }, reset } = form;

  const isLoading = loginMutation.isPending || registerMutation.isPending;

  const onSubmit = async (data: any) => {
    try {
      if (isLoginMode) {
        const result = await loginMutation.mutateAsync({
          email: data.email,
          password: data.password,
        });
        toast.success('Login successful!', `Welcome back, ${result.user.getDisplayName()}`);
        navigate('/');
      } else {
        const result = await registerMutation.mutateAsync({
          email: data.email,
          password: data.password,
          confirmPassword: data.confirmPassword,
          fullName: data.fullName,
          username: data.username,
        });
        toast.success('Registration successful!', result.message);
        navigate('/');
      }
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Authentication failed';
      toast.error(isLoginMode ? 'Login failed' : 'Registration failed', errorMessage);
    }
  };

  const toggleMode = () => {
    setIsLoginMode(!isLoginMode);
    reset(); // Clear form when switching modes
    navigate(isLoginMode ? '/register' : '/login');
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8">
        <div>
          <h2 className="mt-6 text-center text-3xl font-extrabold text-gray-900">
            ChatGPT Clone
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            {isLoginMode ? 'Sign in to your account' : 'Create a new account'}
          </p>
        </div>

        <form className="mt-8 space-y-6" onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-4">
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700">
                Email address
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  {...register('email')}
                  type="email"
                  autoComplete="email"
                  className={`appearance-none relative block w-full pl-10 pr-3 py-2 border ${
                    errors.email ? 'border-red-300' : 'border-gray-300'
                  } placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm`}
                  placeholder="Enter your email"
                  disabled={isLoading}
                />
              </div>
                              {errors.email && (
                  <p className="mt-2 text-sm text-red-600">{String(errors.email?.message || 'Invalid email')}</p>
                )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700">
                Password
                {!isLoginMode && (
                  <span className="text-xs text-gray-500 ml-1">
                    (8+ chars, uppercase, lowercase, number)
                  </span>
                )}
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400" />
                </div>
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={isLoginMode ? 'current-password' : 'new-password'}
                  className={`appearance-none relative block w-full pl-10 pr-10 py-2 border ${
                    errors.password ? 'border-red-300' : 'border-gray-300'
                  } placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm`}
                  placeholder="Enter your password"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center"
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400" />
                  )}
                </button>
              </div>
                              {errors.password && (
                  <p className="mt-2 text-sm text-red-600">{String(errors.password.message)}</p>
                )}
            </div>

            {/* Registration-only fields */}
            {!isLoginMode && (
              <>
                {/* Confirm Password */}
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700">
                    Confirm Password
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      {...register('confirmPassword')}
                      type={showConfirmPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      className={`appearance-none relative block w-full pl-10 pr-10 py-2 border ${
                        errors.confirmPassword ? 'border-red-300' : 'border-gray-300'
                      } placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm`}
                      placeholder="Confirm your password"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-3 flex items-center"
                      onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-5 w-5 text-gray-400" />
                      ) : (
                        <Eye className="h-5 w-5 text-gray-400" />
                      )}
                    </button>
                  </div>
                                      {errors.confirmPassword && (
                      <p className="mt-2 text-sm text-red-600">{String(errors.confirmPassword.message)}</p>
                    )}
                </div>

                {/* Full Name */}
                <div>
                  <label htmlFor="fullName" className="block text-sm font-medium text-gray-700">
                    Full Name (optional)
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      {...register('fullName')}
                      type="text"
                      autoComplete="name"
                      className="appearance-none relative block w-full pl-10 pr-3 py-2 border border-gray-300 placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                      placeholder="Enter your full name"
                      disabled={isLoading}
                    />
                  </div>
                </div>

                {/* Username */}
                <div>
                  <label htmlFor="username" className="block text-sm font-medium text-gray-700">
                    Username (optional)
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-gray-400" />
                    </div>
                    <input
                      {...register('username')}
                      type="text"
                      autoComplete="username"
                      className={`appearance-none relative block w-full pl-10 pr-3 py-2 border ${
                        errors.username ? 'border-red-300' : 'border-gray-300'
                      } placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm`}
                      placeholder="Choose a username"
                      disabled={isLoading}
                    />
                  </div>
                                      {errors.username && (
                      <p className="mt-2 text-sm text-red-600">{String(errors.username.message)}</p>
                    )}
                </div>
              </>
            )}
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              {isLoading ? 'Please wait...' : (isLoginMode ? 'Sign In' : 'Sign Up')}
            </button>
          </div>

          {/* Divider */}
          <div className="mt-6">
            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t border-gray-300" />
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-gray-500">Or continue with</span>
              </div>
            </div>
          </div>

          {/* Google Sign-in Button */}
          <div className="mt-6">
            <GoogleSignInButton
              onSuccess={() => {
                toast.success('Google login successful', 'You have been signed in successfully');
              }}
              onError={(error) => {
                toast.error('Google login failed', error);
              }}
            />
          </div>

          <div className="mt-4 text-center">
            <p className="text-sm text-gray-600">
              {isLoginMode ? "Don't have an account? " : "Already have an account? "}
              <button 
                type="button"
                onClick={toggleMode}
                className="text-blue-600 hover:text-blue-800 font-medium"
              >
                {isLoginMode ? 'Sign up' : 'Sign in'}
              </button>
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}; 