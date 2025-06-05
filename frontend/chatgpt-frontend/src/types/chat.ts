import { Message, UseChatOptions } from '@ai-sdk/react';

export interface ChatMessage extends Message {
  // Extend AI SDK Message with our custom properties
  cost?: number;
  model?: string;
  tokenUsage?: {
    prompt: number;
    completion: number;
    total: number;
  };
}

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: Error | null;
  status: 'ready' | 'submitted' | 'streaming' | 'error';
}

export interface ChatConfig extends UseChatOptions {
  // Our custom configuration extending AI SDK options
  apiUrl?: string;
  enableCostTracking?: boolean;
  maxMessages?: number;
}

export interface ConversationInfo {
  id: string;
  title: string;
  messageCount: number;
  createdAt: Date;
  updatedAt: Date;
} 