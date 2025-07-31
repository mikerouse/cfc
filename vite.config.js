import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command }) => {
  const isDevelopment = process.env.NODE_ENV !== 'production';
  
  return {
    plugins: [
      react({
        include: "**/*.{jsx,tsx}",
        fastRefresh: false
      })
    ],
    server: {
      port: 5173,
      host: true,
      strictPort: true
    },
    esbuild: {
      jsx: 'automatic',
      jsxImportSource: 'react'
    },
    root: 'frontend',
    base: command === 'serve' ? '/' : '/static/frontend/',
    build: {
      outDir: '../static/frontend',
      assetsDir: '',
      manifest: true,
      emptyOutDir: true,
      rollupOptions: {
        input: 'frontend/src/main.jsx',
        output: {
          // Use stable filenames without hash in development
          entryFileNames: isDevelopment ? 'main.js' : 'main-[hash].js',
          chunkFileNames: isDevelopment ? '[name].js' : '[name]-[hash].js',
          assetFileNames: isDevelopment ? '[name][extname]' : '[name]-[hash][extname]'
        }
      },
    },
  };
});
