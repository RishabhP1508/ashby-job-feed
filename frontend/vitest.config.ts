import { defineConfig } from 'vitest/config'

// jsdom because lib/url.ts reads window.location and calls history.replaceState.
export default defineConfig({
  test: { environment: 'jsdom' },
})
