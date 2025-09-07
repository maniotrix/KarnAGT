import React from 'react';
import { usePageTracking } from '../../hooks/usePageTracking';

/**
 * Component to handle Google Analytics page tracking
 * Must be placed inside Router context
 */
export const PageTracker: React.FC = () => {
  usePageTracking();
  return null; // This component renders nothing
};
