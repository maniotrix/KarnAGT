// Chat Query Hooks - TanStack Query integration with Clean Architecture
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ChatRepository } from '../../../infrastructure/repositories/ChatRepository';
import { SendMessage } from '../../use-cases/chat';
import { Conversation } from '../../../domain/entities/Conversation';
import type { SendMessageRequest } from '../../use-cases/chat';

// Repository instance (in real app, this would be injected via DI)
const chatRepository = new ChatRepository();
const sendMessageUseCase = new SendMessage(chatRepository);

// Query keys
export const chatKeys = {
  all: ['chat'] as const,
  conversations: () => [...chatKeys.all, 'conversations'] as const,
  conversation: (id: string) => [...chatKeys.all, 'conversation', id] as const,
  messages: (conversationId: string) => [...chatKeys.all, 'messages', conversationId] as const,
} as const;

// Get all conversations
export function useConversations() {
  return useQuery({
    queryKey: chatKeys.conversations(),
    queryFn: () => chatRepository.getConversations(),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

// Get single conversation
export function useConversation(conversationId: string) {
  return useQuery({
    queryKey: chatKeys.conversation(conversationId),
    queryFn: () => chatRepository.getConversation(conversationId),
    enabled: !!conversationId,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}

// Get conversation messages
export function useConversationMessages(conversationId: string) {
  return useQuery({
    queryKey: chatKeys.messages(conversationId),
    queryFn: async () => {
      const result = await chatRepository.getMessages(conversationId);
      return result.messages;
    },
    enabled: !!conversationId,
    staleTime: 30 * 1000, // 30 seconds
  });
}

// Create new conversation
export function useCreateConversation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: { title?: string; firstMessage?: string }) => {
      // Create a conversation entity from the data
      const conversationData = {
        title: data.title || 'New Conversation',
        description: data.firstMessage || '',
      };
      const conversation = Conversation.create(conversationData);
      return chatRepository.createConversation(conversation);
    },
    onSuccess: (newConversation) => {
      // Add to conversations list
      queryClient.setQueryData(chatKeys.conversations(), (old: any) => {
        if (!old) return [newConversation];
        return [newConversation, ...old];
      });
      
      // Cache the new conversation
      queryClient.setQueryData(
        chatKeys.conversation(newConversation.id), 
        newConversation
      );
    },
  });
}

// Send message
export function useSendMessage() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (request: SendMessageRequest) => sendMessageUseCase.execute(request),
    onSuccess: (data) => {
      const { message, conversation } = data;
      
      // Update conversation cache
      queryClient.setQueryData(
        chatKeys.conversation(conversation.id), 
        conversation
      );
      
      // Update messages cache
      queryClient.setQueryData(
        chatKeys.messages(conversation.id), 
        (old: any) => {
          if (!old) return [message];
          return [...old, message];
        }
      );
      
      // Update conversations list (for last message, updated time)
      queryClient.setQueryData(chatKeys.conversations(), (old: any) => {
        if (!old) return [conversation];
        return old.map((conv: any) => 
          conv.id === conversation.id ? conversation : conv
        );
      });
    },
  });
}

// Delete conversation
export function useDeleteConversation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (conversationId: string) => 
      chatRepository.deleteConversation(conversationId),
    onSuccess: (_, conversationId) => {
      // Remove from conversations list
      queryClient.setQueryData(chatKeys.conversations(), (old: any) => {
        if (!old) return [];
        return old.filter((conv: any) => conv.id !== conversationId);
      });
      
      // Remove conversation cache
      queryClient.removeQueries({ 
        queryKey: chatKeys.conversation(conversationId) 
      });
      
      // Remove messages cache
      queryClient.removeQueries({ 
        queryKey: chatKeys.messages(conversationId) 
      });
    },
  });
}

// Share conversation
export function useShareConversation() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (conversationId: string) => 
      chatRepository.shareConversation(conversationId),
    onSuccess: (shareData, conversationId) => {
      // Update conversation cache with share info
      queryClient.setQueryData(
        chatKeys.conversation(conversationId), 
        (old: any) => {
          if (!old) return old;
          return {
            ...old,
            shareUrl: shareData.shareUrl,
            isShared: true,
          };
        }
      );
    },
  });
} 