// Domain Entity: Conversation - Migrated from existing types/chat.ts
import { ConversationResponse, ConversationCreate } from '../../types/chat';
import { Message } from './Message';

export interface ConversationData {
  readonly id: string;
  readonly conversationId: string;
  readonly title: string;
  readonly description?: string;
  readonly status: string;
  readonly modelName?: string;
  readonly temperature?: number;
  readonly maxTokens?: number;
  readonly memoryEnabled: boolean;
  readonly messageCount: number;
  readonly totalTokensUsed: number;
  readonly totalCostUsd: number;
  readonly isPinned: boolean;
  readonly isShared: boolean;
  readonly topics: string[];
  readonly tags: string[];
  readonly userRating?: number;
  readonly qualityScore?: number;
  readonly createdAt: Date;
  readonly updatedAt: Date;
  readonly lastMessageAt?: Date;
  readonly latestUserMessage?: string;
  readonly messages?: Message[];
}

export class Conversation implements ConversationData {
  constructor(
    public readonly id: string,
    public readonly conversationId: string,
    public readonly title: string,
    public readonly description: string | undefined,
    public readonly status: string,
    public readonly modelName: string | undefined,
    public readonly temperature: number | undefined,
    public readonly maxTokens: number | undefined,
    public readonly memoryEnabled: boolean,
    public readonly messageCount: number,
    public readonly totalTokensUsed: number,
    public readonly totalCostUsd: number,
    public readonly isPinned: boolean,
    public readonly isShared: boolean,
    public readonly topics: string[],
    public readonly tags: string[],
    public readonly userRating: number | undefined,
    public readonly qualityScore: number | undefined,
    public readonly createdAt: Date,
    public readonly updatedAt: Date,
    public readonly lastMessageAt: Date | undefined,
    public readonly latestUserMessage: string | undefined,
    public readonly messages?: Message[]
  ) {}

  // Factory method from existing ConversationResponse
  static fromBackendResponse(response: ConversationResponse): Conversation {
    const messages = response.messages?.map(msg => Message.fromBackendResponse(msg));
    
    return new Conversation(
      response.id.toString(),
      response.conversation_id,
      response.title,
      response.description,
      response.status,
      response.model_name,
      response.temperature,
      response.max_tokens,
      response.memory_enabled,
      response.message_count,
      response.total_tokens_used,
      response.total_cost_usd,
      response.is_pinned,
      response.is_shared,
      response.topics,
      response.tags,
      response.user_rating,
      response.quality_score,
      new Date(response.created_at),
      new Date(response.updated_at),
      response.last_message_at ? new Date(response.last_message_at) : undefined,
      response.latest_user_message,
      messages
    );
  }

  // Factory method for creating new conversations
  static create(data: {
    title?: string;
    memoryEnabled?: boolean;
    modelName?: string;
    temperature?: number;
    maxTokens?: number;
    metadata?: Record<string, any>;
  }): Conversation {
    const id = crypto.randomUUID();
    const conversationId = crypto.randomUUID();
    const now = new Date();
    
    return new Conversation(
      id,
      conversationId,
      data.title || 'New Conversation',
      undefined,
      'active',
      data.modelName,
      data.temperature,
      data.maxTokens,
      data.memoryEnabled ?? true,
      0,
      0,
      0,
      false,
      false,
      [],
      [],
      undefined,
      undefined,
      now,
      now,
      undefined,
      undefined,
      []
    );
  }

  // Domain business methods
  isEmpty(): boolean {
    return this.messageCount === 0;
  }

  hasMessages(): boolean {
    return this.messageCount > 0;
  }

  isActive(): boolean {
    return this.status === 'active';
  }

  isArchived(): boolean {
    return this.status === 'archived';
  }

  canDelete(): boolean {
    return !this.isPinned;
  }

  canShare(): boolean {
    return this.hasMessages() && this.isActive();
  }

  getLastMessageDate(): Date | null {
    return this.lastMessageAt || null;
  }

  getTotalCost(): string {
    return `$${this.totalCostUsd.toFixed(4)}`;
  }

  getAverageRating(): number {
    return this.userRating || 0;
  }

  hasHighQuality(): boolean {
    return (this.qualityScore || 0) > 0.8;
  }

  // Add a message (business rule)
  addMessage(message: Message): Conversation {
    const updatedMessages = [...(this.messages || []), message];
    
    return new Conversation(
      this.id,
      this.conversationId,
      this.title,
      this.description,
      this.status,
      this.modelName,
      this.temperature,
      this.maxTokens,
      this.memoryEnabled,
      this.messageCount + 1,
      this.totalTokensUsed + (message.totalTokens || 0),
      this.totalCostUsd + (message.costUsd || 0),
      this.isPinned,
      this.isShared,
      this.topics,
      this.tags,
      this.userRating,
      this.qualityScore,
      this.createdAt,
      new Date(),
      new Date(),
      updatedMessages
    );
  }

  // Convert to backend ConversationCreate format
  toBackendCreateFormat(): ConversationCreate {
    return {
      title: this.title,
      is_shared: this.isShared,
      memory_config: this.memoryEnabled ? {
        enabled: true,
        max_turns: 10,
        summary_threshold: 5,
      } : undefined,
      metadata: {
        model_name: this.modelName,
        temperature: this.temperature,
        max_tokens: this.maxTokens,
      },
    };
  }

  // Convert to backend ConversationResponse format
  toBackendResponse(): ConversationResponse {
    return {
      id: parseInt(this.id),
      conversation_id: this.conversationId,
      title: this.title,
      description: this.description,
      status: this.status,
      model_name: this.modelName,
      temperature: this.temperature,
      max_tokens: this.maxTokens,
      memory_enabled: this.memoryEnabled,
      message_count: this.messageCount,
      total_tokens_used: this.totalTokensUsed,
      total_cost_usd: this.totalCostUsd,
      is_pinned: this.isPinned,
      is_shared: this.isShared,
      topics: this.topics,
      tags: this.tags,
      user_rating: this.userRating,
      quality_score: this.qualityScore,
      created_at: this.createdAt.toISOString(),
      updated_at: this.updatedAt.toISOString(),
      last_message_at: this.lastMessageAt?.toISOString(),
      messages: this.messages?.map(msg => msg.toBackendResponse()),
    };
  }
} 