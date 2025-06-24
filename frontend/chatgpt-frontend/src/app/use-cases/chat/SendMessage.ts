// Use Case: Send Message - Business logic for sending chat messages
import { IChatRepository } from '../../../domain/interfaces/IChatRepository';
import { Message } from '../../../domain/entities/Message';
import { Conversation } from '../../../domain/entities/Conversation';

export interface SendMessageRequest {
  conversationId: string;
  content: string;
  parentMessageId?: string;
  stagingFiles?: Array<{ file_id: string; s3_key: string }>;
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
      if (!request.content?.trim() && (!request.stagingFiles || request.stagingFiles.length === 0)) {
        throw new Error('Message must have content or images');
      }

      if (request.content && request.content.length > 4000) {
        throw new Error('Message content cannot exceed 4000 characters');
      }

      // Validate staging files if present
      if (request.stagingFiles && request.stagingFiles.length > 0) {
        if (request.stagingFiles.length > 10) {
          throw new Error('Cannot attach more than 10 images per message');
        }

        // Validate each staging file has required fields
        for (const file of request.stagingFiles) {
          if (!file.file_id || !file.s3_key) {
            throw new Error('Invalid staging file data');
          }
        }
      }

      // Business logic: Create message entity first to validate
      const messageData = {
        conversationId: request.conversationId,
        content: request.content?.trim() || '',
        role: 'user' as const,
        parentMessageId: request.parentMessageId,
        stagingFiles: request.stagingFiles,
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