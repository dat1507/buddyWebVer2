import react from '@vitejs/plugin-react'
import { readFileSync } from 'node:fs'
import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'

const tlsCertificate = process.env.LOCAL_TLS_CERT_FILE?.trim()
const tlsPrivateKey = process.env.LOCAL_TLS_KEY_FILE?.trim()

if (Boolean(tlsCertificate) !== Boolean(tlsPrivateKey)) {
  throw new Error('Local TLS certificate and key must be configured together.')
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    allowedHosts: ['localhost', '127.0.0.1'],
    https:
      tlsCertificate && tlsPrivateKey
        ? {
            cert: readFileSync(tlsCertificate),
            key: readFileSync(tlsPrivateKey),
          }
        : undefined,
    proxy: {
      '/api': {
        target: process.env.LOCAL_API_PROXY_TARGET?.trim() || 'http://127.0.0.1:8000',
        changeOrigin: false,
        ws: true,
      },
    },
  },
})
