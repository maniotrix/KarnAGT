// Use Case: Login User - Business logic for authentication
import { IAuthRepository } from '../../../domain/interfaces/IAuthRepository';
import { User } from '../../../domain/entities/User';
import { LoginRequest, TokenResponse } from '../../../types/auth';

export interface LoginUserRequest {
  email: string;
  password: string;
}

export interface LoginUserResponse {
  user: User;
  tokens: TokenResponse;
  success: boolean;
  message: string;
}

export class LoginUser {
  constructor(private authRepository: IAuthRepository) {}

  async execute(request: LoginUserRequest): Promise<LoginUserResponse> {
    try {
      // Validate input
      if (!request.email || !request.password) {
        throw new Error('Email and password are required');
      }

      if (!request.email.includes('@')) {
        throw new Error('Invalid email format');
      }

      // Business logic: Create login request
      const loginData: LoginRequest = {
        email: request.email.toLowerCase().trim(),
        password: request.password,
      };

      // Execute login through repository
      const { user, tokens } = await this.authRepository.login(loginData);

      // Store tokens for session
      this.authRepository.storeTokenResponse(tokens);

      return {
        user,
        tokens,
        success: true,
        message: 'Login successful',
      };
    } catch (error) {
      throw new Error(
        error instanceof Error ? error.message : 'Login failed'
      );
    }
  }
} 