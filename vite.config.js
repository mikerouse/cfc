import { defineConfig } from 'vite';

export default defineConfig(({ command }) => ({
  plugins: [],
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
