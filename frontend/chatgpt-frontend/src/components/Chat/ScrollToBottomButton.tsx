import React from 'react';
import { ArrowDown } from 'lucide-react';
import { motion } from 'framer-motion';
import { useScrollToBottom, useSticky } from 'react-scroll-to-bottom';

interface ScrollToBottomButtonProps {
  /** Custom position classes - default is bottom-center */
  className?: string;
  /** Whether to show only when messages exist */
  messageCount?: number;
}

export const ScrollToBottomButton: React.FC<ScrollToBottomButtonProps> = ({
  className = 'absolute bottom-4 left-0 right-0 flex justify-center z-10',
  messageCount = 0
}) => {
  // Library hooks - no complex logic needed
  const scrollToBottom = useScrollToBottom();
  const [isAtBottom] = useSticky();
  
  // Show button when user scrolled up and there are messages
  const shouldShow = !isAtBottom && messageCount > 0;

  if (!shouldShow) return null;

  return (
    <div className={className}>
      <motion.button
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.8 }}
        onClick={() => scrollToBottom()}
        className="p-3 bg-blue-600 hover:bg-blue-700 text-white rounded-full shadow-xl border-2 border-white dark:border-gray-800 transition-all duration-200 hover:scale-105"
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
      >
        <ArrowDown className="w-5 h-5" />
      </motion.button>
    </div>
  );
};
