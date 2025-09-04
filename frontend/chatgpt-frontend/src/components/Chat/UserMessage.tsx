import React, { useState, useEffect } from 'react';
import { Message, ImageAttachment } from '../../types/chat';
import { useConversationImagesContext } from '../../contexts/ConversationImagesContext';

// Interactive Markdown Component
import { InteractiveMarkdown } from './InteractiveMarkdown/InteractiveMarkdown';
import { ImageModal } from './ImageModal';

// Modern UI Libraries  
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@radix-ui/react-tooltip';
import { 
  Copy,
  Check,
  Edit3,
  FileText
} from 'lucide-react';
import { motion } from 'framer-motion';



interface UserMessageProps {
  message: Message;
  onEdit?: (messageId: string, newContent: string) => Promise<boolean>;
}

export const UserMessage: React.FC<UserMessageProps> = ({ 
  message, 
  onEdit
}) => {
  // Copy functionality
  const [copied, setCopied] = useState(false);
  
  // Edit functionality
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(message.content);
  const [isSaving, setIsSaving] = useState(false);
  
  // Image modal functionality
  const [currentImageIndex, setCurrentImageIndex] = useState<number>(-1);
  
  // File IDs are now handled at the conversation level by ConversationImagesProvider

  // ✅ CONVERSATION CONTEXT: Get image URLs from conversation-level provider
  const { getImageUrl, isLoading, isError } = useConversationImagesContext();



  const handleCopy = async () => {
    try {
      // Modern Clipboard API (preferred)
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(message.content);
      } else {
        // Fallback for older browsers or non-HTTPS contexts
        const textArea = document.createElement('textarea');
        textArea.value = message.content;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        document.execCommand('copy');
        textArea.remove();
      }
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Failed to copy message:', error);
      // Still show copied state even if there was an error
      // User might have manually copied the text
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleEdit = () => {
    setIsEditing(true);
    setEditContent(message.content);
  };

  const handleSave = async () => {
    if (!onEdit || !message.message_id) return;
    
    const trimmedContent = editContent.trim();
    if (!trimmedContent) {
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
    
    // If edit failed, stay in display mode - user must manually click edit to retry
    if (!success) {
      // Reset content to current message content in case backend partially updated it
      setEditContent(message.content);
      // Note: We don't setIsEditing(true) here - user must click edit button to retry
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
              <button 
                onClick={() => setCurrentImageIndex(0)}
                className="overflow-hidden rounded-lg w-full h-full max-w-96 max-h-64 cursor-pointer hover:opacity-90 transition-opacity"
              >
                <img 
                  alt={image.filename}
                  className="max-w-full object-cover object-center overflow-hidden rounded-lg w-full h-full max-w-96 max-h-64 w-fit transition-opacity duration-300 opacity-100"
                  src={image.url}
                />
              </button>
            ) : (
              // Loading state
              <div className="w-full h-48 bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center">
                {isLoading ? (
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 dark:border-blue-400"></div>
                    <span className="text-sm text-gray-600 dark:text-gray-400">Loading...</span>
                  </div>
                ) : isError ? (
                  <div className="text-red-600 dark:text-red-400 text-sm text-center">
                    <div>⚠️ Failed to load</div>
                    <div className="mt-1">Image unavailable</div>
                  </div>
                ) : (
                  <div className="text-gray-400 dark:text-gray-500 text-sm">📷 Image</div>
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
                  <button 
                    onClick={() => setCurrentImageIndex(index)}
                    className={`h-32 w-32 overflow-hidden rounded-lg cursor-pointer hover:opacity-90 transition-opacity ${
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
                ) : (
                  // Loading state
                  <div className="h-32 w-32 bg-gray-100 dark:bg-gray-800 rounded-lg flex items-center justify-center">
                    {isLoading ? (
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 dark:border-blue-400"></div>
                    ) : (
                      <div className="text-gray-400 dark:text-gray-500">📷</div>
                    )}
                  </div>
                )}
              </div>
            ))}
            {displayImages.length > 2 && (
              <div className="text-gray-500 dark:text-gray-400 ml-2">
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
        className="px-3 py-2 sm:px-4 sm:py-3 md:px-6 md:py-4 rounded-lg group hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors flex justify-end"
      >
        {/* Message Content */}
        <div className="flex flex-col max-w-[80%] min-w-0 items-end">


          {/* Images Display */}
          {renderImages()}

          {/* Document Files Display */}
          {documentFilenames.length > 0 && (
            <div className="flex w-[70%] flex-col items-end mb-2">
              <div className="bg-gray-100 dark:bg-gray-700 rounded-lg p-3 max-w-72">
                <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-gray-300 mb-2">
                  <FileText className="w-4 h-4" />
                  <span className="font-medium">
                    {documentFilenames.length} document{documentFilenames.length > 1 ? 's' : ''}
                  </span>
                </div>
                <div className="space-y-1">
                  {documentFilenames.map((filename: string, index: number) => (
                    <div key={index} className="text-gray-600 dark:text-gray-400 truncate">
                      📄 {filename}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Message Bubble */}
          <div className="px-3 py-2 sm:px-4 sm:py-3 md:px-5 md:py-4 rounded-2xl max-w-full bg-blue-600 text-white ml-8">
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
                <div className="flex items-center gap-2 mt-2 text-blue-100">
                  <span>Press Ctrl+Enter to save, Esc to cancel</span>
                </div>
              </div>
            ) : (
              <div className="prose prose-fluid max-w-full prose-invert text-white">
                {/* Show saving indicator if message is being edited */}
                {isSaving && (
                  <div className="flex items-center gap-2 mb-2 opacity-75">
                    <div className="w-3 h-3 border border-current border-t-transparent rounded-full animate-spin" />
                    <span>Saving changes...</span>
                  </div>
                )}
                
                <InteractiveMarkdown 
                  content={message.content}
                  theme="user"
                  className="break-words overflow-hidden"
                />
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
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 ${
                    isSaving ? 'opacity-50 cursor-not-allowed' : ''
                  }`}
                >
                  Cancel
                </button>
                
                <button
                  onClick={handleSave}
                  disabled={isSaving || !editContent.trim()}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors bg-blue-600 dark:bg-blue-500 text-white hover:bg-blue-700 dark:hover:bg-blue-600 ${
                    (isSaving || !editContent.trim()) ? 'opacity-50 cursor-not-allowed' : ''
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
                        className="p-2 rounded-lg opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 min-h-[44px] min-w-[44px] flex items-center justify-center"
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
                      className="p-2 rounded-lg opacity-100 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity hover:bg-blue-100 dark:hover:bg-blue-900/30 text-blue-600 dark:text-blue-400 min-h-[44px] min-w-[44px] flex items-center justify-center"
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


      </motion.div>

      {/* Image Modal */}
      <ImageModal 
        images={displayImages}
        currentIndex={currentImageIndex}
        onClose={() => setCurrentImageIndex(-1)}
        onNavigate={setCurrentImageIndex}
      />
    </TooltipProvider>
  );
}; 