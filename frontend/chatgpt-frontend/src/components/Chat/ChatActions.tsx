import React, { useState } from 'react';

// Modern UI Libraries
import * as Dialog from '@radix-ui/react-dialog';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@radix-ui/react-tooltip';
import { 
  Square,
  RotateCcw,
  Share2,
  Trash2,
  AlertTriangle,
  Copy,
  Check
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// Clean Architecture Integration
import { useUiStore } from '../../app/stores/uiStore';

interface ChatActionsProps {
  onShare: () => void;
  onDelete: () => void;
  onStop: () => void;
  onRegenerate: () => void;
  isStreaming: boolean;
  canShare: boolean;
  canDelete: boolean;
}

export const ChatActions: React.FC<ChatActionsProps> = ({
  onShare,
  onDelete,
  onStop,
  onRegenerate,
  isStreaming,
  canShare,
  canDelete,
}) => {
  // Clean Architecture Integration
  const { theme } = useUiStore();
  
  // Local state for dialogs and interactions
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleShare = async () => {
    try {
      await onShare();
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      console.error('Share failed:', error);
    }
  };

  const handleDelete = () => {
    onDelete();
    setDeleteDialogOpen(false);
  };

  const actions = [
    // Stop streaming action
    ...(isStreaming ? [{
      key: 'stop',
      label: 'Stop',
      icon: Square,
      onClick: onStop,
      variant: 'destructive' as const,
      tooltip: 'Stop generation'
    }] : []),
    
    // Regenerate action (when not streaming)
    ...(!isStreaming ? [{
      key: 'regenerate',
      label: 'Regenerate',
      icon: RotateCcw,
      onClick: onRegenerate,
      variant: 'secondary' as const,
      tooltip: 'Regenerate response'
    }] : []),
    
    // Share action
    ...(canShare ? [{
      key: 'share',
      label: 'Share',
      icon: Share2,
      onClick: () => setShareDialogOpen(true),
      variant: 'secondary' as const,
      tooltip: 'Share conversation'
    }] : []),
    
    // Delete action
    ...(canDelete ? [{
      key: 'delete',
      label: 'Delete',
      icon: Trash2,
      onClick: () => setDeleteDialogOpen(true),
      variant: 'destructive' as const,
      tooltip: 'Delete conversation'
    }] : [])
  ];

  const getButtonStyles = (variant: 'primary' | 'secondary' | 'destructive') => {
    const baseStyles = "flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200 focus:outline-none focus:ring-2";
    
    switch (variant) {
      case 'primary':
        return `${baseStyles} bg-blue-600 hover:bg-blue-700 text-white focus:ring-blue-500`;
      case 'secondary':
        return `${baseStyles} bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 focus:ring-gray-500`;
      case 'destructive':
        return `${baseStyles} bg-red-100 hover:bg-red-200 dark:bg-red-900 dark:hover:bg-red-800 text-red-700 dark:text-red-300 focus:ring-red-500`;
      default:
        return baseStyles;
    }
  };

  if (actions.length === 0) {
    return null;
  }

  return (
    <TooltipProvider>
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: 10 }}
        className="flex items-center gap-2 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-200 dark:border-gray-700"
      >
        <AnimatePresence>
          {actions.map((action, index) => {
            const Icon = action.icon;
            return (
              <motion.div
                key={action.key}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ delay: index * 0.05 }}
              >
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      onClick={action.onClick}
                      className={getButtonStyles(action.variant)}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{action.label}</span>
                    </button>
                  </TooltipTrigger>
                  <TooltipContent>
                    <p>{action.tooltip}</p>
                  </TooltipContent>
                </Tooltip>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </motion.div>

      {/* Delete Confirmation Dialog */}
      <Dialog.Root open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black bg-opacity-50" />
          <Dialog.Content className="fixed top-[50%] left-[50%] max-h-[85vh] w-[90vw] max-w-md translate-x-[-50%] translate-y-[-50%] rounded-lg bg-white dark:bg-gray-800 p-6 shadow-lg">
            <Dialog.Title className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
              <AlertTriangle className="w-5 h-5 text-red-500" />
              Delete Conversation
            </Dialog.Title>
            <Dialog.Description className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              Are you sure you want to delete this conversation? This action cannot be undone.
            </Dialog.Description>
            <div className="flex gap-2 mt-6">
              <Dialog.Close asChild>
                <button className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition-colors">
                  Cancel
                </button>
              </Dialog.Close>
              <button
                onClick={handleDelete}
                className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors"
              >
                Delete
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      {/* Share Confirmation Dialog */}
      <Dialog.Root open={shareDialogOpen} onOpenChange={setShareDialogOpen}>
        <Dialog.Portal>
          <Dialog.Overlay className="fixed inset-0 bg-black bg-opacity-50" />
          <Dialog.Content className="fixed top-[50%] left-[50%] max-h-[85vh] w-[90vw] max-w-md translate-x-[-50%] translate-y-[-50%] rounded-lg bg-white dark:bg-gray-800 p-6 shadow-lg">
            <Dialog.Title className="flex items-center gap-2 text-lg font-semibold text-gray-900 dark:text-white">
              <Share2 className="w-5 h-5 text-blue-500" />
              Share Conversation
            </Dialog.Title>
            <Dialog.Description className="mt-2 text-sm text-gray-600 dark:text-gray-400">
              This will create a shareable link for this conversation.
            </Dialog.Description>
            <div className="flex gap-2 mt-6">
              <Dialog.Close asChild>
                <button className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg transition-colors">
                  Cancel
                </button>
              </Dialog.Close>
              <button
                onClick={handleShare}
                className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
              >
                {copied ? (
                  <>
                    <Check className="w-4 h-4" />
                    Copied!
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    Copy Link
                  </>
                )}
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </TooltipProvider>
  );
}; 