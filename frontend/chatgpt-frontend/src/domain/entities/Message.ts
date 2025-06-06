// Domain Entity: Message - Migrated from existing types/chat.ts
import { MessageResponse, MessageCreate } from '../../types/chat';

export interface MessageData {
  readonly id: string;
  readonly messageId: string;
  readonly conversationId: string;
  readonly content: string;
  readonly role: 'user' | 'assistant' | 'system';
  readonly createdAt: Date;
  readonly updatedAt: Date;
  readonly parentMessageId?: string;
  readonly totalTokens?: number;
  readonly costUsd?: number;
  readonly modelName?: string;
  readonly attachments?: string[];
  readonly metadata?: Record<string, any>;
}

export class Message implements MessageData {
  constructor(
    public readonly id: string,
    public readonly messageId: string,
    public readonly conversationId: string,
    public readonly content: string,
    public readonly role: 'user' | 'assistant' | 'system',
    public readonly createdAt: Date,
    public readonly updatedAt: Date,
    public readonly parentMessageId?: string,
    public readonly totalTokens?: number,
    public readonly costUsd?: number,
    public readonly modelName?: string,
    public readonly attachments?: string[],
    public readonly metadata?: Record<string, any>
  ) {}

  // Factory method from existing MessageResponse
  static fromBackendResponse(response: MessageResponse): Message {
    return new Message(
      response.id.toString(),
      response.message_id,
      response.conversation_id,
      response.content,
      response.role,
      new Date(response.created_at),
      new Date(response.updated_at),
      response.parent_message_id,
      response.total_tokens,
      response.cost_usd,
      response.model_name,
      response.attachments,
      response.metadata
    );
  }

  // Factory method for creating new messages
  static create(data: {
    conversationId: string;
    content: string;
    role: 'user' | 'assistant' | 'system';
    parentMessageId?: string;
    attachments?: string[];
    metadata?: Record<string, any>;
  }): Message {
    const id = crypto.randomUUID();
    const messageId = crypto.randomUUID();
    const now = new Date();
    
    // Business rules
    if (!data.content.trim()) {
      throw new Error('Message content cannot be empty');
    }

    if (data.content.length > 10000) {
      throw new Error('Message content too long (max 10000 characters)');
    }

    return new Message(
      id,
      messageId,
      data.conversationId,
      data.content.trim(),
      data.role,
      now,
      now,
      data.parentMessageId,
      undefined,
      undefined,
      undefined,
      data.attachments,
      data.metadata
    );
  }

  // Domain business methods
  isFromUser(): boolean {
    return this.role === 'user';
  }

  isFromAssistant(): boolean {
    return this.role === 'assistant';
  }

  isSystem(): boolean {
    return this.role === 'system';
  }

  hasAttachments(): boolean {
    return !!this.attachments && this.attachments.length > 0;
  }

  getWordCount(): number {
    return this.content.split(/\s+/).length;
  }

  canEdit(): boolean {
    return this.isFromUser();
  }

  hasCost(): boolean {
    return !!this.costUsd && this.costUsd > 0;
  }

  // Convert to AI SDK format (reusing existing pattern)
  toAISDKFormat() {
    return {
      id: this.messageId,
      role: this.role,
      content: this.content,
      createdAt: this.createdAt,
    };
  }

  // Convert to backend MessageCreate format
  toBackendCreateFormat(): MessageCreate {
    return {
      content: this.content,
      role: this.role,
      parent_message_id: this.parentMessageId,
      attachments: this.attachments,
      metadata: this.metadata,
    };
  }

  // Convert to backend MessageResponse format
  toBackendResponse(): MessageResponse {
    return {
      id: parseInt(this.id),
      message_id: this.messageId,
      conversation_id: this.conversationId,
      content: this.content,
      role: this.role,
      parent_message_id: this.parentMessageId,
      total_tokens: this.totalTokens,
      cost_usd: this.costUsd,
      model_name: this.modelName,
      attachments: this.attachments,
      metadata: this.metadata,
      created_at: this.createdAt.toISOString(),
      updated_at: this.updatedAt.toISOString(),
    };
  }
} 