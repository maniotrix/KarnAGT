import React from 'react';
import { Loader2 } from 'lucide-react';

export const AppLoading: React.FC = () => (
  <div className="min-h-screen bg-gray-50 flex items-center justify-center">
    <div className="text-center">
      <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4 text-blue-600" />
      <p className="text-gray-600">Loading...</p>
    </div>
  </div>
); 