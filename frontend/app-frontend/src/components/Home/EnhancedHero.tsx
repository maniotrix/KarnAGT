import React, { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { motion, useScroll, useTransform } from 'framer-motion';
import { ArrowRight, Download, Sparkles, Zap, Users, MessageSquare, Clock, Shield, Cpu, ChevronDown } from 'lucide-react';

interface AnimatedCounterProps {
  end: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
}

const AnimatedCounter: React.FC<AnimatedCounterProps> = ({ 
  end, 
  duration = 2000, 
  suffix = '', 
  prefix = '' 
}) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime: number;
    let animationFrame: number;

    const animate = (timestamp: number) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      
      setCount(Math.floor(progress * end));
      
      if (progress < 1) {
        animationFrame = requestAnimationFrame(animate);
      }
    };

    animationFrame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animationFrame);
  }, [end, duration]);

  return <span>{prefix}{count.toLocaleString()}{suffix}</span>;
};

interface EnhancedHeroProps {
  onInstallClick: () => void;
}

export const EnhancedHero: React.FC<EnhancedHeroProps> = ({ onInstallClick }) => {
  const heroRef = useRef<HTMLDivElement>(null);
  const { scrollYProgress } = useScroll({
    target: heroRef,
    offset: ["start start", "end start"]
  });
  
  // Content animations based on hero scroll progress
  const contentY = useTransform(scrollYProgress, [0, 1], [0, 80]);
  const contentOpacity = useTransform(scrollYProgress, [0, 0.7, 1], [1, 0.4, 0.1]);
  const scrollIndicatorOpacity = useTransform(scrollYProgress, [0, 0.8, 1], [1, 0.3, 0]);

  // Smooth scroll function for the more indicator
  const handleScrollDown = () => {
    const viewportHeight = window.innerHeight;
    const scrollAmount = viewportHeight * 0.8; // Scroll down 80% of viewport height
    
    window.scrollBy({
      top: scrollAmount,
      behavior: 'smooth'
    });
  };

  return (
    <div ref={heroRef} className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 bg-gradient-to-br from-blue-50 via-indigo-50 to-purple-50 dark:from-gray-900 dark:via-blue-900/20 dark:to-purple-900/20">
        {/* Animated Orbs */}
        <motion.div
          className="absolute top-1/4 left-1/4 w-64 h-64 bg-blue-400/20 rounded-full blur-3xl"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute top-3/4 right-1/4 w-96 h-96 bg-purple-400/20 rounded-full blur-3xl"
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        
        {/* Grid Pattern */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#8b5cf6_1px,transparent_1px),linear-gradient(to_bottom,#8b5cf6_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] opacity-10 dark:opacity-5" />
      </div>

      {/* Enhanced bottom gradient for smooth transition */}
      <div className="absolute inset-x-0 bottom-0 h-32 bg-gradient-to-b from-transparent via-white/40 to-white dark:via-gray-900/40 dark:to-gray-900 pointer-events-none" />

      <motion.div 
        className="relative z-10 w-full px-4 sm:px-6 lg:px-8 text-center flex flex-col justify-center min-h-full py-8 pb-28 pt-20"
        style={{ y: contentY, opacity: contentOpacity }}
      >
        <div className="max-w-7xl mx-auto">
          {/* Main Heading */}
          <motion.div
            initial={{ y: 50, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.2 }}
            className="mb-8"
          >
          <h1 className="text-4xl sm:text-5xl lg:text-7xl font-bold text-gray-900 dark:text-white mb-4">
            Meet{' '}
            <span className="relative">
              <span className="bg-gradient-to-r from-blue-600 via-teal-500 to-blue-600 bg-[length:200%_100%] bg-clip-text text-transparent animate-shimmer underline decoration-blue-400/60 decoration-1 underline-offset-8">
                KarnAGT
              </span>
              <motion.div
                className="absolute -top-1 -right-5 sm:-top-2 sm:-right-4 lg:top-2 lg:-right-7"
                animate={{ rotate: [0, 15, -15, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
              >
                <Sparkles className="w-4 h-4 sm:w-5 sm:h-5 lg:w-6 lg:h-6 text-yellow-500" />
              </motion.div>
            </span>
          </h1>
          <p className="text-xl sm:text-2xl text-gray-600 dark:text-gray-300 max-w-3xl mx-auto leading-relaxed">
            Your advanced AI agent that{' '}
            <motion.span
              className="text-blue-600 dark:text-blue-400 font-semibold"
              animate={{ opacity: [1, 0.7, 1] }}
              transition={{ duration: 2, repeat: Infinity }}
            >
              thinks
            </motion.span>
            ,{' '}
            <motion.span
              className="text-purple-600 dark:text-purple-400 font-semibold"
              animate={{ opacity: [1, 0.7, 1] }}
              transition={{ duration: 2, repeat: Infinity, delay: 0.5 }}
            >
              sees
            </motion.span>
            ,{' '}
            <motion.span
              className="text-green-600 dark:text-green-400 font-semibold"
              animate={{ opacity: [1, 0.7, 1] }}
              transition={{ duration: 2, repeat: Infinity, delay: 1 }}
            >
              remembers
            </motion.span>
            , and{' '}
            <motion.span
              className="text-orange-600 dark:text-orange-400 font-semibold"
              animate={{ opacity: [1, 0.7, 1] }}
              transition={{ duration: 2, repeat: Infinity, delay: 1.5 }}
            >
              creates
            </motion.span>
            {' '}complete solutions with everything you need, in your language.
          </p>
        </motion.div>

        {/* Temporary Value Proposition - Replace with Stats Row later */}
        {/* <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="flex justify-center mb-12"
        >
          <div className="inline-flex items-center gap-3 px-6 py-3 bg-white/80 dark:bg-gray-800/80 backdrop-blur rounded-full border border-gray-200/50 dark:border-gray-700/50 shadow-lg">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Always up-to-date
              </span>
            </div>
            <div className="w-px h-4 bg-gray-300 dark:bg-gray-600"></div>
            <div className="flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-purple-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Always learning
              </span>
            </div>
            <div className="w-px h-4 bg-gray-300 dark:bg-gray-600"></div>
            <div className="flex items-center gap-2">
              <Zap className="w-4 h-4 text-blue-500" />
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Always ready
              </span>
            </div>
          </div>
        </motion.div> */}

        {/* Stats Row - Uncomment when ready to use */}
        <motion.div
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.4 }}
          className="flex flex-wrap justify-center gap-8 mb-12 text-sm sm:text-base"
        >
          <div className="flex items-center gap-2 px-4 py-2 bg-white/80 dark:bg-gray-800/80 backdrop-blur rounded-full border border-gray-200/50 dark:border-gray-700/50">
            <Clock className="w-4 h-4 text-blue-500" />
            <span className="text-gray-700 dark:text-gray-300">
              &lt; <AnimatedCounter end={5} suffix="s" /> response time
            </span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-white/80 dark:bg-gray-800/80 backdrop-blur rounded-full border border-gray-200/50 dark:border-gray-700/50">
            <Zap className="w-4 h-4 text-yellow-500" />
            <span className="text-gray-700 dark:text-gray-300">
              <AnimatedCounter end={99} suffix=".9%" /> uptime
            </span>
          </div>
          <div className="flex items-center gap-2 px-4 py-2 bg-white/80 dark:bg-gray-800/80 backdrop-blur rounded-full border border-gray-200/50 dark:border-gray-700/50">
            <Shield className="w-4 h-4 text-green-500" />
            <span className="text-gray-700 dark:text-gray-300">
              <AnimatedCounter end={100} suffix="%" /> private
            </span>
          </div>
        </motion.div>

          {/* CTA Buttons */}
          <motion.div
            initial={{ y: 30, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.6 }}
            className="flex flex-col sm:flex-row gap-4 justify-center items-center mb-8"
          >
          <Link to="/register">
            <motion.button
              className="group relative w-full sm:w-auto px-8 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300 overflow-hidden"
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-blue-700 to-purple-700 opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
              <div className="relative flex items-center justify-center gap-2">
                <span className="text-lg">Get Started for Free</span>
                <motion.div
                  animate={{ x: [0, 5, 0] }}
                  transition={{ duration: 1.5, repeat: Infinity }}
                >
                  <ArrowRight className="w-5 h-5" />
                </motion.div>
              </div>
            </motion.button>
          </Link>

          <Link to="/login">
            <motion.button
              className="w-full sm:w-auto px-8 py-4 bg-white/80 dark:bg-gray-800/80 backdrop-blur border border-gray-200/50 dark:border-gray-700/50 text-gray-700 dark:text-gray-300 font-semibold rounded-xl hover:bg-white dark:hover:bg-gray-800 transition-all duration-300"
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              Sign In
            </motion.button>
          </Link>
        </motion.div>

          {/* Install App Button */}
          <motion.div
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.8, delay: 0.8 }}
          >
            <button
              onClick={onInstallClick}
              className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium text-blue-600 dark:text-blue-400 bg-blue-50/80 dark:bg-blue-900/30 backdrop-blur border border-blue-200/50 dark:border-blue-700/50 rounded-lg hover:bg-blue-100/80 dark:hover:bg-blue-900/50 transition-all duration-300"
            >
              <Download className="w-4 h-4" />
              Install as App
            </button>
          </motion.div>
        </div>

        {/* Scroll Indicator - Bottom positioned but centered within content container */}
        <div className="absolute bottom-8 left-0 right-0 z-20 pointer-events-none">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <motion.div
              style={{ opacity: scrollIndicatorOpacity }}
              className="flex justify-center pointer-events-auto"
            >
              <motion.button
                className="cursor-pointer group hover:scale-110 transition-transform duration-200 focus:outline-none rounded-lg p-2"
                animate={{ y: [0, 6, 0] }}
                transition={{ duration: 2, repeat: Infinity }}
                onClick={handleScrollDown}
                aria-label="Scroll down to watch KarnAGT videos in action"
              >
                <div className="flex flex-col items-center gap-2 text-gray-400 dark:text-gray-500 group-hover:text-gray-600 dark:group-hover:text-gray-300 transition-colors duration-200">
                   <span className="text-xs font-medium tracking-wide uppercase">Videos & More</span>
                  <motion.div
                    animate={{ opacity: [1, 0.3, 1] }}
                    transition={{ duration: 2, repeat: Infinity }}
                  >
                    <ChevronDown className="w-5 h-5" />
                  </motion.div>
                </div>
              </motion.button>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </div>
  );
};
