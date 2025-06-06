import React, { KeyboardEvent, FormEvent, useRef, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

// Modern UI Libraries
import { 
  Send, 
  Loader2,
  CornerDownLeft,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useHotkeys } from 'react-hotkeys-hook';

// Clean Architecture Integration
import { useUiStore } from '../../app/stores/uiStore';

// Validation Schema
const messageSchema = z.object({
  message: z.string()
    .min(1, 'Message cannot be empty')
    .max(4000, 'Message too long (max 4000 characters)')
    .refine(val => val.trim().length > 0, 'Message cannot be only whitespace')
});

type MessageFormData = z.infer<typeof messageSchema>;

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
  
  // Form setup with validation
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    setValue,
    watch,
    reset
  } = useForm<MessageFormData>({
    resolver: zodResolver(messageSchema),
    mode: 'onChange',
    defaultValues: {
      message: input
    }
  });

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const formValue = watch('message');

  // Sync form value with parent state
  useEffect(() => {
    setValue('message', input);
  }, [input, setValue]);

  useEffect(() => {
    setInput(formValue || '');
  }, [formValue, setInput]);

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
  }, [formValue]);

  // Keyboard shortcuts
  useHotkeys('mod+enter', (e) => {
    e.preventDefault();
    if (!disabled && !isLoading && formValue?.trim()) {
      handleFormSubmit({ message: formValue });
    }
  }, { enableOnFormTags: ['textarea'] });

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!disabled && !isLoading && formValue?.trim()) {
        handleFormSubmit({ message: formValue });
      }
    }
  };

  const handleFormSubmit = (data: MessageFormData) => {
    if (!disabled && !isLoading && data.message.trim()) {
      // Create a synthetic form event for compatibility
      const syntheticEvent = {
        preventDefault: () => {},
        target: { value: data.message },
        currentTarget: null,
        bubbles: false,
        cancelable: false,
        defaultPrevented: false,
        eventPhase: 0,
        isTrusted: false,
        nativeEvent: {} as Event,
        persist: () => {},
        stopPropagation: () => {},
        timeStamp: Date.now(),
        type: 'submit'
      } as unknown as FormEvent;
      
      onSubmit(syntheticEvent);
      reset(); // Clear form after submission
    }
  };

  const characterCount = formValue?.length || 0;
  const isOverLimit = characterCount > 4000;
  const isNearLimit = characterCount > 3500;

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="w-full"
    >
      <form onSubmit={handleSubmit(handleFormSubmit)} className="relative">
        {/* Main Input Container */}
        <div className={`flex items-end gap-3 p-4 bg-white dark:bg-gray-800 border rounded-2xl transition-all duration-200 ${
          disabled 
            ? 'border-gray-200 dark:border-gray-700 opacity-60' 
            : errors.message
              ? 'border-red-300 dark:border-red-600 ring-2 ring-red-100 dark:ring-red-900/20'
              : 'border-gray-300 dark:border-gray-600 focus-within:border-blue-500 dark:focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 dark:focus-within:ring-blue-900/20'
        }`}>
          {/* Textarea */}
          <div className="flex-1 min-w-0">
            <textarea
              {...register('message')}
              ref={textareaRef}
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
            disabled={disabled || isLoading || !isValid || !formValue?.trim()}
            className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-200 ${
              disabled || isLoading || !isValid || !formValue?.trim()
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg transform hover:scale-105'
            }`}
            title={
              disabled 
                ? "Input disabled" 
                : isLoading 
                  ? "Sending..." 
                  : !formValue?.trim()
                    ? "Type a message to send"
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
            {errors.message ? (
              <motion.div
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-1 text-red-600 dark:text-red-400"
              >
                <AlertCircle className="w-4 h-4" />
                <span>{errors.message.message}</span>
              </motion.div>
            ) : disabled ? (
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