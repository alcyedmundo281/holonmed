import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import { version } from './package.json';

export default defineConfig({
  plugins: [react()],
  // La versión se inyecta desde package.json: escribirla también en el
  // componente sería una copia condenada a desincronizarse.
  define: { __APP_VERSION__: JSON.stringify(version) },
  server: {
    port: 5173,
    proxy: {
      // Evita configurar CORS en desarrollo: el frontend llama a rutas
      // relativas y Vite las reenvía al backend.
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
});
