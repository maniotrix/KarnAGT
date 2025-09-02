import React, { useState } from 'react';
import { Smartphone, Monitor, Tablet, ChevronDown, ChevronUp, Download, AlertCircle } from 'lucide-react';

interface PWAInstallContentProps {
  defaultOpenSection?: string | null;
  showTitle?: boolean;
}

export const PWAInstallContent: React.FC<PWAInstallContentProps> = ({ 
  defaultOpenSection = null,
  showTitle = true 
}) => {
  const [openSection, setOpenSection] = useState<string | null>(defaultOpenSection);

  const toggleSection = (section: string) => {
    setOpenSection(openSection === section ? null : section);
  };

  const installSections = [
    {
      id: 'android',
      title: 'Android',
      icon: <Smartphone className="h-6 w-6 text-green-500" />,
      steps: [
        'Open KarnAGT in Chrome browser',
        'Look for an "Install" prompt at the bottom of the screen, or',
        'Tap the menu button (three dots) in the top-right corner',
        'Select "Add to Home screen" or "Install app"',
        'Tap "Install" or "Add" when prompted',
        'The app icon will appear on your home screen'
      ]
    },
    {
      id: 'ios',
      title: 'iOS (iPhone/iPad)',
      icon: <Tablet className="h-6 w-6 text-blue-500" />,
      steps: [
        'Open KarnAGT in Safari (required for iOS PWA installation)',
        'Tap the Share button at the bottom of the screen',
        'Scroll down and tap "Add to Home Screen"',
        'Edit the name if desired, then tap "Add"',
        'The KarnAGT app icon will appear on your home screen',
        'Tap the icon to open KarnAGT as a native app'
      ]
    },
    {
      id: 'mac',
      title: 'Mac (Safari & Chrome)',
      icon: <Monitor className="h-6 w-6 text-gray-500" />,
      steps: [
        'Option 1 - Safari: Open KarnAGT in Safari',
        'Click the "Share" icon in the toolbar',
        'Select "Add to Dock" from the dropdown menu, or',
        'Option 2 - Chrome: Open KarnAGT in Chrome',
        'Look for the install icon (⊕) in the address bar',
        'Click the install icon and select "Install"',
        'Find the app in Applications folder or Launchpad'
      ]
    },
    {
      id: 'desktop',
      title: 'Windows/Linux Desktop',
      icon: <Monitor className="h-6 w-6 text-purple-500" />,
      steps: [
        'Open KarnAGT in Chrome, Edge, or another supported browser',
        'Look for the install icon (⊕) in the address bar, or',
        'Click the menu button (three dots) and select "Install KarnAGT"',
        'Click "Install" in the confirmation dialog',
        'KarnAGT will open in its own window',
        'Find the app in your Start menu or desktop'
      ]
    },
    {
      id: 'chromebook',
      title: 'Chromebook/Chrome OS',
      icon: <Monitor className="h-6 w-6 text-indigo-500" />,
      steps: [
        'Open KarnAGT in Chrome (pre-installed on Chromebooks)',
        'Look for the install icon (⊕) in the address bar',
        'Click the install icon or use the three-dot menu',
        'Select "Install KarnAGT" and click "Install"',
        'The app will appear in your app launcher',
        'Access it from the launcher or search for "KarnAGT"'
      ]
    }
  ];

  const troubleshootingTips = [
    "Install button not showing? Make sure you're using Chrome, Edge, or Safari",
    "On Android: Look for an automatic install prompt at the bottom of the screen first",
    "On iOS: Only Safari supports app installation - other browsers won't work",
    "Try refreshing the page or visiting the site multiple times to trigger the install prompt",
    "For unsupported browsers: bookmark the page for quick access"
  ];

  return (
    <div>
      {/* Header */}
      {showTitle && (
        <div className="flex items-center mb-6">
          <Download className="h-6 w-6 text-blue-500 mr-3" />
          <h2 className="text-3xl font-bold text-gray-900">Install KarnAGT App</h2>
        </div>
      )}

      {/* Description */}
      <p className="text-gray-600 mb-6 text-lg">
        Install KarnAGT as an app on your device for faster loading, offline access when needed, 
        and convenient access directly from your home screen or desktop - just like any other app.
      </p>

      {/* Platform Selection Prompt */}
      <div className="text-center mb-8">
        <p className="text-gray-500 text-sm">
          Click on your platform below to expand the installation steps
        </p>
      </div>

      {/* Installation Sections */}
      <div className="space-y-4 mb-8">
        {installSections.map((section) => (
          <div
            key={section.id}
            className="border border-gray-200 rounded-lg overflow-hidden"
          >
            {/* Section Header */}
            <button
              onClick={() => toggleSection(section.id)}
              className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset transition-colors"
            >
              <div className="flex items-center">
                {section.icon}
                <span className="ml-3 text-lg font-medium text-gray-900">
                  {section.title}
                </span>
              </div>
              {openSection === section.id ? (
                <ChevronUp className="h-5 w-5 text-gray-500" />
              ) : (
                <ChevronDown className="h-5 w-5 text-gray-500" />
              )}
            </button>

            {/* Section Content */}
            {openSection === section.id && (
              <div className="px-4 pb-4 border-t border-gray-100">
                <ol className="mt-4 space-y-3">
                  {section.steps.map((step, index) => (
                    <li key={index} className="flex items-start">
                      <span className="flex-shrink-0 w-6 h-6 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">
                        {index + 1}
                      </span>
                      <span className="text-gray-700 leading-relaxed">{step}</span>
                    </li>
                  ))}
                </ol>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Benefits */}
      <div className="p-4 bg-blue-50 rounded-lg mb-6">
        <h3 className="font-medium text-blue-900 mb-2">Benefits of Installing:</h3>
        <ul className="text-sm text-blue-800 space-y-1">
          <li>• Faster loading and better performance</li>
          <li>• Works offline for basic functionality</li>
          <li>• Native app-like experience</li>
          <li>• Easy access from home screen or desktop</li>
          <li>• Push notifications (when available)</li>
        </ul>
      </div>

      {/* Troubleshooting */}
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <div className="flex items-center mb-2">
          <AlertCircle className="h-5 w-5 text-yellow-600 mr-2" />
          <h3 className="font-medium text-yellow-900">Troubleshooting:</h3>
        </div>
        <ul className="text-sm text-yellow-800 space-y-1">
          {troubleshootingTips.map((tip, index) => (
            <li key={index}>• {tip}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};
