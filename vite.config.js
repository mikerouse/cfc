import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command }) => ({
  plugins: [react()],
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
      input: {
        main: 'src/main.jsx',
      },
    },
  },
}));
