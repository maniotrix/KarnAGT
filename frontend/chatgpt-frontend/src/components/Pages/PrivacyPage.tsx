import React from 'react';
import { ArrowLeft, Shield, Eye, Lock, Database, UserCheck, Globe } from 'lucide-react';
import Logo from '../ui/Logo';

/**
 * Privacy Policy Page - Data protection and privacy practices
 * 
 * Features:
 * - Comprehensive privacy policy
 * - Data collection transparency
 * - User rights information
 * - Responsive design with mobile scrolling
 * - Legal compliance (GDPR, CCPA)
 */
export const PrivacyPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col overflow-y-auto" style={{ height: 'auto', minHeight: '100vh' }}>
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Logo size="sm" className="mr-2" />
              <a href="/" className="text-lg sm:text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">KarnAGT</a>
            </div>
            <a
              href="/"
              className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-sm font-medium transition-colors"
            >
              Go to Home
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-2 sm:px-0">
        {/* Hero Section */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 sm:pt-16 pb-8">
          <div className="flex justify-start mb-4">
            <button
              onClick={() => window.history.back()}
              className="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 text-sm font-medium underline hover:no-underline transition-all"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </button>
          </div>
          <div className="text-center mb-8">
            <Shield className="h-16 w-16 text-blue-500 dark:text-blue-400 mx-auto mb-4" />
            <h1 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Privacy Policy
            </h1>
            <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Your privacy is fundamental to how we build and operate KarnAGT. This policy explains how we collect, use, and protect your information.
            </p>
            <div className="mt-4 text-sm text-gray-500 dark:text-gray-400">
              Last updated: January 2025
            </div>
          </div>
        </div>

        {/* Quick Navigation */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex flex-wrap gap-4 text-sm">
              <a href="#data-collection" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">Data Collection</a>
              <a href="#how-we-use" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">How We Use Data</a>
              <a href="#data-sharing" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">Data Sharing</a>
              <a href="#your-rights" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">Your Rights</a>
              <a href="#security" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">Security</a>
              <a href="#contact" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">Contact Us</a>
            </div>
          </div>
        </div>

        {/* Privacy Policy Content */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8 sm:p-12 space-y-12">
            
            {/* Introduction */}
            <div className="prose prose-gray max-w-none">
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-6 mb-8">
                <div className="flex items-start">
                  <Eye className="h-6 w-6 text-blue-600 dark:text-blue-400 mt-1 mr-3 flex-shrink-0" />
                  <div>
                    <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">Privacy-First Approach</h3>
                    <p className="text-blue-800 dark:text-blue-200 text-sm">
                      At KarnAGT, privacy isn't an afterthought—it's fundamental to our design. We collect only what we need, 
                      protect everything we store, and give you complete control over your data.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Data Collection */}
            <section id="data-collection">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <Database className="h-6 w-6 text-green-500 mr-2" />
                1. What Information We Collect
              </h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <div className="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Information You Provide</h3>
                  <ul className="list-disc pl-5 space-y-2">
                    <li><strong>Account Information:</strong> Email address, username, full name (optional), password (encrypted)</li>
                    <li><strong>Profile Data:</strong> Avatar image, bio, preferences</li>
                    <li><strong>Communications:</strong> Messages you send to our AI system, uploaded files and documents</li>
                    <li><strong>Support Requests:</strong> Information you provide when contacting customer support</li>
                  </ul>
                </div>
                
                <div className="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Information We Collect Automatically</h3>
                  <ul className="list-disc pl-5 space-y-2">
                    <li><strong>Usage Data:</strong> How you interact with KarnAGT, features used, session duration</li>
                    <li><strong>Device Information:</strong> Browser type, operating system, screen resolution</li>
                    <li><strong>Log Data:</strong> IP addresses, timestamps, error logs (for debugging and security)</li>
                    <li><strong>Cookies:</strong> Authentication tokens, preferences, analytics data</li>
                  </ul>
                </div>

                <div className="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Information We Don't Collect</h3>
                  <ul className="list-disc pl-5 space-y-2 text-green-700 dark:text-green-400">
                    <li>We don't track your location unless explicitly needed for a feature</li>
                    <li>We don't access your device's contacts, photos, or other apps</li>
                    <li>We don't collect sensitive personal information like health data or financial information</li>
                    <li>We don't use invasive tracking or fingerprinting techniques</li>
                  </ul>
                </div>
              </div>
            </section>

            {/* How We Use Data */}
            <section id="how-we-use">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <UserCheck className="h-6 w-6 text-purple-500 mr-2" />
                2. How We Use Your Information
              </h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p className="text-lg">We use your information solely to provide and improve KarnAGT services:</p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg">
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Core Service Operations</h3>
                    <ul className="list-disc pl-5 space-y-1">
                      <li>Process your AI conversations and requests</li>
                      <li>Store and retrieve your chat history</li>
                      <li>Authenticate and secure your account</li>
                      <li>Provide personalized responses and recommendations</li>
                    </ul>
                  </div>
                  
                  <div className="bg-gray-50 dark:bg-gray-700 p-6 rounded-lg">
                    <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Service Improvement</h3>
                    <ul className="list-disc pl-5 space-y-1">
                      <li>Analyze usage patterns to enhance features</li>
                      <li>Debug issues and improve performance</li>
                      <li>Develop new AI capabilities</li>
                      <li>Ensure system security and prevent abuse</li>
                    </ul>
                  </div>
                </div>

                <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-700 p-4 rounded-lg">
                  <p className="text-yellow-800 dark:text-yellow-200 text-sm">
                    <strong>AI Training:</strong> We may use anonymized conversation data to improve our AI models, 
                    but personal identifiers are always removed and we never share your specific conversations.
                  </p>
                </div>
              </div>
            </section>

            {/* Data Sharing */}
            <section id="data-sharing">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <Globe className="h-6 w-6 text-orange-500 mr-2" />
                3. When We Share Information
              </h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-700 p-6 rounded-lg">
                  <h3 className="font-semibold text-red-900 dark:text-red-100 mb-3">We Never Sell Your Data</h3>
                  <p className="text-red-800 dark:text-red-200">
                    We do not sell, rent, or trade your personal information to third parties for marketing or any other commercial purposes. Period.
                  </p>
                </div>

                <p className="text-lg font-medium">We only share information in these limited circumstances:</p>
                
                <div className="space-y-4">
                  <div className="border-l-4 border-blue-500 pl-4">
                    <h4 className="font-semibold">Service Providers</h4>
                    <p>Trusted partners who help us operate KarnAGT (cloud hosting, email delivery, analytics) under strict data protection agreements.</p>
                  </div>
                  
                  <div className="border-l-4 border-blue-500 pl-4">
                    <h4 className="font-semibold">Legal Requirements</h4>
                    <p>If required by law, court order, or to protect our legal rights, but we'll notify you unless prohibited by law.</p>
                  </div>
                  
                  <div className="border-l-4 border-blue-500 pl-4">
                    <h4 className="font-semibold">Safety & Security</h4>
                    <p>To prevent fraud, abuse, or harm to KarnAGT users or the public, but only the minimum necessary information.</p>
                  </div>

                  <div className="border-l-4 border-blue-500 pl-4">
                    <h4 className="font-semibold">Business Transfers</h4>
                    <p>If KarnAGT is acquired, your data may be transferred, but you'll be notified and the same privacy protections will apply.</p>
                  </div>
                </div>
              </div>
            </section>

            {/* Your Rights */}
            <section id="your-rights">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <UserCheck className="h-6 w-6 text-indigo-500 mr-2" />
                4. Your Privacy Rights
              </h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p className="text-lg">You have complete control over your data:</p>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="bg-green-50 dark:bg-green-900/20 p-6 rounded-lg">
                    <h3 className="font-semibold text-green-900 dark:text-green-100 mb-3">Access & Portability</h3>
                    <ul className="list-disc pl-5 space-y-1 text-green-800 dark:text-green-200">
                      <li>Download all your data in a readable format</li>
                      <li>See exactly what information we have about you</li>
                      <li>Get copies of your conversations and files</li>
                    </ul>
                  </div>
                  
                  <div className="bg-blue-50 dark:bg-blue-900/20 p-6 rounded-lg">
                    <h3 className="font-semibold text-blue-900 dark:text-blue-100 mb-3">Control & Correction</h3>
                    <ul className="list-disc pl-5 space-y-1 text-blue-800 dark:text-blue-200">
                      <li>Update or correct your profile information</li>
                      <li>Delete specific conversations or files</li>
                      <li>Opt out of data processing for service improvement</li>
                    </ul>
                  </div>
                  
                  <div className="bg-purple-50 dark:bg-purple-900/20 p-6 rounded-lg">
                    <h3 className="font-semibold text-purple-900 dark:text-purple-100 mb-3">Deletion & Restriction</h3>
                    <ul className="list-disc pl-5 space-y-1 text-purple-800 dark:text-purple-200">
                      <li>Delete your account and all associated data</li>
                      <li>Request temporary restriction of processing</li>
                      <li>Withdraw consent for optional data uses</li>
                    </ul>
                  </div>
                  
                  <div className="bg-orange-50 dark:bg-orange-900/20 p-6 rounded-lg">
                    <h3 className="font-semibold text-orange-900 dark:text-orange-100 mb-3">Objection & Complaint</h3>
                    <ul className="list-disc pl-5 space-y-1 text-orange-800 dark:text-orange-200">
                      <li>Object to specific data processing activities</li>
                      <li>File complaints with data protection authorities</li>
                      <li>Contact us directly with privacy concerns</li>
                    </ul>
                  </div>
                </div>

                <div className="bg-gray-100 dark:bg-gray-700 p-4 rounded-lg">
                  <p className="text-sm text-gray-700 dark:text-gray-300">
                    <strong>How to Exercise Your Rights:</strong> Contact us at privacy@karnagt.com or use the privacy settings in your account dashboard. 
                    We'll respond within 30 days and help you exercise any of these rights free of charge.
                  </p>
                </div>
              </div>
            </section>

            {/* Security */}
            <section id="security">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <Lock className="h-6 w-6 text-red-500 mr-2" />
                5. How We Protect Your Information
              </h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p className="text-lg">Security is built into every aspect of KarnAGT:</p>
                
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="text-center">
                    <div className="bg-red-50 dark:bg-red-900/30 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Lock className="h-8 w-8 text-red-600 dark:text-red-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Encryption</h3>
                    <p className="text-gray-600 dark:text-gray-400">
                      All data is encrypted in transit (TLS 1.3) and at rest (AES-256). Your conversations are encrypted before they leave your device.
                    </p>
                  </div>
                  
                  <div className="text-center">
                    <div className="bg-blue-50 dark:bg-blue-900/30 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Shield className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Access Controls</h3>
                    <p className="text-gray-600 dark:text-gray-400">
                      Strict access controls, multi-factor authentication, and regular security audits protect against unauthorized access.
                    </p>
                  </div>
                  
                  <div className="text-center">
                    <div className="bg-green-50 dark:bg-green-900/30 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                      <Database className="h-8 w-8 text-green-600 dark:text-green-400" />
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">Infrastructure</h3>
                    <p className="text-gray-600 dark:text-gray-400">
                      SOC 2 compliant cloud infrastructure with automatic backups, monitoring, and incident response procedures.
                    </p>
                  </div>
                </div>

                <div className="bg-gray-100 dark:bg-gray-700 p-6 rounded-lg">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">Data Retention</h3>
                  <p className="text-gray-700 dark:text-gray-300">
                    We keep your data only as long as needed to provide services or comply with legal requirements. 
                    Chat history is retained for 2 years unless you delete it sooner. Account information is deleted within 30 days of account closure.
                  </p>
                </div>
              </div>
            </section>

            {/* Updates */}
            <section>
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">6. Policy Updates</h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p>
                  We may update this privacy policy to reflect changes in our practices or legal requirements. 
                  When we make significant changes, we'll notify you via email or prominently display a notice in KarnAGT.
                </p>
                <p>
                  Continued use of KarnAGT after policy updates constitutes acceptance of the new terms. 
                  You can always find the latest version at this URL.
                </p>
              </div>
            </section>

            {/* Contact */}
            <section id="contact">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">7. Contact Information</h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p>
                  Questions about this privacy policy or how we handle your data? We're here to help:
                </p>
                <div className="bg-blue-50 dark:bg-blue-900/20 p-6 rounded-lg">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <h4 className="font-semibold text-blue-900 dark:text-blue-100">Privacy Officer</h4>
                      <p className="text-blue-800 dark:text-blue-200">privacy@karnagt.com</p>
                    </div>
                    <div>
                      <h4 className="font-semibold text-blue-900 dark:text-blue-100">General Support</h4>
                      <p className="text-blue-800 dark:text-blue-200">help@karnagt.com</p>
                    </div>
                  </div>
                  <p className="text-blue-700 dark:text-blue-300 text-sm mt-4">
                    We typically respond to privacy requests within 30 days and support requests within 24 hours.
                  </p>
                </div>
              </div>
            </section>
          </div>

          {/* Summary Box */}
          <div className="mt-8 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-700 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-green-900 dark:text-green-100 mb-3">Privacy Summary</h3>
            <ul className="space-y-2 text-green-800 dark:text-green-200 text-sm">
              <li>✓ We collect only what's necessary to provide KarnAGT services</li>
              <li>✓ We never sell your personal data to third parties</li>
              <li>✓ You have complete control over your data and can delete it anytime</li>
              <li>✓ All data is encrypted and stored securely</li>
              <li>✓ We're transparent about our practices and responsive to your concerns</li>
            </ul>
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gray-100 dark:bg-gray-800 py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-4">
              Ready to experience privacy-first AI?
            </h2>
            <p className="text-lg text-gray-600 dark:text-gray-400 mb-8 max-w-2xl mx-auto">
              Join KarnAGT and experience the power of AI with the privacy and control you deserve.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/register"
                className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-lg text-white bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200"
              >
                Create Account
              </a>
              <a
                href="/help"
                className="inline-flex items-center px-8 py-4 border border-gray-300 dark:border-gray-600 text-lg font-medium rounded-lg text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Learn More
              </a>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col sm:flex-row justify-between items-center">
            <div className="text-center sm:text-left mb-4 sm:mb-0">
              <p className="text-gray-600 dark:text-gray-400">&copy; 2025 KarnAGT. All rights reserved.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-4 sm:gap-8">
              <a href="/home" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all">Home</a>
              <a href="/about" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all">About</a>
              <a href="/help" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all">Help</a>
              <a href="/terms" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all">Terms</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
