// Chat API service connecting backend streaming to AI SDK
import { 
  ConversationCreate, 
  ConversationResponse, 
  MessageCreate, 
  MessageResponse,
  StreamMessage,
  StreamEvent
} from '../types/chat';
import { API_ENDPOINTS, buildApiUrl, ENV } from '../config/env';

class ChatApiService {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem(ENV.ACCESS_TOKEN_KEY);
    return {
      'Content-Type': 'application/json',
      ...(token && { Authorization: `Bearer ${token}` }),
    };
  }

  // GET /api/v1/chat/conversations
  async getConversations(): Promise<ConversationResponse[]> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATIONS), {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch conversations');
    }

    const result = await response.json();
    // Extract data array from paginated response
    return result.data || [];
  }

  // POST /api/v1/chat/conversations
  async createConversation(data: ConversationCreate): Promise<ConversationResponse> {
    const response = await fetch(buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATIONS), {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error('Failed to create conversation');
    }

    return response.json();
  }

  // GET /api/v1/chat/conversations/{id}
  async getConversation(conversationId: string): Promise<ConversationResponse> {
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATION_DETAIL(conversationId)),
      {
        method: 'GET',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to fetch conversation');
    }

    const result = await response.json();
    // Extract conversation from detailed response and attach recent messages
    const conversation = result.conversation;
    if (result.recent_messages) {
      conversation.messages = result.recent_messages;
    }
    return conversation;
  }

  // GET /api/v1/chat/conversations/{id}/messages
  async getMessages(
    conversationId: string, 
    options: { limit?: number; offset?: number } = {}
  ): Promise<{ messages: MessageResponse[]; pagination: any }> {
    const { limit = 20, offset = 0 } = options;
    
    const url = new URL(buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATION_MESSAGES(conversationId)));
    url.searchParams.set('limit', limit.toString());
    url.searchParams.set('offset', offset.toString());
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: this.getAuthHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to fetch messages');
    }

    const result = await response.json();
    return {
      messages: result.data || [],
      pagination: result.pagination || {}
    };
  }

  // POST /api/v1/chat/conversations/{id}/messages
  async sendMessage(conversationId: string, message: MessageCreate): Promise<MessageResponse> {
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.SEND_MESSAGE(conversationId)),
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
        body: JSON.stringify(message),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to send message');
    }

    return response.json();
  }

  // DELETE /api/v1/chat/conversations/{id}
  async deleteConversation(conversationId: string): Promise<void> {
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.CONVERSATION_DETAIL(conversationId)),
      {
        method: 'DELETE',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to delete conversation');
    }
  }

  // Share conversation - POST /api/v1/chat/conversations/{id}/share
  async shareConversation(conversationId: string): Promise<{ share_url: string }> {
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.SHARE_CONVERSATION(conversationId)),
      {
        method: 'POST',
        headers: this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to share conversation');
    }

    return response.json();
  }

  // POST /api/v1/chat/conversations/{id}/messages/{messageId}/edit/stream
  async editMessage(
    conversationId: string,
    messageId: string,
    content: string
  ): Promise<Response> {
    const response = await fetch(
      buildApiUrl(API_ENDPOINTS.CHAT.EDIT_MESSAGE_STREAM(conversationId, messageId)),
      {
        method: 'POST',
        headers: {
          ...this.getAuthHeaders(),
          'Accept': 'text/event-stream',
          'Cache-Control': 'no-cache',
        },
        body: JSON.stringify({ content }),
      }
    );

    if (!response.ok) {
      const errorData = await response.text().catch(() => 'Failed to start streaming edit');
      throw new Error(errorData || 'Failed to start streaming edit');
    }

    return response;
  }

  // **CRITICAL**: AI SDK Integration - Custom fetch for streaming
  createAISDKFetch() {
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
      };

      // Call your backend streaming endpoint
      const response = await fetch(
        buildApiUrl(API_ENDPOINTS.CHAT.STREAM_MESSAGE(conversationId)),
        {
          method: 'POST',
          headers: {
            ...this.getAuthHeaders(),
            'Accept': 'text/event-stream',
            'Cache-Control': 'no-cache',
          },
          body: JSON.stringify(streamMessage),
        }
      );

      if (!response.ok) {
        throw new Error(`Stream request failed: ${response.statusText}`);
      }

      // Transform your backend SSE stream to AI SDK compatible format
      return this.transformSSEToAISDK(response);
    };
  }

  // Transform your backend SSE stream to AI SDK compatible format
  private transformSSEToAISDK(response: Response): Response {
    // Create a reference to the instance method
    const transformMessage = this.transformBackendMessageToAISDK.bind(this);
    
    const readable = new ReadableStream({
      start(controller) {
        const reader = response.body?.getReader();
        if (!reader) {
          controller.close();
          return;
        }

        const decoder = new TextDecoder();
        let buffer = '';

        const pump = async (): Promise<void> => {
          try {
            const { done, value } = await reader.read();
            
            if (done) {
              controller.close();
              return;
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
              if (line.trim() === '') {
                // Skip empty lines
                continue;
              }
              
              if (line.startsWith('event: ')) {
                // Skip event type lines - we get the type from data
                continue;
              }
              
              if (line.startsWith('data: ')) {
                const data = line.slice(6);
                console.log('Processing data line:', data);
                
                if (data === '[DONE]') {
                  controller.close();
                  return;
                }

                try {
                  const event: StreamEvent = JSON.parse(data);
                  console.log('SSE Event received:', event);
                  
                  // Transform backend events to AI SDK data stream format
                  let aiSDKData: string;
                  
                  // The backend sends events in format: {"type": event_type, "data": {...}}
                  switch (event.type) {
                    case 'token':
                      // AI SDK data stream format for text: 0:"content"\n
                      // Backend format: {"type": "token", "data": {"content": "...", ...}}
                      aiSDKData = `0:${JSON.stringify(event.data?.content || '')}\n`;
                      break;
                      
                    case 'completion':
                      // AI SDK data stream format for finish: d:{"finishReason":"stop","usage":{...}}\n
                      const finishData: any = {
                        finishReason: 'stop'
                      };
                      
                      // Add usage if available
                      if (event.data?.usage) {
                        finishData.usage = {
                          promptTokens: event.data.usage.prompt_tokens || 0,
                          completionTokens: event.data.usage.completion_tokens || 0
                        };
                      }
                      
                      // Send finish message and then close stream
                      console.log('Sending finish message:', finishData);
                      const finishLine = `d:${JSON.stringify(finishData)}\n`;
                      controller.enqueue(new TextEncoder().encode(finishLine));
                      
                      // Close the stream
                      controller.close();
                      return;
                      
                    case 'end':
                    case 'stream_end':
                      // Stream completed - close immediately
                      console.log('Stream end received, closing...');
                      controller.close();
                      return;
                      
                    case 'error':
                      // AI SDK data stream format for error: 3:"error message"\n
                      aiSDKData = `3:${JSON.stringify(event.data?.error || 'Stream error')}\n`;
                      break;
                      
                    case 'stream_start':
                    case 'heartbeat':
                      // Skip these events
                      continue;
                      
                    default:
                      console.log('Unknown SSE event type:', event.type, event);
                      continue;
                  }

                  // Send data stream format directly (already includes \n)
                  console.log('Sending to AI SDK:', aiSDKData.trim());
                  controller.enqueue(new TextEncoder().encode(aiSDKData));
                  
                } catch (parseError) {
                  console.error('Failed to parse SSE data:', parseError, 'Raw data:', data);
                }
              }
            }

            pump();
          } catch (error) {
            console.error('Stream error:', error);
            controller.error(error);
          }
        };

        pump();
      },
    });

    return new Response(readable, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  }

  // Transform backend MessageResponse to AI SDK Message format
  private transformBackendMessageToAISDK(backendMessage: MessageResponse) {
    return {
      id: backendMessage.message_id,
      role: backendMessage.role,
      content: backendMessage.content,
      createdAt: new Date(backendMessage.created_at),
      // Additional backend-specific fields
      message_id: backendMessage.message_id,
      parent_message_id: backendMessage.parent_message_id,
      total_tokens: backendMessage.total_tokens,
      cost_usd: backendMessage.cost_usd,
      model_name: backendMessage.model_name,
      attachments: backendMessage.attachments,
      metadata: backendMessage.metadata,
    };
  }

  // Transform AI SDK message to backend format
  transformAISDKMessageToBackend(aiMessage: any): MessageCreate {
    return {
      content: aiMessage.content,
      role: aiMessage.role,
      parent_message_id: aiMessage.parent_message_id,
      attachments: aiMessage.attachments || [],
      metadata: aiMessage.metadata || {},
    };
  }
}

export const chatApi = new ChatApiService(); 