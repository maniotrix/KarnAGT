import React, { useState } from 'react';
import { Message } from '../../types/chat';

// Markdown Support
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';

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
  Check,
  Edit3,
  Save,
  X
} from 'lucide-react';
import { motion } from 'framer-motion';

// Clean Architecture Integration
import { useUiStore } from '../../app/stores/uiStore';

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
  // Clean Architecture Integration
  const { theme } = useUiStore();
  
  // Copy functionality
  const [copied, setCopied] = useState(false);
  
  // Edit functionality
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [isSaving, setIsSaving] = useState(false);
  
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

  const handleEdit = () => {
    setIsEditing(true);
    setEditContent(message.content);
  };

  const handleSave = async () => {
    if (!onEdit || !message.message_id) return;
    
    const trimmedContent = editContent.trim();
    if (!trimmedContent || trimmedContent === message.content) {
      setIsEditing(false);
      return;
    }
    
    // STEP 1: Immediately exit edit mode and show saving state
    setIsEditing(false);
    setIsSaving(true);
    
    // STEP 2: Call the edit function (this will update the message and clear subsequent ones)
    const success = await onEdit(message.message_id, trimmedContent);
    
    // STEP 3: Clear saving state
    setIsSaving(false);
    
    // If edit failed, go back to edit mode so user can retry
    if (!success) {
      setIsEditing(true);
      // Reset content to current message content in case backend partially updated it
      setEditContent(message.content);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditContent(message.content);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancel();
    }
  };

  const isUser = message.role === 'user';
  const isAssistant = message.role === 'assistant';
  const canEdit = isUser && onEdit && !isStreaming;

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
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
        <div className={`flex flex-col ${isUser ? 'max-w-[80%] items-end' : 'max-w-full items-start'}`}>
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
          <div className={`px-4 py-3 rounded-2xl max-w-none ${
            isUser 
              ? 'bg-blue-600 text-white ml-8' 
              : 'bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700'
          }`}>
            {/* Message Text with Edit/Display Mode */}
            {isEditing ? (
              <div>
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className={`w-full p-3 rounded-lg border resize-none min-h-[100px] ${
                    isUser 
                      ? 'bg-blue-700 text-white border-blue-500 placeholder-blue-200' 
                      : 'bg-gray-50 dark:bg-gray-900 text-gray-900 dark:text-white border-gray-300 dark:border-gray-600'
                  } focus:outline-none focus:ring-2 focus:ring-blue-500`}
                  placeholder="Edit your message..."
                  disabled={isSaving}
                  autoFocus
                />
                <div className={`flex items-center gap-2 mt-2 text-xs ${
                  isUser 
                    ? 'text-blue-100' 
                    : 'text-gray-500 dark:text-gray-400'
                }`}>
                  <span>Press Ctrl+Enter to save, Esc to cancel</span>
                </div>
              </div>
            ) : (
              <div className={`prose prose-sm max-w-none ${
                isUser 
                  ? 'prose-invert text-white' 
                  : 'prose-gray dark:prose-invert text-gray-900 dark:text-white'
              }`}>
                {/* Show saving indicator if message is being edited */}
                {isSaving && (
                  <div className="flex items-center gap-2 mb-2 text-xs opacity-75">
                    <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
                    <span>Saving changes...</span>
                  </div>
                )}
                
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    // Custom styling for code blocks
                    pre: ({ children, ...props }) => (
                      <pre {...props} className="bg-gray-100 dark:bg-gray-900 rounded-lg p-3 overflow-x-auto">
                        {children}
                      </pre>
                    ),
                    // Custom styling for inline code
                    code: ({ children, className, ...props }) => {
                      const isInline = !className;
                      return (
                        <code 
                          {...props} 
                          className={`${className || ''} ${
                            isInline 
                              ? 'bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-sm' 
                              : ''
                          }`}
                        >
                          {children}
                        </code>
                      );
                    }
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            )}
          </div>

          {/* Action Buttons - Now below the message bubble */}
          <div className={`flex items-center gap-1 mt-2 ${isUser ? 'justify-end' : 'justify-start'}`}>
            {/* Edit Mode Buttons */}
            {isEditing ? (
              <>
                <button
                  onClick={handleCancel}
                  disabled={isSaving}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isUser 
                      ? 'bg-gray-100 text-gray-700 hover:bg-gray-200' 
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  } ${isSaving ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  Cancel
                </button>
                
                <button
                  onClick={handleSave}
                  disabled={isSaving || !editContent.trim() || editContent.trim() === message.content}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isUser 
                      ? 'bg-blue-600 text-white hover:bg-blue-700' 
                      : 'bg-blue-600 text-white hover:bg-blue-700'
                  } ${(isSaving || !editContent.trim() || editContent.trim() === message.content) ? 'opacity-50 cursor-not-allowed' : ''}`}
                >
                  {isSaving ? 'Saving...' : 'Send'}
                </button>
              </>
            ) : (
              <>
                {/* Edit Button - Only for user messages */}
                {canEdit && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={handleEdit}
                        className={`p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity ${
                          isUser 
                            ? 'hover:bg-blue-100 text-blue-600' 
                            : 'hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400'
                        }`}
                      >
                        <Edit3 className="w-3 h-3" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">
                      <p>Edit message</p>
                    </TooltipContent>
                  </Tooltip>
                )}
                
                {/* Copy Button */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={handleCopy}
                      className={`p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity ${
                        isUser 
                          ? 'hover:bg-blue-100 text-blue-600' 
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
                  <TooltipContent side="bottom">
                    <p>{copied ? 'Copied!' : 'Copy message'}</p>
                  </TooltipContent>
                </Tooltip>
              </>
            )}
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

// Export memoized version to prevent re-renders when input changes
export const ChatMessage = React.memo(ChatMessageComponent); 