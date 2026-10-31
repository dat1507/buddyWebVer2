import { readdir, readFile } from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const dist = fileURLToPath(new URL('../dist/', import.meta.url))
const markers = [
  'demo@buddyweb.local',
  'Demo Student',
  'buddyweb-local-ui-demo-v1',
  '/__demo',
  'Enter Demo as Student',
  'synthetic-local-csrf-only',
  'LOCAL_DEMO_NO_REALTIME',
  '.demo-toolbar',
  '.demo-entry',
  'Campus Welcome Walk',
]
let scanned = 0
const failures = []
async function inspect(directory) {
  for (const entry of await readdir(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name)
    if (entry.isDirectory()) await inspect(file)
    else if (/\.(js|css|html|json|map)$/.test(entry.name)) {
      scanned++
      const content = await readFile(file, 'utf8')
      for (const marker of markers)
        if (content.includes(marker)) failures.push({ file: path.relative(dist, file), marker })
    }
  }
}
await inspect(dist)
if (!scanned || failures.length)
  throw new Error(`Production demo exclusion FAILED: ${JSON.stringify(failures)}`)
console.log(
  `Production demo exclusion PASS: ${scanned} build files; ${markers.length} forbidden demo markers absent.`,
)
