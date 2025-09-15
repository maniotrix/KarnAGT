import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Link } from 'react-router-dom';
import { Globe, Image, FileText, Code, Brain, Languages, Sparkles, ArrowRight } from 'lucide-react';

interface Feature {
  icon: React.ReactNode;
  title: string;
  description: string;
  gradient: string;
  delay: number;
  videoId: string; // YouTube video ID
  videoTitle: string;
  thumbnailUrl?: string; // Optional custom thumbnail
}

const features: Feature[] = [
  {
    icon: <Globe className="h-8 w-8" />,
    title: "Zero setup overhead",
    description: "No model selection, no configuration. KarnAGT auto-selects and optimizes everything for you.",
    gradient: "from-purple-500 to-pink-500",
    delay: 0.1,
    videoId: "8BXKd4fCJn8", // Replace with actual YouTube video ID
    videoTitle: "See KarnAGT in action"
  },
  {
    icon: <Image className="h-8 w-8" />,
    title: "Always searches web first",
    description: "Get current, accurate information with automatic web research and source citations.",
    gradient: "from-pink-500 to-rose-500",
    delay: 0.2,
    videoId: "CHDs4PTXkN8", // 🔍 AI Agent Finds the Latest iPhone News in Seconds
    videoTitle: "AI Agent Finds the Latest iPhone News in Seconds"
  },
  {
    icon: <FileText className="h-8 w-8" />,
    title: "Inbuilt Vision and File Intelligence",
    description: "Reads 20+ file types and understands images, charts, screenshots—no setup required.",
    gradient: "from-green-500 to-emerald-500",
    delay: 0.3,
    videoId: "vhArzprR-IY", // 👀 AI Turns a Hand-Drawn Sketch into a Webpage
    videoTitle: "AI Turns a Hand-Drawn Sketch into a Webpage"
  },
  {
    icon: <Code className="h-8 w-8" />,
    title: "Creates what you need",
    description: "Generate reports, charts, spreadsheets, and documents—not just answers.",
    gradient: "from-blue-500 to-cyan-500",
    delay: 0.4,
    videoId: "8BXKd4fCJn8", // 📊 AI Agent Reads a CSV File and Creates a Chart Instantly
    videoTitle: "AI Agent Reads a CSV File and Creates a Chart Instantly"
  },
  {
    icon: <Brain className="h-8 w-8" />,
    title: "Understands You",
    description: "Remembers preferences and patterns to personalize guidance over time.",
    gradient: "from-orange-500 to-yellow-500",
    delay: 0.5,
    videoId: "usEGXeNrEh8", // 🧠 This AI Agent That Remembers Your Preferences
    videoTitle: "AI Agent That Remembers Your Preferences"
  },
  {
    icon: <Languages className="h-8 w-8" />,
    title: "Multilingual by default",
    description: "Communicates naturally in many languages—ask and answer in the language you prefer.",
    gradient: "from-indigo-500 to-purple-500",
    delay: 0.6,
    videoId: "A-kjbJlxjNo", // 🌍 AI Agent Switches Language Between English, Hindi, Spanish, etc.
    videoTitle: "AI Agent Switches Between Multiple Languages"
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
  const [playingVideo, setPlayingVideo] = useState<number | null>(null);
  
  const getYoutubeThumbnail = (videoId: string) => {
    return `https://img.youtube.com/vi/${videoId}/maxresdefault.jpg`;
  };

  const handleVideoPlay = (index: number) => {
    setPlayingVideo(index === playingVideo ? null : index);
  };

  return (
    <motion.div 
      className="relative bg-white dark:bg-gray-900 py-20 overflow-hidden"
      initial={{ opacity: 0, y: 60 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "0px" }}
      transition={{ 
        duration: 0.6, 
        ease: "easeOut"
      }}
    >
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
          initial={{ y: 20, opacity: 0 }}
          whileInView={{ y: 0, opacity: 1 }}
          viewport={{ once: true, margin: "0px" }}
          transition={{ duration: 0.5, delay: 0.1 }}
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
            Advanced reasoning meets practical action. Think through problems, research current information, and provide complete solutions—from insights to implementation.
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
          viewport={{ once: true, margin: "0px" }}
        >
          {features.map((feature, index) => (
            <motion.div
              key={index}
              variants={itemVariants}
              className="group relative"
            >
              {/* Card */}
              <div className="relative h-full bg-white dark:bg-gray-800/80 backdrop-blur-sm rounded-2xl border border-gray-200 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600/50 shadow-sm hover:shadow-2xl transition-all duration-500 hover:-translate-y-2 overflow-hidden">
                {/* Gradient Border Effect */}
                <div className={`absolute inset-0 rounded-2xl bg-gradient-to-r ${feature.gradient} opacity-0 group-hover:opacity-10 transition-opacity duration-500 blur-lg`} />
                
                 {/* Enhanced Video Thumbnail Section */}
                 <div className="relative">
                   {/* Gradient Frame Border */}
                   <div className={`absolute -inset-0.5 rounded-xl bg-gradient-to-r ${feature.gradient} opacity-0 group-hover:opacity-30 transition-opacity duration-500 blur-sm -z-10`} />
                   
                   {playingVideo === index ? (
                     // YouTube Embed when playing
                     <motion.div 
                       className="aspect-video rounded-xl overflow-hidden"
                       initial={{ scale: 0.98, opacity: 0 }}
                       animate={{ scale: 1, opacity: 1 }}
                       transition={{ duration: 0.3, ease: "easeOut" }}
                     >
                       <iframe
                         src={`https://www.youtube.com/embed/${feature.videoId}?autoplay=1`}
                         title={feature.videoTitle}
                         className="w-full h-full"
                         allowFullScreen
                         allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                       />
                       
                       {/* Close Button */}
                       <button
                         onClick={(e) => {
                           e.stopPropagation();
                           handleVideoPlay(index);
                         }}
                         className="absolute top-3 right-3 p-2 bg-black/50 backdrop-blur-sm rounded-full text-white hover:bg-black/70 transition-colors"
                       >
                         <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                           <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                         </svg>
                       </button>
                     </motion.div>
                   ) : (
                     // Enhanced Video Thumbnail
                     <div 
                       className="relative aspect-video cursor-pointer group/video rounded-xl overflow-hidden"
                       onClick={() => handleVideoPlay(index)}
                     >
                       {/* Thumbnail Image */}
                       <img 
                         src={getYoutubeThumbnail(feature.videoId)}
                         alt={feature.videoTitle}
                         className="w-full h-full object-cover transition-transform duration-500 group-hover/video:scale-105"
                         onError={(e) => {
                           // Fallback to standard definition thumbnail
                           e.currentTarget.src = `https://img.youtube.com/vi/${feature.videoId}/sddefault.jpg`;
                         }}
                       />
                       
                       {/* Shimmer Effect on Hover */}
                       <motion.div 
                         className="absolute inset-0 -skew-x-12 bg-gradient-to-r from-transparent via-white/20 to-transparent opacity-0 group-hover/video:opacity-100 pointer-events-none"
                         animate={{
                           x: ["-100%", "100%"]
                         }}
                         transition={{
                           duration: 1.5,
                           repeat: Infinity,
                           ease: "easeOut"
                         }}
                       />
                       
                       {/* Glassmorphism Overlay */}
                       <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-black/20 to-black/30 group-hover/video:from-black/50 group-hover/video:via-black/15 group-hover/video:to-black/25 transition-all duration-300">
                         
                         {/* Enhanced Elevated Play Button */}
                         <div className="absolute inset-0 flex items-center justify-center">
                           {/* Backdrop blur circle for depth */}
                           <div className="absolute w-20 h-20 bg-white/5 backdrop-blur-xl rounded-full opacity-60 group-hover/video:opacity-80 transition-opacity duration-500" />
                           
                           {/* Outer glow ring */}
                           <div className={`absolute w-16 h-16 rounded-full bg-gradient-to-br ${feature.gradient} opacity-20 blur-sm group-hover/video:opacity-30 transition-opacity duration-300`} />
                           
                           <motion.div
                             className={`relative w-14 h-14 rounded-full bg-gradient-to-br ${feature.gradient} backdrop-blur-md border border-white/30 group-hover/video:scale-110 transition-all duration-300 flex items-center justify-center`}
                             style={{
                               boxShadow: `
                                 0 8px 32px rgba(0, 0, 0, 0.3),
                                 0 4px 16px rgba(0, 0, 0, 0.2),
                                 0 2px 8px rgba(0, 0, 0, 0.1),
                                 inset 0 1px 0 rgba(255, 255, 255, 0.2),
                                 inset 0 -1px 0 rgba(0, 0, 0, 0.1)
                               `
                             }}
                             whileHover={{ 
                               scale: 1.05,
                               y: -2,
                               boxShadow: `
                                 0 12px 48px rgba(0, 0, 0, 0.4),
                                 0 8px 24px rgba(0, 0, 0, 0.25),
                                 0 4px 12px rgba(0, 0, 0, 0.15),
                                 inset 0 1px 0 rgba(255, 255, 255, 0.3),
                                 inset 0 -1px 0 rgba(0, 0, 0, 0.15)
                               `
                             }}
                             whileTap={{ 
                               scale: 0.95,
                               y: 0,
                               boxShadow: `
                                 0 4px 16px rgba(0, 0, 0, 0.3),
                                 0 2px 8px rgba(0, 0, 0, 0.2),
                                 inset 0 1px 0 rgba(255, 255, 255, 0.1),
                                 inset 0 -1px 0 rgba(0, 0, 0, 0.2)
                               `
                             }}
                             animate={{
                               y: [0, -1, 0],
                             }}
                             transition={{
                               y: { duration: 4, repeat: Infinity, ease: "easeInOut" },
                               boxShadow: { duration: 0.2 }
                             }}
                           >
                             {/* Inner highlight */}
                             <div className="absolute inset-0.5 rounded-full bg-gradient-to-t from-transparent to-white/20 opacity-60" />
                             
                             {/* Play button context hint */}
                             <div className="absolute inset-0 rounded-full border-2 border-white/10 opacity-0 group-hover/video:opacity-100 transition-opacity duration-300" />
                             
                             {/* Icon with enhanced depth */}
                             <div className="relative h-8 w-8 text-white" style={{ 
                               filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.3)) drop-shadow(0 1px 2px rgba(0,0,0,0.2))'
                             }}>
                    {feature.icon}
                  </div>
                  
                             {/* Subtle play symbol overlay for context */}
                             <div className="absolute -bottom-1 -right-1 w-3 h-3 bg-white/20 rounded-full flex items-center justify-center opacity-0 group-hover/video:opacity-100 transition-opacity duration-300">
                               <svg className="w-2 h-2 text-white/80" fill="currentColor" viewBox="0 0 24 24">
                                 <path d="M8 5v14l11-7z"/>
                               </svg>
                             </div>
                           </motion.div>
                         </div>
                         
                          {/* Enhanced Video Title Badge */}
                          <div className="absolute bottom-3 left-3 right-3">
                            <div className="px-3 py-1.5 bg-black/40 backdrop-blur-md rounded-full border border-white/10">
                              <p className="text-white text-xs font-medium flex items-center gap-2">
                                {/* Enhanced Play Icon */}
                                <div className="relative">
                                  <div className="w-5 h-5 rounded-full bg-white/20 flex items-center justify-center shadow-lg border border-white/30">
                                    <svg className="w-2.5 h-2.5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24" style={{
                                      filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.3))'
                                    }}>
                                      <path d="M8 5v14l11-7z"/>
                                    </svg>
                                  </div>
                                  {/* Subtle glow */}
                                  <div className="absolute inset-0 rounded-full bg-white/10 opacity-50 blur-sm -z-10" />
                                </div>
                                <span className="truncate">{feature.videoTitle}</span>
                              </p>
                            </div>
                          </div>
                       </div>
                     </div>
                   )}
                 </div>

                {/* Content Section */}
                <div className="p-6 relative">
                  {/* Floating particles */}
                  <motion.div
                    className="absolute top-2 right-2 w-2 h-2 bg-yellow-400 rounded-full opacity-0 group-hover:opacity-100"
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
                  <motion.div
                    className="absolute bottom-2 left-2 w-1.5 h-1.5 bg-blue-400 rounded-full opacity-0 group-hover:opacity-100"
                    animate={{
                      scale: [0, 1, 0],
                      opacity: [0, 1, 0],
                    }}
                    transition={{
                      duration: 2,
                      repeat: Infinity,
                      delay: feature.delay + 0.5,
                    }}
                  />

                  {/* Text Content */}
                  <div className="relative text-center">
                    <h3 className="text-xl font-bold text-gray-900 dark:text-white mb-4 group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:bg-clip-text group-hover:from-gray-900 group-hover:to-gray-600 dark:group-hover:from-white dark:group-hover:to-gray-300 transition-all duration-300">
                      {feature.title}
                    </h3>
                    
                    <p className="text-gray-600 dark:text-gray-400 leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
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
    </motion.div>
  );
};
