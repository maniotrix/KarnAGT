import React, { useEffect, useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Menu, Download, Palette, LogIn, Shield, ArrowRight } from 'lucide-react';
import { useCurrentUser } from '../../app/hooks/auth';
import Logo from '../ui/Logo';
import { PWAInstallModal } from '../ui/PWAInstallModal';
import { ThemeToggle } from '../ui/ThemeToggle';
import { EnhancedHero } from './EnhancedHero';
import { ModernFeatures } from './ModernFeatures';
import { DownloadableOutputs } from './DownloadableOutputs';
import { InteractiveSteps } from './InteractiveSteps';
import { SocialProof } from './SocialProof';

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
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [isPWAModalOpen, setIsPWAModalOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Redirect if already logged in (same pattern as AuthForm)
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
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex flex-col overflow-y-auto" style={{ height: 'auto', minHeight: '100vh' }}>
      {/* Header */}
      <header className="absolute top-0 left-0 right-0 z-50 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                      <div className="flex justify-between items-center h-16">
              <div className="flex items-center">
                {/* Hamburger Menu */}
                <div className="relative mr-3" ref={dropdownRef}>
                  <button
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    className="inline-flex items-center p-2 border border-white/20 dark:border-gray-700/20 rounded-lg text-gray-700 dark:text-gray-300 bg-white/10 dark:bg-gray-800/10 backdrop-blur-md hover:bg-white/40 hover:border-white/40 dark:hover:bg-gray-700/40 dark:hover:border-gray-600/40 hover:shadow-xl hover:scale-105 focus:outline-none focus:ring-2 focus:ring-white/30 transition-all duration-300 shadow-lg"
                    aria-label="Menu"
                  >
                    <Menu className="h-4 w-4" />
                  </button>
                  
                  {isDropdownOpen && (
                    <div className="absolute left-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-md shadow-lg border border-gray-200 dark:border-gray-700 py-1 z-50">
                      {/* Theme Toggle Section */}
                      <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
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
                        className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        onClick={() => setIsDropdownOpen(false)}
                      >
                        About
                      </a>
                      <a
                        href="/help"
                        className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        onClick={() => setIsDropdownOpen(false)}
                      >
                        Help
                      </a>
                      <a
                        href="/terms"
                        className="block px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                        onClick={() => setIsDropdownOpen(false)}
                      >
                        Terms
                      </a>
                      
                      <div className="border-t border-gray-200 dark:border-gray-700 my-1"></div>
                      
                      <button
                        onClick={() => {
                          setIsPWAModalOpen(true);
                          setIsDropdownOpen(false);
                        }}
                        className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex items-center"
                      >
                        <Download className="h-4 w-4 mr-2" />
                        Install as App
                      </button>
                    </div>
                  )}
                </div>
                
                <Logo size="sm" className="mr-2" />
                <h1 className="text-lg sm:text-xl md:text-2xl font-bold text-gray-900 dark:text-gray-100">KarnAGT</h1>
              </div>
              
            <div className="flex items-center">
              <Link
                to="/login"
                className="inline-flex items-center px-3 py-2 sm:px-4 border border-white/20 dark:border-gray-700/20 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white/10 dark:bg-gray-800/10 backdrop-blur-md hover:bg-white/40 hover:border-white/40 dark:hover:bg-gray-700/40 dark:hover:border-gray-600/40 hover:shadow-xl hover:scale-105 focus:outline-none focus:ring-2 focus:ring-white/30 transition-all duration-300 shadow-lg"
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

        {/* Downloadable Outputs Section */}
        <DownloadableOutputs />

        {/* Interactive Steps Section */}
        <InteractiveSteps />

        {/* Social Proof Section */}
        <SocialProof />

        {/* Popular use cases - Enhanced */}
        <div className="relative bg-gradient-to-br from-gray-50 to-blue-50/30 dark:from-gray-800 dark:to-blue-900/10 py-16 overflow-hidden">
          {/* Background Pattern */}
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-100/20 via-transparent to-transparent dark:from-blue-500/5" />
        </div>

          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h3 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-4">
                Real examples people actually ask for
              </h3>
              <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
                From simple questions to complete deliverables—see how KarnAGT creates what you actually need
              </p>
            </div>
            
            {/* Enhanced chips with flex wrap layout */}
            <div className="flex flex-wrap justify-center gap-4">
              {[
                { name: 'Analyze spending data → budget charts', icon: '📊', color: 'from-blue-500 to-cyan-500' },
                { name: 'Research paper → study guide', icon: '📚', color: 'from-green-500 to-emerald-500' },
                { name: 'Compare job offers → decision table', icon: '⚖️', color: 'from-purple-500 to-pink-500' },
                { name: 'Photo collection → Python organizer', icon: '🐍', color: 'from-orange-500 to-red-500' },
                { name: 'Dataset → interactive visualizations', icon: '📈', color: 'from-indigo-500 to-purple-500' },
                { name: 'Lecture notes → formatted summaries', icon: '📝', color: 'from-blue-500 to-indigo-500' },
                { name: 'Complex topic → clear infographic', icon: '🎨', color: 'from-pink-500 to-rose-500' },
                { name: 'Web research → sourced report', icon: '🔍', color: 'from-yellow-500 to-orange-500' }
              ].map((chip, index) => (
                <div
                  key={chip.name}
                  className="group relative px-6 py-4 text-sm font-medium rounded-2xl bg-white/80 dark:bg-gray-800/80 backdrop-blur border border-gray-200/50 dark:border-gray-700/50 hover:border-transparent hover:shadow-xl transition-all duration-300 cursor-pointer transform hover:-translate-y-1"
                  style={{ animationDelay: `${index * 0.1}s` }}
                >
                  {/* Gradient border on hover */}
                  <div className={`absolute -inset-0.5 rounded-2xl bg-gradient-to-r ${chip.color} opacity-0 group-hover:opacity-100 blur transition-opacity duration-300 -z-10`} />
                  
                  <div className="relative flex items-center gap-3">
                    <span className="text-lg">{chip.icon}</span>
                    <span className="text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white transition-colors">
                      {chip.name}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Enhanced Reassurance Strip */}
        <div className="relative bg-white dark:bg-gray-900 py-16">
          <div className="absolute inset-0 bg-gradient-to-r from-blue-50/50 via-purple-50/30 to-indigo-50/50 dark:from-blue-900/10 dark:via-purple-900/5 dark:to-indigo-900/10" />
          
          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-100/80 dark:bg-blue-900/30 backdrop-blur rounded-full text-blue-800 dark:text-blue-300 text-sm font-medium mb-6">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                Powered by Advanced AI
              </div>
              
              <h3 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-4">
                Creates what you need, not just answers
              </h3>
              
              <p className="text-lg text-gray-600 dark:text-gray-400 max-w-3xl mx-auto">
                Most AI gives you information. KarnAGT delivers completed work—professional documents, analysis reports, and ready-to-use outputs you can share immediately.
              </p>
            </div>

            {/* Feature highlights */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="group relative p-6 bg-white/60 dark:bg-gray-800/60 backdrop-blur rounded-2xl border border-gray-200/50 dark:border-gray-700/50 hover:border-blue-300/50 dark:hover:border-blue-600/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-lg text-white">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                  </div>
                  <h4 className="font-semibold text-gray-900 dark:text-white">Lightning Fast</h4>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Optimized inference with sub-second response times for most queries
                </p>
              </div>
              
              <div className="group relative p-6 bg-white/60 dark:bg-gray-800/60 backdrop-blur rounded-2xl border border-gray-200/50 dark:border-gray-700/50 hover:border-purple-300/50 dark:hover:border-purple-600/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-gradient-to-r from-purple-500 to-pink-500 rounded-lg text-white">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                  </div>
                  <h4 className="font-semibold text-gray-900 dark:text-white">Always Learning</h4>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Continuously updated with latest knowledge and improved reasoning capabilities
                </p>
              </div>
              
              <div className="group relative p-6 bg-white/60 dark:bg-gray-800/60 backdrop-blur rounded-2xl border border-gray-200/50 dark:border-gray-700/50 hover:border-green-300/50 dark:hover:border-green-600/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
                <div className="flex items-center gap-3 mb-3">
                  <div className="p-2 bg-gradient-to-r from-green-500 to-emerald-500 rounded-lg text-white">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                    </svg>
                  </div>
                  <h4 className="font-semibold text-gray-900 dark:text-white">Reliable Results</h4>
                </div>
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  Consistent, accurate outputs with built-in fact-checking and source verification
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Enhanced Privacy & Control */}
        <div className="relative bg-gray-50 dark:bg-gray-900 py-16 overflow-hidden">
          {/* Background Elements */}
          <div className="absolute inset-0">
            <div className="absolute top-1/4 left-1/4 w-64 h-64 bg-blue-500/5 rounded-full blur-3xl" />
            <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-green-500/5 rounded-full blur-3xl" />
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_bottom,_var(--tw-gradient-stops))] from-blue-50/20 via-transparent to-transparent dark:from-blue-500/5" />
            </div>
          
          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="relative rounded-3xl bg-gradient-to-br from-white via-blue-50/30 to-green-50/30 dark:from-gray-800 dark:via-blue-900/10 dark:to-green-900/10 border border-gray-200/50 dark:border-gray-700/50 p-8 sm:p-12 overflow-hidden backdrop-blur">
              {/* Decorative pattern */}
              <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-transparent rounded-full blur-2xl" />
              <div className="absolute bottom-0 left-0 w-24 h-24 bg-gradient-to-tr from-green-500/10 to-transparent rounded-full blur-2xl" />
              
              <div className="relative">
                <div className="flex items-center justify-center gap-3 mb-8">
                  <div className="p-4 bg-gradient-to-r from-blue-600 to-green-600 rounded-2xl text-white shadow-lg">
                    <Shield className="h-8 w-8" />
            </div>
                  <div className="text-center">
                    <h3 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-2">
                      Privacy & Control
                    </h3>
                    <p className="text-lg text-gray-600 dark:text-gray-400">
                      Your data, your rules, your peace of mind
                    </p>
          </div>
        </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                  <div className="group relative p-6 bg-white/60 dark:bg-gray-700/60 backdrop-blur rounded-2xl border border-gray-200/50 dark:border-gray-600/50 hover:border-blue-300/50 dark:hover:border-blue-600/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-cyan-500 rounded-2xl opacity-0 group-hover:opacity-20 blur transition-opacity duration-300 -z-10" />
                    
                    <div className="relative">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                          <svg className="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                          </svg>
                        </div>
                        <h4 className="font-bold text-gray-900 dark:text-white">Private by Design</h4>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                        Your personal workspace with end-to-end encryption. No data mining, no tracking, no compromise.
                      </p>
                    </div>
                  </div>
                  
                  <div className="group relative p-6 bg-white/60 dark:bg-gray-700/60 backdrop-blur rounded-2xl border border-gray-200/50 dark:border-gray-600/50 hover:border-green-300/50 dark:hover:border-green-600/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-green-500 to-emerald-500 rounded-2xl opacity-0 group-hover:opacity-20 blur transition-opacity duration-300 -z-10" />
                    
                    <div className="relative">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
                          <svg className="w-5 h-5 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                          </svg>
                        </div>
                        <h4 className="font-bold text-gray-900 dark:text-white">Enterprise Security</h4>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                        Bank-grade infrastructure with SOC 2 compliance, regular audits, and 24/7 monitoring.
                      </p>
                    </div>
                  </div>
                  
                  <div className="group relative p-6 bg-white/60 dark:bg-gray-700/60 backdrop-blur rounded-2xl border border-gray-200/50 dark:border-gray-600/50 hover:border-purple-300/50 dark:hover:border-purple-600/50 transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
                    <div className="absolute -inset-0.5 bg-gradient-to-r from-purple-500 to-pink-500 rounded-2xl opacity-0 group-hover:opacity-20 blur transition-opacity duration-300 -z-10" />
                    
                    <div className="relative">
                      <div className="flex items-center gap-3 mb-4">
                        <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                          <svg className="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                          </svg>
                        </div>
                        <h4 className="font-bold text-gray-900 dark:text-white">Full Transparency</h4>
                      </div>
                      <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                        Clear data practices, open-source components, and complete control over your information.
              </p>
            </div>
          </div>
        </div>

                {/* Trust indicators */}
                <div className="mt-8 pt-8 border-t border-gray-200/50 dark:border-gray-700/50">
                  <div className="flex flex-wrap justify-center items-center gap-6 text-sm text-gray-600 dark:text-gray-400">
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                      <span>SOC 2 Compliant</span>
                    </div>
                    <div className="w-px h-4 bg-gray-300 dark:bg-gray-600"></div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                      <span>GDPR Ready</span>
                    </div>
                    <div className="w-px h-4 bg-gray-300 dark:bg-gray-600"></div>
                    <div className="flex items-center gap-2">
                      <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                      <span>Zero-Trust Architecture</span>
                    </div>
                  </div>
              </div>
              </div>
            </div>
          </div>
        </div>

        {/* Enhanced Call to Action Section */}
        <div className="relative bg-gradient-to-br from-blue-50 via-indigo-50 to-slate-50 dark:from-gray-900 dark:via-blue-950 dark:to-slate-950 py-20 overflow-hidden">
          {/* Animated Background Elements */}
          <div className="absolute inset-0">
            <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(255,255,255,.1)_50%,transparent_75%)] bg-[length:20px_20px] opacity-20" />
            <div className="absolute top-0 left-1/4 w-96 h-96 bg-white/5 rounded-full blur-3xl animate-pulse" />
            <div className="absolute bottom-0 right-1/4 w-64 h-64 bg-slate-300/10 rounded-full blur-3xl animate-pulse" style={{ animationDelay: '1s' }} />
            
            {/* Floating particles */}
            <div className="absolute top-20 left-20 w-2 h-2 bg-white/30 rounded-full animate-bounce" style={{ animationDelay: '0.5s' }} />
            <div className="absolute top-40 right-32 w-3 h-3 bg-blue-200/40 rounded-full animate-bounce" style={{ animationDelay: '1.5s' }} />
            <div className="absolute bottom-32 left-1/3 w-2 h-2 bg-slate-200/30 rounded-full animate-bounce" style={{ animationDelay: '2s' }} />
          </div>
          
          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            {/* Main CTA Content */}
            <div className="mb-12">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-blue-100/80 dark:bg-white/20 backdrop-blur rounded-full text-blue-700 dark:text-blue-100 text-sm font-medium mb-6">
                <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
                Ready to get started?
              </div>
              
              <h2 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 dark:text-white mb-6">
                Ready when{' '}
                <span className="relative">
                  <span className="bg-gradient-to-r from-yellow-300 to-orange-300 bg-clip-text text-transparent">
                    you are
                  </span>
                  <div className="absolute -bottom-2 left-0 right-0 h-1 bg-gradient-to-r from-yellow-300 to-orange-300 rounded-full opacity-70"></div>
                </span>
            </h2>
              
              <p className="text-xl text-gray-600 dark:text-blue-100 mb-10 max-w-3xl mx-auto leading-relaxed">
                Stop settling for just answers. Get completed work—reports, charts, documents, and analysis you can use immediately. Join thousands who've made the switch to outcome-focused AI.
            </p>
            </div>

            {/* CTA Buttons */}
            <div className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-12">
            <Link
              to="/register"
                className="group relative w-full sm:w-auto px-8 py-4 bg-blue-600 hover:bg-blue-700 dark:bg-white text-white dark:text-blue-600 font-bold text-lg rounded-xl shadow-2xl hover:shadow-3xl transition-all duration-300 overflow-hidden transform hover:scale-105 hover:-translate-y-1"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-700 to-purple-700 dark:from-blue-50 dark:to-purple-50 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                <div className="relative flex items-center justify-center gap-3">
                  <span>Create your account</span>
                  <div className="flex items-center justify-center w-6 h-6 bg-white text-blue-600 dark:bg-blue-600 dark:text-white rounded-full group-hover:bg-blue-50 dark:group-hover:bg-blue-700 transition-colors">
                    <ArrowRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform duration-200" />
                  </div>
                </div>
                
                {/* Shimmer effect */}
                <div className="absolute inset-0 -skew-x-12 bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover:opacity-100 group-hover:animate-[shimmer_0.6s_ease-out] pointer-events-none" />
              </Link>
              
              <Link
                to="/login"
                className="group w-full sm:w-auto px-8 py-4 border-2 border-gray-300 dark:border-white/30 text-gray-700 dark:text-white font-semibold text-lg rounded-xl hover:bg-gray-100 dark:hover:bg-white/10 hover:border-gray-400 dark:hover:border-white/50 backdrop-blur transition-all duration-300 hover:scale-105"
              >
                <div className="flex items-center justify-center gap-2">
                  <span>Sign In</span>
                  <svg className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-200" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                  </svg>
                </div>
            </Link>
            </div>

            {/* Trust indicators */}
            <div className="flex flex-wrap justify-center items-center gap-8 text-gray-500 dark:text-blue-200">
              <div className="flex items-center gap-2 text-sm">
                <svg className="w-4 h-4 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
                <span>Free to start</span>
              </div>
              <div className="w-px h-4 bg-gray-400/30 dark:bg-blue-300/30"></div>
              <div className="flex items-center gap-2 text-sm">
                <svg className="w-4 h-4 text-blue-500 dark:text-blue-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                </svg>
                <span>No credit card required</span>
              </div>
              <div className="w-px h-4 bg-gray-400/30 dark:bg-blue-300/30"></div>
              <div className="flex items-center gap-2 text-sm">
                <svg className="w-4 h-4 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                <span>Setup in 30 seconds</span>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* PWA Install Modal */}
      <PWAInstallModal 
        isOpen={isPWAModalOpen} 
        onClose={() => setIsPWAModalOpen(false)} 
      />

      {/* Footer */}
      <footer className="bg-white dark:bg-gray-800 border-t border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex flex-col sm:flex-row justify-between items-center">
            <div className="text-center sm:text-left mb-4 sm:mb-0">
              <p className="text-gray-600 dark:text-gray-400 text-fluid-xs">&copy; 2025 KarnAGT. All rights reserved.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-4 sm:gap-8">
              <a href="/about" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all text-fluid-xs">About</a>
              <a href="/help" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all text-fluid-xs">Help</a>
              <a href="/terms" className="text-gray-600 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 underline hover:no-underline transition-all text-fluid-xs">Terms</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
