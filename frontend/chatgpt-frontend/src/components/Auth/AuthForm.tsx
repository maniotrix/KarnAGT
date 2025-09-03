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
import Logo from '../ui/Logo';
import { validators } from '../../utils/validationUtils';

// Modular validation schemas using reusable validators
const loginSchema = z.object({
  email: validators.email,
  password: validators.loginPassword,
});

const registerSchema = z.object({
  email: validators.email,
  password: validators.password,
  confirmPassword: validators.passwordConfirm,
  fullName: validators.fullName,
  // username: validators.username, // Disabled for now
}).refine(
  (data) => data.password === data.confirmPassword,
  {
    message: "Passwords don't match",
    path: ["confirmPassword"],
  }
);

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
          // username: data.username, // Disabled for now
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center py-8 px-6 sm:py-12 sm:px-8 lg:px-12 overflow-y-auto" style={{ height: 'auto', minHeight: '100vh' }}>
      <div className="max-w-md w-full space-y-8">
        <div>
          <div className="flex flex-col items-center">
            <div className="mb-4">
              <Logo size="lg" />
            </div>
            <h2 className="text-3xl font-extrabold text-gray-900 dark:text-gray-100">
              KarnAGT
            </h2>
          </div>
          <p className="mt-4 text-center text-sm text-gray-600 dark:text-gray-400">
            {isLoginMode ? 'Sign in to your account' : 'Create a new account'}
          </p>
          <div className="mt-2 text-center">
            <Link
              to="/home"
              className="text-xs text-blue-600 dark:text-blue-400 hover:text-blue-500 dark:hover:text-blue-300 transition-colors"
            >
              ← Back to Home
            </Link>
          </div>
        </div>

        {/* Google Sign-in Button - Primary Option */}
        <div className="mt-8">
          <GoogleSignInButton
            onSuccess={() => {
              toast.success('Google login successful', 'You have been signed in successfully');
            }}
            onError={(error) => {
              toast.error('Google login failed', error);
            }}
          />
        </div>

        {/* Divider */}
        <div className="mt-6">
          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-gray-300 dark:border-gray-600" />
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-2 bg-gray-50 dark:bg-gray-900 text-gray-500 dark:text-gray-400">Or sign {isLoginMode ? 'in' : 'up'} with email</span>
            </div>
          </div>
        </div>

        <form className="mt-6 space-y-6" onSubmit={handleSubmit(onSubmit)}>
          <div className="space-y-4">
            {/* Email Field */}
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Email address
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Mail className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                </div>
                <input
                  {...register('email')}
                  type="email"
                  autoComplete="email"
                  className={`appearance-none relative block w-full pl-10 pr-3 py-2 border ${
                    errors.email ? 'border-red-300 dark:border-red-600' : 'border-gray-300 dark:border-gray-600'
                  } placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm`}
                  placeholder="Enter your email"
                  disabled={isLoading}
                />
              </div>
                              {errors.email && (
                  <p className="mt-2 text-sm text-red-600 dark:text-red-400">{String(errors.email?.message || 'Invalid email')}</p>
                )}
            </div>

            {/* Password Field */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                Password
                {!isLoginMode && (
                  <span className="text-xs text-gray-500 dark:text-gray-400 ml-1">
                    (8+ chars, uppercase, lowercase, number)
                  </span>
                )}
              </label>
              <div className="mt-1 relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <Lock className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                </div>
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete={isLoginMode ? 'current-password' : 'new-password'}
                  className={`appearance-none relative block w-full pl-10 pr-10 py-2 border ${
                    errors.password ? 'border-red-300 dark:border-red-600' : 'border-gray-300 dark:border-gray-600'
                  } placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm`}
                  placeholder="Enter your password"
                  disabled={isLoading}
                />
                <button
                  type="button"
                  className="absolute inset-y-0 right-0 pr-3 flex items-center z-20 cursor-pointer hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                  onMouseDown={(e) => e.preventDefault()}
                  onTouchStart={(e) => e.preventDefault()}
                  onClick={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    setShowPassword(!showPassword);
                  }}
                >
                  {showPassword ? (
                    <EyeOff className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                  ) : (
                    <Eye className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                  )}
                </button>
              </div>
                              {errors.password && (
                  <p className="mt-2 text-sm text-red-600 dark:text-red-400">{String(errors.password.message)}</p>
                )}
            </div>

            {/* Registration-only fields */}
            {!isLoginMode && (
              <>
                {/* Confirm Password */}
                <div>
                  <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Confirm Password
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <Lock className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                    </div>
                    <input
                      {...register('confirmPassword')}
                      type={showConfirmPassword ? 'text' : 'password'}
                      autoComplete="new-password"
                      className={`appearance-none relative block w-full pl-10 pr-10 py-2 border ${
                        errors.confirmPassword ? 'border-red-300 dark:border-red-600' : 'border-gray-300 dark:border-gray-600'
                      } placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm`}
                      placeholder="Confirm your password"
                      disabled={isLoading}
                    />
                    <button
                      type="button"
                      className="absolute inset-y-0 right-0 pr-3 flex items-center z-20 cursor-pointer hover:text-gray-600 dark:hover:text-gray-300 transition-colors"
                      onMouseDown={(e) => e.preventDefault()}
                      onTouchStart={(e) => e.preventDefault()}
                      onClick={(e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        setShowConfirmPassword(!showConfirmPassword);
                      }}
                    >
                      {showConfirmPassword ? (
                        <EyeOff className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                      ) : (
                        <Eye className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                      )}
                    </button>
                  </div>
                                      {errors.confirmPassword && (
                      <p className="mt-2 text-sm text-red-600 dark:text-red-400">{String(errors.confirmPassword.message)}</p>
                    )}
                </div>

                {/* Full Name */}
                <div>
                  <label htmlFor="fullName" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Full Name (optional)
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                    </div>
                    <input
                      {...register('fullName')}
                      type="text"
                      autoComplete="name"
                      className="appearance-none relative block w-full pl-10 pr-3 py-2 border border-gray-300 dark:border-gray-600 placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm"
                      placeholder="Enter your full name"
                      disabled={isLoading}
                    />
                  </div>
                </div>

                {/* Username */}
                {/* <div>
                  <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Username (optional)
                  </label>
                  <div className="mt-1 relative">
                    <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                      <User className="h-5 w-5 text-gray-400 dark:text-gray-500" />
                    </div>
                    <input
                      {...register('username')}
                      type="text"
                      autoComplete="username"
                      className={`appearance-none relative block w-full pl-10 pr-3 py-2 border ${
                        errors.username ? 'border-red-300 dark:border-red-600' : 'border-gray-300 dark:border-gray-600'
                      } placeholder-gray-500 dark:placeholder-gray-400 text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm`}
                      placeholder="Choose a username"
                      disabled={isLoading}
                    />
                  </div>
                                      {errors.username && (
                      <p className="mt-2 text-sm text-red-600 dark:text-red-400">{String(errors.username.message)}</p>
                    )}
                </div> */}
              </>
            )}
          </div>

          <div>
            <button
              type="submit"
              disabled={isLoading}
              className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isLoading && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              {isLoading ? 'Please wait...' : (isLoginMode ? 'Sign In' : 'Sign Up')}
            </button>
          </div>



          <div className="mt-4 text-center">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {isLoginMode ? "Don't have an account? " : "Already have an account? "}
              <button 
                type="button"
                onClick={toggleMode}
                className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 font-medium"
              >
                {isLoginMode ? 'Sign up' : 'Sign in'}
              </button>
            </p>
          </div>

          {/* Terms and Legal Links */}
          <div className="mt-4 text-center">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {!isLoginMode && "By signing up, you agree to our "}
              <a href="/terms" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline hover:no-underline transition-all">
                Terms & Conditions
              </a>
              {!isLoginMode && " and "}
              {!isLoginMode && (
                <a href="/privacy-policy" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline hover:no-underline transition-all">
                  Privacy Policy
                </a>
              )}
              {isLoginMode && (
                <span>
                  <span className="mx-1">·</span>
                  <a href="/help" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline hover:no-underline transition-all">
                    Need Help?
                  </a>
                </span>
              )}
            </p>
          </div>
        </form>
      </div>
    </div>
  );
}; 