import React, { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@radix-ui/react-tooltip';

interface CodeBlockProps {
  children: React.ReactNode;
  className?: string;
  inline?: boolean;
}

interface PreBlockProps {
  children: React.ReactNode;
  className?: string;
}

// Copy button component for code blocks
const CopyButton: React.FC<{ text: string; size?: 'sm' | 'md' }> = ({ text, size = 'md' }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy code:', error);
    }
  };

  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-4 h-4';
  const buttonSize = size === 'sm' ? 'p-1' : 'p-1.5';

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={handleCopy}
            className={`${buttonSize} rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors opacity-0 group-hover:opacity-100`}
            title={copied ? 'Copied!' : 'Copy code'}
          >
            {copied ? (
              <Check className={`${iconSize} text-green-600`} />
            ) : (
              <Copy className={`${iconSize} text-gray-600 dark:text-gray-400`} />
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent>
          <p>{copied ? 'Copied!' : 'Copy code'}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};

// Enhanced inline code component with copy button
export const InlineCode: React.FC<CodeBlockProps> = ({ children, className, ...props }) => {
  const codeText = typeof children === 'string' ? children : children?.toString() || '';
  
  return (
    <span className="group relative inline-flex items-center">
      <code 
        {...props} 
        className={`${className || ''} bg-gray-200 dark:bg-gray-700 px-1 py-0.5 rounded text-sm`}
      >
        {children}
      </code>
      {codeText.length > 5 && ( // Only show copy button for longer code snippets
        <span className="ml-1">
          <CopyButton text={codeText} size="sm" />
        </span>
      )}
    </span>
  );
};

// Enhanced pre block component with copy button
export const PreBlock: React.FC<PreBlockProps> = ({ children, className, ...props }) => {
  // Extract text content from the code element
  const getCodeText = (children: React.ReactNode): string => {
    if (typeof children === 'string') {
      return children;
    }
    
    if (React.isValidElement(children) && children.props) {
      const props = children.props as any;
      if (props.children) {
        if (typeof props.children === 'string') {
          return props.children;
        }
        
        if (Array.isArray(props.children)) {
          return props.children.join('');
        }
      }
    }
    
    return children?.toString() || '';
  };

  const codeText = getCodeText(children);

  return (
    <div className="group relative">
      <pre {...props} className={`${className || ''} bg-gray-100 dark:bg-gray-900 rounded-lg p-3 overflow-x-auto`}>
        {children}
      </pre>
      <div className="absolute top-2 right-2">
        <CopyButton text={codeText} />
      </div>
    </div>
  );
};

// Main code component that handles both inline and block code
export const CodeComponent: React.FC<CodeBlockProps> = ({ children, className, inline, ...props }) => {
  if (inline) {
    return <InlineCode className={className} {...props}>{children}</InlineCode>;
  }

  // For block code, we'll let the pre component handle the copy button
  return (
    <code 
      {...props} 
      className={className}
    >
      {children}
    </code>
  );
};