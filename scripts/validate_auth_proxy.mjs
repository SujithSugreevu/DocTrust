import assert from 'node:assert/strict'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const read = (relativePath) => fs.readFileSync(path.join(projectRoot, relativePath), 'utf8')

const vercelConfig = JSON.parse(read('vercel.json'))
const rewrites = vercelConfig.rewrites ?? []
const apiRewriteIndex = rewrites.findIndex((rewrite) => rewrite.source === '/api/:path*')
const spaRewriteIndex = rewrites.findIndex((rewrite) => rewrite.source === '/(.*)')

assert.notEqual(apiRewriteIndex, -1, 'Vercel must proxy /api/:path* to Render')
assert.equal(
  rewrites[apiRewriteIndex].destination,
  'https://doctrust-backend.onrender.com/api/:path*',
  'Vercel API rewrite destination must remain the Django API',
)
assert.ok(
  spaRewriteIndex === -1 || apiRewriteIndex < spaRewriteIndex,
  'The API rewrite must precede the SPA catch-all rewrite',
)

const apiSource = read('src/services/api.js')
const authSource = read('src/services/auth.js')

assert.match(apiSource, /return normalizedPath/)
assert.doesNotMatch(apiSource, /https:\/\/doctrust-backend\.onrender\.com/)
assert.doesNotMatch(authSource, /https:\/\/doctrust-backend\.onrender\.com/)
assert.match(authSource, /\/api\/auth\/csrf\//)
assert.match(authSource, /\/api\/auth\/login\//)
assert.ok(authSource.includes('credentials'))
assert.match(authSource, /X-CSRFToken/)

console.log('Auth proxy configuration is valid: relative browser paths, ordered Vercel API rewrite, credentials, and CSRF header.')
