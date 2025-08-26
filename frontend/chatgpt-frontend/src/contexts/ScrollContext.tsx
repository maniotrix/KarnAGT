import React, { createContext, useContext } from 'react';
import { useScrollToBottom as useLibraryScrollToBottom, useSticky } from 'react-scroll-to-bottom';

interface ScrollContextType {
  scrollToBottom: (options?: { behavior?: 'auto' | 'smooth' }) => void;
  isAtBottom: boolean;
}

const ScrollContext = createContext<ScrollContextType | null>(null);

/**
 * Provider that must be used INSIDE ScrollToBottom component
 * This gives us access to the library's scroll hooks
 */
export const ScrollProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  // Get the library's scroll function and sticky state
  const scrollToBottom = useLibraryScrollToBottom();
  const [isAtBottom] = useSticky();
  
  const value: ScrollContextType = {
    scrollToBottom,
    isAtBottom
  };
  
  return (
    <ScrollContext.Provider value={value}>
      {children}
    </ScrollContext.Provider>
  );
};

/**
 * Custom hook to access scroll functionality
 * Can be used by any component inside ScrollProvider
 */
export const useScrollToBottom = () => {
  const context = useContext(ScrollContext);
  
  if (!context) {
    throw new Error('useScrollToBottom must be used within ScrollProvider');
  }
  
  return context;
};
