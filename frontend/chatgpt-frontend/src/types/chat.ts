// Backend types from your chat_schemas.py

// Image attachment object structure (from backend)
export interface ImageAttachment {
  type?: string;
  file_id: string;
  openai_file_id?: string;
  filename: string;
  original_filename?: string;
  content_type?: string;
  size?: number;
  dimensions?: { width: number; height: number };
  urls?: {
    display?: string;
    api?: string;
    thumbnail?: string;
    [key: string]: string | undefined;
  };
  s3_key?: string;
  uploaded_at?: string;
}

// Exact MessageCreate from your backend line 15
export interface MessageCreate {
  content: string;
  role: 'user' | 'assistant' | 'system';
  parent_message_id?: string;
  attachments?: string[];
  metadata?: Record<string, any>;
  staging_files?: Record<string, any>; // New format: {"images": [...], "vectors": [...], "unknown": [...]}
}

// MessageUpdate interface for editing messages
export interface MessageUpdate {
  content?: string;
  metadata?: Record<string, any>;
}

// Exact MessageResponse from your backend line 121
export interface MessageResponse {
  id: number;
  message_id: string;
  conversation_id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  parent_message_id?: string;
  total_tokens?: number;
  cost_usd?: number;
  model_name?: string;
  attachments?: string[] | ImageAttachment[]; // Can be either string IDs or full attachment objects
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

// Exact ConversationCreate from your backend line 28
export interface ConversationCreate {
  title?: string;
  is_shared?: boolean;
  memory_config?: {
    enabled: boolean;
    max_turns: number;
    summary_threshold: number;
  };
  metadata?: Record<string, any>;
}

// Exact ConversationResponse from your backend line 65
export interface ConversationResponse {
  id: number;
  conversation_id: string;
  title: string;
  description?: string;
  status: string;
  model_name?: string;
  temperature?: number;
  max_tokens?: number;
  memory_enabled: boolean;
  message_count: number;
  total_tokens_used: number;
  total_cost_usd: number;
  is_pinned: boolean;
  is_shared: boolean;
  topics: string[];
  tags: string[];
  user_rating?: number;
  quality_score?: number;
  created_at: string;
  updated_at: string;
  last_message_at?: string;
  messages?: MessageResponse[];
}

// Exact StreamMessage from your backend line 35
export interface StreamMessage {
  conversation_id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  parent_message_id?: string;
  include_memory?: boolean;
  stream_mode?: 'text' | 'json' | 'function_call';
  attachments?: string[];
  metadata?: Record<string, any>;
  staging_files?: Record<string, any>; // New format: {"images": [...], "vectors": [...], "unknown": [...]}
}

// SSE Event types from your backend streaming
export interface StreamEvent {
  type: 'message' | 'token' | 'end' | 'error' | 'metadata' | 'completion' | 'stream_end' | 'stream_start' | 'heartbeat';
  data: any;
  id?: string;
}

export interface StreamTokenEvent {
  type: 'token';
  content: string;
  message_id: string;
}

export interface StreamMessageEvent {
  type: 'message';
  message: MessageResponse;
}

export interface StreamEndEvent {
  type: 'end';
  message: MessageResponse;
  conversation: ConversationResponse;
}

export interface StreamErrorEvent {
  type: 'error';
  error: string;
  message?: string;
}

// Simple Message interface that matches frontend needs - replaces AISDKMessage
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  createdAt?: Date;
  // Backend specific fields (using snake_case as they come from backend)
  message_id?: string;
  parent_message_id?: string;
  total_tokens?: number;
  cost_usd?: number;
  model_name?: string;
  attachments?: string[] | ImageAttachment[]; // Can be either string IDs or full attachment objects
  metadata?: Record<string, any>;
  // LOCAL IMAGE DATA: Keep actual image data for immediate display after send
  localImages?: Array<{
    fileId: string;
    filename: string;
    file: File;
    blobUrl: string;
    s3Key: string;
  }>;
}

// Chat state for components
export interface ChatState {
  conversation: ConversationResponse | null;
  isStreaming: boolean;
  isLoading: boolean;
  error: string | null;
  tokenUsage: {
    total: number;
    cost: number;
    model: string;
  };
}

// Chat hook options
export interface ChatOptions {
  conversationId?: string;
  memoryEnabled?: boolean;
  onStreamStart?: () => void;
  onStreamEnd?: (data: StreamEndEvent) => void;
  onTokenUpdate?: (token: StreamTokenEvent) => void;
  onError?: (error: StreamErrorEvent) => void;
  onConversationUpdate?: (conversation: ConversationResponse) => void;
} 