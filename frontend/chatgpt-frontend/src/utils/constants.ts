// Application Constants
export const APP_CONFIG = {
  NAME: 'KarnAGT',
  VERSION: '1.0.0',
  MAX_MESSAGE_LENGTH: 4000,
  MAX_MESSAGES_PER_CONVERSATION: 100,
  AUTO_SCROLL_THRESHOLD: 100,
} as const;

// Chat Configuration
export const CHAT_CONFIG = {
  DEFAULT_MODEL: 'gpt-4',
  SUPPORTED_MODELS: ['gpt-4', 'gpt-3.5-turbo'],
  TYPING_INDICATOR_DELAY: 500,
  STREAM_TIMEOUT: 30000,
} as const;

// UI Constants
export const UI_CONFIG = {
  ANIMATION_DURATION: 300,
  DEBOUNCE_DELAY: 300,
  MOBILE_BREAKPOINT: 768,
  SCROLL_BEHAVIOR: 'smooth' as ScrollBehavior,
} as const;

// Storage Keys
export const STORAGE_KEYS = {
  AUTH_TOKEN: 'chat_auth_token',
  USER_PREFERENCES: 'chat_user_preferences',
  CONVERSATION_HISTORY: 'chat_conversation_history',
  THEME: 'chat_theme',
} as const;

// Error Messages
export const ERROR_MESSAGES = {
  NETWORK_ERROR: 'Network error. Please check your connection.',
  AUTH_ERROR: 'Authentication failed. Please log in again.',
  RATE_LIMIT: 'Too many requests. Please wait a moment.',
  SERVER_ERROR: 'Server error. Please try again later.',
  INVALID_INPUT: 'Invalid input. Please check your message.',
} as const;

// Success Messages
export const SUCCESS_MESSAGES = {
  MESSAGE_SENT: 'Message sent successfully',
  CHAT_CLEARED: 'Chat cleared successfully',
  SETTINGS_SAVED: 'Settings saved successfully',
} as const; 