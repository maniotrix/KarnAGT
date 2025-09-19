// Infrastructure: ChatRepository - Migrated from existing services/chatApi.ts
import { IChatRepository } from '../../domain/interfaces/IChatRepository';
import { Message } from '../../domain/entities/Message';
import { Conversation } from '../../domain/entities/Conversation';
import { 
  ConversationResponse, 
  MessageResponse, 
  StreamMessage, 
  StreamEvent,
  MessageCreate
} from '../../types/chat';
import { API_ENDPOINTS, buildApiUrl, ENV } from '../../config/env';
import { authService } from '../../services/authService';

export class ChatRepository implements IChatRepository {
  /**
   * Get headers for authenticated requests
   * Now uses CSRF token instead of Authorization headers (httpOnly cookies system)
   */
  private getAuthHeaders(includeCsrf: boolean = false): HeadersInit {
    const headers: HeadersInit = {
      'Content-Type': 'application/json',
    };

    // Add CSRF token for mutating operations
    if (includeCsrf) {
      const csrfToken = authService.getCSRFToken();
      if (csrfToken) {
        headers['X-CSRF-Token'] = csrfToken;
      }
    }

    return headers;
  }

  // Conversation methods - migrated from existing chatApi.ts
  async getConversations(includeLatestUserMessage: boolean = true): Promise<Conversation[]> {
    const url = new URL(buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATIONS));
    if (includeLatestUserMessage) {
      url.searchParams.set('include_latest_user_message', 'true');
    }
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      credentials: 'include', // Send httpOnly cookies
      headers: this.getAuthHeaders(), // No CSRF needed for GET
    });

    if (!response.ok) {
      throw new Error('Failed to fetch conversations');
    }

    const result = await response.json();
    const conversationResponses: ConversationResponse[] = result.data || [];
    
    // Convert to domain entities
    return conversationResponses.map(conv => Conversation.fromBackendResponse(conv));
  }

  async getConversation(conversationId: string): Promise<Conversation> {
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATION_DETAIL(conversationId)),
      {
        method: 'GET',
        credentials: 'include', // Send httpOnly cookies
        headers: this.getAuthHeaders(), // No CSRF needed for GET
      }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch conversation');
    }

    const result = await response.json();
    const conversation = result.conversation;
    if (result.recent_messages) {
      conversation.messages = result.recent_messages;
    }
    
    // Convert to domain entity
    return Conversation.fromBackendResponse(conversation);
  }

  async createConversation(conversation: Conversation): Promise<Conversation> {
    console.log('💬 ChatRepository.createConversation called with:', { title: conversation.title });
    
    const createData = conversation.toBackendCreateFormat();
    console.log('💬 Sending create data:', createData);
    
    const response = await fetch(buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATIONS), {
      method: 'POST',
      credentials: 'include', // Send httpOnly cookies
      headers: this.getAuthHeaders(true), // ✅ CSRF required for POST
      body: JSON.stringify(createData),
    });

    console.log('💬 Create conversation response status:', response.status);

    if (!response.ok) {
      const error = await response.json();
      console.error('💬 Create conversation failed:', error);
      throw new Error('Failed to create conversation');
    }

    const conversationResponse: ConversationResponse = await response.json();
    console.log('💬 Create conversation successful:', conversationResponse);
    return Conversation.fromBackendResponse(conversationResponse);
  }

  async updateConversation(conversation: Conversation): Promise<Conversation> {
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATION_DETAIL(conversation.conversationId)),
      {
        method: 'PUT',
        credentials: 'include', // Send httpOnly cookies
        headers: this.getAuthHeaders(true), // ✅ CSRF required for PUT
        body: JSON.stringify(conversation.toBackendResponse()),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to update conversation');
    }

    const conversationResponse: ConversationResponse = await response.json();
    return Conversation.fromBackendResponse(conversationResponse);
  }

  async deleteConversation(conversationId: string): Promise<void> {
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATION_DETAIL(conversationId)),
      {
        method: 'DELETE',
        credentials: 'include', // Send httpOnly cookies
        headers: this.getAuthHeaders(true), // ✅ CSRF required for DELETE
      }
    );

    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
  }

  async shareConversation(conversationId: string): Promise<{ shareUrl: string }> {
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.SHARE_CONVERSATION(conversationId)),
      {
        method: 'POST',
        credentials: 'include', // Send httpOnly cookies
        headers: this.getAuthHeaders(true), // ✅ CSRF required for POST
      }
    );

    if (!response.ok) {
      throw new Error('Failed to share conversation');
    }

    const result = await response.json();
    return { shareUrl: result.share_url };
  }

  // Message methods
  async getMessages(
    conversationId: string, 
    options: { limit?: number; offset?: number } = {}
  ): Promise<{ messages: Message[]; pagination: any }> {
    const { limit = 20, offset = 0 } = options;
    
    const url = new URL(buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATION_MESSAGES(conversationId)));
    url.searchParams.set('limit', limit.toString());
    url.searchParams.set('offset', offset.toString());
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      credentials: 'include', // Send httpOnly cookies
      headers: this.getAuthHeaders(), // No CSRF needed for GET
    });

    if (!response.ok) {
      throw new Error('Failed to fetch messages');
    }

    const result = await response.json();
    const messageResponses: MessageResponse[] = result.data || [];
    
    // Convert to domain entities
    const messages = messageResponses.map(msg => Message.fromBackendResponse(msg));
    
    return {
      messages,
      pagination: result.pagination || {}
    };
  }

  async sendMessage(conversationId: string, message: Message): Promise<Message> {
    console.log('💬 ChatRepository.sendMessage called:', { conversationId, content: message.content.substring(0, 50) + '...' });
    
    const messageCreate = message.toBackendCreateFormat();
    console.log('💬 Sending message data:', messageCreate);
    
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.SEND_MESSAGE(conversationId)),
      {
        method: 'POST',
        credentials: 'include', // Send httpOnly cookies
        headers: this.getAuthHeaders(true), // ✅ CSRF required for POST
        body: JSON.stringify(messageCreate),
      }
    );

    console.log('💬 Send message response status:', response.status);

    if (!response.ok) {
      const error = await response.json();
      console.error('💬 Send message failed:', error);
      throw new Error('Failed to send message');
    }

    const messageResponse: MessageResponse = await response.json();
    console.log('💬 Send message successful:', messageResponse);
    return Message.fromBackendResponse(messageResponse);
  }

  // Streaming support - migrated from existing AI SDK integration
  async streamMessage(
    conversationId: string, 
    message: StreamMessage,
    callbacks: {
      onStart?: () => void;
      onToken?: (token: string) => void;
      onComplete?: (message: Message) => void;
      onError?: (error: Error) => void;
    }
  ): Promise<ReadableStream> {
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.STREAM_MESSAGE(conversationId)),
      {
        method: 'POST',
        credentials: 'include', // Send httpOnly cookies
        headers: {
          ...this.getAuthHeaders(true), // ✅ CSRF required for POST
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        body: JSON.stringify(message),
      }
    );

    if (!response.ok) {
      if (response.status === 429) {
        throw new Error('Conversation busy. Please wait or reload.');
      }
      throw new Error(`Stream request failed: ${response.statusText}`);
    }

    // Process the SSE stream
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('No readable stream available');
    }

    callbacks.onStart?.();

    return new ReadableStream({
      start(controller) {
        const pump = async (): Promise<void> => {
          try {
            const { done, value } = await reader.read();
            
            if (done) {
              controller.close();
              return;
            }

            // Process SSE chunks
            const chunk = new TextDecoder().decode(value);
            const lines = chunk.split('\n').filter(line => line.trim());
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const eventData = JSON.parse(line.slice(6));
                  
                  switch (eventData.type) {
                    case 'token':
                      callbacks.onToken?.(eventData.content);
                      break;
                    case 'end':
                      if (eventData.message) {
                        const message = Message.fromBackendResponse(eventData.message);
                        callbacks.onComplete?.(message);
                      }
                      break;
                    case 'error':
                      callbacks.onError?.(new Error(eventData.error));
                      break;
                  }
                } catch (error) {
                  console.warn('Failed to parse SSE data:', line);
                }
              }
            }

            controller.enqueue(value);
            return pump();
          } catch (error) {
            callbacks.onError?.(error as Error);
            controller.error(error);
          }
        };

        pump();
      }
    });
  }

  // AI SDK integration - migrated from existing implementation
  createAISDKFetch(): (input: RequestInfo | URL, init?: RequestInit) => Promise<Response> {
    return async (input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> => {
      // Parse AI SDK request
      const body = init.body ? JSON.parse(init.body as string) : {};
      const messages = body.messages || [];
      const conversationId = body.conversationId;

      if (!conversationId) {
        throw new Error('Conversation ID required for streaming');
      }

      // Transform AI SDK message to backend StreamMessage format
      const lastMessage = messages[messages.length - 1];
      if (!lastMessage) {
        throw new Error('No message to send');
      }

      const streamMessage: StreamMessage = {
        conversation_id: conversationId,
        content: lastMessage.content,
        role: lastMessage.role,
        parent_message_id: lastMessage.parent_message_id,
        include_memory: true,
        stream_mode: 'text',
        attachments: lastMessage.attachments || [],
        metadata: lastMessage.metadata || {},
        staging_files: lastMessage.staging_files || {},
      };

      // Call backend streaming endpoint
      const response = await fetch(
        buildApiUrl(API_ENDPOINTS.CHAT.STREAM_MESSAGE(conversationId)),
        {
          method: 'POST',
          credentials: 'include', // Send httpOnly cookies
          headers: {
            ...this.getAuthHeaders(true), // ✅ CSRF required for POST
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          body: JSON.stringify(streamMessage),
        }
      );

      if (!response.ok) {
        if (response.status === 429) {
          throw new Error('Conversation busy. Please wait or reload.');
        }
        throw new Error(`Stream request failed: ${response.statusText}`);
      }

      // Transform backend SSE stream to AI SDK compatible format
      return this.transformSSEToAISDK(response);
    };
  }

  private transformSSEToAISDK(response: Response): Response {
    const stream = new ReadableStream({
      start(controller) {
        const reader = response.body?.getReader();
        if (!reader) {
          controller.close();
          return;
        }

        const pump = async (): Promise<void> => {
          try {
            const { done, value } = await reader.read();
            
            if (done) {
              controller.close();
              return;
            }

            // Process backend SSE and convert to AI SDK format
            const chunk = new TextDecoder().decode(value);
            const lines = chunk.split('\n').filter(line => line.trim());
            
            for (const line of lines) {
              if (line.startsWith('data: ')) {
                try {
                  const eventData = JSON.parse(line.slice(6));
                  
                  // Convert backend events to AI SDK format
                  let aiSDKData;
                  switch (eventData.type) {
                    case 'token':
                      aiSDKData = {
                        type: 'text-delta',
                        textDelta: eventData.content
                      };
                      break;
                    case 'end':
                      aiSDKData = {
                        type: 'finish',
                        finishReason: 'stop'
                      };
                      break;
                    default:
                      continue;
                  }

                  const aiSDKLine = `data: ${JSON.stringify(aiSDKData)}\n\n`;
                  controller.enqueue(new TextEncoder().encode(aiSDKLine));
                } catch (error) {
                  console.warn('Failed to parse SSE data:', line);
                }
              }
            }

            return pump();
          } catch (error) {
            controller.error(error);
          }
        };

        pump();
      }
    });

    return new Response(stream, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  }
} 