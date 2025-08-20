// Environment configuration based on backend structure
export const ENV = {
  // Backend API Configuration
  API_BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  API_VERSION: import.meta.env.VITE_API_VERSION || 'v1',
  
  // Google OAuth Configuration
  GOOGLE_CLIENT_ID: import.meta.env.VITE_GOOGLE_CLIENT_ID || 'your-google-client-id.apps.googleusercontent.com',
  
  // Storage Keys (DEPRECATED - tokens now in httpOnly cookies)
  ACCESS_TOKEN_KEY: 'chat_access_token', // ⚠️ DEPRECATED: Now in httpOnly cookie
  REFRESH_TOKEN_KEY: 'chat_refresh_token', // ⚠️ DEPRECATED: Now in httpOnly cookie
  USER_PROFILE_KEY: 'chat_user_profile', // ⚠️ DEPRECATED: User profiles cached in TanStack Query memory, not localStorage
  
  // Cookie Names (for httpOnly cookie + CSRF system)
  COOKIE_NAMES: {
    ACCESS_TOKEN: 'access_token',    // httpOnly cookie (backend manages)
    REFRESH_TOKEN: 'refresh_token',  // httpOnly cookie (backend manages)  
    CSRF_TOKEN: 'csrf_token',        // Regular cookie (JS reads this)
  },
  
  // Feature Flags
  ENABLE_ANALYTICS: import.meta.env.VITE_ENABLE_ANALYTICS === 'true',
  ENABLE_MEMORY: import.meta.env.VITE_ENABLE_MEMORY === 'true',
  ENABLE_FILES: import.meta.env.VITE_ENABLE_FILES === 'true',
  DEBUG_MODE: import.meta.env.VITE_DEBUG_MODE === 'true',
} as const;

// API Endpoints matching your backend structure
export const API_ENDPOINTS = {
  // Auth endpoints from your backend/app/api/v1/endpoints/auth.py
  AUTH: {
    STATUS: '/api/v1/auth/status',
    REGISTER: '/api/v1/auth/register',
    LOGIN: '/api/v1/auth/login',
    GOOGLE_LOGIN: '/api/v1/auth/google-login',
    REFRESH: '/api/v1/auth/refresh',
    LOGOUT: '/api/v1/auth/logout',
    ME: '/api/v1/auth/me',
    FORGOT_PASSWORD: '/api/v1/auth/forgot-password',
    RESET_PASSWORD: '/api/v1/auth/reset-password',
    VERIFY_EMAIL: '/api/v1/auth/verify-email',
    RESEND_VERIFICATION: '/api/v1/auth/resend-verification',
    CHANGE_PASSWORD: '/api/v1/auth/change-password',
  },
  
  // Chat endpoints from your backend/app/api/v1/endpoints/chat.py
  CHAT: {
    CONVERSATIONS: '/api/v1/chat/conversations',
    CONVERSATION_DETAIL: (id: string) => `/api/v1/chat/conversations/${id}`,
    CONVERSATION_MESSAGES: (id: string) => `/api/v1/chat/conversations/${id}/messages`,
    SEND_MESSAGE: (id: string) => `/api/v1/chat/conversations/${id}/messages`,
    STREAM_MESSAGE: (id: string) => `/api/v1/chat/conversations/${id}/stream`,
    EDIT_MESSAGE_STREAM: (conversationId: string, messageId: string) => `/api/v1/chat/conversations/${conversationId}/messages/${messageId}/edit/stream`,
    SHARE_CONVERSATION: (id: string) => `/api/v1/chat/conversations/${id}/share`,
    BULK_CONVERSATIONS: '/api/v1/chat/conversations/bulk',
    TEST_STREAMING: '/api/v1/chat/stream/test',
    TEST_EDIT_STREAMING: '/api/v1/chat/stream/test-edit',
    CANCEL_STREAM: (streamId: string) => `/api/v1/chat/stream/cancel/${streamId}`,
    CANCEL_ALL_STREAMS: '/api/v1/chat/stream/cancel-all',
    ACTIVE_STREAMS: '/api/v1/chat/stream/active',
  },
  
  // AI Files endpoints from your backend/app/api/v1/endpoints/ai_files.py
  AI_FILES: {
    STATUS: '/api/v1/ai-files/status',
    STAGING_BULK_UPLOAD: '/api/v1/ai-files/staging/bulk-upload',
    STAGING_DISCARD: (fileId: string) => `/api/v1/ai-files/staging/discard/${fileId}`,
    STAGING_BULK_DISCARD: '/api/v1/ai-files/staging/bulk-discard',
    STAGING_ADMIN_CLEANUP: '/api/v1/ai-files/staging/admin/cleanup',
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