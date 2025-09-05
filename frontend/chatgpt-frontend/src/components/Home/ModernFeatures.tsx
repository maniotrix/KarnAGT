import React from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Globe, Image, FileText, Code, Brain, Languages, Sparkles, ArrowRight } from 'lucide-react';

interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
  gradient: string;
  delay: number;
}

const features: Feature[] = [
  {
    icon: <Globe className="h-8 w-8" />,
    title: "Fresh, reliable answers",
    description: "Get concise summaries backed by up‑to‑date web research when you need it.",
    gradient: "from-purple-500 to-pink-500",
    delay: 0.1
  },
  {
    icon: <Image className="h-8 w-8" />,
    title: "Vision built in",
    description: "Understand images, charts, and screenshots to extract insights and context.",
    gradient: "from-pink-500 to-rose-500",
    delay: 0.2
  },
  {
    icon: <FileText className="h-8 w-8" />,
    title: "Works with your files",
    description: "Ask questions about your documents and get actionable insights in seconds.",
    gradient: "from-green-500 to-emerald-500",
    delay: 0.3
  },
  {
    icon: <Code className="h-8 w-8" />,
    title: "Does the hard parts",
    description: "Offload analysis and computations to AI‑powered code execution.",
    gradient: "from-blue-500 to-cyan-500",
    delay: 0.4
  },
  {
    icon: <Brain className="h-8 w-8" />,
    title: "Understands your context",
    description: "Remembers preferences and patterns to personalize guidance over time.",
    gradient: "from-orange-500 to-yellow-500",
    delay: 0.5
  },
  {
    icon: <Languages className="h-8 w-8" />,
    title: "Multilingual by default",
    description: "Communicates naturally in many languages—ask and answer in the language you prefer.",
    gradient: "from-indigo-500 to-purple-500",
    delay: 0.6
  }
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.3
    }
  }
};

const itemVariants = {
  hidden: { y: 50, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      duration: 0.8,
      ease: "easeOut"
    }
  }
};

export const ModernFeatures: React.FC = () => {
  return (
    <div className="relative bg-white dark:bg-gray-900 py-20 overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0">
        {/* Gradient Mesh */}
        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-blue-50/50 via-transparent to-purple-50/50 dark:from-blue-900/10 dark:via-transparent dark:to-purple-900/10" />
        
        {/* Floating Shapes */}
        <motion.div
          className="absolute top-1/4 right-1/4 w-32 h-32 bg-gradient-to-br from-blue-400/5 to-purple-400/5 dark:from-blue-400/10 dark:to-purple-400/10 rounded-full blur-xl"
          animate={{
            scale: [1, 1.2, 1],
            rotate: [0, 180, 360],
          }}
          transition={{
            duration: 20,
            repeat: Infinity,
            ease: "linear"
          }}
        />
        <motion.div
          className="absolute bottom-1/4 left-1/4 w-24 h-24 bg-gradient-to-br from-green-400/5 to-blue-400/5 dark:from-green-400/10 dark:to-blue-400/10 rounded-full blur-xl"
          animate={{
            scale: [1.2, 1, 1.2],
            rotate: [360, 180, 0],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "linear"
          }}
        />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header */}
        <motion.div
          className="text-center mb-16"
          initial={{ y: 50, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8 }}
        >
          <div className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-900/30 dark:to-purple-900/30 border border-blue-200/50 dark:border-blue-700/50 rounded-full text-blue-800 dark:text-blue-300 text-sm font-medium mb-6">
            <Sparkles className="w-4 h-4" />
            Why KarnAGT
          </div>
          
          <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white mb-6">
            Powerful AI for{' '}
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              everyone
            </span>
          </h2>
          
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto leading-relaxed">
            An advanced agentic system that thinks, sees, remembers, and adapts—transforming how you work with AI-powered intelligence.
          </p>
          
          <motion.p
            className="mt-4 text-lg text-green-600 dark:text-green-400 font-medium"
            initial={{ scale: 0.8, opacity: 0 }}
            whileInView={{ scale: 1, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ delay: 0.5, duration: 0.5 }}
          >
            🎉 Free powerful AI for everyone
          </motion.p>
        </motion.div>

        {/* Features Grid */}
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              variants={itemVariants}
              className="group relative"
            >
              {/* Card */}
              <div className="relative h-full p-8 bg-white dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl border border-gray-200 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600/50 shadow-sm hover:shadow-2xl transition-all duration-500 hover:-translate-y-2">
                {/* Gradient Border Effect */}
                <div className={`absolute inset-0 rounded-2xl bg-gradient-to-r ${feature.gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-500 blur-lg`} />
                
                {/* Icon Container */}
                <div className="relative mb-6">
                  <div className={`inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-r ${feature.gradient} text-white shadow-lg group-hover:scale-110 transition-transform duration-300`}>
                    {feature.icon}
                  </div>
                  
                  {/* Floating particles */}
                  <motion.div
                    className="absolute -top-1 -right-1 w-2 h-2 bg-yellow-400 rounded-full opacity-0 group-hover:opacity-100"
                    animate={{
                      scale: [0, 1, 0],
                      opacity: [0, 1, 0],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      delay: feature.delay,
                    }}
                  />
                </div>

                {/* Content */}
                <div className="relative">
                  <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-3 group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:bg-clip-text group-hover:from-gray-900 group-hover:to-gray-600 dark:group-hover:from-white dark:group-hover:to-gray-300 transition-all duration-300">
                    {feature.title}
                  </h3>
                  
                  <p className="text-gray-600 dark:text-gray-400 leading-relaxed mb-4">
                    {feature.description}
                  </p>
                  
                  {/* Learn More Link */}
                  <motion.div
                    className="flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400 opacity-0 group-hover:opacity-100 transition-all duration-300"
                    initial={false}
                    animate={{
                      x: [0, 5, 0],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      repeatDelay: 3,
                    }}
                  >
                    <span>Learn more</span>
                    <ArrowRight className="w-4 h-4" />
                  </motion.div>
                </div>

                {/* Hover Glow Effect */}
                <div className={`absolute -inset-0.5 rounded-2xl bg-gradient-to-r ${feature.gradient} opacity-0 group-hover:opacity-15 blur transition-opacity duration-500 -z-10`} />
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Bottom CTA */}
        <motion.div
          className="text-center mt-16"
          initial={{ y: 30, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.8, duration: 0.8 }}
        >
          <p className="text-lg text-gray-600 dark:text-gray-400 mb-6">
            Built for individuals. Private by default. Always ready.
          </p>
          
          <motion.div
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
          >
            <Link
              to="/register"
              className="inline-flex items-center gap-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl shadow-lg hover:shadow-xl transition-all duration-300"
            >
              <span>Start building with KarnAGT</span>
              <ArrowRight className="w-4 h-4" />
            </Link>
          </motion.div>
        </motion.div>
      </div>
    </div>
  );
};
