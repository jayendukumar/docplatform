import { test, expect } from '@playwright/test'

test('workspace loads a persisted sample and exposes its data', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Good documents start here.' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Welcome letter' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Workspace status' })).toBeVisible()
  await page.getByRole('button', { name: 'Explore template' }).click()
  await expect(page.getByRole('heading', { name: 'Sample data' })).toBeVisible()
  await expect(page.locator('pre')).toContainText('Alex')
  await page.getByRole('button', { name: 'Back to templates' }).click()
  await expect(page.getByRole('button', { name: 'Explore template' })).toBeVisible()
})

test('workspace fits a narrow screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.getByRole('button', { name: 'Explore template' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})
