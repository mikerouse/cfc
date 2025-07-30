import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command }) => ({
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
    rollupOptions: {
      input: 'frontend/src/main.jsx',
    },
  },
}));
