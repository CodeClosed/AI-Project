import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';

// https://vitejs.dev/config/
export default defineConfig({
  base: './',
  plugins: [
    react(),
    {
      name: 'copy-404',
      closeBundle() {
        try {
          const indexPath = path.resolve(__dirname, 'dist', 'index.html');
          const notFoundPath = path.resolve(__dirname, 'dist', '404.html');
          if (fs.existsSync(indexPath)) {
            fs.copyFileSync(indexPath, notFoundPath);
          }
        } catch (e) {
          console.warn('Could not copy 404.html:', e);
        }
      },
    },
  ],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
