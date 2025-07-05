import React, { KeyboardEvent, FormEvent, useRef, useEffect, ChangeEvent, useState } from 'react';

// Modern UI Libraries
import { 
  Send, 
  Loader2,
  CornerDownLeft,
  AlertTriangle
} from 'lucide-react';
// Remove framer motion to improve performance
// import { motion, AnimatePresence } from 'framer-motion';
import { useHotkeys } from 'react-hotkeys-hook';

// Clean Architecture Integration
import { useUiStore } from '../../app/stores/uiStore';
import { useChatInputFocus } from '../../hooks/useChatInputFocus';

// Universal File Upload Integration
import { UniversalFileUpload, type UniversalFileUploadRef } from './UniversalFileUpload';
import type { UploadFile } from '../../types/upload';

interface ChatInputProps {
  input: string;
  setInput: (value: string) => void;
  onSubmit: (e: FormEvent) => void;
  isLoading: boolean;
  disabled?: boolean;
  placeholder?: string;
  onFileUpload?: (files: UploadFile[]) => void;
  enableFileUpload?: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({
  input,
  setInput,
  onSubmit,
  isLoading,
  disabled = false,
  placeholder = "Type your message...",
  onFileUpload,
  enableFileUpload = true,
}) => {
  // Clean Architecture Integration
  const { theme } = useUiStore();
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileUploadRef = useRef<UniversalFileUploadRef>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [fileCount, setFileCount] = useState<number>(0);

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
    e.stopPropagation(); // Prevent any event bubbling
    
    console.log('🚀 [ChatInput] Form submit triggered explicitly');
    
    if (!disabled && !isLoading && (input.trim() || fileCount > 0)) {
      onSubmit(e);
      // Reset user intent after successful submit so we can auto-focus after AI response
      resetUserIntent();
      // Clear uploaded files after sending
      fileUploadRef.current?.clearFiles();
      setFileCount(0);
      setUploadError(null);
    } else {
      console.log('🚫 [ChatInput] Form submit blocked - conditions not met:', {
        disabled,
        isLoading,
        hasInput: !!input.trim(),
        hasFiles: fileCount > 0,
        isOverLimit
      });
    }
  };

  // Keyboard shortcuts
  useHotkeys('mod+enter', (e) => {
    e.preventDefault();
    e.stopPropagation();
    console.log('⌨️ [ChatInput] Keyboard shortcut Cmd+Enter triggered');
    if (!disabled && !isLoading && (input.trim() || fileCount > 0)) {
      handleFormSubmit(e as any);
    }
  }, { enableOnFormTags: ['textarea'] });

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      e.stopPropagation();
      console.log('⌨️ [ChatInput] Enter key pressed (without Shift)');
      if (!disabled && !isLoading && (input.trim() || fileCount > 0)) {
        handleFormSubmit(e as any);
      }
    }
  };

  const handleFileUploadComplete = (files: UploadFile[]) => {
    console.log('📁 [ChatInput] Upload complete callback');
    setUploadError(null);
    if (onFileUpload) {
      onFileUpload(files);
    }
  };

  const handleFilesChanged = (allFiles: UploadFile[]) => {
    console.log('📁 [ChatInput] Files changed, updating count to:', allFiles.filter(f => f.status === 'success').length);
    setFileCount(allFiles.filter(f => f.status === 'success').length);
    
    // CRITICAL FIX: Also notify parent about file changes (including removals)
    if (onFileUpload) {
      console.log('📁 [ChatInput] Notifying parent about file changes:', allFiles);
      onFileUpload(allFiles);
    }
  };

  const handleFileUploadError = (error: string) => {
    setUploadError(error);
    // Clear error after 5 seconds
    setTimeout(() => setUploadError(null), 5000);
  };

  const characterCount = input?.length || 0;
  const isOverLimit = characterCount > 4000;
  const isNearLimit = characterCount > 3500;
  const hasFiles = fileCount > 0;

  // Get file breakdown for display
  const filesByCategory = fileUploadRef.current?.getFilesByCategory();
  const imageCount = filesByCategory?.images.length || 0;
  const documentCount = filesByCategory?.documents.length || 0;

  return (
    <div className="w-full">
      <form onSubmit={handleFormSubmit} className="relative">
        {/* File Upload Error */}
        {uploadError && (
          <div className="mb-2 p-2 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-sm text-red-700">
            <AlertTriangle className="w-4 h-4 flex-shrink-0" />
            <span>{uploadError}</span>
          </div>
        )}

        {/* Main Input Container */}
        <div className={`flex items-end gap-3 p-4 bg-white dark:bg-gray-800 border rounded-2xl transition-all duration-200 ${
          disabled 
            ? 'border-gray-200 dark:border-gray-700 opacity-60' 
            : isOverLimit
              ? 'border-red-300 dark:border-red-600 ring-2 ring-red-100 dark:ring-red-900/20'
              : 'border-gray-300 dark:border-gray-600 focus-within:border-blue-500 dark:focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-100 dark:focus-within:ring-blue-900/20'
        }`}>
          
          {/* Universal File Upload (Compact) - Show before textarea */}
          {enableFileUpload && (
            <div className="flex-shrink-0">
              <UniversalFileUpload
                ref={fileUploadRef}
                compact={true}
                disabled={disabled}
                maxFiles={5}
                acceptedTypes="all"
                onUploadComplete={handleFileUploadComplete}
                onFilesSelected={handleFilesChanged}
                onError={handleFileUploadError}
              />
            </div>
          )}

          {/* Textarea */}
          <div className="flex-1 min-w-0">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              placeholder={hasFiles ? "Describe what you'd like me to analyze in these files..." : placeholder}
              disabled={disabled}
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
            disabled={disabled || isLoading || (!input.trim() && !hasFiles) || isOverLimit}
            onClick={(e) => {
              console.log('🖱️ [ChatInput] Send button clicked explicitly');
              // Let the form submission handle the rest
            }}
            className={`flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-200 ${
              disabled || isLoading || (!input.trim() && !hasFiles) || isOverLimit
                ? 'bg-gray-100 dark:bg-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed'
                : 'bg-blue-600 hover:bg-blue-700 text-white shadow-md hover:shadow-lg transform hover:scale-105'
            }`}
            title={
              disabled 
                ? "Input disabled" 
                : isLoading 
                  ? "Sending..." 
                  : (!input.trim() && !hasFiles)
                    ? "Type a message or upload files to send"
                    : isOverLimit
                      ? "Message is too long"
                      : hasFiles
                        ? "Send message with files"
                        : "Send message (Enter)"
            }
          >
            {isLoading ? (
              <Loader2 className="w-5 h-5 animate-spin" />
            ) : (
              <Send className="w-5 h-5" />
            )}
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
            ) : hasFiles ? (
              <span className="text-blue-600 dark:text-blue-400">
                {fileCount} file{fileCount !== 1 ? 's' : ''} ready
                {imageCount > 0 && documentCount > 0 
                  ? ` (${imageCount} images, ${documentCount} documents)`
                  : imageCount > 0 
                    ? ` (${imageCount} image${imageCount !== 1 ? 's' : ''})`
                    : documentCount > 0
                      ? ` (${documentCount} document${documentCount !== 1 ? 's' : ''})`
                      : ''
                }
              </span>
            ) : (
              <div className="flex items-center gap-1 text-gray-500 dark:text-gray-400">
                <CornerDownLeft className="w-4 h-4" />
                <span>Enter to send, Shift+Enter for new line</span>
                {enableFileUpload && (
                  <span className="ml-2 text-gray-400">• Click 📁 to add files</span>
                )}
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
    </div>
  );
}; 