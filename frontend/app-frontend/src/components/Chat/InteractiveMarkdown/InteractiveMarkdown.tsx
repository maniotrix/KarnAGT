import React from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';

import { InteractiveMarkdownProps } from './types';
import { useMarkdownComponents } from './hooks/useMarkdownComponents';

export const InteractiveMarkdown: React.FC<InteractiveMarkdownProps> = ({ 
  content, 
  className = '',
  theme = 'assistant'
}) => {
  const components = useMarkdownComponents(theme);

  return (
    <div className={className}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
