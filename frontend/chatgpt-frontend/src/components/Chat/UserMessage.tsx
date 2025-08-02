import React, { useState, useEffect } from 'react';
import { Message, ImageAttachment } from '../../types/chat';
import { useConversationImagesContext } from '../../contexts/ConversationImagesContext';

// Markdown Support
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';

// Modern UI Libraries  
import { Avatar, AvatarFallback } from '@radix-ui/react-avatar';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@radix-ui/react-tooltip';
import * as Dialog from '@radix-ui/react-dialog';
import { 
  User, 
  Clock,
  Copy,
  Check,
  Edit3,
  X,
  FileText
} from 'lucide-react';
import { motion } from 'framer-motion';

// Clean Architecture Integration
import { useUiStore } from '../../app/stores/uiStore';

interface UserMessageProps {
  message: Message;
  onEdit?: (messageId: string, newContent: string) => Promise<boolean>;
}

export const UserMessage: React.FC<UserMessageProps> = ({ 
  message, 
  onEdit
}) => {
  // Clean Architecture Integration
  const { theme } = useUiStore();
  
  // Copy functionality
  const [copied, setCopied] = useState(false);
  
  // Edit functionality
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [isSaving, setIsSaving] = useState(false);
  
  // Image modal functionality
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  
  // File IDs are now handled at the conversation level by ConversationImagesProvider

  // ✅ CONVERSATION CONTEXT: Get image URLs from conversation-level provider
  const { getImageUrl, isLoading, isError } = useConversationImagesContext();

  const formatTime = (date: Date | string) => {
    const d = typeof date === 'string' ? new Date(date) : date;
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy message:', error);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditContent(message.content);
  };

  const handleSave = async () => {
    if (!onEdit || !message.message_id) return;
    
    const trimmedContent = editContent.trim();
    if (!trimmedContent || trimmedContent === message.content) {
      setIsEditing(false);
      return;
    }
    
    // STEP 1: Immediately exit edit mode and show saving state
    setIsEditing(false);
    setIsSaving(true);
    
    // STEP 2: Call the edit function (this will update the message and clear subsequent ones)
    const success = await onEdit(message.message_id, trimmedContent);
    
    // STEP 3: Clear saving state
    setIsSaving(false);
    
    // If edit failed, go back to edit mode so user can retry
    if (!success) {
      setIsEditing(true);
      // Reset content to current message content in case backend partially updated it
      setEditContent(message.content);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditContent(message.content);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      handleCancel();
    }
  };

  const canEdit = onEdit && !isSaving;

  // ✅ MODERN: Get images using metadata + generated URLs  
  const getDisplayImages = () => {
    // FIRST: Use local images if available (fresh uploads before AI response)
    if (message.localImages?.length) {
      return message.localImages.map(img => ({
        id: img.fileId,
        filename: img.filename,
        url: img.blobUrl
      }));
    }
    
    // SECOND: Use backend attachments with on-demand generated URLs
    if (message.attachments?.length) {
      return message.attachments
        .map((attachment, index) => {
          // Handle attachment objects (preferred)
          if (typeof attachment === 'object' && attachment !== null) {
            const fileId = attachment.file_id;
            const generatedUrl = getImageUrl(fileId);
            
            return {
              id: fileId,
              filename: attachment.filename || attachment.original_filename || `Image ${index + 1}`,
              url: generatedUrl // Will be null if loading/error
            };
          }
          // Handle string file IDs (legacy/fallback)  
          else if (typeof attachment === 'string') {
            const generatedUrl = getImageUrl(attachment);
            
            return {
              id: attachment,
              filename: `Image ${index + 1}`,
              url: generatedUrl
            };
          }
          return null;
        })
        .filter(Boolean) as Array<{ id: string; filename: string; url: string | null }>;
    }
    
    return [];
  };

  const displayImages = getDisplayImages();

  // Get document filenames from local data first, then backend data
  const getDocumentFilenames = () => {
    // FIRST: Use local documents if available (fresh uploads before backend processing)
    if (message.localDocuments?.length) {
      return message.localDocuments.map(doc => doc.filename);
    }
    
    // SECOND: Use backend vector_file_references after processing is complete
    if (message.vector_file_references?.processed_files) {
      return message.vector_file_references.processed_files.map((file: any) => file.filename).filter(Boolean);
    }
    
    return [];
  };

  const documentFilenames = getDocumentFilenames();

  // Render images with loading states
  const renderImages = () => {
    if (!displayImages.length) return null;

    if (displayImages.length === 1) {
      // Single image - larger display
      const image = displayImages[0];
      
      return (
        <div className="flex w-[70%] flex-col items-end mb-2">
          <div className="overflow-hidden rounded-lg w-full h-full max-w-96 max-h-64">
            {image.url ? (
              <Dialog.Root open={selectedImage === image.url} onOpenChange={(open) => !open && setSelectedImage(null)}>
                <Dialog.Trigger asChild>
                  <button 
                    onClick={() => setSelectedImage(image.url!)}
                    className="overflow-hidden rounded-lg w-full h-full max-w-96 max-h-64"
                  >
                    <img 
                      alt={image.filename}
                      className="max-w-full object-cover object-center overflow-hidden rounded-lg w-full h-full max-w-96 max-h-64 w-fit transition-opacity duration-300 opacity-100"
                      src={image.url}
                    />
                  </button>
                </Dialog.Trigger>
              </Dialog.Root>
            ) : (
              // Loading state
              <div className="w-full h-48 bg-gray-100 rounded-lg flex items-center justify-center">
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                    <span className="text-sm text-gray-600">Loading...</span>
                  </div>
                ) : isError ? (
                  <div className="text-red-600 text-sm text-center">
                    <div>⚠️ Failed to load</div>
                    <div className="text-xs mt-1">Image unavailable</div>
                  </div>
                ) : (
                  <div className="text-gray-400 text-sm">📷 Image</div>
                )}
              </div>
            )}
          </div>
        </div>
      );
    } else {
      // Multiple images - grid display
      return (
        <div className="flex w-[70%] flex-col items-end mb-2">
          <div className="flex flex-row items-center justify-end gap-1 max-w-72">
            {displayImages.slice(0, 2).map((image, index) => (
              <div 
                key={image.id}
                className={`h-32 w-32 overflow-hidden rounded-lg ${
                  index === 0 ? 'rounded-ss-2xl rounded-es-2xl' : 'rounded-se-2xl rounded-ee-sm'
                }`}
              >
                {image.url ? (
                  <Dialog.Root open={selectedImage === image.url} onOpenChange={(open) => !open && setSelectedImage(null)}>
                    <Dialog.Trigger asChild>
                      <button 
                        onClick={() => setSelectedImage(image.url!)}
                        className={`h-32 w-32 overflow-hidden rounded-lg ${
                          index === 0 ? 'rounded-ss-2xl rounded-es-2xl' : 'rounded-se-2xl rounded-ee-sm'
                        }`}
                      >
                        <img 
                          alt={image.filename}
                          className={`max-w-full aspect-square object-cover object-center h-32 w-32 overflow-hidden rounded-lg w-fit transition-opacity duration-300 opacity-100 ${
                            index === 0 ? 'rounded-ss-2xl rounded-es-2xl' : 'rounded-se-2xl rounded-ee-sm'
                          }`}
                          src={image.url}
                        />
                      </button>
                    </Dialog.Trigger>
                  </Dialog.Root>
                ) : (
                  // Loading state
                  <div className="h-32 w-32 bg-gray-100 rounded-lg flex items-center justify-center">
                    {isLoading ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                    ) : (
                      <div className="text-gray-400 text-xs">📷</div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {displayImages.length > 2 && (
              <div className="text-xs text-gray-500 ml-2">
                +{displayImages.length - 2} more
              </div>
            )}
          </div>
        </div>
      );
    }
  };

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className="flex gap-4 p-4 rounded-lg group hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors justify-end"
      >
        {/* Message Content */}
        <div className="flex flex-col max-w-[80%] items-end">
          {/* Message Header */}
          <div className="flex items-center gap-2 mb-2 flex-row-reverse">
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              You
            </span>
            
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              <span>{formatTime(message.createdAt || new Date())}</span>
            </div>
          </div>

          {/* Images Display */}
          {renderImages()}

          {/* Document Files Display */}
          {documentFilenames.length > 0 && (
            <div className="flex w-[70%] flex-col items-end mb-2">
              <div className="bg-gray-100 rounded-lg p-3 max-w-72">
                <div className="flex items-center gap-2 text-sm text-gray-700 mb-2">
                  <FileText className="w-4 h-4" />
                  <span className="font-medium">
                    {documentFilenames.length} document{documentFilenames.length > 1 ? 's' : ''}
                  </span>
                </div>
                <div className="space-y-1">
                  {documentFilenames.map((filename: string, index: number) => (
                    <div key={index} className="text-xs text-gray-600 truncate">
                      📄 {filename}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Message Bubble */}
          <div className="px-4 py-3 rounded-2xl max-w-none bg-blue-600 text-white ml-8">
            {/* Message Text with Edit/Display Mode */}
            {isEditing ? (
              <div>
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  onKeyDown={handleKeyDown}
                  className="w-full p-3 rounded-lg border resize-none min-h-[100px] bg-blue-700 text-white border-blue-500 placeholder-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Edit your message..."
                  disabled={isSaving}
                  autoFocus
                />
                <div className="flex items-center gap-2 mt-2 text-xs text-blue-100">
                  <span>Press Ctrl+Enter to save, Esc to cancel</span>
                </div>
              </div>
            ) : (
              <div className="prose prose-sm max-w-none prose-invert text-white">
                {/* Show saving indicator if message is being edited */}
                {isSaving && (
                  <div className="flex items-center gap-2 mb-2 text-xs opacity-75">
                    <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
                    <span>Saving changes...</span>
                  </div>
                )}
                
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  rehypePlugins={[rehypeHighlight]}
                  components={{
                    // Custom styling for code blocks
                    pre: ({ children, ...props }) => (
                      <pre {...props} className="bg-blue-800 rounded-lg p-3 overflow-x-auto">
                        {children}
                      </pre>
                    ),
                    // Custom styling for inline code
                    code: ({ children, className, ...props }) => {
                      const isInline = !className;
                      return (
                        <code 
                          {...props} 
                          className={`${className || ''} ${
                            isInline 
                              ? 'bg-blue-800 px-1 py-0.5 rounded text-sm' 
                              : ''
                          }`}
                        >
                          {children}
                        </code>
                      );
                    }
                  }}
                >
                  {message.content}
                </ReactMarkdown>
              </div>
            )}
          </div>

          {/* Action Buttons - Below the message bubble */}
          <div className="flex items-center gap-1 mt-2 justify-end">
            {/* Edit Mode Buttons */}
            {isEditing ? (
              <>
                <button
                  onClick={handleCancel}
                  disabled={isSaving}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors bg-gray-100 text-gray-700 hover:bg-gray-200 ${
                    isSaving ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                >
                  Cancel
                </button>
                
                <button
                  onClick={handleSave}
                  disabled={isSaving || !editContent.trim() || editContent.trim() === message.content}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors bg-blue-600 text-white hover:bg-blue-700 ${
                    (isSaving || !editContent.trim() || editContent.trim() === message.content) ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                >
                  {isSaving ? 'Saving...' : 'Send'}
                </button>
              </>
            ) : (
              <>
                {/* Edit Button */}
                {canEdit && (
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <button
                        onClick={handleEdit}
                        className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-100 text-blue-600"
                      >
                        <Edit3 className="w-3 h-3" />
                      </button>
                    </TooltipTrigger>
                    <TooltipContent side="bottom">
                      <p>Edit message</p>
                    </TooltipContent>
                  </Tooltip>
                )}
                
                {/* Copy Button */}
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={handleCopy}
                      className="p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-opacity hover:bg-blue-100 text-blue-600"
                    >
                      {copied ? (
                        <Check className="w-3 h-3" />
                      ) : (
                        <Copy className="w-3 h-3" />
                      )}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="bottom">
                    <p>{copied ? 'Copied!' : 'Copy message'}</p>
                  </TooltipContent>
                </Tooltip>
              </>
            )}
          </div>
        </div>

        {/* User Avatar */}
        <Avatar className="w-8 h-8 shrink-0">
          <AvatarFallback className="bg-gray-100 dark:bg-gray-700">
            <User className="w-4 h-4 text-gray-600 dark:text-gray-400" />
          </AvatarFallback>
        </Avatar>
      </motion.div>

      {/* Image Lightbox Modal */}
      <Dialog.Root open={!!selectedImage} onOpenChange={(open) => !open && setSelectedImage(null)}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 flex items-center justify-center overflow-hidden bg-black/90 dark:bg-black/80 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
          <Dialog.Content className="fixed left-[50%] top-[50%] translate-x-[-50%] translate-y-[-50%] focus:outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95 data-[state=closed]:slide-out-to-left-1/2 data-[state=closed]:slide-out-to-top-[48%] data-[state=open]:slide-in-from-left-1/2 data-[state=open]:slide-in-from-top-[48%]">
            {/* Close Button */}
            <Dialog.Close asChild>
              <button 
                className="absolute right-4 top-4 z-10 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2"
                aria-label="Close"
              >
                <X className="h-5 w-5 text-gray-100" />
              </button>
            </Dialog.Close>
            
            {/* Image Display */}
            {selectedImage && (
              <div className="relative max-h-[85vh] max-w-[90vw]">
                <img 
                  alt="Enlarged view"
                  className="h-full w-full object-contain"
                  src={selectedImage}
                />
              </div>
            )}
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </TooltipProvider>
  );
}; 