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



  const troubleshootingTips = [
    <>🔍 <strong>Important:</strong> All menus and buttons mentioned are part of your <strong>BROWSER</strong>, <span className="text-red-500 dark:text-red-400">not our website</span></>,
    <>Install button not showing? Make sure you're using <strong>Chrome</strong>, <strong>Edge</strong>, or <strong>Safari</strong></>,
    <>On <strong>Android:</strong> Look for an automatic install prompt at the bottom of your screen first</>,
    <>On <strong>iOS:</strong> Only Safari supports app installation - <span className="text-red-500 dark:text-red-400">other browsers won't work</span></>,
    <>Can't find the browser menu? Look for <strong>⋮ (three dots)</strong> or <strong>⋯</strong> in your browser's toolbar/address bar</>,
    <>Try refreshing the page or visiting the site multiple times to trigger the install prompt</>,
    <>For unsupported browsers: bookmark the page for quick access instead</>
  ];

  return (
    <div>
      {/* Header */}
      {showTitle && (
        <div className="flex items-center mb-6">
          <Download className="h-6 w-6 text-blue-500 mr-3" />
          <h2 className="text-3xl font-bold text-gray-900 dark:text-gray-100">Install KarnAGT App</h2>
        </div>
      )}

      {/* Description */}
      <p className="text-gray-600 dark:text-gray-400 mb-4 text-lg">
        Install KarnAGT as a standalone app on your device for faster loading, offline access when needed, 
        and convenient access directly from your home screen or desktop - just like any other app.
      </p>

      {/* Important Notice */}
      <div className="p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg mb-6">
        <p className="text-blue-900 dark:text-blue-100 text-sm font-medium">
          💡 <strong>Quick tip:</strong> All installation options use your <strong>web browser's built-in features</strong> - 
          you <span className="text-red-600 dark:text-red-400">don't need to do anything on our website</span> or <span className="text-red-600 dark:text-red-400">download anything from an app store</span>.
        </p>
      </div>

      {/* Platform Selection Prompt */}
      <div className="text-center mb-8">
        <p className="text-gray-500 dark:text-gray-400 text-sm">
          Click on your platform below to expand the installation steps
        </p>
      </div>

      {/* Installation Sections */}
      <div className="space-y-4 mb-8">
        {/* Android Section */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('android')}
            className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset transition-colors"
          >
            <div className="flex items-center">
              <Smartphone className="h-6 w-6 text-green-500" />
              <span className="ml-3 text-lg font-medium text-gray-900 dark:text-gray-100">Android</span>
            </div>
            {openSection === 'android' ? <ChevronUp className="h-5 w-5 text-gray-500 dark:text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-500 dark:text-gray-400" />}
          </button>
          {openSection === 'android' && (
            <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700">
              <ol className="mt-4 space-y-3">
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">1</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Open KarnAGT in <strong>Chrome browser</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">2</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Tap <strong>Chrome's menu (⋮)</strong> in the browser's top-right corner <span className="line-through text-red-500 dark:text-red-400">(not on our website)</span></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">3</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Select <strong>"Add to Home screen"</strong> or <strong>"Install app"</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">4</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Tap <strong>"Install"</strong> or <strong>"Add"</strong> when prompted</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">5</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">✅ The app icon will appear on your <strong>home screen</strong></span>
                </li>
              </ol>
            </div>
          )}
        </div>

        {/* iOS Section */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('ios')}
            className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset transition-colors"
          >
            <div className="flex items-center">
              <Tablet className="h-6 w-6 text-blue-500" />
              <span className="ml-3 text-lg font-medium text-gray-900 dark:text-gray-100">iOS (iPhone/iPad)</span>
            </div>
            {openSection === 'ios' ? <ChevronUp className="h-5 w-5 text-gray-500 dark:text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-500 dark:text-gray-400" />}
          </button>
          {openSection === 'ios' && (
            <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700">
              <ol className="mt-4 space-y-3">
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">1</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Open KarnAGT in <strong>Safari</strong> <span className="text-red-500 dark:text-red-400">(other browsers won't work)</span></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">2</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Tap the <strong>Share button</strong> at the bottom of the screen</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">3</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Scroll down and tap <strong>"Add to Home Screen"</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">4</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Edit the name if desired, then tap <strong>"Add"</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">5</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">✅ The KarnAGT app icon will appear on your <strong>home screen</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">6</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Tap the icon to open KarnAGT as a <strong>native app</strong></span>
                </li>
              </ol>
            </div>
          )}
        </div>

        {/* Mac Section */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
            <button
            onClick={() => toggleSection('mac')}
              className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset transition-colors"
            >
              <div className="flex items-center">
              <Monitor className="h-6 w-6 text-gray-500" />
              <span className="ml-3 text-lg font-medium text-gray-900 dark:text-gray-100">Mac (Safari & Chrome)</span>
            </div>
            {openSection === 'mac' ? <ChevronUp className="h-5 w-5 text-gray-500 dark:text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-500 dark:text-gray-400" />}
          </button>
          {openSection === 'mac' && (
            <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700">
              <ol className="mt-4 space-y-3">
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">1</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed"><strong>Option 1 - Safari:</strong> Open KarnAGT in <strong>Safari</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">2</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Click the <strong>"Share"</strong> icon in the toolbar</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">3</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Select <strong>"Add to Dock"</strong> from the dropdown menu, <strong>OR</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">4</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed"><strong>Option 2 - Chrome:</strong> Open KarnAGT in <strong>Chrome</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">5</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Look for the <strong>install icon (⊕)</strong> in the address bar</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">6</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Click the install icon and select <strong>"Install"</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">7</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">✅ Find the app in <strong>Applications folder</strong> or <strong>Launchpad</strong></span>
                </li>
              </ol>
              </div>
          )}
        </div>

        {/* Windows/Linux Desktop Section */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('desktop')}
            className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset transition-colors"
          >
            <div className="flex items-center">
              <Monitor className="h-6 w-6 text-purple-500" />
              <span className="ml-3 text-lg font-medium text-gray-900 dark:text-gray-100">Windows/Linux Desktop</span>
            </div>
            {openSection === 'desktop' ? <ChevronUp className="h-5 w-5 text-gray-500 dark:text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-500 dark:text-gray-400" />}
            </button>
          {openSection === 'desktop' && (
            <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700">
              <ol className="mt-4 space-y-3">
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">1</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Open KarnAGT in <strong>Chrome</strong>, <strong>Edge</strong>, or another supported browser</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">2</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed"><strong>Method 1:</strong> Look for the <strong>install/download icon (⊕ or ⬇)</strong> in your browser's address bar</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">3</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Click that icon and select <strong>"Install"</strong> <strong>OR</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">4</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed"><strong>Method 2:</strong> Click your <strong>browser's menu (⋮)</strong> in the top-right corner</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">5</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Select <strong>"Install KarnAGT..."</strong> or <strong>"Apps &gt; Install this site as an app"</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">6</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Click <strong>"Install"</strong> in the confirmation dialog</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">7</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">✅ KarnAGT will open as a <strong>standalone app</strong> in its own window</span>
                </li>
              </ol>
            </div>
          )}
        </div>

        {/* Chromebook Section */}
        <div className="border border-gray-200 dark:border-gray-700 rounded-lg overflow-hidden">
          <button
            onClick={() => toggleSection('chromebook')}
            className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset transition-colors"
          >
            <div className="flex items-center">
              <Monitor className="h-6 w-6 text-indigo-500" />
              <span className="ml-3 text-lg font-medium text-gray-900 dark:text-gray-100">Chromebook/Chrome OS</span>
            </div>
            {openSection === 'chromebook' ? <ChevronUp className="h-5 w-5 text-gray-500 dark:text-gray-400" /> : <ChevronDown className="h-5 w-5 text-gray-500 dark:text-gray-400" />}
          </button>
          {openSection === 'chromebook' && (
              <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700">
                <ol className="mt-4 space-y-3">
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">1</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Open KarnAGT in <strong>Chrome</strong> (pre-installed on Chromebooks)</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">2</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Look for the <strong>install icon (⊕)</strong> in Chrome's address bar</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">3</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Click the install icon <strong>OR</strong> use <strong>Chrome's menu (⋮)</strong> in the browser toolbar</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">4</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Select <strong>"Install KarnAGT"</strong> and click <strong>"Install"</strong> in the popup</span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">5</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">✅ KarnAGT will appear as an <strong>app</strong> in your <strong>Chrome OS launcher</strong></span>
                </li>
                <li className="flex items-start">
                  <span className="flex-shrink-0 w-6 h-6 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full flex items-center justify-center text-sm font-medium mr-3 mt-0.5">6</span>
                  <span className="text-gray-700 dark:text-gray-300 leading-relaxed">Access it from the launcher or search for <strong>"KarnAGT"</strong></span>
                    </li>
                </ol>
              </div>
            )}
          </div>
      </div>

      {/* Benefits */}
      <div className="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg mb-6">
        <h3 className="font-medium text-blue-900 dark:text-blue-100 mb-2">Benefits of Installing:</h3>
        <ul className="text-sm text-blue-800 dark:text-blue-200 space-y-1">
          <li>• Faster loading and better performance</li>
          <li>• Works offline for basic functionality</li>
          <li>• Native app-like experience</li>
          <li>• Easy access from home screen or desktop</li>
          <li>• Push notifications (when available)</li>
        </ul>
      </div>

      {/* Troubleshooting */}
      <div className="p-4 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 rounded-lg">
        <div className="flex items-center mb-2">
          <AlertCircle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 mr-2" />
          <h3 className="font-medium text-yellow-900 dark:text-yellow-100">Troubleshooting:</h3>
        </div>
        <ul className="text-sm text-yellow-800 dark:text-yellow-200 space-y-1">
          {troubleshootingTips.map((tip, index) => (
            <li key={index} className="text-sm text-yellow-800 dark:text-yellow-200">• {tip}</li>
          ))}
        </ul>
      </div>
    </div>
  );
};
