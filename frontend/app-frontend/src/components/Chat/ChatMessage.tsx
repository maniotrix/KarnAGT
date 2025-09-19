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
  userMessage?: Message;
  assistantContent?: string;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  isStreaming = false, 
  onEdit, 
  messageTools = [],
  isThinking = false,
  userMessage,
  assistantContent
}) => {
  if (message.role === 'user') {
    return (
      <UserMessage 
        message={message}
        onEdit={onEdit}
        isStreaming={isStreaming}
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
        userMessage={userMessage}
        assistantContent={assistantContent}
      />
    );
  }

  return null;
}; 