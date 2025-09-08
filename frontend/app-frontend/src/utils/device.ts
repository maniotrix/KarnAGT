// Utilities for detecting device capabilities and type
// Touch-first approach with safe fallbacks and SSR guards

import { useEffect, useState } from 'react';

export function isTouchDevice(): boolean {
  if (typeof window === 'undefined' || typeof navigator === 'undefined') return false;
  const hasOntouch = 'ontouchstart' in window;
  const touchPoints = (navigator as any).maxTouchPoints ?? 0;
  const msTouchPoints = (navigator as any).msMaxTouchPoints ?? 0;
  return hasOntouch || touchPoints > 0 || msTouchPoints > 0;
}

export function isSmallViewport(breakpointPx: number = 768): boolean {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= breakpointPx;
}

export function isLikelyMobile(breakpointPx: number = 768): boolean {
  if (typeof window === 'undefined') return false;

  // Preferred: feature detection via media queries
  const supportsMatchMedia = typeof window.matchMedia === 'function';
  const hasCoarsePointer = supportsMatchMedia ? window.matchMedia('(pointer: coarse)').matches : false;
  const noHover = supportsMatchMedia ? window.matchMedia('(hover: none)').matches : false;

  const touch = isTouchDevice();
  const small = isSmallViewport(breakpointPx);

  // Mobile devices are typically touch + coarse pointer/no hover.
  // Include small viewport as a conservative fallback alongside touch.
  return (touch && (hasCoarsePointer || noHover)) || (touch && small);
}

export function getDeviceType(breakpointPx: number = 768): 'mobile' | 'desktop' {
  return isLikelyMobile(breakpointPx) ? 'mobile' : 'desktop';
}

// Optional: UA-based check (not recommended; exported for edge cases/tests)
export function isMobileUserAgent(): boolean {
  if (typeof navigator === 'undefined') return false;
  return /mobi|android|iphone|ipad|ipod|iemobile|opera mini/i.test(navigator.userAgent);
}

// React hook: keeps UI responsive to changes (resize, input mode changes)
export function useIsMobile(breakpointPx: number = 768): boolean {
  const [isMobile, setIsMobile] = useState<boolean>(false);

  useEffect(() => {
    if (typeof window === 'undefined') return;

    const supportsMatchMedia = typeof window.matchMedia === 'function';
    const mqlCoarse = supportsMatchMedia ? window.matchMedia('(pointer: coarse)') : null;
    const mqlNoHover = supportsMatchMedia ? window.matchMedia('(hover: none)') : null;

    const update = () => {
      const touch = isTouchDevice();
      const small = isSmallViewport(breakpointPx);
      const coarse = mqlCoarse ? mqlCoarse.matches : false;
      const noHover = mqlNoHover ? mqlNoHover.matches : false;
      setIsMobile((touch && (coarse || noHover)) || (touch && small));
    };

    update();

    const unsubscribers: Array<() => void> = [];

    const subscribe = (mql: MediaQueryList | null, handler: () => void) => {
      if (!mql) return;
      // Safari compatibility: addEventListener vs addListener
      const listener = () => handler();
      if ((mql as any).addEventListener) {
        (mql as any).addEventListener('change', listener);
        unsubscribers.push(() => (mql as any).removeEventListener('change', listener));
      } else if ((mql as any).addListener) {
        (mql as any).addListener(listener);
        unsubscribers.push(() => (mql as any).removeListener(listener));
      }
    };

    subscribe(mqlCoarse, update);
    subscribe(mqlNoHover, update);

    const resizeHandler = () => update();
    window.addEventListener('resize', resizeHandler);
    window.addEventListener('orientationchange', resizeHandler);
    unsubscribers.push(() => window.removeEventListener('resize', resizeHandler));
    unsubscribers.push(() => window.removeEventListener('orientationchange', resizeHandler));

    return () => {
      unsubscribers.forEach((u) => u());
    };
  }, [breakpointPx]);

  return isMobile;
}


