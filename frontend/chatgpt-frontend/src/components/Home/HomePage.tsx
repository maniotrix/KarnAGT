import React, { useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { MessageSquare, FileText, Globe, Code, Brain, ArrowRight, LogIn, UserPlus, Zap, Shield, Search, CheckCircle2, Languages, Image } from 'lucide-react';
import { useCurrentUser } from '../../app/hooks/auth';
import Logo from '../ui/Logo';

/**
 * Simple Home page component - Landing page for unauthenticated users
 * 
 * Features:
 * - Welcome message and app overview
 * - Call-to-action buttons for login/register
 * - Feature highlights
 * - Responsive design
 * - Redirects authenticated users to main app
 */
export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const { data: user } = useCurrentUser();

  // Redirect if already logged in (same pattern as AuthForm)
  useEffect(() => {
    if (user) {
      navigate('/');
    }
  }, [user, navigate]);

  const features = [
    {
      icon: <Globe className="h-8 w-8 text-purple-500" />,
      title: "Fresh, reliable answers",
      description: "Get concise summaries backed by up‑to‑date web research when you need it."
    },
    {
      icon: <Image className="h-8 w-8 text-pink-500" />,
      title: "Vision built in",
      description: "Understand images, charts, and screenshots to extract insights and context."
    },
    {
      icon: <FileText className="h-8 w-8 text-green-500" />,
      title: "Works with your files",
      description: "Ask questions about your documents and get actionable insights in seconds."
    },
    {
      icon: <Code className="h-8 w-8 text-blue-500" />,
      title: "Does the hard parts",
      description: "Offload analysis and computations to AI‑powered code execution."
    },
    {
      icon: <Brain className="h-8 w-8 text-orange-500" />,
      title: "Understands your context",
      description: "Remembers preferences and patterns to personalize guidance over time."
    },
    {
      icon: <Languages className="h-8 w-8 text-indigo-500" />,
      title: "Multilingual by default",
      description: "Communicates naturally in many languages—ask and answer in the language you prefer."
    }
  ];

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col overflow-y-auto" style={{ height: 'auto', minHeight: '100vh' }}>
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                      <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                <Logo size="sm" className="mr-2" />
                <h1 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-900">KarnAGT</h1>
              </div>
            <div className="flex items-center space-x-2 sm:space-x-4">
              <Link
                to="/login"
                className="inline-flex items-center px-3 py-2 sm:px-4 border border-gray-300 rounded-md text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                <LogIn className="h-4 w-4 mr-2" />
                Sign In
              </Link>
              <Link
                to="/register"
                className="inline-flex items-center px-3 py-2 sm:px-4 border border-transparent rounded-md text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                <UserPlus className="h-4 w-4 mr-2" />
                Sign Up
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-2 sm:px-0">
        {/* Hero Section */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 sm:pt-16 lg:pt-20 pb-8">
          <div className="text-center">
            <div className="flex flex-col items-center mb-6">
              <div className="mb-6">
                <Logo size="2xl" />
              </div>
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 text-center">
                Meet <span className="text-blue-600">KarnAGT</span>—your advanced AI agent
              </h1>
            </div>
            <p className="text-xl sm:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
              An intelligent agentic system that reasons, sees, remembers, and communicates in any language. 
              Always up‑to‑date. Always learning. Always ready to help you achieve more.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link
                to="/register"
                className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200 transform hover:scale-105"
              >
                Get Started for Free
                <ArrowRight className="ml-2 h-5 w-5" />
              </Link>
              <Link
                to="/login"
                className="inline-flex items-center px-8 py-4 border border-gray-300 text-lg font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Sign In
              </Link>
            </div>
            <p className="mt-6 text-sm sm:text-base text-gray-500 max-w-xl mx-auto">
              Built for individuals. Private by default. Always ready.
            </p>
          </div>
        </div>

        {/* Features Section */}
        <div className="bg-white pt-4 pb-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              
              <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
                Why KarnAGT
              </h2>
              <div className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-green-50 to-blue-50 border border-green-200 rounded-full text-green-800 text-sm font-medium mb-6">
                🎉 Free powerful AI for everyone
              </div>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                An advanced agentic system that thinks, sees, remembers, and adapts—transforming how you work with AI-powered intelligence.
              </p>
            </div>
            
            <div className="flex flex-wrap justify-center gap-8">
              {features.map((feature, index) => (
                <div
                  key={index}
                  className="text-center p-6 rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-lg transition-all duration-200 w-full sm:w-72"
                >
                  <div className="flex justify-center mb-4">
                    {feature.icon}
                  </div>
                  <h3 className="text-xl font-semibold text-gray-900 mb-2">
                    {feature.title}
                  </h3>
                  <p className="text-gray-600">
                    {feature.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* How it works */}
        <div className="bg-white py-8">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-10">
              <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-3">How it works</h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">From intent to outcome in three clear steps.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="rounded-2xl border border-gray-200 bg-white p-6">
                <div className="flex items-center gap-3 mb-3">
                  <Search className="h-5 w-5 text-blue-600" />
                  <h3 className="text-lg font-semibold text-gray-900">Describe your goal</h3>
                </div>
                <p className="text-gray-600">Share what you need—drafts, summaries, analysis, plans, or calculations.</p>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-white p-6">
                <div className="flex items-center gap-3 mb-3">
                  <Zap className="h-5 w-5 text-yellow-600" />
                  <h3 className="text-lg font-semibold text-gray-900">AI plans and executes</h3>
                </div>
                <p className="text-gray-600">KarnAGT reasons, searches the web, analyzes images, works with your files, and executes code—all in any language.</p>
              </div>
              <div className="rounded-2xl border border-gray-200 bg-white p-6">
                <div className="flex items-center gap-3 mb-3">
                  <CheckCircle2 className="h-5 w-5 text-green-600" />
                  <h3 className="text-lg font-semibold text-gray-900">Get a polished result</h3>
                </div>
                <p className="text-gray-600">Receive clear, actionable output you can use immediately—no busywork.</p>
              </div>
            </div>
          </div>
        </div>

        {/* Popular use cases */}
        <div className="bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-4">
            <div className="text-center mb-6">
              <h3 className="text-xl font-semibold text-gray-900">Popular use cases</h3>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {[
                'Research summaries',
                'Document Q&A',
                'Vision analysis',
                'Data analysis',
                'Multilingual translation',
                'Code assistance',
                'Complex reasoning',
                'Learning & tutoring'
              ].map((chip) => (
                <span key={chip} className="px-3 py-1.5 text-sm rounded-full bg-gray-100 text-gray-700 border border-gray-200">
                  {chip}
                </span>
              ))}
            </div>
          </div>
        </div>

        {/* Social Proof / Reassurance Strip */}
        <div className="bg-white">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <div className="rounded-2xl border border-gray-200 bg-gray-50 p-6 text-center">
              <p className="text-gray-700 text-base sm:text-lg">
                Powered by state-of-the-art models with agentic reasoning—so you get intelligent outcomes, not just responses.
              </p>
            </div>
          </div>
        </div>

        {/* Privacy & Control */}
        <div className="bg-white pb-2">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="rounded-2xl border border-gray-200 p-6">
              <div className="flex items-center gap-3 mb-2">
                <Shield className="h-5 w-5 text-blue-600" />
                <h3 className="text-lg font-semibold text-gray-900">Privacy & Control</h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-gray-700">
                <div>Private by design—your personal workspace.</div>
                <div>State‑of‑the‑art security infrastructure protects your data.</div>
                <div>Transparent behavior—you’re always in control.</div>
              </div>
            </div>
          </div>
        </div>

        {/* Call to Action Section */}
        <div className="bg-blue-50 py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 mb-4">
              Ready when you are
            </h2>
            <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
              Experience agentic AI that understands your goals, thinks through complex problems, and delivers results that matter.
            </p>
            <Link
              to="/register"
              className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200 transform hover:scale-105"
            >
              Create your account
              <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col sm:flex-row justify-between items-center">
            <div className="text-center sm:text-left mb-4 sm:mb-0">
              <p className="text-gray-600">&copy; 2025 KarnAGT. All rights reserved.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-4 sm:gap-8">
              <a href="/about" className="text-gray-600 hover:text-blue-600 underline hover:no-underline transition-all">About</a>
              <a href="/help" className="text-gray-600 hover:text-blue-600 underline hover:no-underline transition-all">Help</a>
              <a href="/terms" className="text-gray-600 hover:text-blue-600 underline hover:no-underline transition-all">Terms</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
