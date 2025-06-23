import React from 'react';
import { Message } from '../../types/chat';
import { UserMessage } from './UserMessage';
import { AssistantMessage } from './AssistantMessage';
import { useMessageImages } from '../../hooks/useMessageImages';

interface ChatMessageProps {
  message: Message;
  isStreaming?: boolean;
  onEdit?: (messageId: string, newContent: string) => Promise<boolean>;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ message, isStreaming = false, onEdit }) => {
  // Load images with caching and timeout handling
  const { images, loading: imagesLoading, error: imagesError } = useMessageImages(message);
  
  // Convert to the format expected by UserMessage component
  const stagingImages = message.role === 'user' ? images.map(img => ({
    fileId: img.fileId,
    filename: img.filename,
    previewUrl: img.previewUrl
  })) : [];

  if (message.role === 'user') {
    return (
      <UserMessage 
        message={message}
        onEdit={onEdit}
        stagingImages={stagingImages}
      />
    );
  }

  if (message.role === 'assistant') {
    return (
      <AssistantMessage 
        message={message}
        isStreaming={isStreaming}
      />
    );
  }

  return null;
}; 