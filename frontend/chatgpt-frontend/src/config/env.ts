// Environment configuration based on backend structure
export const ENV = {
  // Backend API Configuration
  API_BASE_URL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
  API_VERSION: process.env.REACT_APP_API_VERSION || 'v1',
  
  // Storage Keys
  ACCESS_TOKEN_KEY: 'chat_access_token',
  REFRESH_TOKEN_KEY: 'chat_refresh_token',
  USER_PROFILE_KEY: 'chat_user_profile',
  
  // Feature Flags
  ENABLE_ANALYTICS: process.env.REACT_APP_ENABLE_ANALYTICS === 'true',
  ENABLE_MEMORY: process.env.REACT_APP_ENABLE_MEMORY === 'true',
  ENABLE_FILES: process.env.REACT_APP_ENABLE_FILES === 'true',
  DEBUG_MODE: process.env.REACT_APP_DEBUG_MODE === 'true',
} as const;

// API Endpoints matching your backend structure
export const API_ENDPOINTS = {
  // Auth endpoints from your backend/app/api/v1/endpoints/auth.py
  AUTH: {
    STATUS: '/api/v1/auth/status',
    REGISTER: '/api/v1/auth/register',
    LOGIN: '/api/v1/auth/login',
    REFRESH: '/api/v1/auth/refresh',
    LOGOUT: '/api/v1/auth/logout',
    ME: '/api/v1/auth/me',
    FORGOT_PASSWORD: '/api/v1/auth/forgot-password',
    RESET_PASSWORD: '/api/v1/auth/reset-password',
    VERIFY_EMAIL: '/api/v1/auth/verify-email',
    CHANGE_PASSWORD: '/api/v1/auth/change-password',
  },
  
  // Chat endpoints from your backend/app/api/v1/endpoints/chat.py
  CHAT: {
    CONVERSATIONS: '/api/v1/chat/conversations',
    CONVERSATION_DETAIL: (id: string) => `/api/v1/chat/conversations/${id}`,
    CONVERSATION_MESSAGES: (id: string) => `/api/v1/chat/conversations/${id}/messages`,
    SEND_MESSAGE: (id: string) => `/api/v1/chat/conversations/${id}/messages`,
    STREAM_MESSAGE: (id: string) => `/api/v1/chat/conversations/${id}/stream`,
    SHARE_CONVERSATION: (id: string) => `/api/v1/chat/conversations/${id}/share`,
    BULK_CONVERSATIONS: '/api/v1/chat/conversations/bulk',
    TEST_STREAMING: '/api/v1/chat/stream/test',
  },
  
  // Other endpoints
  MEMORY: '/api/v1/memory',
  FILES: '/api/v1/files',
  TOOLS: '/api/v1/tools',
  ANALYTICS: '/api/v1/analytics',
} as const;

export const buildApiUrl = (endpoint: string): string => {
  return `${ENV.API_BASE_URL}${endpoint}`;
}; 