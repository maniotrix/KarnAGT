import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0', // Allow access from any IP address on the network
    port: 3000,
    open: true
  },
  build: {
    outDir: 'build',
    sourcemap: false, // Disable source maps to hide source code
    // Remove console logs in production
    minify: 'esbuild',
    rollupOptions: {
      external: [],
      output: {
        // Better obfuscation of chunk names and exports
        entryFileNames: 'assets/[name].[hash].js',
        chunkFileNames: 'assets/[name].[hash].js',
        assetFileNames: 'assets/[name].[hash].[ext]',
        // Remove comments and make debugging harder
        compact: true,
      }
    }
  },
  esbuild: {
    // Remove console.log in production builds
    drop: process.env.NODE_ENV === 'production' ? ['console', 'debugger'] : [],
    // Enable top-level await and other modern features
    target: 'esnext',
    // Additional obfuscation
    legalComments: 'none',
  },
  resolve: {
    alias: {
      '@': '/src'
    }
  },
  define: {
    // Fallback for environment variables
    __DEV__: JSON.stringify(process.env.NODE_ENV !== 'production')
  }
}) 