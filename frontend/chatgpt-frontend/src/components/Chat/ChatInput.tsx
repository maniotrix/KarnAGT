import React, { KeyboardEvent, FormEvent, useRef, useEffect, ChangeEvent } from 'react';

// Modern UI Libraries
import { 
  Send, 
  Loader2,
  CornerDownLeft
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useHotkeys } from 'react-hotkeys-hook';

// Clean Architecture Integration
import { useUiStore } from '../../app/stores/uiStore';
import { useChatInputFocus } from '../../hooks/useChatInputFocus';

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  input,
  setInput,
  onSubmit,
  isLoading,
  disabled = false,
  placeholder = "Type your message...",
}) => {
  // Clean Architecture Integration
  const { theme } = useUiStore();
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // 🎯 FOCUS MANAGEMENT: Use our custom hook for intelligent focus behavior
  const { focusInput, resetUserIntent } = useChatInputFocus({
    isLoading,
    disabled,
    inputRef: textareaRef,
    autoFocusOnMount: true,
    autoFocusAfterResponse: true,
  });

  const handleInputChange = (e: ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
  };

  // Auto-resize textarea
  const adjustTextareaHeight = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  };

  useEffect(() => {
    adjustTextareaHeight();
  }, [input]);

  const handleFormSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!disabled && !isLoading && input.trim()) {
      onSubmit(e);
      // Reset user intent after successful submit so we can auto-focus after AI response
      resetUserIntent();
    }
  };

  // Keyboard shortcuts
  useHotkeys('mod+enter', (e) => {
    e.preventDefault();
    if (!disabled && !isLoading && input.trim()) {
      handleFormSubmit(e as any);
    }
  }, { enableOnFormTags: ['textarea'] });

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && !isLoading && input.trim()) {
        handleFormSubmit(e as any);
      }
    }
  };

  const characterCount = input?.length || 0;
  const isOverLimit = characterCount > 4000;
  const isNearLimit = characterCount > 3500;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full"
    >
      <form onSubmit={handleFormSubmit} className="relative">
        {/* Main Input Container */}
        <div className={`flex items-end gap-3 p-4 bg-white dark:bg-gray-800 border rounded-2xl transition-all duration-200 ${
          disabled 
            ? 'border-gray-200 dark:border-gray-700 opacity-60' 
            : isOverLimit
              ? 'border-red-300 dark:border-red-600 ring-2 ring-red-100 dark:ring-red-900/20'
              : 'border-gray-300 dark:border-gray-600 focus-within:border-blue-500 dark:focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 dark:focus-within:ring-blue-900/20'
        }`}>
          {/* Textarea */}
          <div className="flex-1 min-w-0">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              disabled={disabled || isLoading}
              className="w-full resize-none border-0 bg-transparent text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400 focus:outline-none focus:ring-0 text-base leading-6"
              rows={1}
              style={{
                minHeight: '24px',
                maxHeight: '200px',
              }}
              onInput={adjustTextareaHeight}
            />
          </div>

          {/* Send Button */}
          <button
            type="submit"
            disabled={disabled || isLoading || !input.trim() || isOverLimit}
            className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-200 ${
              disabled || isLoading || !input.trim() || isOverLimit
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg transform hover:scale-105'
            }`}
            title={
              disabled 
                ? "Input disabled" 
                : isLoading 
                  ? "Sending..." 
                  : !input.trim()
                    ? "Type a message to send"
                    : isOverLimit
                      ? "Message is too long"
                      : "Send message (Enter)"
            }
          >
            <AnimatePresence mode="wait">
              {isLoading ? (
                <motion.div
                  key="loading"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                >
                  <Loader2 className="w-5 h-5 animate-spin" />
                </motion.div>
              ) : (
                <motion.div
                  key="send"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                >
                  <Send className="w-5 h-5" />
                </motion.div>
              )}
            </AnimatePresence>
          </button>
        </div>

        {/* Input Hints and Status */}
        <div className="flex items-center justify-between mt-2 px-2">
          {/* Left side: Hints and errors */}
          <div className="flex items-center gap-4 text-sm">
            {disabled ? (
              <span className="text-gray-500 dark:text-gray-400">
                Input disabled
              </span>
            ) : (
              <div className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
                <CornerDownLeft className="w-4 h-4" />
                <span>Enter to send, Shift+Enter for new line</span>
              </div>
            )}
          </div>

          {/* Right side: Character count */}
          <div className={`text-sm transition-colors ${
            isOverLimit 
              ? 'text-red-600 dark:text-red-400 font-medium'
              : isNearLimit
                ? 'text-amber-600 dark:text-amber-400'
                : 'text-gray-500 dark:text-gray-400'
          }`}>
            {characterCount}/4000
          </div>
        </div>
      </form>
    </motion.div>
  );
}; 