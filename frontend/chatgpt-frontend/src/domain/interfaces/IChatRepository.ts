// Repository Interface: Chat - Domain contract for data access
import { Message } from '../entities/Message';
import { Conversation } from '../entities/Conversation';
import { StreamMessage, StreamEvent } from '../../types/chat';

export interface IChatRepository {
  // Conversation management
  getConversations(): Promise<Conversation[]>;
  getConversation(conversationId: string): Promise<Conversation>;
  createConversation(conversation: Conversation): Promise<Conversation>;
  updateConversation(conversation: Conversation): Promise<Conversation>;
  deleteConversation(conversationId: string): Promise<void>;
  shareConversation(conversationId: string): Promise<{ shareUrl: string }>;

  // Message management
  getMessages(conversationId: string, options?: {
    limit?: number;
    offset?: number;
  }): Promise<{ messages: Message[]; pagination: any }>;
  
  sendMessage(conversationId: string, message: Message): Promise<Message>;
  
  // Streaming support (AI SDK integration)
  streamMessage(
    conversationId: string, 
    message: StreamMessage,
    callbacks: {
      onStart?: () => void;
      onToken?: (token: string) => void;
      onComplete?: (message: Message) => void;
      onError?: (error: Error) => void;
    }
  ): Promise<ReadableStream>;

  // AI SDK integration
  createAISDKFetch(): (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
} 