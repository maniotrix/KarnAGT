import React from 'react';
import { motion } from 'framer-motion';
import { Download } from 'lucide-react';

interface OutputType {
  name: string;
  ext: string;
  icon: string;
  color: string;
  desc: string;
}

const outputTypes: OutputType[] = [
  { name: 'Excel Files', ext: 'XLSX', icon: '📊', color: 'from-green-500 to-emerald-500', desc: 'Data & analysis' },
  { name: 'Reports', ext: 'PDF', icon: '📄', color: 'from-red-500 to-rose-500', desc: 'Professional docs' },
  { name: 'Charts', ext: 'PNG', icon: '📈', color: 'from-blue-500 to-cyan-500', desc: 'Visualizations' },
  { name: 'Web Pages', ext: 'HTML', icon: '🌐', color: 'from-orange-500 to-yellow-500', desc: 'Interactive content' },
  { name: 'Data Sets', ext: 'CSV', icon: '🗂️', color: 'from-purple-500 to-pink-500', desc: 'Clean data' },
  { name: 'Structured', ext: 'JSON', icon: '⚡', color: 'from-indigo-500 to-blue-500', desc: 'API ready' }
];

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
      delayChildren: 0.2
    }
  }
};

const itemVariants = {
  hidden: { 
    opacity: 0, 
    y: 30,
    scale: 0.9
  },
  visible: {
    opacity: 1,
    y: 0,
    scale: 1,
    transition: {
      duration: 0.5,
      ease: "easeOut"
    }
  }
};

const headerVariants = {
  hidden: { opacity: 0, y: 40 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.6,
      ease: "easeOut"
    }
  }
};

export const DownloadableOutputs: React.FC = () => {
  return (
    <motion.div 
      className="relative bg-gradient-to-br from-white via-blue-50/30 to-indigo-50/30 dark:from-gray-900 dark:via-blue-900/10 dark:to-indigo-900/10 py-20 overflow-hidden"
      initial={{ opacity: 0 }}
      whileInView={{ opacity: 1 }}
      viewport={{ once: true, margin: "0px" }}
      transition={{ duration: 0.6 }}
    >
      {/* Enhanced Background Pattern */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_var(--tw-gradient-stops))] from-blue-100/20 via-transparent to-transparent dark:from-blue-500/5" />
        
        {/* Floating background elements */}
        <motion.div
          className="absolute top-1/4 left-1/4 w-32 h-32 bg-gradient-to-br from-blue-400/5 to-purple-400/5 rounded-full blur-2xl"
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.6, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 w-24 h-24 bg-gradient-to-br from-green-400/5 to-blue-400/5 rounded-full blur-2xl"
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.4, 0.7, 0.4],
          }}
          transition={{
            duration: 6,
            repeat: Infinity,
            ease: "easeInOut",
            delay: 2
          }}
        />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Section Header with enhanced animations */}
        <motion.div
          className="text-center mb-16"
          variants={headerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "0px" }}
        >
          <motion.div 
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-100/80 dark:bg-blue-900/30 backdrop-blur rounded-full text-blue-800 dark:text-blue-300 text-sm font-medium mb-6"
            whileHover={{ scale: 1.05 }}
            transition={{ type: "spring", stiffness: 400 }}
          >
            <motion.div
              animate={{ rotate: [0, 15, -15, 0] }}
              transition={{ duration: 2, repeat: Infinity, repeatDelay: 3 }}
            >
              <Download className="w-4 h-4" />
            </motion.div>
            Ready-to-use outputs
          </motion.div>
          
          <motion.h3 
            className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white mb-6"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.2, duration: 0.6 }}
          >
            Download what you{' '}
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              actually need
            </span>
          </motion.h3>
          
          <motion.p 
            className="text-xl text-gray-600 dark:text-gray-400 max-w-3xl mx-auto leading-relaxed"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: 0.4, duration: 0.6 }}
          >
            Get professional outputs you can use immediately—no copy-pasting, no reformatting, just results.
          </motion.p>
        </motion.div>

        {/* Enhanced Output Types Grid */}
        <motion.div
          className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6"
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true, margin: "0px" }}
        >
          {outputTypes.map((output, index) => (
            <motion.div
              key={output.name}
              variants={itemVariants}
              className="group relative"
            >
              <div className="relative h-full p-6 bg-white/80 dark:bg-gray-800/80 backdrop-blur rounded-2xl border border-gray-200 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600/50 shadow-sm hover:shadow-2xl transition-all duration-500 cursor-pointer hover:-translate-y-2">
                {/* Gradient Border Effect */}
                <div className={`absolute inset-0 rounded-2xl bg-gradient-to-r ${output.color} opacity-0 group-hover:opacity-10 transition-opacity duration-500 blur-lg`} />
                
                <div className="relative text-center">
                  {/* Simple animated icon */}
                  <div className="text-4xl mb-4 group-hover:scale-110 transition-transform duration-300">
                    {output.icon}
                  </div>
                  
                  {/* File extension badge */}
                  <div className={`inline-flex items-center justify-center px-3 py-1 bg-gradient-to-r ${output.color} text-white text-xs font-bold rounded-full mb-3`}>
                    {output.ext}
                  </div>
                  
                  {/* Title with clean hover effect */}
                  <h4 className="font-bold text-gray-900 dark:text-white mb-2 group-hover:text-transparent group-hover:bg-gradient-to-r group-hover:bg-clip-text group-hover:from-gray-900 group-hover:to-gray-600 dark:group-hover:from-white dark:group-hover:to-gray-300 transition-all duration-300">
                    {output.name}
                  </h4>
                  
                  <p className="text-xs text-gray-600 dark:text-gray-400">
                    {output.desc}
                  </p>
                </div>

                {/* Hover Glow Effect */}
                <div className={`absolute -inset-0.5 rounded-2xl bg-gradient-to-r ${output.color} opacity-0 group-hover:opacity-15 blur transition-opacity duration-500 -z-10`} />
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* Enhanced Bottom message */}
        <motion.div 
          className="text-center mt-12"
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "0px" }}
          transition={{ delay: 0.8, duration: 0.6 }}
        >
          <p className="text-lg text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            <span className="font-semibold text-blue-600 dark:text-blue-400">
              Ask once, get everything.
            </span>{' '}
            KarnAGT automatically generates multiple formats so you have exactly what you need.
          </p>
        </motion.div>
      </div>
    </motion.div>
  );
};
