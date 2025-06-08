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
    sourcemap: true
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