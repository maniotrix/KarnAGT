import React from 'react';
import { Message } from '../../types/chat';
import { UserMessage } from './UserMessage';
import { AssistantMessage } from './AssistantMessage';

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
  onEdit?: (messageId: string, newContent: string) => Promise<boolean>;
}

const ChatMessageComponent: React.FC<ChatMessageProps> = ({ 
  message, 
  isStreaming = false,
  onEdit
}) => {
  // Route to appropriate component based on message role
  switch (message.role) {
    case 'user':
      return (
        <UserMessage 
          message={message} 
          onEdit={onEdit}
        />
      );
    case 'assistant':
      return (
        <AssistantMessage 
          message={message} 
          isStreaming={isStreaming}
        />
      );
    case 'system':
      // System messages could have their own component in the future
      return (
        <div className="text-center text-xs text-gray-500 dark:text-gray-400 py-2">
          {message.content}
        </div>
      );
    default:
      // Fallback for unknown message types
      console.warn('Unknown message role:', message.role);
      return (
        <div className="text-center text-xs text-red-500 py-2">
          Unknown message type: {message.role}
        </div>
      );
  }
};

// Export memoized version to prevent re-renders when input changes
export const ChatMessage = React.memo(ChatMessageComponent); 