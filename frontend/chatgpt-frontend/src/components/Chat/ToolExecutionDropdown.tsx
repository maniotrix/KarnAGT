import React, { useState } from 'react';
import { ToolExecution } from '../../types/chat';
import { ToolTimelineItem } from './ToolTimelineItem';

// Modern UI Libraries
import { 
  Settings, 
  ChevronDown 
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
  
  // Sort tools chronologically (earliest first)
  const sortedTools = [...tools].sort((a, b) => 
    new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
  
  // Only show the dropdown when thinking or when there are tools
  if (!isThinking && sortedTools.length === 0) {
    return null;
  }
  
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.3 }}
      className="mb-2 mx-4"
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
              {isThinking ? 'AI Tools' : `Tools Used (${sortedTools.length})`}
            </span>
            {isThinking && (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
                className="w-3 h-3 border border-blue-500 border-t-transparent rounded-full"
              />
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
                    {isThinking ? 'Preparing tools...' : 'No tools were used'}
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