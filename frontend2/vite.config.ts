import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.')

  return {
    plugins: [react()],
    server: {
      host: true,
      proxy: {
        '/user-api': {
          target: env.VITE_USER_API_URL ?? 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/user-api/, ''),
        },
        '/agg-api': {
          target: env.VITE_AGGREGATION_API_URL ?? 'http://localhost:8001',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/agg-api/, ''),
        },
      },
    },
  }
})