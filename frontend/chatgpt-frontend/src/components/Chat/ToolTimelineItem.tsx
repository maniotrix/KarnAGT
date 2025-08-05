import React from 'react';
import { ToolExecution } from '../../types/chat';

// Modern UI Libraries
import { 
  Loader2, 
  Check, 
  X, 
  Circle,
  AlertTriangle 
} from 'lucide-react';
import { motion } from 'framer-motion';

interface ToolTimelineItemProps {
  tool: ToolExecution;
  index: number;
  isLast: boolean;
}

export const ToolTimelineItem: React.FC<ToolTimelineItemProps> = ({ tool, index, isLast }) => {
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
          <div className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
            {tool.display_name}
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
          
          {tool.error && (
            <div className="flex items-center space-x-1">
              <AlertTriangle className="w-3 h-3 text-red-500" />
              <span className="text-xs text-red-600 dark:text-red-400 truncate">
                {tool.error}
              </span>
            </div>
          )}
        </div>
        
        {/* Tool Type Badge */}
        <div className="mt-1">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
            {tool.tool_type}
          </span>
        </div>
      </div>
    </motion.div>
  );
};