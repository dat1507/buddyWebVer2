// Explicit opt-in local review. This file is never imported by application builds.
import { createServer } from 'vite'
import { fileURLToPath } from 'node:url'
const root = fileURLToPath(new URL('../', import.meta.url))
process.env.VITE_API_URL = '/api'
process.env.VITE_PUBLIC_EVENTS_ENABLED = 'true'
process.env.VITE_ADMIN_EVENTS_ENABLED = 'true'
process.env.VITE_EVENT_SLIDER_USE_MOCKS = 'false'
process.env.LOCAL_API_PROXY_TARGET = 'http://127.0.0.1:8043'
const tlsRoot = fileURLToPath(new URL('../../../../../tls/', import.meta.url))
process.env.LOCAL_TLS_CERT_FILE ||= `${tlsRoot}localhost.crt`
process.env.LOCAL_TLS_KEY_FILE ||= `${tlsRoot}localhost-key.pem`
const server = await createServer({
  root,
  server: {
    host: '127.0.0.1',
    port: 5197,
    strictPort: true,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8043', changeOrigin: false },
      '/storage/v1': { target: 'http://127.0.0.1:54321', changeOrigin: true },
    },
  },
})
await server.listen()
console.log('Local Recap review: https://127.0.0.1:5197/events/recap')
for (const signal of ['SIGINT', 'SIGTERM'])
  process.on(signal, async () => {
    await server.close()
    process.exit(0)
  })
