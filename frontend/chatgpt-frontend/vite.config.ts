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
    sourcemap: true,
    // Remove console logs in production
    minify: 'esbuild',
    rollupOptions: {
      external: [],
    }
  },
  esbuild: {
    // Remove console.log in production builds
    drop: process.env.NODE_ENV === 'production' ? ['console', 'debugger'] : [],
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