import React from 'react';
import { motion } from 'framer-motion';
import { Star, Quote, Shield, Zap, Users, Globe, Clock, FileText, Download } from 'lucide-react';

interface Testimonial {
  id: number;
  name: string;
  role: string;
  company: string;
  content: string;
  rating: number;
  avatar: string;
}

interface Stat {
  icon: React.ReactNode;
  value: string;
  label: string;
  description: string;
}

// Mock testimonials - replace with real ones
const testimonials: Testimonial[] = [
  {
    id: 1,
    name: "Sarah Chen",
    role: "Product Manager",
    company: "TechCorp",
    content: "KarnAGT has transformed how our team handles research and analysis. The AI's ability to understand context and provide actionable insights is incredible.",
    rating: 5,
    avatar: "SC"
  },
  {
    id: 2,
    name: "Marcus Rodriguez",
    role: "Data Scientist",
    company: "Analytics Pro",
    content: "The vision capabilities are outstanding. I can upload complex charts and get detailed explanations that would take me hours to analyze manually.",
    rating: 5,
    avatar: "MR"
  },
  {
    id: 3,
    name: "Emily Johnson",
    role: "Content Creator",
    company: "Creative Studio",
    content: "Working in multiple languages has never been easier. KarnAGT maintains context perfectly across different languages and cultural nuances.",
    rating: 5,
    avatar: "EJ"
  }
];

const stats: Stat[] = [
  {
    icon: <Clock className="h-6 w-6" />,
    value: "< 5s",
    label: "Response Time",
    description: "Lightning-fast AI responses"
  },
  {
    icon: <Zap className="h-6 w-6" />,
    value: "99.9%",
    label: "Uptime",
    description: "Reliable service when you need it"
  },
  {
    icon: <FileText className="h-6 w-6" />,
    value: "20+",
    label: "File Types",
    description: "PDFs, Excel, PowerPoint, images & more"
  },
  {
    icon: <Download className="h-6 w-6" />,
    value: "20+",
    label: "Output Formats",
    description: "Excel, PDF, HTML, PNG, CSV, JSON and more"
  },
  {
    icon: <Globe className="h-6 w-6" />,
    value: "50+",
    label: "Languages",
    description: "Communicate in your preferred language"
  },
  {
    icon: <Shield className="h-6 w-6" />,
    value: "100%",
    label: "Private",
    description: "Your data stays secure and private"
  }
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.2,
      delayChildren: 0.3
    }
  }
};

const itemVariants = {
  hidden: { y: 30, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      duration: 0.6,
      ease: "easeOut"
    }
  }
};

export const SocialProof: React.FC = () => {
  return (
    <div className="relative bg-white dark:bg-gray-900 py-20 overflow-hidden">
      {/* Background Elements */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-gradient-to-b from-blue-50/30 via-transparent to-purple-50/30 dark:from-blue-900/10 dark:via-transparent dark:to-purple-900/10" />
        
        {/* Floating Elements */}
        <motion.div
          className="absolute top-20 left-10 w-2 h-2 bg-blue-400 rounded-full"
          animate={{
            y: [0, -20, 0],
            opacity: [0.3, 1, 0.3],
          }}
          transition={{
            duration: 4,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute top-40 right-20 w-3 h-3 bg-purple-400 rounded-full"
          animate={{
            y: [0, 15, 0],
            opacity: [0.5, 1, 0.5],
          }}
          transition={{
            duration: 5,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 1
          }}
        />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Stats Section */}
        <motion.div
          className="mb-20"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
        >
          <motion.div className="text-center mb-12" variants={itemVariants}>
            <h2 className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-4">
              Trusted by professionals{' '}
              <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                worldwide
              </span>
            </h2>
            <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
              Join thousands of users who rely on KarnAGT for intelligent AI assistance
            </p>
          </motion.div>

          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6">
            {stats.map((stat, index) => (
              <motion.div
                key={index}
                variants={itemVariants}
                className="text-center group"
              >
                <div className="relative inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl text-white mb-4 group-hover:scale-110 transition-transform duration-300">
                  {stat.icon}
                  
                  {/* Glow effect */}
                  <div className="absolute inset-0 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl blur-lg opacity-0 group-hover:opacity-15 transition-opacity duration-300 -z-10" />
                </div>
                
                <motion.div
                  className="text-3xl sm:text-4xl font-bold text-gray-900 dark:text-white mb-2"
                  initial={{ scale: 0 }}
                  whileInView={{ scale: 1 }}
                  viewport={{ once: true }}
                  transition={{ delay: 0.5 + index * 0.1, duration: 0.5 }}
                >
                  {stat.value}
                </motion.div>
                
                <h4 className="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-1">
                  {stat.label}
                </h4>
                
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {stat.description}
                </p>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Testimonials Section */}
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
        >
          <motion.div className="text-center mb-12" variants={itemVariants}>
            <h3 className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-white mb-4">
              What our users say
            </h3>
            <p className="text-gray-600 dark:text-gray-400 max-w-xl mx-auto">
              Real feedback from professionals who use KarnAGT every day
            </p>
          </motion.div>

          {/* Use flexbox for better centering on tablets */}
          <div className="flex flex-wrap justify-center gap-8 md:gap-6 lg:gap-8">
            {testimonials.map((testimonial, index) => (
              <motion.div
                key={testimonial.id}
                variants={itemVariants}
                className="group relative w-full sm:w-80 md:w-72 lg:w-80 xl:w-96 max-w-sm flex-shrink-0"
              >
                {/* Testimonial Card */}
                <div className="relative h-full p-6 bg-white dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl border border-gray-200 dark:border-gray-700/50 hover:border-blue-300 dark:hover:border-blue-600/50 shadow-sm hover:shadow-xl transition-all duration-300 hover:-translate-y-1">
                  {/* Quote Icon */}
                  <div className="absolute -top-3 -left-3 w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white shadow-lg">
                    <Quote className="w-4 h-4" />
                  </div>

                  {/* Rating */}
                  <div className="flex items-center gap-1 mb-4">
                    {[...Array(testimonial.rating)].map((_, i) => (
                      <motion.div
                        key={i}
                        initial={{ scale: 0, rotate: -180 }}
                        whileInView={{ scale: 1, rotate: 0 }}
                        viewport={{ once: true }}
                        transition={{ delay: 0.1 * i, duration: 0.3 }}
                      >
                        <Star className="w-4 h-4 text-yellow-400 fill-current" />
                      </motion.div>
                    ))}
                  </div>

                  {/* Content */}
                  <blockquote className="text-gray-700 dark:text-gray-300 mb-6 leading-relaxed">
                    "{testimonial.content}"
                  </blockquote>

                  {/* Author */}
                  <div className="flex items-center gap-3">
                    {/* Avatar */}
                    <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-semibold text-sm shadow-lg">
                      {testimonial.avatar}
                    </div>
                    
                    <div>
                      <div className="font-semibold text-gray-900 dark:text-white">
                        {testimonial.name}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">
                        {testimonial.role} at {testimonial.company}
                      </div>
                    </div>
                  </div>

                  {/* Hover Glow */}
                  <div className="absolute -inset-0.5 bg-gradient-to-r from-blue-500 to-purple-600 rounded-2xl opacity-0 group-hover:opacity-15 blur transition-opacity duration-300 -z-10" />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Trust Badges */}
        <motion.div
          className="mt-20 text-center"
          initial={{ y: 30, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.8, duration: 0.6 }}
        >
          <div className="inline-flex items-center gap-6 px-8 py-4 bg-gradient-to-r from-gray-50 to-blue-50 dark:from-gray-800 dark:to-blue-900/20 rounded-2xl border border-gray-200/50 dark:border-gray-700/50">
            <div className="flex items-center gap-2 text-green-600 dark:text-green-400">
              <Shield className="w-5 h-5" />
              <span className="font-medium text-sm">Enterprise Security</span>
            </div>
            
            <div className="w-px h-6 bg-gray-300 dark:bg-gray-600" />
            
            <div className="flex items-center gap-2 text-blue-600 dark:text-blue-400">
              <Zap className="w-5 h-5" />
              <span className="font-medium text-sm">99.9% Uptime</span>
            </div>
            
            <div className="w-px h-6 bg-gray-300 dark:bg-gray-600" />
            
            <div className="flex items-center gap-2 text-purple-600 dark:text-purple-400">
              <Globe className="w-5 h-5" />
              <span className="font-medium text-sm">Global CDN</span>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
};
