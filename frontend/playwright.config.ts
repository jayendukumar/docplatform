import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  use: { baseURL: process.env.PLATFORM_TEST_URL || 'http://127.0.0.1:8000', browserName: 'chromium' },
})
