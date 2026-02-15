import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  
  const useHttps = env.VITE_USE_HTTPS === 'true'
  const apiUrl = env.VITE_API_URL
  
  // Paths to SSL certificates (change if needed)
  const certPath = path.resolve(__dirname, 'localhost-cert.pem')
  const keyPath = path.resolve(__dirname, 'localhost-key.pem')
  
  const serverConfig = {
    proxy: {
      '/auth': {
        target: apiUrl,
        secure: false,
        changeOrigin: true
      },
      '/me': {
        target: apiUrl,
        secure: false,
        changeOrigin: true
      },
      '/search': {
        target: apiUrl,
        secure: false,
        changeOrigin: true
      },
      '/video': {
        target: apiUrl,
        secure: false,
        changeOrigin: true
      }
    }
  }
  
  // Only add HTTPS if enabled and cert files exist
  if (useHttps && fs.existsSync(certPath) && fs.existsSync(keyPath)) {
    serverConfig.https = {
      key: fs.readFileSync(keyPath),
      cert: fs.readFileSync(certPath),
    }
  }
  
  return {
    plugins: [
      react({
        babel: {
          plugins: [['babel-plugin-react-compiler']],
        },
      }),
    ],
    server: serverConfig
  }
})