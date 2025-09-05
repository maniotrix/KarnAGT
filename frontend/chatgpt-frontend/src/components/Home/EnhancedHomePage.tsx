import React, { useEffect, useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, Download, Palette, LogIn, ArrowRight, Shield } from 'lucide-react';
import { useCurrentUser } from '../../app/hooks/auth';
import Logo from '../ui/Logo';
import { PWAInstallModal } from '../ui/PWAInstallModal';
import { ThemeToggle } from '../ui/ThemeToggle';
import { EnhancedHero } from './EnhancedHero';
import { ModernFeatures } from './ModernFeatures';
import { InteractiveSteps } from './InteractiveSteps';
import { SocialProof } from './SocialProof';

/**
 * Enhanced Home page component - Modern landing page with improved visual appeal
 * 
 * Features:
 * - Modern hero section with animations and stats
 * - Interactive features showcase
 * - Step-by-step process explanation
 * - Social proof and testimonials
 * - Mobile-first responsive design
 * - Advanced animations and micro-interactions
 */
export const EnhancedHomePage: React.FC = () => {
  const navigate = useNavigate();
  const { data: user } = useCurrentUser();
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isPWAModalOpen, setIsPWAModalOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Redirect if already logged in
  useEffect(() => {
    if (user) {
      navigate('/');
    }
  }, [user, navigate]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <div className="min-h-screen bg-white dark:bg-gray-900 flex flex-col">
      {/* Enhanced Header - Sticky with blur */}
      <header className="sticky top-0 z-50 backdrop-blur-lg bg-white/80 dark:bg-gray-900/80 supports-[backdrop-filter]:bg-white/60 dark:supports-[backdrop-filter]:bg-gray-900/60 border-b border-gray-200/80 dark:border-gray-800/70">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              {/* Hamburger Menu */}
              <div className="relative mr-3" ref={dropdownRef}>
                <button
                  onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                  className="inline-flex items-center p-2 border border-gray-300/70 dark:border-gray-600/70 rounded-md text-gray-700 dark:text-gray-300 bg-white/80 dark:bg-gray-700/80 backdrop-blur hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200"
                  aria-label="Menu"
                >
                  <Menu className="h-4 w-4" />
                </button>
                
                {isDropdownOpen && (
                  <div className="absolute left-0 mt-2 w-56 bg-white/90 dark:bg-gray-800/90 backdrop-blur-lg rounded-xl shadow-xl border border-gray-200/50 dark:border-gray-700/50 py-1 z-50">
                    {/* Theme Toggle Section */}
                    <div className="px-4 py-2 border-b border-gray-200/50 dark:border-gray-700/50">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center">
                          <Palette className="h-4 w-4 mr-2" />
                          Theme
                        </span>
                      </div>
                      <ThemeToggle size="sm" variant="dropdown" className="w-full" />
                    </div>
                    
                    <a
                      href="/about"
                      className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100/50 dark:hover:bg-gray-700/50 transition-colors"
                      onClick={() => setIsDropdownOpen(false)}
                    >
                      About
                    </a>
                    <a
                      href="/help"
                      className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100/50 dark:hover:bg-gray-700/50 transition-colors"
                      onClick={() => setIsDropdownOpen(false)}
                    >
                      Help
                    </a>
                    <a
                      href="/terms"
                      className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100/50 dark:hover:bg-gray-700/50 transition-colors"
                      onClick={() => setIsDropdownOpen(false)}
                    >
                      Terms
                    </a>
                    
                    <div className="border-t border-gray-200/50 dark:border-gray-700/50 my-1"></div>
                    
                    <button
                      onClick={() => {
                        setIsPWAModalOpen(true);
                        setIsDropdownOpen(false);
                      }}
                      className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100/50 dark:hover:bg-gray-700/50 transition-colors flex items-center"
                    >
                      <Download className="h-4 w-4 mr-2" />
                      Install as App
                    </button>
                  </div>
                )}
              </div>
              
              <Logo size="sm" className="mr-2" />
              <h1 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100">
                KarnAGT
              </h1>
            </div>
            
            <div className="flex items-center">
              <Link
                to="/login"
                className="inline-flex items-center px-3 py-2 sm:px-4 border border-gray-300/70 dark:border-gray-600/70 rounded-md text-sm font-medium text-gray-700 dark:text-gray-300 bg-white/80 dark:bg-gray-700/80 backdrop-blur hover:bg-gray-50 dark:hover:bg-gray-600 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200"
              >
                <LogIn className="h-4 w-4 mr-2" />
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1">
        {/* Enhanced Hero Section */}
        <EnhancedHero onInstallClick={() => setIsPWAModalOpen(true)} />

        {/* Modern Features Section */}
        <ModernFeatures />

        {/* Interactive Steps Section */}
        <InteractiveSteps />

        {/* Social Proof Section */}
        <SocialProof />

        {/* Popular use cases - Redesigned */}
        <div className="bg-gray-50 dark:bg-gray-800/50 py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-8">
              <h3 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100 mb-4">
                Popular use cases
              </h3>
              <p className="text-gray-600 dark:text-gray-400 max-w-xl mx-auto">
                Discover how professionals use KarnAGT across different industries
              </p>
            </div>
            
            {/* Scrollable chips for mobile */}
            <div className="overflow-x-auto -mx-4 px-4 py-2 snap-x snap-mandatory">
              <div className="flex gap-3 w-max">
                {[
                  'Research summaries',
                  'Document Q&A',
                  'Vision analysis',
                  'Data analysis',
                  'Multilingual translation',
                  'Code assistance',
                  'Complex reasoning',
                  'Learning & tutoring'
                ].map((chip, index) => (
                  <span
                    key={chip}
                    className="snap-start px-4 py-2.5 text-sm font-medium rounded-full bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-600 hover:border-blue-300 dark:hover:border-blue-600 hover:shadow-md transition-all duration-200 whitespace-nowrap cursor-pointer"
                    style={{ animationDelay: `${index * 0.1}s` }}
                  >
                    {chip}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Privacy & Control - Enhanced */}
        <div className="bg-white dark:bg-gray-900 py-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="relative rounded-3xl bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-800 dark:via-gray-800 dark:to-gray-700 border border-gray-200/50 dark:border-gray-700/50 p-8 sm:p-12 overflow-hidden">
              {/* Background Pattern */}
              <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-blue-200/20 via-transparent to-transparent dark:from-blue-500/5" />
              
              <div className="relative">
                <div className="flex items-center gap-3 mb-6 justify-center">
                  <div className="p-3 bg-blue-600 rounded-2xl text-white shadow-lg">
                    <Shield className="h-6 w-6" />
                  </div>
                  <h3 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white">
                    Privacy & Control
                  </h3>
                </div>
                
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 text-center">
                  <div className="p-4 bg-white/60 dark:bg-gray-700/60 backdrop-blur rounded-xl border border-gray-200/50 dark:border-gray-600/50">
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
                      Private by Design
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Your personal workspace with end-to-end encryption
                    </p>
                  </div>
                  
                  <div className="p-4 bg-white/60 dark:bg-gray-700/60 backdrop-blur rounded-xl border border-gray-200/50 dark:border-gray-600/50">
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
                      Enterprise Security
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      State‑of‑the‑art infrastructure protects your data
                    </p>
                  </div>
                  
                  <div className="p-4 bg-white/60 dark:bg-gray-700/60 backdrop-blur rounded-xl border border-gray-200/50 dark:border-gray-600/50">
                    <h4 className="font-semibold text-gray-900 dark:text-white mb-2">
                      Full Transparency
                    </h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Clear behavior—you're always in control
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Enhanced Call to Action Section */}
        <div className="relative bg-gradient-to-br from-blue-600 via-purple-600 to-indigo-700 py-20 overflow-hidden">
          {/* Background Elements */}
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,.1)_50%,transparent_75%)] bg-[length:20px_20px] opacity-20" />
            <div className="absolute top-0 left-1/4 w-96 h-96 bg-white/5 rounded-full blur-3xl" />
            <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-purple-300/10 rounded-full blur-3xl" />
          </div>
          
          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-4xl sm:text-5xl font-bold text-white mb-6">
              Ready when you are
            </h2>
            <p className="text-xl text-blue-100 mb-10 max-w-3xl mx-auto leading-relaxed">
              Experience agentic AI that understands your goals, thinks through complex problems, and delivers results that matter.
            </p>
            
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
              <Link
                to="/register"
                className="group relative w-full sm:w-auto px-8 py-4 bg-white text-blue-600 font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden transform hover:scale-105"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-50 to-purple-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                <div className="relative flex items-center justify-center gap-2">
                  <span className="text-lg">Create your account</span>
                  <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-200" />
                </div>
              </Link>
              
              <Link
                to="/login"
                className="w-full sm:w-auto px-8 py-4 border-2 border-white/30 text-white font-semibold rounded-xl hover:bg-white/10 hover:border-white/50 transition-all duration-300"
              >
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </main>

      {/* PWA Install Modal */}
      <PWAInstallModal 
        isOpen={isPWAModalOpen} 
        onClose={() => setIsPWAModalOpen(false)} 
      />

      {/* Enhanced Footer */}
      <footer className="bg-gray-900 dark:bg-gray-950 border-t border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-8">
            {/* Logo & Description */}
            <div className="lg:col-span-2">
              <div className="flex items-center mb-4">
                <Logo size="sm" className="mr-2" />
                <span className="text-xl font-bold text-white">KarnAGT</span>
              </div>
              <p className="text-gray-400 mb-6 max-w-md">
                Advanced AI agent that reasons, sees, remembers, and communicates in any language. Built for professionals who demand intelligence and privacy.
              </p>
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 text-green-400 text-sm">
                  <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                  <span>All systems operational</span>
                </div>
              </div>
            </div>
            
            {/* Quick Links */}
            <div>
              <h4 className="text-white font-semibold mb-4">Product</h4>
              <div className="space-y-2">
                <a href="/about" className="block text-gray-400 hover:text-white transition-colors">About</a>
                <a href="/help" className="block text-gray-400 hover:text-white transition-colors">Help</a>
                <a href="/terms" className="block text-gray-400 hover:text-white transition-colors">Terms</a>
                <a href="/privacy" className="block text-gray-400 hover:text-white transition-colors">Privacy</a>
              </div>
            </div>
            
            {/* Support */}
            <div>
              <h4 className="text-white font-semibold mb-4">Support</h4>
              <div className="space-y-2">
                <a href="/contact" className="block text-gray-400 hover:text-white transition-colors">Contact</a>
                <a href="/status" className="block text-gray-400 hover:text-white transition-colors">Status</a>
                <a href="/docs" className="block text-gray-400 hover:text-white transition-colors">Documentation</a>
                <a href="/community" className="block text-gray-400 hover:text-white transition-colors">Community</a>
              </div>
            </div>
          </div>
          
          <div className="border-t border-gray-800 mt-8 pt-8 flex flex-col sm:flex-row justify-between items-center">
            <p className="text-gray-400 text-sm">&copy; 2025 KarnAGT. All rights reserved.</p>
            <div className="flex items-center gap-4 mt-4 sm:mt-0">
              <span className="text-gray-400 text-sm">Made with ❤️ for professionals</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
