// Explicit localhost-only, anonymous UI review. Never loaded by application builds.
import { createServer } from 'vite'
import { fileURLToPath } from 'node:url'
const root = fileURLToPath(new URL('../', import.meta.url))
process.chdir(root)
const id = '11111111-1111-4111-8111-111111111111'
process.env.VITE_API_URL = '/api'
process.env.VITE_PUBLIC_EVENTS_ENABLED = 'true'
process.env.VITE_ADMIN_EVENTS_ENABLED = 'false'
process.env.VITE_EVENT_SLIDER_USE_MOCKS = 'false'
const server = await createServer({
  root,
  server: { host: '127.0.0.1', port: 5196, strictPort: true },
  plugins: [
    {
      name: 'anonymous-event-merch-review',
      configureServer(vite) {
        vite.middlewares.use('/api', (req, res) => {
          const url = new URL(req.url, 'http://127.0.0.1')
          const de = url.searchParams.get('locale') === 'de'
          const title = de ? 'Buddy Day – lokale Vorschau' : 'Buddy Day – local preview'
          let code = 200
          let body
          if (req.method !== 'GET') {
            code = 405
            body = { detail: 'Read-only local fixture' }
          } else if (url.pathname.startsWith('/auth/')) {
            code = 401
            body = { detail: 'Anonymous local review' }
          } else if (url.pathname === '/event-sliders')
            body = [
              {
                id,
                title,
                description: null,
                image_url: 'https://fixture.invalid/cover.webp',
                image_alt: title,
                event_start_at: '2027-01-10T08:00:00Z',
                event_end_at: '2027-01-10T10:00:00Z',
                location: 'VGU Campus',
                registration_url: null,
                registration_enabled: false,
                cta: { label: de ? 'Event ansehen' : 'View event', href: `/events/${id}` },
                sort_order: 0,
              },
            ]
          else if (url.pathname === `/events/${id}`)
            body = {
              id,
              locale: de ? 'de' : 'en',
              title,
              description: de
                ? 'Isolierte lokale Event-Vorschau. Keine Anmeldung oder echten Daten.'
                : 'Isolated local Event preview. No registration or real data.',
              start_date: '2027-01-10T08:00:00Z',
              end_date: '2027-01-10T10:00:00Z',
              timezone: 'Asia/Ho_Chi_Minh',
              location: 'VGU Campus',
              category: 'Community',
              organizer: 'VGU Buddy',
              registration_url: null,
              registration_enabled: false,
              registration_deadline: null,
              status: 'PUBLISHED',
              phase: 'UPCOMING',
              cover: null,
            }
          else {
            code = 404
            body = { detail: 'Local fixture not found' }
          }
          res.writeHead(code, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' })
          res.end(JSON.stringify(body))
        })
      },
    },
  ],
})
await server.listen()
console.log('Anonymous fixture review: http://127.0.0.1:5196 — no backend or real accounts')
for (const signal of ['SIGINT', 'SIGTERM'])
  process.on(signal, async () => {
    await server.close()
    process.exit(0)
  })
