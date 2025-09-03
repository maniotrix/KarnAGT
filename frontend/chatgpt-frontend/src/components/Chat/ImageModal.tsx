import React, { useEffect } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import * as VisuallyHidden from '@radix-ui/react-visually-hidden';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';

interface ImageModalProps {
  images: Array<{ id: string; filename: string; url: string | null }>;
  currentIndex: number;
  onClose: () => void;
  onNavigate: (index: number) => void;
}

export const ImageModal: React.FC<ImageModalProps> = ({ 
  images,
  currentIndex, 
  onClose,
  onNavigate
}) => {
  const isOpen = images.length > 0 && currentIndex >= 0;
  const currentImage = isOpen ? images[currentIndex] : null;
  const hasMultipleImages = images.length > 1;

  // Navigation handlers
  const goToPrevious = () => {
    if (currentIndex > 0) {
      onNavigate(currentIndex - 1);
    }
  };

  const goToNext = () => {
    if (currentIndex < images.length - 1) {
      onNavigate(currentIndex + 1);
    }
  };

  // Keyboard navigation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          goToPrevious();
          break;
        case 'ArrowRight':
          e.preventDefault();
          goToNext();
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, currentIndex, images.length]);

  return (
    <Dialog.Root open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/90 dark:bg-black/80 z-50 data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed inset-0 z-50 flex items-center justify-center focus:outline-none data-[state=open]:animate-in data-[state=closed]:animate-out data-[state=closed]:fade-out-0 data-[state=open]:fade-in-0 data-[state=closed]:zoom-out-95 data-[state=open]:zoom-in-95">
          {/* Accessibility - Hidden Title and Description */}
          <VisuallyHidden.Root>
            <Dialog.Title>Image Gallery</Dialog.Title>
            <Dialog.Description>
              {hasMultipleImages 
                ? `Image gallery with ${images.length} images. Use arrow keys or navigation buttons to browse. Press Escape to close.`
                : 'Full-size view of the uploaded image. Press Escape or click the close button to exit.'
              }
            </Dialog.Description>
          </VisuallyHidden.Root>
          
          {/* Close Button */}
          <Dialog.Close asChild>
            <button 
              className="absolute right-4 top-4 sm:right-6 sm:top-6 md:right-8 md:top-8 z-20 rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm p-2 shadow-lg border border-gray-200/50 dark:border-gray-700/50 transition-all hover:bg-white dark:hover:bg-gray-800 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 min-h-[44px] min-w-[44px] flex items-center justify-center touch-manipulation"
              aria-label="Close image gallery"
            >
              <X className="h-5 w-5 sm:h-6 sm:w-6 text-gray-700 dark:text-gray-300" />
            </button>
          </Dialog.Close>

          {/* Image Counter */}
          {hasMultipleImages && (
            <div className="absolute left-4 top-4 sm:left-6 sm:top-6 md:left-8 md:top-8 z-20 rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm px-3 py-2 shadow-lg border border-gray-200/50 dark:border-gray-700/50 text-gray-700 dark:text-gray-300 text-sm font-medium">
              {currentIndex + 1} of {images.length}
            </div>
          )}

          {/* Previous Button */}
          {hasMultipleImages && currentIndex > 0 && (
            <button
              onClick={goToPrevious}
              className="absolute left-4 top-1/2 transform -translate-y-1/2 z-20 rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm p-3 shadow-lg border border-gray-200/50 dark:border-gray-700/50 transition-all hover:bg-white dark:hover:bg-gray-800 hover:shadow-xl hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 min-h-[52px] min-w-[52px] flex items-center justify-center touch-manipulation disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Previous image"
            >
              <ChevronLeft className="h-6 w-6 text-gray-700 dark:text-gray-300" />
            </button>
          )}

          {/* Next Button */}
          {hasMultipleImages && currentIndex < images.length - 1 && (
            <button
              onClick={goToNext}
              className="absolute right-4 top-1/2 transform -translate-y-1/2 z-20 rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm p-3 shadow-lg border border-gray-200/50 dark:border-gray-700/50 transition-all hover:bg-white dark:hover:bg-gray-800 hover:shadow-xl hover:scale-105 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 min-h-[52px] min-w-[52px] flex items-center justify-center touch-manipulation disabled:opacity-50 disabled:cursor-not-allowed"
              aria-label="Next image"
            >
              <ChevronRight className="h-6 w-6 text-gray-700 dark:text-gray-300" />
            </button>
          )}
          
          {/* Image Display Container */}
          <div className="relative w-full h-full flex items-center justify-center p-4 sm:p-6 md:p-8 pb-20 sm:pb-8">
            {currentImage?.url && (
              <div className="relative max-h-full max-w-full">
                <img 
                  alt={currentImage.filename || `Image ${currentIndex + 1}`}
                  className="max-h-[calc(100vh-8rem)] max-w-[calc(100vw-4rem)] sm:max-h-[calc(100vh-6rem)] sm:max-w-[calc(100vw-6rem)] md:max-h-[calc(100vh-8rem)] md:max-w-[calc(100vw-8rem)] object-contain rounded-lg shadow-2xl"
                  src={currentImage.url}
                />
              </div>
            )}
          </div>

          {/* Bottom Close Button - Mobile Friendly */}
          <Dialog.Close asChild>
            <button 
              className="absolute bottom-4 left-1/2 transform -translate-x-1/2 z-20 sm:hidden rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm px-6 py-3 shadow-lg border border-gray-200/50 dark:border-gray-700/50 transition-all hover:bg-white dark:hover:bg-gray-800 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 min-h-[52px] flex items-center justify-center gap-2 touch-manipulation"
              aria-label="Close image gallery"
            >
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">Close</span>
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
