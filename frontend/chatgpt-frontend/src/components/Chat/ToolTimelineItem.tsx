import React, { useState } from 'react';
import { ToolExecution } from '../../types/chat';

// Modern UI Libraries
import { 
  Loader2, 
  Check, 
  X, 
  Circle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Copy
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

interface ToolTimelineItemProps {
  tool: ToolExecution;
  index: number;
  isLast: boolean;
}

export const ToolTimelineItem: React.FC<ToolTimelineItemProps> = ({ tool, index, isLast }) => {
  // Start expanded if there's error or code content, collapsed for simple completed tools
  const hasDetails = tool.error || (tool.tool_name === 'execute_code' && tool.openai_tool_data?.arguments?.code);
  const [isExpanded, setIsExpanded] = useState(hasDetails || tool.status !== 'completed');
  const [isErrorExpanded, setIsErrorExpanded] = useState(false);
  const [copiedError, setCopiedError] = useState(false);

  const copyErrorToClipboard = async () => {
    if (tool.error) {
      try {
        await navigator.clipboard.writeText(tool.error);
        setCopiedError(true);
        setTimeout(() => setCopiedError(false), 2000);
      } catch (err) {
        console.error('Failed to copy error:', err);
      }
    }
  };

  const getStatusIcon = () => {
    switch (tool.status) {
      case 'started':
        return <Circle className="w-3 h-3 text-blue-500" />;
      case 'running':
        return <Circle className="w-3 h-3 text-blue-500" />;
      case 'completed':
        return <Check className="w-3 h-3 text-green-500" />;
      case 'error':
        return <X className="w-3 h-3 text-red-500" />;
      default:
        return <Circle className="w-3 h-3 text-gray-400" />;
    }
  };
  
  const getStatusColor = () => {
    switch (tool.status) {
      case 'started':
      case 'running':
        return 'border-blue-300 dark:border-blue-600 bg-blue-50 dark:bg-blue-900/20';
      case 'completed':
        return 'border-green-300 dark:border-green-600 bg-green-50 dark:bg-green-900/20';
      case 'error':
        return 'border-red-300 dark:border-red-600 bg-red-50 dark:bg-red-900/20';
      default:
        return 'border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800';
    }
  };
  
  const formatTime = (timestamp: string) => {
    try {
      return new Date(timestamp).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return 'Invalid time';
    }
  };
  
  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, delay: index * 0.1 }}
      className="flex items-start space-x-3"
    >
      {/* Timeline Line */}
      <div className="flex flex-col items-center">
        <div className={`flex items-center justify-center w-6 h-6 rounded-full border-2 ${getStatusColor()}`}>
          {getStatusIcon()}
        </div>
        {!isLast && (
          <div className="w-px h-4 bg-gray-300 dark:bg-gray-600 mt-1" />
        )}
      </div>
      
      {/* Tool Info */}
      <div className="flex-1 min-w-0 pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
              {tool.display_name}
            </div>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex-shrink-0 p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
              title={isExpanded ? "Collapse details" : "Expand details"}
            >
              {isExpanded ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400 ml-2 flex-shrink-0">
            {formatTime(tool.timestamp)}
          </div>
        </div>
        
        {/* Status Text */}
        <div className="flex items-center space-x-1 mt-1">
          <span className={`text-xs font-medium ${
            tool.status === 'started' ? 'text-blue-600 dark:text-blue-400' :
            tool.status === 'running' ? 'text-blue-600 dark:text-blue-400' :
            tool.status === 'completed' ? 'text-green-600 dark:text-green-400' :
            tool.status === 'error' ? 'text-red-600 dark:text-red-400' :
            'text-gray-500 dark:text-gray-400'
          }`}>
            {tool.status === 'started' && 'Started'}
            {tool.status === 'running' && 'Running...'}
            {tool.status === 'completed' && 'Completed'}
            {tool.status === 'error' && 'Failed'}
          </span>
          
        </div>
        
        {/* Collapsible Details */}
        <AnimatePresence>
          {isExpanded && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              {/* Error Message */}
              {(tool.status === 'error' || tool.error) && (
                <div className="mt-2">
                  <div className="flex items-center justify-between text-xs font-medium text-red-700 dark:text-red-300 mb-1">
                    <span>Error:</span>
                    <div className="flex items-center gap-1">
                {tool.error && tool.error.length > 100 && (
                  <button
                    onClick={() => setIsErrorExpanded(!isErrorExpanded)}
                    className="flex items-center gap-1 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 transition-colors"
                  >
                    {isErrorExpanded ? (
                      <>
                        <ChevronUp className="w-3 h-3" />
                        <span>Less</span>
                      </>
                    ) : (
                      <>
                        <ChevronDown className="w-3 h-3" />
                        <span>More</span>
                      </>
                    )}
                  </button>
                )}
                {tool.error && (
                  <button
                    onClick={copyErrorToClipboard}
                    className="flex items-center gap-1 text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 transition-colors"
                    title="Copy error message"
                  >
                    <Copy className="w-3 h-3" />
                    {copiedError && <span className="text-xs">Copied!</span>}
                  </button>
                )}
              </div>
            </div>
            <div className="bg-red-50 dark:bg-red-900/20 rounded-md p-2 text-xs border border-red-200 dark:border-red-800">
              <div className="text-red-800 dark:text-red-200">
                {tool.error ? (
                  <div className={`${isErrorExpanded ? 'max-h-32 overflow-y-auto' : ''}`}>
                    {tool.error.length > 100 && !isErrorExpanded ? (
                      <span>
                        {tool.error.substring(0, 100)}
                        <span className="text-red-600 dark:text-red-400">...</span>
                      </span>
                    ) : (
                      <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed">
                        {tool.error}
                      </pre>
                    )}
                  </div>
                ) : (
                  'Tool execution failed - no details available'
                )}
              </div>
            </div>
          </div>
        )}
        
        {/* Tool Type Badge */}
        <div className="mt-1">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
            {tool.tool_type}
          </span>
        </div>
        
        {/* Code Arguments Display for execute_code tool */}
        {tool.tool_name === 'execute_code' && tool.openai_tool_data?.arguments?.code && (
          <div className="mt-2">
            <div className="text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
              Code (python):
            </div>
            <div className="bg-gray-50 dark:bg-gray-800 rounded-md p-2 text-xs font-mono overflow-x-auto max-h-32 overflow-y-auto border border-gray-200 dark:border-gray-600">
              <pre className="whitespace-pre-wrap text-gray-800 dark:text-gray-200">
                {tool.openai_tool_data.arguments.code}
              </pre>
            </div>
          </div>
        )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};