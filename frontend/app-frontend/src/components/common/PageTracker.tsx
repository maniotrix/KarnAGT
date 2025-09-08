import React from 'react';
import { usePageTracking } from '../../hooks/usePageTracking';
import { usePageTitle } from '../../hooks/usePageTitle';

/**
 * Component to handle Google Analytics page tracking and dynamic page titles
 * Must be placed inside Router context
 */
export const PageTracker: React.FC = () => {
  // Update page title first, then track with GA (title updated before GA reads it)
  usePageTitle();
  usePageTracking();
  return null; // This component renders nothing
};
