import React, { useState } from 'react';
import { Copy, Check, Code2 } from 'lucide-react';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@radix-ui/react-tooltip';
import { 
  DiJavascript1, DiPython, DiReact, DiHtml5, DiCss3, DiSass,
  DiNodejsSmall, DiPhp, DiJava, DiRuby, DiSwift, DiGo,
  DiRust, DiDotnet, DiMysql, DiPostgresql,
  DiMarkdown, DiTerminal, DiCode, DiDatabase
} from 'react-icons/di';
import { SiTypescript, SiKotlin, SiCplusplus } from 'react-icons/si';

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
            className={`${buttonSize} inline-flex items-center justify-center opacity-70 hover:opacity-100 transform hover:scale-110 transition-all duration-200 appearance-none focus:outline-none`}
            title={copied ? 'Copied!' : 'Copy code'}
          >
            {copied ? (
              <Check className={`${iconSize} text-green-600 dark:text-green-400`} />
            ) : (
              <Copy className={`${iconSize} text-gray-700 dark:text-gray-200 hover:text-gray-900 dark:hover:text-gray-100 transition-colors`} />
            )}
          </button>
        </TooltipTrigger>
        <TooltipContent>
          <p className="text-xs font-medium">{copied ? '✓ Copied!' : 'Copy code'}</p>
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
        <span className="ml-0.5 opacity-50 hover:opacity-100 transition-opacity">
          <CopyButton text={codeText} size="sm" />
        </span>
      )}
    </span>
  );
};

// Enhanced pre block component with copy button - Card style
export const PreBlock: React.FC<PreBlockProps> = ({ children, className, ...props }) => {
  const preRef = React.useRef<HTMLPreElement>(null);

  const extractLanguage = (node: React.ReactNode): string | null => {
    const array = React.Children.toArray(node);
    for (const child of array) {
      if (React.isValidElement(child)) {
        const el = child as React.ReactElement<any>;
        // Look on the code element first
        const className: string | undefined = el.props?.className;
        if (className) {
          // Common patterns: "language-ts", "language-python", sometimes with hljs classes
          const match = className.match(/language-([a-zA-Z0-9+#-]+)/);
          if (match?.[1]) return match[1].toLowerCase();
        }
        // Recurse into children if any
        if (el.props?.children) {
          const nested = extractLanguage(el.props.children);
          if (nested) return nested;
        }
      }
    }
    return null;
  };

  const language = extractLanguage(children);

  // Get language-specific icon
  const getLanguageIcon = (lang: string | null) => {
    if (!lang) return Code2;
    
    const langMap: Record<string, any> = {
      // JavaScript/TypeScript
      'javascript': DiJavascript1,
      'js': DiJavascript1,
      'typescript': SiTypescript,
      'ts': SiTypescript,
      'tsx': DiReact,
      'jsx': DiReact,
      
      // Web
      'html': DiHtml5,
      'css': DiCss3,
      'scss': DiSass,
      'sass': DiSass,
      
      // Python
      'python': DiPython,
      'py': DiPython,
      
      // Database
      'sql': DiDatabase,
      'mysql': DiMysql,
      'postgresql': DiPostgresql,
      'postgres': DiPostgresql,
      
      // Shell/Terminal
      'bash': DiTerminal,
      'sh': DiTerminal,
      'zsh': DiTerminal,
      'powershell': DiTerminal,
      'cmd': DiTerminal,
      'shell': DiTerminal,
      
      // Config/Data
      'json': DiCode,
      'yaml': DiCode,
      'yml': DiCode,
      'xml': DiCode,
      'toml': DiCode,
      
      // Other languages
      'java': DiJava,
      'c': SiCplusplus,
      'cpp': SiCplusplus,
      'c++': SiCplusplus,
      'csharp': DiDotnet,
      'cs': DiDotnet,
      'php': DiPhp,
      'ruby': DiRuby,
      'rb': DiRuby,
      'go': DiGo,
      'golang': DiGo,
      'rust': DiRust,
      'rs': DiRust,
      'swift': DiSwift,
      'kotlin': SiKotlin,
      'kt': SiKotlin,
      'node': DiNodejsSmall,
      'nodejs': DiNodejsSmall,
      'dotnet': DiDotnet,
      
      // Markup
      'markdown': DiMarkdown,
      'md': DiMarkdown,
      'text': DiCode,
      'txt': DiCode,
    };
    
    return langMap[lang.toLowerCase()] || Code2;
  };

  const LanguageIcon = getLanguageIcon(language);

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
    <div className="group relative max-w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 shadow-sm overflow-hidden">
      {/* Header bar */}
      <div className="flex items-center justify-between px-3 py-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="flex items-center gap-3">
          {/* Language-specific icon with subtle glow */}
          <div className="flex items-center justify-center w-7 h-7 rounded-md bg-gradient-to-br from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 border border-blue-100 dark:border-blue-800/30">
            <LanguageIcon className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          </div>
          {/* Enhanced language pill */}
          <span className="text-xs font-mono text-gray-700 dark:text-gray-200 select-none">
            {language ? language.toLowerCase() : 'plaintext'}
          </span>
        </div>
        {/* Copy button */}
        <CopyButton text="" onCustomCopy={handleCopy} size="sm" />
      </div>
      
      {/* Code content */}
      <div className="relative">
        <pre 
          {...props} 
          ref={preRef} 
          className={`${className || ''} m-0 p-4 border-none overflow-x-auto text-sm leading-relaxed`}
          style={{ maxWidth: '100%' }}
        >
          {children}
        </pre>
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