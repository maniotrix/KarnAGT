import React, { useState } from 'react';

import { ArrowLeft, Search, MessageSquare, FileText, Settings, HelpCircle, ChevronDown, ChevronUp, Mail, Book, Video, Users } from 'lucide-react';
import Logo from '../ui/Logo';

/**
 * Help Page - Support and documentation
 * 
 * Features:
 * - FAQ with collapsible sections
 * - Getting started guide
 * - Contact support options
 * - Responsive design with mobile scrolling
 * - Search functionality placeholder
 */
export const HelpPage: React.FC = () => {
  const [openFaqIndex, setOpenFaqIndex] = useState<number | null>(0);

  const faqItems = [
    {
      question: "What is KarnAGT and how is it different from other AI tools?",
      answer: "KarnAGT is an advanced agentic AI system that goes beyond simple question-answering. Unlike traditional AI chatbots, KarnAGT can reason through complex problems, execute multi-step workflows, search the web for current information, analyze documents and images, and remember context from previous interactions. It's designed to be your intelligent assistant that actually gets things done."
    },
    {
      question: "How do I get started with KarnAGT?",
      answer: "Getting started is simple! First, create a free account using your email or Google account. Once signed in, you can immediately start chatting with KarnAGT. Try asking it to help with research, analyze a document, or plan a complex task. The AI will guide you through its capabilities as you explore."
    },
    {
      question: "Is my data safe and private?",
      answer: "Absolutely. Your privacy and data security are our top priorities. All conversations are encrypted in transit and at rest. We never share your personal data with third parties, and you have full control over your information. Your workspace is completely private, and you can delete your data at any time."
    },
    {
      question: "What file types can KarnAGT analyze?",
      answer: "KarnAGT can work with a wide variety of file types including PDF documents, Word files, Excel spreadsheets, PowerPoint presentations, images (PNG, JPG, JPEG), text files, and more. It can extract information, answer questions about the content, summarize documents, and even help with data analysis."
    },
    {
      question: "Can KarnAGT access the internet?",
      answer: "Yes! KarnAGT has web search capabilities and can access current information from the internet. This means it can provide up-to-date answers, research recent events, find current statistics, and verify facts in real-time. This sets it apart from AI systems that only have knowledge up to a certain training date."
    },
    {
      question: "How does the multilingual support work?",
      answer: "KarnAGT natively supports over 50 languages and can seamlessly switch between them in the same conversation. You can ask questions in one language and request answers in another. It understands cultural context and nuances, making it truly multilingual rather than just translated."
    },
    {
      question: "Is there a limit to how much I can use KarnAGT?",
      answer: "We offer generous usage limits for free accounts. For most users, these limits are sufficient for daily use."
    },
    {
      question: "Can I use KarnAGT for business or commercial purposes?",
      answer: "Yes, KarnAGT is suitable for both personal and business use. Many professionals use it for research, analysis, content creation, and workflow automation."
    },
    {
      question: "How do I report a problem or get support?",
      answer: "If you encounter any issues or need help, you can contact our support team at help@karnagt.com or through the contact options below. We typically respond within 24 hours. You can also check our documentation for common solutions and troubleshooting steps."
    }
  ];

  const quickLinks = [
    {
      icon: <Book className="h-6 w-6 text-blue-500" />,
      title: "Getting Started Guide",
      description: "Learn the basics and get up to speed quickly",
      action: "Read Guide"
    },
    {
      icon: <Video className="h-6 w-6 text-green-500" />,
      title: "Video Tutorials",
      description: "Watch step-by-step tutorials and demos",
      action: "Watch Videos"
    },
    {
      icon: <Users className="h-6 w-6 text-purple-500" />,
      title: "Community Forum",
      description: "Connect with other users and share tips",
      action: "Join Community"
    },
    {
      icon: <Mail className="h-6 w-6 text-orange-500" />,
      title: "Contact Support",
      description: "Get direct help from our support team at help@karnagt.com",
      action: "Email Support"
    }
  ];

  const toggleFaq = (index: number) => {
    setOpenFaqIndex(openFaqIndex === index ? null : index);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col overflow-y-auto" style={{ height: 'auto', minHeight: '100vh' }}>
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Logo size="sm" className="mr-2" />
              <a href="/" className="text-lg sm:text-xl md:text-2xl font-bold text-gray-900 hover:text-blue-600 transition-colors">KarnAGT</a>
            </div>
            <a
              href="/"
              className="text-blue-600 hover:text-blue-700 text-sm font-medium transition-colors"
            >
              Go to Home
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-2 sm:px-0">
        {/* Hero Section */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-12 sm:pt-16 pb-8">
          <div className="flex justify-start mb-4">
            <button
              onClick={() => window.history.back()}
              className="inline-flex items-center text-gray-600 hover:text-gray-900 text-sm font-medium underline hover:no-underline transition-all"
            >
              <ArrowLeft className="h-4 w-4 mr-2" />
              Back
            </button>
          </div>
          <div className="text-center">
            <div className="flex flex-col items-center mb-6">
              <HelpCircle className="h-16 w-16 text-blue-500 mb-4" />
              <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold text-gray-900 text-center">
                How can we <span className="text-blue-600">help</span>?
              </h1>
            </div>
            <p className="text-xl sm:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
              Find answers, learn how to use KarnAGT effectively, and get the support you need.
            </p>
          </div>

          {/* Search Bar */}
          <div className="max-w-2xl mx-auto mb-12">
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                <Search className="h-5 w-5 text-gray-400" />
              </div>
              <input
                type="text"
                className="block w-full pl-10 pr-3 py-4 border border-gray-300 rounded-lg leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                placeholder="Search for help articles, tutorials, or common questions..."
              />
            </div>
          </div>
        </div>

        {/* Quick Links */}
        <div className="bg-white py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-8">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">Popular Help Topics</h2>
              <p className="text-lg text-gray-600">Quick access to the most helpful resources</p>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {quickLinks.map((link, index) => (
                <div
                  key={index}
                  className="bg-gray-50 p-6 rounded-xl border border-gray-200 hover:border-blue-300 hover:shadow-md transition-all duration-200 cursor-pointer group"
                >
                  <div className="flex flex-col items-center text-center">
                    <div className="mb-4 group-hover:scale-110 transition-transform">
                      {link.icon}
                    </div>
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      {link.title}
                    </h3>
                    <p className="text-gray-600 mb-4 text-sm">
                      {link.description}
                    </p>
                    <span className="text-blue-600 text-sm font-medium group-hover:text-blue-700">
                      {link.action} →
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* FAQ Section */}
        <div className="bg-gray-50 py-12">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">Frequently Asked Questions</h2>
              <p className="text-lg text-gray-600">Find quick answers to common questions about KarnAGT</p>
            </div>
            
            <div className="space-y-4">
              {faqItems.map((item, index) => (
                <div
                  key={index}
                  className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden"
                >
                  <button
                    className="w-full px-6 py-4 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset hover:bg-gray-50 transition-colors"
                    onClick={() => toggleFaq(index)}
                  >
                    <div className="flex justify-between items-center">
                      <h3 className="text-lg font-medium text-gray-900 pr-4">
                        {item.question}
                      </h3>
                      {openFaqIndex === index ? (
                        <ChevronUp className="h-5 w-5 text-gray-500 flex-shrink-0" />
                      ) : (
                        <ChevronDown className="h-5 w-5 text-gray-500 flex-shrink-0" />
                      )}
                    </div>
                  </button>
                  {openFaqIndex === index && (
                    <div className="px-6 pb-4">
                      <p className="text-gray-600 leading-relaxed">
                        {item.answer}
                      </p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Getting Started Guide */}
        <div className="bg-white py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12">
              <h2 className="text-3xl font-bold text-gray-900 mb-4">Getting Started with KarnAGT</h2>
              <p className="text-lg text-gray-600 max-w-2xl mx-auto">
                Follow these simple steps to make the most of your KarnAGT experience
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="text-center p-6">
                <div className="bg-blue-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-xl font-bold text-blue-600">1</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">Create Your Account</h3>
                <p className="text-gray-600">
                  Sign up with your email or Google account to get started. It takes less than a minute.
                </p>
              </div>

              <div className="text-center p-6">
                <div className="bg-green-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-xl font-bold text-green-600">2</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">Start a Conversation</h3>
                <p className="text-gray-600">
                  Ask KarnAGT anything! Try uploading a document, asking for research, or planning a project.
                </p>
              </div>

              <div className="text-center p-6">
                <div className="bg-purple-50 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4">
                  <span className="text-xl font-bold text-purple-600">3</span>
                </div>
                <h3 className="text-xl font-semibold text-gray-900 mb-3">Explore Features</h3>
                <p className="text-gray-600">
                  Discover web search, file analysis, multilingual support, and advanced reasoning capabilities.
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Contact Support */}
        <div className="bg-blue-50 py-12">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <h2 className="text-3xl font-bold text-gray-900 mb-4">
              Still need help?
            </h2>
            <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
              Can't find what you're looking for? Our support team is here to help you get the most out of KarnAGT.
              <br />
              <span className="font-medium text-blue-600">Email us at: help@karnagt.com</span>
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <a 
                href="mailto:help@karnagt.com"
                className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-lg text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-all duration-200"
              >
                <Mail className="h-5 w-5 mr-2" />
                Contact Support
              </a>
              <a
                href="/about"
                className="inline-flex items-center px-8 py-4 border border-gray-300 text-lg font-medium rounded-lg text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors"
              >
                Learn About Us
              </a>
            </div>
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
              <a href="/home" className="text-gray-600 hover:text-blue-600 underline hover:no-underline transition-all">Home</a>
              <a href="/about" className="text-gray-600 hover:text-blue-600 underline hover:no-underline transition-all">About</a>
              <a href="/terms" className="text-gray-600 hover:text-blue-600 underline hover:no-underline transition-all">Terms</a>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};
