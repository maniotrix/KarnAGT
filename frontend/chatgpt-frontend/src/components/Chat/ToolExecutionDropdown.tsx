import React, { useState, useEffect } from 'react';
import { ToolExecution } from '../../types/chat';
import { ToolTimelineItem } from './ToolTimelineItem';

// Modern UI Libraries
import { 
  Settings, 
  ChevronDown,
  Clock
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ToolExecutionDropdownProps {
  tools: ToolExecution[];
  isThinking: boolean;
  isStreaming: boolean;
}

export const ToolExecutionDropdown: React.FC<ToolExecutionDropdownProps> = ({ 
  tools, 
  isThinking, 
  isStreaming 
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
      <div className="bg-gray-50 dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm">
        {/* Dropdown Header */}
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center justify-between p-3 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors rounded-lg"
        >
          <div className="flex items-center space-x-2">
            <Settings className="w-4 h-4 text-gray-500 dark:text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
              {isThinking ? 'Analyzing and Working...' : `Analysis complete  •  Steps : ${sortedTools.length}`}
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
                <span className={`text-xs font-mono ${
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
                  <div className="text-sm text-gray-500 dark:text-gray-400 italic">
                    {isThinking ? 'Preparing ...' : 'No steps to show'}
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