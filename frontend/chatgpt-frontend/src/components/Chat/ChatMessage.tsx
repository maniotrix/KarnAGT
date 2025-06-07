import React, { useState } from 'react';
import { AISDKMessage } from '../../types/chat';

// Modern UI Libraries  
import { Avatar, AvatarFallback, AvatarImage } from '@radix-ui/react-avatar';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@radix-ui/react-tooltip';
import { 
  User, 
  Bot, 
  Clock,
  Zap,
  DollarSign,
  Cpu,
  Copy,
  Check
} from 'lucide-react';
import { motion } from 'framer-motion';

// Clean Architecture Integration
import { useUiStore } from '../../app/stores/uiStore';

interface ChatMessageProps {
  message: AISDKMessage;
  isStreaming?: boolean;
}

export const ChatMessage: React.FC<ChatMessageProps> = ({ 
  message, 
  isStreaming = false 
}) => {
  // Clean Architecture Integration
  const { theme } = useUiStore();
  
  // Copy functionality
  const [copied, setCopied] = useState(false);
  
  const formatTime = (date: Date | string) => {
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy message:', error);
    }
  };

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        data-message-role={message.role}
        className={`flex gap-4 p-4 rounded-lg group hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors ${
          isUser ? 'justify-end' : 'justify-start'
        }`}
      >
        {/* Assistant Avatar */}
        {isAssistant && (
          <Avatar className="w-8 h-8 shrink-0">
            <AvatarFallback className="bg-blue-100 dark:bg-blue-900">
              <Bot className="w-4 h-4 text-blue-600 dark:text-blue-400" />
            </AvatarFallback>
          </Avatar>
        )}

        {/* Message Content */}
        <div className={`flex flex-col max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
          {/* Message Header */}
          <div className={`flex items-center gap-2 mb-2 ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {isUser ? 'You' : 'Assistant'}
            </span>
            
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              <span>{formatTime(message.createdAt || new Date())}</span>
            </div>

            {/* Streaming Indicator */}
            {isStreaming && isAssistant && (
              <motion.div
                animate={{ opacity: [0.4, 1, 0.4] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="flex items-center gap-1"
              >
                <div className="w-2 h-2 bg-green-500 rounded-full" />
                <span className="text-xs text-green-600 dark:text-green-400">Live</span>
              </motion.div>
            )}
          </div>

          {/* Message Bubble */}
          <div className={`relative px-4 py-3 rounded-2xl max-w-none ${
            isUser 
              ? 'bg-blue-600 text-white ml-8' 
              : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 mr-8'
          }`}>
            {/* Message Text - TODO: Add React Markdown in Phase 3 */}
            <div className={`prose prose-sm max-w-none ${
              isUser 
                ? 'prose-invert text-white' 
                : 'prose-gray dark:prose-invert text-gray-900 dark:text-white'
            }`}>
              <p className="mb-0 whitespace-pre-wrap break-words leading-relaxed">
                {message.content}
              </p>
            </div>

            {/* Copy Button */}
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  onClick={handleCopy}
                  className={`absolute top-2 right-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity ${
                    isUser 
                      ? 'hover:bg-blue-700 text-blue-100' 
                      : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400'
                  }`}
                >
                  {copied ? (
                    <Check className="w-3 h-3" />
                  ) : (
                    <Copy className="w-3 h-3" />
                  )}
                </button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{copied ? 'Copied!' : 'Copy message'}</p>
              </TooltipContent>
            </Tooltip>
          </div>

          {/* Message Metadata */}
          {(message.total_tokens || message.cost_usd || message.model_name) && (
            <div className={`flex items-center gap-3 mt-2 text-xs text-gray-500 dark:text-gray-400 ${
              isUser ? 'flex-row-reverse' : 'flex-row'
            }`}>
              {message.model_name && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1">
                      <Cpu className="w-3 h-3" />
                      <span>{message.model_name}</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>AI Model Used</p>
                  </TooltipContent>
                </Tooltip>
              )}
              
              {message.total_tokens && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1">
                      <Zap className="w-3 h-3" />
                      <span>{message.total_tokens}</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Tokens Used</p>
                  </TooltipContent>
                </Tooltip>
              )}
              
              {message.cost_usd && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="flex items-center gap-1">
                      <DollarSign className="w-3 h-3" />
                      <span>${message.cost_usd.toFixed(4)}</span>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>Message Cost</p>
                  </TooltipContent>
                </Tooltip>
              )}
            </div>
          )}
        </div>

        {/* User Avatar */}
        {isUser && (
          <Avatar className="w-8 h-8 shrink-0">
            <AvatarFallback className="bg-gray-100 dark:bg-gray-700">
              <User className="w-4 h-4 text-gray-600 dark:text-gray-400" />
            </AvatarFallback>
          </Avatar>
        )}
      </motion.div>
    </TooltipProvider>
  );
}; 