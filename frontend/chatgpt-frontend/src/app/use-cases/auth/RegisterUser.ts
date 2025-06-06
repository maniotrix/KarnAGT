// Use Case: Register User - Business logic for user registration
import { IAuthRepository } from '../../../domain/interfaces/IAuthRepository';
import { User } from '../../../domain/entities/User';
import { RegisterRequest, TokenResponse } from '../../../types/auth';

export interface RegisterUserRequest {
  email: string;
  password: string;
  confirmPassword: string;
  fullName?: string;
  username?: string;
}

export interface RegisterUserResponse {
  user: User;
  tokens: TokenResponse;
  success: boolean;
  message: string;
}

export class RegisterUser {
  constructor(private authRepository: IAuthRepository) {}

  async execute(request: RegisterUserRequest): Promise<RegisterUserResponse> {
    try {
      // Input validation
      if (!request.email || !request.password) {
        throw new Error('Email and password are required');
      }

      if (!request.email.includes('@')) {
        throw new Error('Invalid email format');
      }

      if (request.password.length < 8) {
        throw new Error('Password must be at least 8 characters long');
      }

      if (request.password !== request.confirmPassword) {
        throw new Error('Passwords do not match');
      }

      // Business logic: Password strength validation
      if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(request.password)) {
        throw new Error('Password must contain at least one uppercase letter, one lowercase letter, and one number');
      }

      // Username validation if provided
      if (request.username && request.username.length < 3) {
        throw new Error('Username must be at least 3 characters long');
      }

      if (request.username && !/^[a-zA-Z0-9_]+$/.test(request.username)) {
        throw new Error('Username can only contain letters, numbers, and underscores');
      }

      // Create registration request
      const registerData: RegisterRequest = {
        email: request.email.toLowerCase().trim(),
        password: request.password,
        confirm_password: request.confirmPassword,
        full_name: request.fullName?.trim(),
        username: request.username?.toLowerCase().trim(),
      };

      // Execute registration through repository
      const { user, tokens } = await this.authRepository.register(registerData);

      // Store tokens for immediate session
      this.authRepository.storeTokenResponse(tokens);

      return {
        user,
        tokens,
        success: true,
        message: user.needsVerification() 
          ? 'Registration successful! Please check your email to verify your account.'
          : 'Registration successful!',
      };
    } catch (error) {
      throw new Error(
        error instanceof Error ? error.message : 'Registration failed'
      );
    }
  }
} 