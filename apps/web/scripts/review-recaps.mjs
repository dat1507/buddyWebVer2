// Explicit opt-in local review. This file is never imported by application builds.
import { createServer } from 'vite'
import { fileURLToPath } from 'node:url'
const root = fileURLToPath(new URL('../', import.meta.url))
const port = Number(process.env.RECAP_REVIEW_PORT || '5197')
const apiPort = Number(process.env.RECAP_REVIEW_API_PORT || '8043')
if (![5197, 5198, 5199].includes(port) || ![8043, 8044, 8045].includes(apiPort))
  throw new Error('Review ports must be approved loopback ports')
const apiTarget = `http://127.0.0.1:${apiPort}`
process.env.VITE_API_URL = '/api'
process.env.VITE_PUBLIC_EVENTS_ENABLED = 'true'
process.env.VITE_ADMIN_EVENTS_ENABLED = 'true'
process.env.VITE_EVENT_SLIDER_USE_MOCKS = 'false'
process.env.LOCAL_API_PROXY_TARGET = apiTarget
const tlsRoot = fileURLToPath(new URL('../../../../../tls/', import.meta.url))
process.env.LOCAL_TLS_CERT_FILE ||= `${tlsRoot}localhost.crt`
process.env.LOCAL_TLS_KEY_FILE ||= `${tlsRoot}localhost-key.pem`
const server = await createServer({
  root,
  server: {
    host: '127.0.0.1',
    port,
    strictPort: true,
    proxy: {
      '/api': { target: apiTarget, changeOrigin: false },
      '/storage/v1': { target: 'http://127.0.0.1:54321', changeOrigin: true },
    },
  },
})
await server.listen()
console.log(`Local Recap review: https://127.0.0.1:${port}/events/recap`)
for (const signal of ['SIGINT', 'SIGTERM'])
  process.on(signal, async () => {
    await server.close()
    process.exit(0)
  })
