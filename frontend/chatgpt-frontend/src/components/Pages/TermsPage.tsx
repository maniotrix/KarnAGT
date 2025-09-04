import React from 'react';

import { ArrowLeft, Shield, FileText, Users, AlertTriangle } from 'lucide-react';
import Logo from '../ui/Logo';

/**
 * Terms and Conditions Page - Legal terms and service agreement
 * 
 * Features:
 * - Comprehensive terms of service
 * - Privacy policy highlights
 * - User responsibilities
 * - Responsive design with mobile scrolling
 * - Last updated information
 */
export const TermsPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col overflow-y-auto" style={{ height: 'auto', minHeight: '100vh' }}>
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Logo size="sm" className="mr-2" />
              <a href="/" className="text-fluid-base font-bold text-gray-900 dark:text-gray-100 hover:text-blue-600 dark:hover:text-blue-400 transition-colors">KarnAGT</a>
            </div>
            <a
              href="/"
              className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 text-fluid-xs font-medium transition-colors"
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
              className="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 text-fluid-xs font-medium underline hover:no-underline transition-all"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </button>
          </div>
          <div className="text-center mb-8">
            <FileText className="h-16 w-16 text-blue-500 dark:text-blue-400 mx-auto mb-4" />
            <h1 className="text-fluid-h2 font-bold text-gray-900 dark:text-gray-100 mb-4">
              Terms & Conditions
            </h1>
            <p className="text-fluid-sm text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Please read these terms carefully before using KarnAGT. By using our service, you agree to these terms.
            </p>
            <div className="mt-4 text-fluid-xs text-gray-500 dark:text-gray-400">
              Last updated: September 2025
            </div>
          </div>
        </div>

        {/* Quick Navigation */}
        <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-10">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
            <div className="flex flex-wrap gap-4 text-fluid-xs">
              <a href="#service-agreement" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">Service Agreement</a>
              <a href="#user-responsibilities" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">User Responsibilities</a>
              <a href="#privacy-data" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">Privacy & Data</a>
              <a href="#intellectual-property" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">Intellectual Property</a>
              <a href="#limitations" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">Limitations</a>
              <a href="#termination" className="text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors">Termination</a>
            </div>
          </div>
        </div>

        {/* Terms Content */}
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-8 sm:p-12 space-y-12">
            
            {/* Introduction */}
            <div className="prose prose-gray max-w-none">
              <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-6 mb-8">
                <div className="flex items-start">
                  <Shield className="h-6 w-6 text-blue-600 dark:text-blue-400 mt-1 mr-3 flex-shrink-0" />
                  <div>
                    <h3 className="text-fluid-sm font-semibold text-blue-900 dark:text-blue-100 mb-2">Agreement Overview</h3>
                    <p className="text-blue-800 dark:text-blue-200 text-fluid-xs">
                      These Terms of Service ("Terms") govern your use of KarnAGT and its associated services. 
                      By creating an account or using our services, you agree to be bound by these terms.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Service Agreement */}
            <section id="service-agreement">
              <h2 className="text-fluid-lg font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <FileText className="h-6 w-6 text-blue-500 mr-2" />
                1. Service Agreement
              </h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p>
                  <strong>1.1 Service Description:</strong> KarnAGT is an advanced artificial intelligence platform 
                  that provides agentic AI capabilities including natural language processing, web search, document analysis, 
                  image understanding, and workflow automation.
                </p>
                <p>
                  <strong>1.2 Eligibility:</strong> You must be at least 13 years old to use KarnAGT. If you are under 
                  18, you must have parental consent to use our services.
                </p>
                <p>
                  <strong>1.3 Account Registration:</strong> You are responsible for maintaining the confidentiality 
                  of your account credentials and for all activities that occur under your account.
                </p>
                <p>
                  <strong>1.4 Service Availability:</strong> While we strive for 99.9% uptime, we do not guarantee 
                  uninterrupted service and reserve the right to modify or discontinue features with reasonable notice.
                </p>
              </div>
            </section>

            {/* User Responsibilities */}
            <section id="user-responsibilities">
              <h2 className="text-fluid-lg font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <Users className="h-6 w-6 text-green-500 mr-2" />
                2. User Responsibilities
              </h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p>
                  <strong>2.1 Acceptable Use:</strong> You agree to use KarnAGT only for lawful purposes and in 
                  accordance with these Terms. You will not use the service to:
                </p>
                <ul className="list-disc pl-6 space-y-2">
                  <li>Generate harmful, illegal, or misleading content</li>
                  <li>Attempt to circumvent usage limits or security measures</li>
                  <li>Reverse engineer or attempt to extract underlying AI models</li>
                  <li>Violate intellectual property rights of others</li>
                  <li>Harass, abuse, or harm other users or individuals</li>
                </ul>
                <p>
                  <strong>2.2 Content Responsibility:</strong> You are solely responsible for any content you input 
                  into KarnAGT and for ensuring you have the right to upload or share such content.
                </p>
                <p>
                  <strong>2.3 Compliance:</strong> You agree to comply with all applicable laws and regulations 
                  when using our service, including but not limited to data protection and privacy laws.
                </p>
              </div>
            </section>

            {/* Privacy and Data */}
            <section id="privacy-data">
              <h2 className="text-fluid-lg font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <Shield className="h-6 w-6 text-purple-500 mr-2" />
                3. Privacy and Data Protection
              </h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p>
                  <strong>3.1 Data Collection:</strong> We collect only the information necessary to provide and 
                  improve our services. This includes account information, usage data, and conversation content. 
                  For detailed information about our data practices, please see our <a href="/privacy-policy" className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline">Privacy Policy</a>.
                </p>
                <p>
                  <strong>3.2 Data Use:</strong> Your data is used to:
                </p>
                <ul className="list-disc pl-6 space-y-1">
                  <li>Provide and improve KarnAGT services</li>
                  <li>Maintain account security and prevent abuse</li>
                  <li>Analyze usage patterns to enhance user experience</li>
                  <li>Comply with legal obligations</li>
                </ul>
                <p>
                  <strong>3.3 Data Security:</strong> We implement industry-standard security measures including 
                  encryption in transit and at rest, access controls, and regular security audits.
                </p>
                <p>
                  <strong>3.4 Data Sharing:</strong> We do not sell your personal data to third parties. We may 
                  share data only in limited circumstances such as legal requirements or with your explicit consent.
                </p>
                <p>
                  <strong>3.5 Data Retention:</strong> We retain your data only as long as necessary to provide 
                  services or comply with legal obligations. You can request data deletion at any time. 
                  Detailed retention periods and deletion procedures are outlined in our <a href="/privacy-policy" className="text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 underline">Privacy Policy</a>.
                </p>
              </div>
            </section>

            {/* Intellectual Property */}
            <section id="intellectual-property">
              <h2 className="text-fluid-lg font-bold text-gray-900 dark:text-gray-100 mb-4">4. Intellectual Property</h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p>
                  <strong>4.1 Service IP:</strong> KarnAGT, including its AI models, algorithms, and interface, 
                  is protected by intellectual property laws and remains the property of KarnAGT and its licensors.
                </p>
                <p>
                  <strong>4.2 User Content:</strong> You retain ownership of content you input into KarnAGT. 
                  By using our service, you grant us a limited license to process your content to provide the service.
                </p>
                <p>
                  <strong>4.3 AI-Generated Content:</strong> Content generated by KarnAGT in response to your 
                  prompts is provided to you for your use, subject to these Terms and applicable law.
                </p>
              </div>
            </section>

            {/* Limitations and Disclaimers */}
            <section id="limitations">
              <h2 className="text-fluid-lg font-bold text-gray-900 dark:text-gray-100 mb-4 flex items-center">
                <AlertTriangle className="h-6 w-6 text-yellow-500 mr-2" />
                5. Limitations and Disclaimers
              </h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p>
                  <strong>5.1 AI Limitations:</strong> While KarnAGT is highly capable, AI-generated content may 
                  contain errors, biases, or inaccuracies. Users should verify important information independently.
                </p>
                <p>
                  <strong>5.2 Service Disclaimer:</strong> KarnAGT is provided "as is" without warranties of any kind. 
                  We do not guarantee that the service will meet your specific requirements or be error-free.
                </p>
                <p>
                  <strong>5.3 Liability Limitation:</strong> Our liability is limited to the maximum extent permitted 
                  by law. We are not liable for indirect, incidental, or consequential damages.
                </p>
                <p>
                  <strong>5.4 Usage Limits:</strong> We may impose reasonable usage limits to ensure fair access 
                  and system performance for all users.
                </p>
              </div>
            </section>

            {/* Termination */}
            <section id="termination">
              <h2 className="text-fluid-lg font-bold text-gray-900 dark:text-gray-100 mb-4">6. Account Termination</h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p>
                  <strong>6.1 User Termination:</strong> You may terminate your account at any time by contacting 
                  our support team or using the account deletion feature in your settings.
                </p>
                <p>
                  <strong>6.2 Service Termination:</strong> We may suspend or terminate accounts that violate 
                  these Terms, engage in abusive behavior, or for other legitimate business reasons.
                </p>
                <p>
                  <strong>6.3 Effect of Termination:</strong> Upon termination, your access to KarnAGT will cease, 
                  and we may delete your data in accordance with our retention policies.
                </p>
              </div>
            </section>

            {/* Updates and Changes */}
            <section>
              <h2 className="text-fluid-lg font-bold text-gray-900 dark:text-gray-100 mb-4">7. Changes to Terms</h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p>
                  We may update these Terms periodically to reflect changes in our services or legal requirements. 
                  We will notify users of significant changes via email or service notification. Continued use of 
                  KarnAGT after changes constitutes acceptance of the new Terms.
                </p>
              </div>
            </section>

            {/* Contact Information */}
            <section>
              <h2 className="text-fluid-lg font-bold text-gray-900 dark:text-gray-100 mb-4">8. Contact Information</h2>
              <div className="space-y-4 text-gray-700 dark:text-gray-300">
                <p>
                  If you have questions about these Terms or need to contact us regarding your account, please 
                  reach out to our support team through the Help page or contact us directly.
                </p>
              </div>
            </section>
          </div>

          {/* Agreement Confirmation */}
          <div className="mt-8 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-700 rounded-lg p-6">
            <h3 className="text-fluid-sm font-semibold text-blue-900 dark:text-blue-100 mb-3">By using KarnAGT, you acknowledge that:</h3>
            <ul className="space-y-2 text-blue-800 dark:text-blue-200 text-fluid-xs">
              <li>✓ You have read and understood these Terms of Service</li>
              <li>✓ You agree to comply with all terms and conditions</li>
              <li>✓ You understand your rights and responsibilities as a user</li>
              <li>✓ You consent to our data practices as described</li>
            </ul>
          </div>
        </div>

        {/* CTA Section */}
        <div className="bg-gray-100 dark:bg-gray-800 py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-fluid-h3 font-bold text-gray-900 dark:text-gray-100 mb-4">
              Ready to get started?
            </h2>
            <p className="text-fluid-sm text-gray-600 dark:text-gray-400 mb-8 max-w-2xl mx-auto">
              Now that you understand our terms, create your account and experience the power of agentic AI.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/register"
                className="inline-flex items-center px-8 py-4 border border-transparent text-fluid-sm font-medium rounded-lg text-white bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200"
              >
                Create Account
              </a>
              <a
                href="/help"
                className="inline-flex items-center px-8 py-4 border border-gray-300 dark:border-gray-600 text-fluid-sm font-medium rounded-lg text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Get Help
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
              <p className="text-gray-600 dark:text-gray-400 text-fluid-xs">&copy; 2025 KarnAGT. All rights reserved.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-4 sm:gap-8">
              <a href="/home" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all text-fluid-xs">Home</a>
              <a href="/about" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all text-fluid-xs">About</a>
              <a href="/help" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all text-fluid-xs">Help</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
