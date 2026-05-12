import React from 'react';

interface LogoProps {
  className?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl';
  variant?: 'icon' | 'full';
  withBackground?: boolean;
  backgroundVariant?: 'light' | 'dark' | 'theme';
}

const Logo: React.FC<LogoProps> = ({ 
  className = '', 
  size = 'md',
  variant = 'icon',
  withBackground = true,
  backgroundVariant = 'theme'
}) => {
  // Responsive logo size classes with mobile-first approach
  const logoSizeClasses = {
    xs: 'w-3 h-3 sm:w-4 sm:h-4',
    sm: 'w-4 h-4 sm:w-5 sm:h-5',
    md: 'w-5 h-5 sm:w-6 sm:h-6', 
    lg: 'w-6 h-6 sm:w-8 sm:h-8 md:w-10 md:h-10',
    xl: 'w-8 h-8 sm:w-10 sm:h-10 md:w-12 md:h-12',
    '2xl': 'w-10 h-10 sm:w-12 sm:h-12 md:w-16 md:h-16'
  };

  // Responsive container size classes for circular backgrounds
  const containerSizeClasses = {
    xs: 'w-6 h-6 sm:w-8 sm:h-8',
    sm: 'w-8 h-8 sm:w-10 sm:h-10',
    md: 'w-10 h-10 sm:w-12 sm:h-12',
    lg: 'w-12 h-12 sm:w-16 sm:h-16 md:w-20 md:h-20',
    xl: 'w-16 h-16 sm:w-20 sm:h-20 md:w-24 md:h-24',
    '2xl': 'w-20 h-20 sm:w-24 sm:h-24 md:w-32 md:h-32'
  };

  // Background variants with white background and blue border
  const backgroundClasses = {
    light: 'bg-white border-blue-200',
    dark: 'bg-white border-blue-200',
    theme: 'bg-white border-blue-200'
  };

  const logoImageClassName = `${logoSizeClasses[size]} object-contain`;
  
  const renderLogo = () => (
    <img
      src="/logo192.png"
      alt="KarnAGT Logo"
      className={logoImageClassName}
      style={{ objectFit: 'contain' }}
    />
  );

  if (variant === 'icon') {
    if (withBackground) {
      return (
        <div className={`
          ${containerSizeClasses[size]} 
          rounded-full 
          border-2 
          ${backgroundClasses[backgroundVariant]}
          flex items-center justify-center 
          transition-all duration-200 
          ${size === '2xl' || size === 'xl' ? 'hover:shadow-lg' : 'hover:shadow-md'} 
          hover:scale-105
          ${className}
        `}>
          {renderLogo()}
        </div>
      );
    }
    
    return (
      <div className={className}>
        {renderLogo()}
      </div>
    );
  }

  // For full variant with text - responsive text sizing
  const textSizeClasses = {
    xs: 'text-xs sm:text-sm',
    sm: 'text-sm sm:text-base',
    md: 'text-base sm:text-lg',
    lg: 'text-lg sm:text-xl md:text-2xl',
    xl: 'text-xl sm:text-2xl md:text-3xl',
    '2xl': 'text-2xl sm:text-3xl md:text-4xl'
  };

  return (
    <div className={`flex items-center space-x-2 sm:space-x-3 ${className}`}>
      {withBackground ? (
        <div className={`
          ${containerSizeClasses[size]} 
          rounded-full 
          border-2 
          ${backgroundClasses[backgroundVariant]}
          flex items-center justify-center 
          transition-all duration-200 
          ${size === '2xl' || size === 'xl' ? 'hover:shadow-lg' : 'hover:shadow-md'}
          hover:scale-105
        `}>
          {renderLogo()}
        </div>
      ) : (
        renderLogo()
      )}
      <span className={`font-semibold text-gray-900 dark:text-white ${textSizeClasses[size]}`}>
        KarnAGT
      </span>
    </div>
  );
};

export default Logo;
