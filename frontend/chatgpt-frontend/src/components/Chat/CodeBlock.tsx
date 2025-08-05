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
const CopyButton: React.FC<{ 
  text: string; 
  size?: 'sm' | 'md';
  onCustomCopy?: () => Promise<void>;
}> = ({ text, size = 'md', onCustomCopy }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      if (onCustomCopy) {
        await onCustomCopy();
      } else {
        await navigator.clipboard.writeText(text);
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy code:', error);
    }
  };

  const iconSize = size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5';
  const buttonSize = size === 'sm' ? 'p-0.5' : 'p-1';

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <button
            onClick={handleCopy}
            className={`${buttonSize} rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors opacity-70 hover:opacity-100 md:opacity-0 md:group-hover:opacity-100`}
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
          <p className="text-xs">{copied ? 'Copied!' : 'Copy code'}</p>
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
        className={`${className || ''}`}
      >
        {children}
      </code>
      {codeText.length > 10 && ( // Only show copy button for longer code snippets
        <span className="ml-0.5 opacity-50 hover:opacity-100 md:opacity-0 md:group-hover:opacity-100 transition-opacity">
          <CopyButton text={codeText} size="sm" />
        </span>
      )}
    </span>
  );
};

// Enhanced pre block component with copy button
export const PreBlock: React.FC<PreBlockProps> = ({ children, className, ...props }) => {
  const preRef = React.useRef<HTMLPreElement>(null);

  const handleCopy = async () => {
    if (preRef.current) {
      // Simple solution: just get the text content from the DOM
      const textContent = preRef.current.textContent || '';
      try {
        await navigator.clipboard.writeText(textContent);
      } catch (error) {
        console.error('Failed to copy:', error);
      }
    }
  };

  return (
    <div className="group relative">
      <pre {...props} ref={preRef} className={className}>
        {children}
      </pre>
      <div className="absolute top-1.5 right-1.5">
        <CopyButton text="" onCustomCopy={handleCopy} />
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