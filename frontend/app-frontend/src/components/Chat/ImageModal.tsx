import React, { useEffect, useState, useRef } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import * as VisuallyHidden from '@radix-ui/react-visually-hidden';
import { X, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, RotateCcw } from 'lucide-react';

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

  // Clean zoom state - no external library needed
  const [zoom, setZoom] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0, startX: 0, startY: 0 });
  const imageRef = useRef<HTMLImageElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Reset zoom when image changes
  useEffect(() => {
    setZoom(1);
    setPosition({ x: 0, y: 0 });
  }, [currentIndex]);

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

  // Zoom handlers
  const handleZoomIn = () => setZoom(prev => Math.min(prev * 1.5, 5));
  const handleZoomOut = () => setZoom(prev => Math.max(prev / 1.5, 0.5));
  const handleResetZoom = () => {
    setZoom(1);
    setPosition({ x: 0, y: 0 });
  };

  // Mouse wheel zoom
  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(prev => Math.min(Math.max(prev * delta, 0.5), 5));
  };

  // Pan functionality
  const handleMouseDown = (e: React.MouseEvent) => {
    if (zoom > 1) {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(true);
      setDragStart({
        x: e.clientX,
        y: e.clientY,
        startX: position.x,
        startY: position.y
      });
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (isDragging && zoom > 1) {
      e.preventDefault();
      e.stopPropagation();
      const deltaX = e.clientX - dragStart.x;
      const deltaY = e.clientY - dragStart.y;
      setPosition({
        x: dragStart.startX + deltaX,
        y: dragStart.startY + deltaY
      });
    }
  };

  const handleMouseUp = (e: React.MouseEvent) => {
    if (isDragging) {
      e.preventDefault();
      e.stopPropagation();
    }
    setIsDragging(false);
  };

  // Touch handling for mobile
  const [touchStart, setTouchStart] = useState<{ x: number; y: number; distance: number } | null>(null);

  const getTouchDistance = (touches: React.TouchList) => {
    if (touches.length < 2) return 0;
    const dx = touches[0].clientX - touches[1].clientX;
    const dy = touches[0].clientY - touches[1].clientY;
    return Math.sqrt(dx * dx + dy * dy);
  };

  const handleTouchStart = (e: React.TouchEvent) => {
    // Always prevent default to stop native zoom/scroll
    e.preventDefault();
    e.stopPropagation();
    
    if (e.touches.length === 2) {
      // Pinch zoom
      const distance = getTouchDistance(e.touches);
      setTouchStart({ x: 0, y: 0, distance });
    } else if (e.touches.length === 1 && zoom > 1) {
      // Single touch pan
      const touch = e.touches[0];
      setIsDragging(true);
      setDragStart({
        x: touch.clientX,
        y: touch.clientY,
        startX: position.x,
        startY: position.y
      });
    }
  };

  const handleTouchMove = (e: React.TouchEvent) => {
    // Always prevent default to stop native zoom/scroll
    e.preventDefault();
    e.stopPropagation();
    
    if (e.touches.length === 2 && touchStart) {
      // Pinch zoom
      const distance = getTouchDistance(e.touches);
      const scale = distance / touchStart.distance;
      setZoom(prev => Math.min(Math.max(prev * scale, 0.5), 5));
      setTouchStart(prev => prev ? { ...prev, distance } : null);
    } else if (e.touches.length === 1 && isDragging && zoom > 1) {
      // Single touch pan
      const touch = e.touches[0];
      const deltaX = touch.clientX - dragStart.x;
      const deltaY = touch.clientY - dragStart.y;
      setPosition({
        x: dragStart.startX + deltaX,
        y: dragStart.startY + deltaY
      });
    }
  };

  const handleTouchEnd = (e: React.TouchEvent) => {
    // Always prevent default to stop native zoom/scroll
    e.preventDefault();
    e.stopPropagation();
    
    setIsDragging(false);
    setTouchStart(null);
  };

  // Keyboard navigation with proper event isolation
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      // Only handle keys if no input is focused to prevent interference
      const activeElement = document.activeElement;
      const isInputFocused = activeElement?.tagName === 'INPUT' || 
                           activeElement?.tagName === 'TEXTAREA' || 
                           activeElement?.tagName === 'SELECT' || 
                           (activeElement as HTMLElement)?.contentEditable === 'true';

      if (isInputFocused) return;

      switch (e.key) {
        case 'ArrowLeft':
          e.preventDefault();
          e.stopPropagation();
          goToPrevious();
          break;
        case 'ArrowRight':
          e.preventDefault();
          e.stopPropagation();
          goToNext();
          break;
        case 'Escape':
          e.preventDefault();
          e.stopPropagation();
          onClose();
          break;
        case '+':
        case '=':
          e.preventDefault();
          e.stopPropagation();
          handleZoomIn();
          break;
        case '-':
          e.preventDefault();
          e.stopPropagation();
          handleZoomOut();
          break;
        case '0':
          e.preventDefault();
          e.stopPropagation();
          handleResetZoom();
          break;
      }
    };

    // Use capture phase to handle events before they reach other elements
    document.addEventListener('keydown', handleKeyDown, { capture: true, passive: false });
    return () => document.removeEventListener('keydown', handleKeyDown, { capture: true });
  }, [isOpen, currentIndex, images.length, zoom]);

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
            <div className="absolute left-4 top-4 sm:left-6 sm:top-6 md:left-8 md:top-8 z-20 rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm px-3 py-2 shadow-lg border border-gray-200/50 dark:border-gray-700/50 text-gray-700 dark:text-gray-300 text-fluid-xs font-medium">
              {currentIndex + 1} of {images.length}
            </div>
          )}

          {/* Zoom Controls */}
          <div className="absolute right-4 bottom-20 sm:bottom-4 sm:right-6 md:right-8 z-20 flex flex-col gap-2">
            <button
              onClick={handleZoomIn}
              className="rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm p-2 shadow-lg border border-gray-200/50 dark:border-gray-700/50 transition-all hover:bg-white dark:hover:bg-gray-800 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 min-h-[44px] min-w-[44px] flex items-center justify-center touch-manipulation"
              aria-label="Zoom in"
            >
              <ZoomIn className="h-5 w-5 text-gray-700 dark:text-gray-300" />
            </button>
            
            <button
              onClick={handleZoomOut}
              className="rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm p-2 shadow-lg border border-gray-200/50 dark:border-gray-700/50 transition-all hover:bg-white dark:hover:bg-gray-800 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 min-h-[44px] min-w-[44px] flex items-center justify-center touch-manipulation"
              aria-label="Zoom out"
            >
              <ZoomOut className="h-5 w-5 text-gray-700 dark:text-gray-300" />
            </button>
            
            <button
              onClick={handleResetZoom}
              className="rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm p-2 shadow-lg border border-gray-200/50 dark:border-gray-700/50 transition-all hover:bg-white dark:hover:bg-gray-800 hover:shadow-xl focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900 min-h-[44px] min-w-[44px] flex items-center justify-center touch-manipulation"
              aria-label="Reset zoom"
            >
              <RotateCcw className="h-5 w-5 text-gray-700 dark:text-gray-300" />
            </button>
          </div>

          {/* Zoom Level Indicator */}
          {zoom !== 1 && (
            <div className="absolute bottom-20 left-4 sm:bottom-4 sm:left-6 md:left-8 z-20 rounded-lg bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm px-3 py-2 shadow-lg border border-gray-200/50 dark:border-gray-700/50 text-gray-700 dark:text-gray-300 text-fluid-xs font-medium">
              {Math.round(zoom * 100)}%
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
          <div 
            ref={containerRef}
            className="relative w-full h-full flex items-center justify-center p-4 sm:p-6 md:p-8 pb-20 sm:pb-8 overflow-hidden"
            onWheel={handleWheel}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onMouseLeave={() => setIsDragging(false)}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            style={{ 
              cursor: isDragging ? 'grabbing' : zoom > 1 ? 'grab' : 'default',
              touchAction: 'none', // Essential for preventing native mobile zoom
              userSelect: 'none',  // Prevent text selection
              WebkitUserSelect: 'none' // Safari support
            }}
          >
            {currentImage?.url && (
              <div 
                className="transition-transform duration-200 ease-out"
                style={{
                  transform: `translate(${position.x}px, ${position.y}px) scale(${zoom})`,
                  transformOrigin: 'center center'
                }}
              >
                <img 
                  ref={imageRef}
                  alt={currentImage.filename || `Image ${currentIndex + 1}`}
                  className="max-h-[calc(100vh-8rem)] max-w-[calc(100vw-4rem)] sm:max-h-[calc(100vh-6rem)] sm:max-w-[calc(100vw-6rem)] md:max-h-[calc(100vh-8rem)] md:max-w-[calc(100vw-8rem)] object-contain rounded-lg shadow-2xl select-none"
                  src={currentImage.url}
                  draggable={false}
                  onDragStart={(e) => e.preventDefault()}
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
              <span className="text-fluid-xs font-medium text-gray-700 dark:text-gray-300">Close</span>
            </button>
          </Dialog.Close>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
};
