import { useEffect, useRef, useCallback } from 'react';
import { useLocation } from 'react-router-dom';

interface UseChatInputFocusOptions {
  isLoading: boolean;
  disabled: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement | null>;
  autoFocusOnMount?: boolean;
  autoFocusAfterResponse?: boolean;
}

export const useChatInputFocus = ({
  isLoading,
  disabled,
  inputRef,
  autoFocusOnMount = true,
  autoFocusAfterResponse = true,
}: UseChatInputFocusOptions) => {
  const location = useLocation();
  const userHasFocusedElsewhere = useRef(false);
  const wasLoading = useRef(isLoading);
  const lastLocation = useRef(location.pathname);
  const documentWasHidden = useRef(false);

  // Focus the input safely
  const focusInput = useCallback(() => {
    if (!disabled && inputRef.current && !userHasFocusedElsewhere.current) {
      // Small delay to ensure DOM is ready
      requestAnimationFrame(() => {
        inputRef.current?.focus();
      });
    }
  }, [disabled, inputRef]);

  // Track user focus intent - if they click elsewhere, respect that
  useEffect(() => {
    const handleFocusOut = (event: FocusEvent) => {
      const target = event.target as Element;
      const input = inputRef.current;
      
      // If focus moves away from our input to something else (not null)
      if (input && target && target !== input && !input.contains(target)) {
        userHasFocusedElsewhere.current = true;
      }
    };

    const handleClick = (event: MouseEvent) => {
      const target = event.target as Element;
      const input = inputRef.current;
      
      // If user clicks on our input, they want to focus it
      if (input && target && (target === input || input.contains(target))) {
        userHasFocusedElsewhere.current = false;
      }
      // If they click elsewhere, respect that
      else if (input && target && !input.contains(target)) {
        userHasFocusedElsewhere.current = true;
      }
    };

    // Reset user intent when they explicitly interact with our input
    const handleInputFocus = () => {
      userHasFocusedElsewhere.current = false;
    };

    document.addEventListener('focusout', handleFocusOut, true);
    document.addEventListener('click', handleClick, true);
    inputRef.current?.addEventListener('focus', handleInputFocus);

    return () => {
      document.removeEventListener('focusout', handleFocusOut, true);
      document.removeEventListener('click', handleClick, true);
      inputRef.current?.removeEventListener('focus', handleInputFocus);
    };
  }, [inputRef]);

  // Track document visibility for page reload/app focus scenarios
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        documentWasHidden.current = true;
      } else if (documentWasHidden.current) {
        // Page/app regained focus, reset user intent and focus input
        documentWasHidden.current = false;
        userHasFocusedElsewhere.current = false;
        if (autoFocusOnMount) {
          setTimeout(focusInput, 100); // Small delay for stability
        }
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  }, [focusInput, autoFocusOnMount]);

  // Focus on mount (new chat, page load, component mount)
  useEffect(() => {
    if (autoFocusOnMount) {
      userHasFocusedElsewhere.current = false;
      focusInput();
    }
  }, [autoFocusOnMount, focusInput]);

  // Focus after route navigation (new chat, conversation switch)
  useEffect(() => {
    const currentPath = location.pathname;
    const pathChanged = currentPath !== lastLocation.current;
    
    if (pathChanged) {
      lastLocation.current = currentPath;
      userHasFocusedElsewhere.current = false;
      
      if (autoFocusOnMount) {
        // Small delay to ensure new route is fully rendered
        setTimeout(focusInput, 150);
      }
    }
  }, [location.pathname, focusInput, autoFocusOnMount]);

  // Focus after AI response completion
  useEffect(() => {
    const loadingJustFinished = wasLoading.current && !isLoading;
    wasLoading.current = isLoading;

    if (loadingJustFinished && autoFocusAfterResponse && !disabled) {
      // AI response just completed, focus the input for next message
      setTimeout(focusInput, 100);
    }
  }, [isLoading, autoFocusAfterResponse, disabled, focusInput]);

  // Return utility functions for manual control
  return {
    focusInput,
    resetUserIntent: () => {
      userHasFocusedElsewhere.current = false;
    },
    hasUserFocusedElsewhere: () => userHasFocusedElsewhere.current,
  };
}; 