/**
 * Frontend validation utilities using Zod
 * Reusable validation functions to match backend security validation
 */

import { z } from 'zod';

/**
 * Email validation with security checks
 */
export const createEmailValidator = (maxLength: number = 320) => {
  return z
    .string()
    .email('Invalid email address')
    .max(maxLength, 'Email too long')
    .refine(
      (val) => !val || !val.includes('..'),
      'Email cannot contain consecutive dots'
    )
    .refine(
      (val) => !val || (!val.startsWith('.') && !val.endsWith('.')),
      'Email cannot start or end with a dot'
    )
    .refine((val) => {
      if (!val) return true;
      const domain = val.split('@')[1];
      return domain && domain.length <= 253;
    }, 'Email domain too long');
};

/**
 * Password validation with strength requirements
 */
export const createPasswordValidator = (minLength: number = 8, maxLength: number = 128) => {
  return z
    .string()
    .min(minLength, `Password must be at least ${minLength} characters`)
    .max(maxLength, 'Password too long')
    .regex(/[A-Z]/, 'Password must contain at least one uppercase letter')
    .regex(/[a-z]/, 'Password must contain at least one lowercase letter')
    .regex(/\d/, 'Password must contain at least one number');
};

/**
 * Simple password validator for login (no strength requirements)
 */
export const createLoginPasswordValidator = (maxLength: number = 128) => {
  return z
    .string()
    .min(1, 'Password is required')
    .max(maxLength, 'Password too long');
};

/**
 * Text input sanitization (for names, etc.)
 */
export const createSanitizedTextValidator = (maxLength: number, fieldName: string = 'Field') => {
  return z
    .string()
    .max(maxLength, `${fieldName} too long`)
    .refine(
      (val) => !val || !/[<>{}\\|`"']/.test(val),
      `${fieldName} contains invalid characters`
    )
    .refine(
      (val) => !val || !/\s{3,}/.test(val),
      `${fieldName} contains excessive whitespace`
    )
    .refine(
      (val) => !val || !/[\x00-\x1f\x7f-\x9f]/.test(val),
      `${fieldName} contains invalid characters`
    )
    .optional();
};

/**
 * Username validation with security checks
 */
export const createUsernameValidator = (minLength: number = 3, maxLength: number = 100) => {
  const reservedUsernames = [
    'admin', 'administrator', 'root', 'user', 'test', 'api', 'www',
    'mail', 'ftp', 'support', 'help', 'info', 'contact', 'null',
    'undefined', 'system', 'service', 'public', 'private', 'static',
    'app', 'application', 'server', 'database', 'db', 'auth', 'login'
  ];

  return z
    .string()
    .optional()
    .refine(
      (val) => !val || val.length >= minLength,
      `Username must be at least ${minLength} characters`
    )
    .refine(
      (val) => !val || val.length <= maxLength,
      'Username too long'
    )
    .refine(
      (val) => !val || /^[a-zA-Z0-9_-]+$/.test(val),
      'Username can only contain letters, numbers, hyphens, and underscores'
    )
    .refine(
      (val) => !val || !reservedUsernames.includes(val.toLowerCase()),
      'Username is reserved'
    )
    .refine(
      (val) => !val || !/^\d+$/.test(val),
      'Username cannot be all numbers'
    )
    .refine(
      (val) => !val || !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(val),
      'Username cannot look like a UUID'
    );
};

/**
 * Password confirmation validator
 */
export const createPasswordConfirmValidator = (maxLength: number = 128) => {
  return z
    .string()
    .min(1, 'Please confirm your password')
    .max(maxLength, 'Password too long');
};

/**
 * Generic token validator (for secure tokens like password reset, email verification)
 */
export const createTokenValidator = (maxLength: number = 500, tokenType: string = 'token') => {
  return z
    .string()
    .min(1, `${tokenType} is required`)
    .max(maxLength, `${tokenType} too long`)
    .refine(
      (val) => !val || /^[A-Za-z0-9._-]+$/.test(val),
      `Invalid ${tokenType} format`
    )
    .refine(
      (val) => !val || !['test', 'fake', 'invalid', 'demo', '123456'].includes(val.toLowerCase()),
      `Invalid ${tokenType}`
    );
};

/**
 * Pre-configured validators for common use cases
 */
export const validators = {
  // Email validators
  email: createEmailValidator(),
  emailShort: createEmailValidator(255),

  // Password validators
  password: createPasswordValidator(),
  loginPassword: createLoginPasswordValidator(),
  passwordConfirm: createPasswordConfirmValidator(),

  // Text validators
  fullName: createSanitizedTextValidator(255, 'Full name'),
  shortText: createSanitizedTextValidator(100, 'Text'),
  longText: createSanitizedTextValidator(500, 'Text'),

  // Username
  username: createUsernameValidator(),

  // Tokens
  resetToken: createTokenValidator(500, 'reset token'),
  verificationToken: createTokenValidator(500, 'verification token'),
};

