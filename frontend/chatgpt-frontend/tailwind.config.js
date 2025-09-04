/** @type {import('tailwindcss').Config} */
export default {
    darkMode: ["class"],
    content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
  	extend: {
  		colors: {
  			chat: {
  				primary: '#10a37f',
  				'primary-hover': '#0f9171',
  				dark: '#343541',
  				darker: '#202123',
  				light: '#f7f7f8',
  				border: '#d1d5db',
  				user: '#f7f7f8',
  				assistant: '#ffffff'
  			},
  			background: 'hsl(var(--background))',
  			foreground: 'hsl(var(--foreground))',
  			card: {
  				DEFAULT: 'hsl(var(--card))',
  				foreground: 'hsl(var(--card-foreground))'
  			},
  			popover: {
  				DEFAULT: 'hsl(var(--popover))',
  				foreground: 'hsl(var(--popover-foreground))'
  			},
  			primary: {
  				DEFAULT: 'hsl(var(--primary))',
  				foreground: 'hsl(var(--primary-foreground))'
  			},
  			secondary: {
  				DEFAULT: 'hsl(var(--secondary))',
  				foreground: 'hsl(var(--secondary-foreground))'
  			},
  			muted: {
  				DEFAULT: 'hsl(var(--muted))',
  				foreground: 'hsl(var(--muted-foreground))'
  			},
  			accent: {
  				DEFAULT: 'hsl(var(--accent))',
  				foreground: 'hsl(var(--accent-foreground))'
  			},
  			destructive: {
  				DEFAULT: 'hsl(var(--destructive))',
  				foreground: 'hsl(var(--destructive-foreground))'
  			},
  			border: 'hsl(var(--border))',
  			input: 'hsl(var(--input))',
  			ring: 'hsl(var(--ring))',
  			chart: {
  				'1': 'hsl(var(--chart-1))',
  				'2': 'hsl(var(--chart-2))',
  				'3': 'hsl(var(--chart-3))',
  				'4': 'hsl(var(--chart-4))',
  				'5': 'hsl(var(--chart-5))'
  			}
  		},
  		fontFamily: {
  			sans: [
  				'Inter',
  				'system-ui',
  				'sans-serif'
  			]
  		},
  		animation: {
  			'fade-in': 'fadeIn 0.2s ease-in-out',
  			'slide-in': 'slideIn 0.3s ease-out',
  			typing: 'typing 1.5s infinite'
  		},
  		keyframes: {
  			fadeIn: {
  				'0%': {
  					opacity: '0'
  				},
  				'100%': {
  					opacity: '1'
  				}
  			},
  			slideIn: {
  				'0%': {
  					transform: 'translateY(10px)',
  					opacity: '0'
  				},
  				'100%': {
  					transform: 'translateY(0)',
  					opacity: '1'
  				}
  			},
  			typing: {
  				'0%, 100%': {
  					opacity: '1'
  				},
  				'50%': {
  					opacity: '0.5'
  				}
  			}
  		},
  		borderRadius: {
  			lg: 'var(--radius)',
  			md: 'calc(var(--radius) - 2px)',
  			sm: 'calc(var(--radius) - 4px)'
  		},
      typography: {
        DEFAULT: {
          css: {
            pre: null,
            code: null,
            'pre code': null,
          }
        }
      },
      fontSize: {
        // Existing Tailwind sizes remain unchanged
        ...require('tailwindcss/defaultTheme').fontSize,
        
        // 🎯 FLUID TYPOGRAPHY UTILITIES - Industry Standard 2024
        'fluid-xs': ['clamp(0.75rem, 1.5vw + 0.4rem, 0.875rem)', { lineHeight: '1.4' }],
        'fluid-sm': ['clamp(0.875rem, 2vw + 0.5rem, 1rem)', { lineHeight: '1.5' }],
        'fluid-base': ['clamp(1rem, 2.5vw + 0.5rem, 1.25rem)', { lineHeight: '1.6' }],
        'fluid-lg': ['clamp(1.125rem, 3vw + 0.5rem, 1.5rem)', { lineHeight: '1.6' }],
        'fluid-xl': ['clamp(1.25rem, 3.5vw + 0.75rem, 1.75rem)', { lineHeight: '1.4' }],
        'fluid-2xl': ['clamp(1.5rem, 4vw + 0.75rem, 2.25rem)', { lineHeight: '1.3' }],
        'fluid-3xl': ['clamp(1.75rem, 5vw + 1rem, 3rem)', { lineHeight: '1.2' }],
        
        // Chat-specific sizes
        'fluid-message': ['clamp(0.95rem, 2vw + 0.4rem, 1rem)', { lineHeight: '1.6' }],
        'fluid-ui': ['clamp(0.8rem, 1.5vw + 0.4rem, 0.9rem)', { lineHeight: '1.5' }],
      }
  	}
  },
  plugins: [
    require("tailwindcss-animate"),
    require('@tailwindcss/typography'),
  ],
} 