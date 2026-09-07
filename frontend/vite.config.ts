import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// 开发代理：/api 与 /files 指向本地 FastAPI（默认 8000）
const BACKEND = process.env.VITE_PROXY || 'http://127.0.0.1:8000';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': BACKEND,
      '/files': BACKEND,
      '/health': BACKEND,
    },
  },
  build: {
    outDir: 'dist',
    target: 'es2019',
  },
});