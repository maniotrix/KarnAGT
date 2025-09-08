/**
 * Viewport Height Utilities for Mobile Compatibility
 * Handles dynamic viewport height changes on mobile devices
 */

/**
 * Sets up viewport height CSS custom properties for mobile compatibility
 * This is a fallback for browsers that don't support dvh units
 */
export const setupViewportHeight = (): void => {
  const setVh = () => {
    // Calculate actual viewport height
    const vh = window.innerHeight * 0.01;
    // Set CSS custom property
    document.documentElement.style.setProperty('--vh', `${vh}px`);
  };

  // Set on initial load
  setVh();

  // Update on resize and orientation change
  window.addEventListener('resize', setVh);
  window.addEventListener('orientationchange', () => {
    // Add small delay for orientation change to complete
    setTimeout(setVh, 100);
  });

  // For iOS Safari - handle viewport changes when address bar shows/hides
  window.addEventListener('scroll', () => {
    // Only update if there's a significant change in viewport height
    const currentVh = window.innerHeight * 0.01;
    const currentCssVh = parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--vh'));
    
    if (Math.abs(currentVh - currentCssVh) > 1) {
      setVh();
    }
  }, { passive: true });
};

/**
 * Prevents document-level scrolling and bounce effects on mobile
 */
export const preventMobileScrolling = (): void => {
  // Prevent pull-to-refresh and overscroll behavior
  document.addEventListener('touchmove', (e) => {
    // Allow scrolling within scrollable containers
    let target = e.target as Element;
    while (target && target !== document.body) {
      const style = window.getComputedStyle(target);
      if (style.overflowY === 'auto' || style.overflowY === 'scroll') {
        return; // Allow scrolling in this container
      }
      target = target.parentElement as Element;
    }
    
    // Prevent default if not in a scrollable container
    e.preventDefault();
  }, { passive: false });

  // Prevent zoom on input focus (iOS)
  document.addEventListener('touchstart', (e) => {
    if (e.touches.length > 1) {
      e.preventDefault();
    }
  }, { passive: false });
};

/**
 * Initialize all viewport utilities
 */
export const initViewportUtils = (): void => {
  setupViewportHeight();
  preventMobileScrolling();
};

