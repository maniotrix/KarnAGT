import React, { useState, useEffect } from 'react';
import { ToolExecution, Message } from '../../types/chat';
import { ToolTimelineItem } from './ToolTimelineItem';

// Modern UI Libraries
import { 
  Settings, 
  ChevronDown,
  Clock
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Progressive message component for showing context-aware loading messages
interface ProgressiveMessageProps {
  elapsedSeconds: number;
  userMessage?: Message;
}

const ProgressiveMessage: React.FC<ProgressiveMessageProps> = ({ elapsedSeconds, userMessage }) => {
  // Check message context for smart messaging - handle both temp and persisted messages
  const hasImages = 
    // Fresh messages (temp IDs): Check localImages
    (userMessage?.localImages && userMessage.localImages.length > 0) ||
    // Persisted messages (real IDs): Check attachments for image content types
    userMessage?.attachments?.some((attachment: any) => {
      if (typeof attachment === 'string') return false; // Skip string IDs
      return attachment.content_type && attachment.content_type.startsWith('image/');
    });
  
  const hasFiles = 
    // Fresh messages (temp IDs): Check localDocuments  
    (userMessage?.localDocuments && userMessage.localDocuments.length > 0) ||
    // Persisted messages (real IDs): Check vector_file_references
    (userMessage?.vector_file_references?.processed_files && 
     userMessage.vector_file_references.processed_files.length > 0);
  
  // Context-specific messages with their durations
  const getContextMessage = (): { message: string; duration: number } | null => {
    if (hasImages && hasFiles) {
      return { message: "Processing images and documents...(<10s)", duration: 10 };
    }
    if (hasImages) {
      return { message: "Analyzing images...(<5s)", duration: 5 };
    }
    if (hasFiles) {
      return { message: "Processing documents...(<10s)", duration: 10 };
    }
    return null;
  };

  // Default cycling messages for general progress
  const getDefaultMessage = (): string => {
    const messages = [
      "Thinking...(<5s)",
      "Gathering information...",
      "Gathering information...(almost ready)"
    ];
    
    const contextInfo = getContextMessage();
    // If we had context messages, adjust the elapsed time for cycling
    const adjustedElapsed = contextInfo ? Math.max(0, elapsedSeconds - contextInfo.duration) : elapsedSeconds;
    const messageIndex = Math.floor(adjustedElapsed / 3) % messages.length;
    return messages[messageIndex];
  };

  // Main message logic with time-based switching
  const getMessage = (): string => {
    const contextInfo = getContextMessage();
    
    // If we have context-specific messages and haven't exceeded their duration
    if (contextInfo && elapsedSeconds < contextInfo.duration) {
      return contextInfo.message;
    }
    
    // Fall back to default cycling messages
    return getDefaultMessage();
  };

  return (
    <motion.span 
      key={getMessage()} // Key change triggers re-animation
      initial={{ opacity: 0, y: 5 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className="truncate bg-gradient-to-r from-gray-500 via-gray-300 to-gray-500 dark:from-gray-400 dark:via-gray-200 dark:to-gray-400 bg-clip-text text-transparent bg-[length:200%_100%] animate-shimmer"
    >
      {getMessage()}
    </motion.span>
  );
};

interface ToolExecutionDropdownProps {
  tools: ToolExecution[];
  isThinking: boolean;
  isStreaming: boolean;
  userMessage?: Message;
  assistantContent?: string;
}

export const ToolExecutionDropdown: React.FC<ToolExecutionDropdownProps> = ({ 
  tools, 
  isThinking, 
  isStreaming,
  userMessage,
  assistantContent
}) => {
  const [isExpanded, setIsExpanded] = useState(false);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);
  
  // Sort tools chronologically (earliest first)
  const sortedTools = [...tools].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
  
  // Timer - count seconds when thinking, keep final value when done
  useEffect(() => {
    if (isThinking) {
      // Reset and start timer when thinking begins
      setElapsedSeconds(0);
      const interval = setInterval(() => {
        setElapsedSeconds(prev => prev + 1);
      }, 1000);
      
      return () => clearInterval(interval);
    }
    // When thinking stops, timer stops but keeps the final value
  }, [isThinking]);
  
  // Auto-expand during execution, collapse after completion
  useEffect(() => {
    if (isThinking) {
      // Expand when AI is working
      setIsExpanded(true);
    } else if (sortedTools.length > 0) {
      // Collapse after completion but keep header visible if tools were used
      setIsExpanded(false);
    }
  }, [isThinking, sortedTools.length]);
  
  // Only show the dropdown when thinking or when there are tools or when we have elapsed time to show
  if (!isThinking && sortedTools.length === 0 && elapsedSeconds === 0) {
    return null;
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3 }}
      className="w-full"
    >
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm text-fluid-xs">
        {/* Dropdown Header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between p-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors rounded-lg"
        >
          <div className="flex items-center space-x-2">
            <Settings className="w-4 h-4 text-gray-500 dark:text-gray-400" />
              <span className="font-medium text-gray-700 dark:text-gray-300">
              {isThinking ? 'Analyzing and Working...' : `Result ready  •  Steps : ${sortedTools.length}`}
            </span>
            {isThinking && (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-3 h-3 border border-blue-500 border-t-transparent rounded-full"
              />
            )}
            {/* Timer - show when thinking or when finished (regardless of tools) */}
            {(isThinking || (!isThinking && elapsedSeconds > 0)) && (
              <div className={`flex items-center space-x-1 ml-2 px-2 py-1 rounded-md border ${
                isThinking 
                  ? 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800' 
                  : 'bg-green-50 dark:bg-green-900/30 border-green-200 dark:border-green-800'
              }`}>
                <Clock className={`w-3 h-3 ${
                  isThinking 
                    ? 'text-blue-600 dark:text-blue-400' 
                    : 'text-green-600 dark:text-green-400'
                }`} />
                <span className={`font-mono ${
                  isThinking 
                    ? 'text-blue-700 dark:text-blue-300' 
                    : 'text-green-700 dark:text-green-300'
                }`}>
                  {elapsedSeconds}s
                </span>
              </div>
            )}
          </div>
          <ChevronDown 
            className={`w-4 h-4 text-gray-500 dark:text-gray-400 transition-transform ${
              isExpanded ? 'rotate-180' : ''
            }`} 
          />
        </button>
        
        {/* Dropdown Content */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="border-t border-gray-200 dark:border-gray-700"
            >
              <div className="p-3 space-y-2">
                {sortedTools.length === 0 ? (
                  <div className="text-gray-500 dark:text-gray-400 italic">
                    {isThinking && (!assistantContent || assistantContent.trim() === '') ? (
                      // No tokens received yet - show progressive messaging
                      <ProgressiveMessage 
                        elapsedSeconds={elapsedSeconds} 
                        userMessage={userMessage}
                      />
                    ) : isThinking ? (
                      // First token received - switch to simple generating message
                      'Generating response...'
                    ) : (
                      'No steps to show'
                    )}
                  </div>
                ) : (
                  <div className="space-y-1">
                    {sortedTools.map((tool, index) => (
                      <ToolTimelineItem 
                        key={`${tool.tool_id}-${tool.timestamp}-${index}`} 
                        tool={tool} 
                        index={index}
                        isLast={index === sortedTools.length - 1}
                      />
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};