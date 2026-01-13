import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
  },
  preview: {
    host: '0.0.0.0',
    port: 3000, // Port será sobrescrita pela variável $PORT no comando
    allowedHosts: [
      'deadlytruth-production.up.railway.app',
      '.railway.app', // Permite todos os subdomínios do Railway
      'localhost',
    ],
  },
})
