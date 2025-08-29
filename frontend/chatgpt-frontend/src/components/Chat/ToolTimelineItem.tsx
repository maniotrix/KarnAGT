import React, { useState } from 'react';
import { ToolExecution } from '../../types/chat';
import { getToolDisplayName, getToolStatusMessage } from '../../constants/toolDisplayNames';

// Markdown & Syntax Highlighting
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';

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
  // Start expanded if there's error, stderr, or code content, collapsed for simple completed tools
  const hasDetails = tool.error || tool.stderr || (tool.tool_name === 'execute_code' && tool.openai_tool_data?.arguments?.code);
  const [isExpanded, setIsExpanded] = useState(hasDetails || tool.status !== 'completed');
  const [isErrorExpanded, setIsErrorExpanded] = useState(false);
  const [isStderrExpanded, setIsStderrExpanded] = useState(false);
  const [isStderrFullExpanded, setIsStderrFullExpanded] = useState(false); // For full stderr content
  const [isCodeExpanded, setIsCodeExpanded] = useState(false); // Code collapsed by default
  const [copiedError, setCopiedError] = useState(false);
  const [copiedStderr, setCopiedStderr] = useState(false);
  const [copiedCode, setCopiedCode] = useState(false);

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

  const copyStderrToClipboard = async () => {
    if (tool.stderr) {
      try {
        await navigator.clipboard.writeText(tool.stderr);
        setCopiedStderr(true);
        setTimeout(() => setCopiedStderr(false), 2000);
      } catch (err) {
        console.error('Failed to copy stderr:', err);
      }
    }
  };

  const copyCodeToClipboard = async () => {
    const code = tool.openai_tool_data?.arguments?.code;
    if (code) {
      try {
        await navigator.clipboard.writeText(code);
        setCopiedCode(true);
        setTimeout(() => setCopiedCode(false), 2000);
      } catch (err) {
        console.error('Failed to copy code:', err);
      }
    }
  };

  const detectLanguage = (code: string) => {
    // Simple language detection based on common patterns
    if (code.includes('import ') && (code.includes('def ') || code.includes('print('))) {
      return { name: 'Python', emoji: '🐍', lang: 'python' };
    }
    if (code.includes('function ') || code.includes('const ') || code.includes('console.log')) {
      return { name: 'JavaScript', emoji: '🟨', lang: 'javascript' };
    }
    if (code.includes('SELECT ') || code.includes('FROM ') || code.includes('WHERE ')) {
      return { name: 'SQL', emoji: '🗄️', lang: 'sql' };
    }
    // Default to Python for execute_code tool
    return { name: 'Python', emoji: '🐍', lang: 'python' };
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
    // Return empty if no timestamp provided
    if (!timestamp || timestamp.trim() === '') {
      return '';
    }
    
    try {
      // Handle UTC timestamps from backend properly
      const date = new Date(timestamp.endsWith('Z') ? timestamp : timestamp + 'Z');
      
      // Check if the date is valid
      if (isNaN(date.getTime())) {
        return '';
      }
      
      return date.toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit',
        second: '2-digit'
      });
    } catch {
      return '';
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
              {getToolDisplayName(tool.tool_name)}
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
          {formatTime(tool.timestamp) && (
            <div className="text-xs text-gray-500 dark:text-gray-400 ml-2 flex-shrink-0">
              {formatTime(tool.timestamp)}
            </div>
          )}
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
            {tool.status === 'started' && '🔄 Started'}
            {tool.status === 'running' && '⏳ In progress...'}
            {tool.status === 'completed' && '✅ Done'}
            {tool.status === 'error' && '❌ Failed'}
          </span>
          
          {/* Warning indicator for completed tools with stderr */}
          {tool.status === 'completed' && tool.stderr && (
            <button
              onClick={() => {
                if (!isExpanded) {
                  // If parent is collapsed, expand it first
                  setIsExpanded(true);
                  setIsStderrExpanded(true);
                } else {
                  // If parent is expanded, toggle stderr details
                  setIsStderrExpanded(!isStderrExpanded);
                }
              }}
              className="flex items-center space-x-1 hover:bg-yellow-50 dark:hover:bg-yellow-900/10 px-1 py-0.5 rounded transition-colors"
              title={
                !isExpanded 
                  ? "Show warning details" 
                  : isStderrExpanded 
                    ? "Hide warning details" 
                    : "Show warning details"
              }
            >
              <AlertTriangle className="w-3 h-3 text-yellow-500" />
              <span className="text-xs text-yellow-600 dark:text-yellow-400">
                Warning
              </span>
              {/* Always show chevron to indicate expandable warning content */}
              {(!isExpanded || !isStderrExpanded) ? (
                <ChevronDown className="w-3 h-3 text-yellow-500" />
              ) : (
                <ChevronUp className="w-3 h-3 text-yellow-500" />
              )}
            </button>
          )}
        </div>
        
        {/* Query display for search tools - shown as content */}
        {(tool.tool_name === 'web_search' || tool.tool_name === 'user_uploaded_documents_query') && tool.openai_tool_data?.arguments?.query && (
          <div className="mt-2">
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-md p-2 border border-blue-200 dark:border-blue-800">
              <div className="flex items-start gap-2">
                <span className="text-xs font-medium text-blue-700 dark:text-blue-300 flex-shrink-0">
                  Query:
                </span>
                <span className="text-xs text-blue-800 dark:text-blue-200 break-words">
                  {tool.openai_tool_data.arguments.query}
                </span>
              </div>
            </div>
          </div>
        )}
        
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
        
        {/* Stderr Warning Message - Collapsible */}
        <AnimatePresence>
          {(tool.status === 'completed' && tool.stderr && isStderrExpanded) && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden mt-2"
            >
              <div className="flex items-center justify-between text-xs font-medium text-yellow-700 dark:text-yellow-300 mb-1">
                <span>Warning Details:</span>
                <div className="flex items-center gap-1">
                  {tool.stderr && tool.stderr.length > 200 && (
                    <button
                      onClick={() => setIsStderrFullExpanded(!isStderrFullExpanded)}
                      className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400 hover:text-yellow-800 dark:hover:text-yellow-300 transition-colors"
                    >
                      {isStderrFullExpanded ? (
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
                  {tool.stderr && (
                    <button
                      onClick={copyStderrToClipboard}
                      className="flex items-center gap-1 text-yellow-600 dark:text-yellow-400 hover:text-yellow-800 dark:hover:text-yellow-300 transition-colors"
                      title="Copy stderr output"
                    >
                      <Copy className="w-3 h-3" />
                      {copiedStderr && <span className="text-xs">Copied!</span>}
                    </button>
                  )}
                </div>
              </div>
              <div className="bg-yellow-50 dark:bg-yellow-900/20 rounded-md p-2 text-xs border border-yellow-200 dark:border-yellow-800">
                <div className="text-yellow-800 dark:text-yellow-200">
                  {tool.stderr ? (
                    <div className={`${isStderrFullExpanded ? 'max-h-64 overflow-y-auto' : ''}`}>
                      {tool.stderr.length > 200 && !isStderrFullExpanded ? (
                        <span>
                          <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed inline">
                            {tool.stderr.substring(0, 200)}
                          </pre>
                          <span className="text-yellow-600 dark:text-yellow-400">...</span>
                        </span>
                      ) : (
                        <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed">
                          {tool.stderr}
                        </pre>
                      )}
                    </div>
                  ) : (
                    'Tool execution completed with warnings - no details available'
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        
        {/* Tool Type Badge */}
        <div className="mt-1">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200">
            {tool.tool_type}
          </span>
        </div>
        
              {/* Enhanced Code Display for execute_code tool */}
              {tool.tool_name === 'execute_code' && tool.openai_tool_data?.arguments?.code && (() => {
                const language = detectLanguage(tool.openai_tool_data.arguments.code);
                return (
                <div className="mt-2">
                  <div className="flex items-center justify-between text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                    <div className="flex items-center gap-2">
                      <span className="inline-flex items-center px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-900/20 text-blue-800 dark:text-blue-300">
                        {language.name} Code
                      </span>
                      <button
                        onClick={() => setIsCodeExpanded(!isCodeExpanded)}
                        className="flex items-center gap-1 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 transition-colors"
                        title={isCodeExpanded ? "Collapse code" : "Expand code"}
                      >
                        {isCodeExpanded ? (
                          <>
                            <ChevronUp className="w-3 h-3" />
                            <span>Hide</span>
                          </>
                        ) : (
                          <>
                            <ChevronDown className="w-3 h-3" />
                            <span>Show</span>
                          </>
                        )}
                      </button>
                    </div>
                    <button
                      onClick={copyCodeToClipboard}
                      className="flex items-center gap-1 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-300 transition-colors p-1 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
                      title="Copy code"
                    >
                      <Copy className="w-3 h-3" />
                      {copiedCode && <span className="text-xs">Copied!</span>}
                    </button>
                  </div>
                  <AnimatePresence>
                    {isCodeExpanded && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        transition={{ duration: 0.2 }}
                        className="overflow-hidden"
                      >
                        <div className="relative bg-gray-100 dark:bg-gray-900 rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
                          <div className="max-h-48 overflow-y-auto">
                            <div className="prose prose-sm max-w-none dark:prose-invert">
                              <ReactMarkdown
                                rehypePlugins={[rehypeHighlight]}
                                components={{
                                  pre: ({ children, ...props }) => (
                                    <pre {...props} className="!bg-transparent !p-3 !m-0 text-xs overflow-x-auto">
                                      {children}
                                    </pre>
                                  ),
                                  code: ({ children, className, ...props }) => (
                                    <code 
                                      {...props} 
                                      className={`${className || ''} !bg-transparent text-xs leading-relaxed`}
                                    >
                                      {children}
                                    </code>
                                  ),
                                  // Custom link handling - open external links in new tab
                                  a: ({ href, children, ...props }) => {
                                    const isExternal = href && (href.startsWith('http://') || href.startsWith('https://'));
                                    const isProxyUrl = href && /\/api\/v1\/proxy\/(images|files|code-files)\//.test(href);
                                    
                                    return (
                                      <a 
                                        {...props}
                                        href={href}
                                        target={isExternal && !isProxyUrl ? '_blank' : undefined}
                                        rel={isExternal && !isProxyUrl ? 'noopener noreferrer' : undefined}
                                        className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 underline text-xs"
                                      >
                                        {children}
                                      </a>
                                    );
                                  }
                                }}
                              >
                                {`\`\`\`${language.lang}\n${tool.openai_tool_data.arguments.code}\n\`\`\``}
                              </ReactMarkdown>
                            </div>
                          </div>
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
                );
              })()}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.div>
  );
};