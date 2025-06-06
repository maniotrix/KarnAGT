// API Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const API_ENDPOINTS = {
  CHAT: '/api/v1/chat',
  AUTH: '/api/v1/auth',
  CONVERSATIONS: '/api/v1/chat/conversations',
  STREAM: '/api/v1/chat/conversations/:id/stream',
} as const;

// API Client Configuration
export class ApiClient {
  private baseUrl: string;
  private headers: Record<string, string>;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
    this.headers = {
      'Content-Type': 'application/json',
    };
  }

  setAuthToken(token: string) {
    this.headers['Authorization'] = `Bearer ${token}`;
  }

  removeAuthToken() {
    delete this.headers['Authorization'];
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    
    const config: RequestInit = {
      ...options,
      headers: {
        ...this.headers,
        ...options.headers,
      },
    };

    const response = await fetch(url, config);

    if (!response.ok) {
      throw new Error(`API Error: ${response.status} ${response.statusText}`);
    }

    return response.json();
  }

  // Streaming-specific method for chat
  async streamChat(
    conversationId: string,
    message: string,
    options: { signal?: AbortSignal } = {}
  ): Promise<ReadableStream> {
    const url = `${this.baseUrl}${API_ENDPOINTS.STREAM.replace(':id', conversationId)}`;
    
    const response = await fetch(url, {
      method: 'POST',
      headers: this.headers,
      body: JSON.stringify({ content: message }),
      signal: options.signal,
    });

    if (!response.ok) {
      throw new Error(`Stream Error: ${response.status} ${response.statusText}`);
    }

    return response.body as ReadableStream;
  }
}

// Global API client instance
export const apiClient = new ApiClient();

// Utility functions for common API operations
export const apiUtils = {
  setAuthToken: (token: string) => apiClient.setAuthToken(token),
  removeAuthToken: () => apiClient.removeAuthToken(),
  
  // Chat proxy for AI SDK integration
  chatProxy: async (messages: any[], options: any = {}) => {
    // This will be the proxy endpoint that AI SDK calls
    // It translates AI SDK format to our FastAPI backend format
    return apiClient.request('/api/chat/proxy', {
      method: 'POST',
      body: JSON.stringify({ messages, ...options }),
    });
  },
}; 