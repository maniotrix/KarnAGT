import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Zap, CheckCircle2, ArrowRight } from 'lucide-react';

interface Step {
  id: number;
  icon: React.ReactNode;
  title: string;
  description: string;
  details: string;
  gradient: string;
  example: string;
}

const steps: Step[] = [
  {
    id: 1,
    icon: <Search className="h-6 w-6" />,
    title: "Describe your goal",
    description: "Share what you need—drafts, summaries, analysis, plans, or calculations. No setup or model choice required.",
    details: "Simply type your request in natural language. KarnAGT understands context and nuance, so you don't need to use specific commands or formats.",
    gradient: "from-blue-500 to-cyan-500",
    example: "Analyze this sales report and create a summary with charts and recommendations for next quarter."
  },
  {
    id: 2,
    icon: <Zap className="h-6 w-6" />,
    title: "AI plans and executes",
    description: "KarnAGT reasons, searches the web, analyzes images, works with your files, and executes code—all in any language.",
    details: "Watch as KarnAGT breaks down complex tasks, uses multiple tools, and applies reasoning to deliver comprehensive solutions.",
    gradient: "from-yellow-500 to-orange-500",
    example: "I'll analyze your sales data, research market trends, and generate visualizations to support my recommendations."
  },
  {
    id: 3,
    icon: <CheckCircle2 className="h-6 w-6" />,
    title: "Get a polished result",
    description: "Receive clear, actionable output along with fresh generated files, you can use immediately—no busywork.",
    details: "Get professionally formatted results with citations, explanations, fresh generated files and next steps. Everything is ready to use or share.",
    gradient: "from-green-500 to-emerald-500",
    example: "Here's your Excel file with quarterly analysis, PNG charts, PDF report, and 5 growth recommendations ready to share."
  }
];

export const InteractiveSteps: React.FC = () => {
  const [activeStep, setActiveStep] = useState<number>(1);
  const [isAnimating, setIsAnimating] = useState<boolean>(false);

  const handleStepClick = (stepId: number) => {
    if (stepId !== activeStep && !isAnimating) {
      setIsAnimating(true);
      setActiveStep(stepId);
      setTimeout(() => setIsAnimating(false), 500);
    }
  };

  const nextStep = () => {
    const next = activeStep === 3 ? 1 : activeStep + 1;
    handleStepClick(next);
  };

  return (
    <div className="relative bg-gray-50 dark:bg-gray-900 py-20 overflow-hidden">
      {/* Background Pattern */}
      <div className="absolute inset-0">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#f0f0f0_1px,transparent_1px),linear-gradient(to_bottom,#f0f0f0_1px,transparent_1px)] dark:bg-[linear-gradient(to_right,#374151_1px,transparent_1px),linear-gradient(to_bottom,#374151_1px,transparent_1px)] bg-[size:2rem_2rem] opacity-30" />
        
        {/* Animated Gradient Orbs */}
        <motion.div
          className="absolute top-1/4 left-1/4 w-64 h-64 bg-blue-500/10 rounded-full blur-3xl"
          animate={{
            scale: [1, 1.3, 1],
            x: [0, 50, 0],
            y: [0, -30, 0],
          }}
          transition={{
            duration: 12,
            repeat: Infinity,
            ease: "easeInOut"
          }}
        />
        <motion.div
          className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl"
          animate={{
            scale: [1.2, 1, 1.2],
            x: [0, -30, 0],
            y: [0, 40, 0],
          }}
          transition={{
            duration: 15,
            repeat: Infinity,
            ease: "easeInOut"
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
          <h2 className="text-4xl sm:text-5xl font-bold text-gray-900 dark:text-white mb-6">
            Simple interface,{' '}
            <span className="bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
              powerful results
            </span>
          </h2>
          <p className="text-xl text-gray-600 dark:text-gray-400 max-w-2xl mx-auto">
            Describe what you need → Get professional deliverables. No complex software to learn.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          {/* Steps Navigation */}
          <div className="space-y-6">
            {steps.map((step, index) => (
              <motion.div
                key={step.id}
                className={`relative cursor-pointer transition-all duration-300 ${
                  activeStep === step.id ? 'scale-105' : 'hover:scale-102'
                }`}
                onClick={() => handleStepClick(step.id)}
                whileHover={{ x: 5 }}
              >
                {/* Connection Line */}
                {index < steps.length - 1 && (
                  <div className="absolute left-8 top-16 w-0.5 h-12 bg-gradient-to-b from-gray-300 to-transparent dark:from-gray-600 dark:to-transparent" />
                )}
                
                {/* Step Card */}
                <div className={`relative p-6 rounded-2xl border-2 transition-all duration-300 ${
                  activeStep === step.id
                    ? 'bg-white dark:bg-gray-800 border-blue-300 dark:border-blue-600'
                    : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                }`}>
                  
                  <div className="relative flex items-start gap-4">
                    {/* Step Number & Icon */}
                    <div className={`relative flex items-center justify-center w-16 h-16 rounded-2xl ${
                      activeStep === step.id
                        ? `bg-gradient-to-r ${step.gradient} text-white`
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'
                    }`}>
                      <div className="absolute -top-2 -right-2 flex items-center justify-center w-6 h-6 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-full text-xs font-bold">
                        {step.id}
                      </div>
                      {step.icon}
                    </div>
                    
                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <h3 className={`text-xl font-bold mb-2 transition-colors duration-300 ${
                        activeStep === step.id
                          ? 'text-gray-900 dark:text-white'
                          : 'text-gray-700 dark:text-gray-300'
                      }`}>
                        {step.title}
                      </h3>
                      <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">
                        {step.description}
                      </p>
                      
                      {/* Expanded Details */}
                      <AnimatePresence>
                        {activeStep === step.id && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            transition={{ duration: 0.3 }}
                            className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700"
                          >
                            <p className="text-gray-700 dark:text-gray-300 text-sm mb-3">
                              {step.details}
                            </p>
                            <div className="p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                              <p className="text-xs text-gray-600 dark:text-gray-400 italic">
                                "{step.example}"
                              </p>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                </div>
              </motion.div>
            ))}
          </div>

          {/* Interactive Demo Area */}
          <div className="relative">
            <div className="sticky top-8">
              {/* Demo Container */}
              <motion.div
                className="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-200 dark:border-gray-700 overflow-hidden"
                key={activeStep}
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.5 }}
              >
                {/* Demo Header */}
                <div className="flex items-center justify-between p-4 bg-gray-50 dark:bg-gray-700/50 border-b border-gray-200 dark:border-gray-600">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded-lg bg-gradient-to-r ${steps[activeStep - 1].gradient} text-white`}>
                      {steps[activeStep - 1].icon}
                    </div>
                    <div>
                      <h4 className="font-semibold text-gray-900 dark:text-white">
                        Step {activeStep}
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400">
                        {steps[activeStep - 1].title}
                      </p>
                    </div>
                  </div>
                  
                  {/* Auto-play Control */}
                  <button
                    onClick={nextStep}
                    className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg transition-colors"
                  >
                    <ArrowRight className="w-4 h-4" />
                    Next
                  </button>
                </div>
                
                {/* Demo Content */}
                <div className="p-6 min-h-[300px] flex items-center justify-center">
                  <motion.div
                    className="text-center"
                    initial={{ y: 20, opacity: 0 }}
                    animate={{ y: 0, opacity: 1 }}
                    transition={{ delay: 0.2 }}
                  >
                    <div className={`inline-flex items-center justify-center w-20 h-20 rounded-full bg-gradient-to-r ${steps[activeStep - 1].gradient} text-white mb-6`}>
                      <div className="h-10 w-10 flex items-center justify-center">
                        {steps[activeStep - 1].icon}
                      </div>
                    </div>
                    
                    <h3 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
                      {steps[activeStep - 1].title}
                    </h3>
                    
                    <p className="text-gray-600 dark:text-gray-400 max-w-sm mx-auto leading-relaxed">
                      {steps[activeStep - 1].details}
                    </p>
                    
                    {/* Example Quote */}
                    <motion.div
                      className="mt-6 p-4 bg-gradient-to-r from-gray-50 to-blue-50 dark:from-gray-700 dark:to-blue-900/20 rounded-xl border border-gray-200 dark:border-gray-600"
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      transition={{ delay: 0.5 }}
                    >
                      <p className="text-sm text-gray-700 dark:text-gray-300 italic">
                        "{steps[activeStep - 1].example}"
                      </p>
                    </motion.div>
                  </motion.div>
                </div>
              </motion.div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};