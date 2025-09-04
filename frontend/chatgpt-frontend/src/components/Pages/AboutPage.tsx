import React from 'react';

import { ArrowLeft, Brain, Shield, Globe, Users, Zap, Heart } from 'lucide-react';
import Logo from '../ui/Logo';

/**
 * About Page - Company information and mission
 * 
 * Features:
 * - Company overview and mission
 * - Team information
 * - Technology overview
 * - Responsive design with mobile scrolling
 * - Proper padding and navigation
 */
export const AboutPage: React.FC = () => {
  const teamValues = [
    {
      icon: <Brain className="h-8 w-8 text-purple-500" />,
      title: "Innovation First",
      description: "We push the boundaries of what's possible with AI technology, creating solutions that truly make a difference."
    },
    {
      icon: <Shield className="h-8 w-8 text-blue-500" />,
      title: "Privacy by Design",
      description: "Your data security and privacy are fundamental to everything we build. We believe AI should empower, not compromise."
    },
    {
      icon: <Globe className="h-8 w-8 text-green-500" />,
      title: "Global Accessibility",
      description: "AI should be accessible to everyone, everywhere. We build with inclusivity and multilingual support at our core."
    },
    {
      icon: <Users className="h-8 w-8 text-orange-500" />,
      title: "Human-Centered",
      description: "Technology serves humanity, not the other way around. We design AI that augments human intelligence and creativity."
    }
  ];

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
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 sm:pt-16 lg:pt-20 pb-8">
          <div className="flex justify-start mb-4">
            <button
              onClick={() => window.history.back()}
              className="inline-flex items-center text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-100 text-fluid-xs font-medium underline hover:no-underline transition-all"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </button>
          </div>
          <div className="text-center">
            <div className="flex flex-col items-center mb-6">
              <div className="mb-6">
                <Logo size="xl" />
              </div>
              <h1 className="text-fluid-h2 font-bold text-gray-900 dark:text-gray-100 text-center">
                About <span className="text-blue-600 dark:text-blue-400">KarnAGT</span>
              </h1>
            </div>
            <p className="text-fluid-lg text-gray-600 dark:text-gray-400 mb-8 max-w-3xl mx-auto">
              We're building the future of agentic AI—intelligent systems that think, reason, and adapt to help humans achieve more.
            </p>
          </div>
        </div>

        {/* Mission Section */}
        <div className="bg-white dark:bg-gray-800 py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-fluid-h3 font-bold text-gray-900 dark:text-gray-100 mb-6">Our Mission</h2>
              <p className="text-fluid-sm text-gray-600 dark:text-gray-400 max-w-4xl mx-auto leading-relaxed">
                At KarnAGT, we believe artificial intelligence should enhance human potential, not replace it. 
                Our mission is to create AI agents that truly understand context, learn from interaction, and 
                adapt to individual needs while maintaining the highest standards of privacy and security.
              </p>
            </div>
            
            <div className="bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/20 dark:to-purple-900/20 rounded-2xl p-8 sm:p-12">
              <div className="flex flex-col lg:flex-row items-center gap-8">
                <div className="flex-1">
                  <h3 className="text-fluid-base font-bold text-gray-900 dark:text-gray-100 mb-4">Why Agentic AI?</h3>
                  <p className="text-gray-700 dark:text-gray-300 text-fluid-sm mb-6">
                    Traditional AI gives you responses. Agentic AI gives you results. Our systems don't just answer 
                    questions—they understand your goals, plan complex tasks, execute multi-step workflows, and 
                    learn from every interaction to serve you better.
                  </p>
                  <div className="flex items-center text-blue-600 dark:text-blue-400">
                    <Zap className="h-5 w-5 mr-2" />
                    <span className="font-medium">Powered by advanced reasoning and execution capabilities</span>
                  </div>
                </div>
                <div className="w-full lg:w-auto">
                  <div className="grid grid-cols-2 gap-4 text-center">
                    <div className="bg-white dark:bg-gray-700 p-4 rounded-xl shadow-sm">
                      <div className="text-fluid-base font-bold text-blue-600 dark:text-blue-400">24/7</div>
                      <div className="text-fluid-xs text-gray-600 dark:text-gray-400">Available</div>
                    </div>
                    <div className="bg-white dark:bg-gray-700 p-4 rounded-xl shadow-sm">
                      <div className="text-fluid-base font-bold text-purple-600 dark:text-purple-400">50+</div>
                      <div className="text-fluid-xs text-gray-600 dark:text-gray-400">Languages</div>
                    </div>
                    <div className="bg-white dark:bg-gray-700 p-4 rounded-xl shadow-sm">
                      <div className="text-fluid-base font-bold text-green-600 dark:text-green-400">∞</div>
                      <div className="text-fluid-xs text-gray-600 dark:text-gray-400">Scalable</div>
                    </div>
                    <div className="bg-white dark:bg-gray-700 p-4 rounded-xl shadow-sm">
                      <div className="text-fluid-base font-bold text-orange-600 dark:text-orange-400">100%</div>
                      <div className="text-fluid-xs text-gray-600 dark:text-gray-400">Private</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Values Section */}
        <div className="bg-gray-50 dark:bg-gray-900 py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-fluid-h3 font-bold text-gray-900 dark:text-gray-100 mb-4">Our Values</h2>
              <p className="text-fluid-sm text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                These principles guide everything we do, from product development to customer relationships.
              </p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
              {teamValues.map((value, index) => (
                <div
                  key={index}
                  className="bg-white dark:bg-gray-800 p-8 rounded-2xl shadow-sm border border-gray-200 dark:border-gray-700 hover:shadow-md transition-shadow"
                >
                  <div className="flex items-start gap-4">
                    <div className="flex-shrink-0">
                      {value.icon}
                    </div>
                    <div>
                      <h3 className="text-fluid-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
                        {value.title}
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                        {value.description}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Technology Section */}
        <div className="bg-white dark:bg-gray-800 py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-fluid-h3 font-bold text-gray-900 dark:text-gray-100 mb-4">Our Technology</h2>
              <p className="text-fluid-sm text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
                Built on state-of-the-art AI research and engineering excellence, KarnAGT represents the next 
                generation of artificial intelligence systems.
              </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
              <div className="text-center">
                <div className="bg-blue-50 dark:bg-blue-900/30 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Brain className="h-8 w-8 text-blue-600 dark:text-blue-400" />
                </div>
                <h3 className="text-fluid-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Advanced Reasoning</h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Multi-step reasoning capabilities that can break down complex problems and execute sophisticated workflows.
                </p>
              </div>
              <div className="text-center">
                <div className="bg-green-50 dark:bg-green-900/30 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Globe className="h-8 w-8 text-green-600 dark:text-green-400" />
                </div>
                <h3 className="text-fluid-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Real-time Knowledge</h3>
                <p className="text-gray-600 dark:text-gray-400">
                  Always up-to-date with web-connected research capabilities and real-time information access.
                </p>
              </div>
              <div className="text-center">
                <div className="bg-purple-50 dark:bg-purple-900/30 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Shield className="h-8 w-8 text-purple-600 dark:text-purple-400" />
                </div>
                <h3 className="text-fluid-sm font-semibold text-gray-900 dark:text-gray-100 mb-2">Privacy-First Architecture</h3>
                <p className="text-gray-600 dark:text-gray-400">
                  End-to-end security with data encryption, private workspaces, and transparent data handling.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Contact Section */}
        <div className="bg-blue-50 dark:bg-blue-900/20 py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-fluid-h3 font-bold text-gray-900 dark:text-gray-100 mb-4">
              Ready to experience the future?
            </h2>
            <p className="text-fluid-sm text-gray-600 dark:text-gray-400 mb-8 max-w-2xl mx-auto">
              Join thousands of users who are already using KarnAGT to enhance their productivity and creativity.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a
                href="/register"
                className="inline-flex items-center px-8 py-4 border border-transparent text-fluid-sm font-medium rounded-lg text-white bg-blue-600 dark:bg-blue-500 hover:bg-blue-700 dark:hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200"
              >
                Get Started Free
              </a>
              <a
                href="/help"
                className="inline-flex items-center px-8 py-4 border border-gray-300 dark:border-gray-600 text-fluid-sm font-medium rounded-lg text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-700 hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
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
              <p className="text-gray-600 dark:text-gray-400 text-fluid-xs">&copy; 2025 KarnAGT. All rights reserved.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-4 sm:gap-8">
              <a href="/home" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all text-fluid-xs">Home</a>
              <a href="/help" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all text-fluid-xs">Help</a>
              <a href="/terms" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all text-fluid-xs">Terms</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
