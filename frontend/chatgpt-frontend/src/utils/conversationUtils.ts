// Utility functions for conversation display

import { Message } from '../domain/entities/Message';
import { Conversation } from '../domain/entities/Conversation';

/**
 * Get display title for a conversation, using latest USER message content (WhatsApp style)
 * Falls back to original title if no user messages or empty content
 */
export function getConversationDisplayTitle(
  conversation: Conversation | { title: string; messages?: Message[]; latestUserMessage?: string },
  maxLength: number = 50
): string {
  // First, try to use the latest user message from the API if available
  if ('latestUserMessage' in conversation && conversation.latestUserMessage?.trim()) {
    const cleanContent = conversation.latestUserMessage
      .trim()
      .replace(/\n+/g, ' ') // Replace newlines with spaces
      .replace(/\s+/g, ' '); // Replace multiple spaces with single space

    // Truncate with ellipsis if needed
    if (cleanContent.length <= maxLength) {
      return cleanContent;
    }
    return cleanContent.substring(0, maxLength).trim() + '...';
  }

  // Fallback: If no latestUserMessage from API, search through messages array
  if (!conversation.messages || conversation.messages.length === 0) {
    return conversation.title || 'New Chat';
  }

  // Get the latest USER message (iterate from end to find last user message)
  const latestUserMessage = [...conversation.messages]
    .reverse()
    .find(message => message.role === 'user');
  
  // If no user message or no content, return original title
  if (!latestUserMessage?.content?.trim()) {
    return conversation.title || 'New Chat';
  }

  // Clean and truncate the message content
  const cleanContent = latestUserMessage.content
    .trim()
    .replace(/\n+/g, ' ') // Replace newlines with spaces
    .replace(/\s+/g, ' '); // Replace multiple spaces with single space

  // Truncate with ellipsis if needed
  if (cleanContent.length <= maxLength) {
    return cleanContent;
  }

  return cleanContent.substring(0, maxLength).trim() + '...';
}

/**
 * Get display title for conversation from raw message data, using latest USER message
 * Used when we have message data but not in Conversation entity format
 */
export function getDisplayTitleFromMessages(
  title: string,
  messages: { content: string; role: string }[] | undefined,
  maxLength: number = 50
): string {
  // If no messages, return original title
  if (!messages || messages.length === 0) {
    return title || 'New Chat';
  }

  // Get the latest USER message (iterate from end to find last user message)
  const latestUserMessage = [...messages]
    .reverse()
    .find(message => message.role === 'user');
  
  // If no user message or no content, return original title
  if (!latestUserMessage?.content?.trim()) {
    return title || 'New Chat';
  }

  // Clean and truncate the message content
  const cleanContent = latestUserMessage.content
    .trim()
    .replace(/\n+/g, ' ') // Replace newlines with spaces
    .replace(/\s+/g, ' '); // Replace multiple spaces with single space

  // Truncate with ellipsis if needed
  if (cleanContent.length <= maxLength) {
    return cleanContent;
  }

  return cleanContent.substring(0, maxLength).trim() + '...';
}