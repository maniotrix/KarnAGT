// Use Case: Send Message - Business logic for sending chat messages
import { IChatRepository } from '../../../domain/interfaces/IChatRepository';
import { Message } from '../../../domain/entities/Message';
import { Conversation } from '../../../domain/entities/Conversation';

export interface SendMessageRequest {
  conversationId: string;
  content: string;
  parentMessageId?: string;
}

export interface SendMessageResponse {
  message: Message;
  conversation: Conversation;
  success: boolean;
}

export class SendMessage {
  constructor(private chatRepository: IChatRepository) {}

  async execute(request: SendMessageRequest): Promise<SendMessageResponse> {
    try {
      // Input validation
      if (!request.content?.trim()) {
        throw new Error('Message content cannot be empty');
      }

      if (request.content.length > 4000) {
        throw new Error('Message content cannot exceed 4000 characters');
      }

      // Business logic: Create message entity first to validate
      const messageData = {
        conversationId: request.conversationId,
        content: request.content.trim(),
        role: 'user' as const,
        parentMessageId: request.parentMessageId,
      };

      // This will validate through domain entity
      const message = Message.create(messageData);

      // Send through repository
      const sentMessage = await this.chatRepository.sendMessage(
        request.conversationId,
        message
      );

      // Get updated conversation
      const conversation = await this.chatRepository.getConversation(request.conversationId);
      if (!conversation) {
        throw new Error('Conversation not found after message sent');
      }

      return {
        message: sentMessage,
        conversation,
        success: true,
      };
    } catch (error) {
      throw new Error(
        error instanceof Error ? error.message : 'Failed to send message'
      );
    }
  }
} 