import React from 'react';
import { ArrowDown } from 'lucide-react';
import { useScrollToBottom } from '../../contexts/ScrollContext';

interface ScrollToBottomButtonProps {
  /** Additional CSS classes for styling (no positioning) */
  className?: string;
  /** Whether to show only when messages exist */
  messageCount?: number;
}

export const ScrollToBottomButton: React.FC<ScrollToBottomButtonProps> = ({
  className = '',
  messageCount = 0
}) => {
  // Use our custom hook - clean and simple!
  const { scrollToBottom, isAtBottom } = useScrollToBottom();
  
  // Show button when user scrolled up and there are messages
  const shouldShow = !isAtBottom && messageCount > 0;

  if (!shouldShow) return null;

  // Clean button component - parent decides positioning - NO ANIMATIONS
  return (
    <button
      onClick={() => scrollToBottom({ behavior: 'smooth' })}
      className={`p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-xl border-2 border-white dark:border-gray-800 ${className}`}
    >
      <ArrowDown className="w-5 h-5" />
    </button>
  );
};
