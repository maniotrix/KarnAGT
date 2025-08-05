import React from 'react';
import { Message, ToolExecution } from '../../types/chat';
import { UserMessage } from './UserMessage';
import { AssistantMessage } from './AssistantMessage';

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
  onEdit?: (messageId: string, newContent: string) => Promise<boolean>;
  messageTools?: ToolExecution[];
  isThinking?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  isStreaming = false, 
  onEdit, 
  messageTools = [],
  isThinking = false 
}) => {
  if (message.role === 'user') {
    return (
      <UserMessage 
        message={message}
        onEdit={onEdit}
      />
    );
  }

  if (message.role === 'assistant') {
    return (
      <AssistantMessage 
        message={message}
        isStreaming={isStreaming}
        messageTools={messageTools}
        isThinking={isThinking}
      />
    );
  }

  return null;
}; 