import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  root: 'frontend',
  base: '/static/frontend/',
  build: {
    outDir: '../static/frontend',
    assetsDir: '',
    manifest: true,
    rollupOptions: {
      input: {
        main: 'frontend/src/main.jsx',
      },
    },
  },
});
