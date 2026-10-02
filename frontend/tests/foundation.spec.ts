import { test, expect } from '@playwright/test'
import { inflateSync } from 'node:zlib'

function assertCenteredImagePdf(pdfBase64: string) {
  const pdf = Buffer.from(pdfBase64, 'base64').toString('latin1')
  const streams = [...pdf.matchAll(/stream\r?\n([\s\S]*?)\r?\nendstream/g)].flatMap(match => {
    try { return [inflateSync(Buffer.from(match[1], 'latin1')).toString('latin1')] } catch { return [] }
  })
  const content = streams.find(stream => /\/\w+ Do/.test(stream) && stream.includes(' cm'))
  expect(content).toBeTruthy()
  const clip = content?.match(/([\d.]+) ([\d.]+) ([\d.]+) ([\d.]+) re\s+W\* n/)
  const image = content?.match(/([\d.]+) 0 0 -([\d.]+) ([\d.]+) ([\d.]+) cm\s+0 0 0 RG/)
  expect(clip).toBeTruthy()
  expect(image).toBeTruthy()
  const expectedX = Number(clip?.[1]) + (Number(clip?.[3]) - Number(image?.[1])) / 2
  expect(Math.abs(Number(image?.[3]) - expectedX)).toBeLessThan(3)
}

test('workspace loads a persisted sample and exposes its data', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Good documents start here.' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Welcome letter' })).toBeVisible()
  await expect(page.getByRole('heading', { name: 'Workspace status' })).toBeVisible()
  const overview = page.locator('.workspace-status-row')
  await expect(overview.locator('.status-panel')).toBeVisible()
  await expect(overview.locator('.project-status-banner')).toBeVisible()
  expect(await page.locator('.workspace-status-row > *').first().getAttribute('class')).toContain('status-panel')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  await expect(page.getByRole('heading', { name: 'Sample data' })).toBeVisible()
  await expect(page.locator('pre')).toContainText('Alex')
  await page.getByRole('button', { name: 'Back to templates' }).click()
  await expect(page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) }).getByRole('button', { name: 'Explore template' })).toBeVisible()
})

test('workspace fits a narrow screen', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) }).getByRole('button', { name: 'Explore template' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})

test('project status lists every source story with evidence-backed status', async ({ page }) => {
  await page.goto('/')
  await page.getByRole('link', { name: 'View project status' }).click()
  await expect(page.getByRole('heading', { name: 'Project status' })).toBeVisible()
  const statusTable = page.locator('table.story-table')
  await expect(statusTable).toContainText('E1-01')
  await expect(statusTable).toContainText('E15-05')
  await expect(statusTable.locator('tr').filter({ hasText: 'E1-01' }).getByText('Implemented')).toBeVisible()
  await expect(statusTable.locator('tr').filter({ hasText: 'E2-01' }).getByText('Implemented')).toBeVisible()
  await expect(statusTable.locator('tr').filter({ hasText: 'E2-05' }).getByText('Implemented')).toBeVisible()
  await expect(statusTable.locator('tr').filter({ hasText: 'E2-06' }).getByText('Implemented')).toBeVisible()
  await expect(statusTable.locator('tr').filter({ hasText: 'E11-03' }).getByText('Implemented')).toBeVisible()
  await expect(statusTable.locator('tr').filter({ hasText: 'E13-01' }).getByText('Planned')).toBeVisible()
  await expect(page.locator('.overall-status')).toContainText('%')
})

test('multilingual starter gallery launches a language-specific draft', async ({ page }) => {
  await page.goto('/')
  const gallery = page.locator('.starter-gallery')
  await expect(gallery.getByRole('heading', { name: 'Multilingual starters' })).toBeVisible()
  const invoice = gallery.locator('.starter-card').filter({ hasText: 'Invoice' })
  await expect(invoice.getByRole('button', { name: /Use starter.*ja/ })).toBeVisible()
  await invoice.getByRole('button', { name: /Use starter.*ja/ }).click()
  await expect(page.locator('article.detail').getByRole('heading', { name: 'Invoice (ja)' })).toBeVisible()
})

test('editor saves a formatted draft and renders a server preview', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await expect(page.locator('.workspace-grid-selected')).toBeVisible()
  await expect(page.locator('.workspace-grid-selected .editor-page')).toBeVisible()
  const pageSettingsToggle = page.getByRole('button', { name: /Page settings/ })
  await expect(page.locator('#page-settings-panel')).toHaveCount(0)
  await pageSettingsToggle.click()
  await expect(page.locator('#page-settings-panel')).toBeVisible()
  await expect(page.getByLabel('Top margin')).toBeVisible()
  await expect(page.getByLabel('Right margin')).toBeVisible()
  await expect(page.getByLabel('Bottom margin')).toBeVisible()
  await expect(page.getByLabel('Left margin')).toBeVisible()
  await expect(page.getByLabel('Document title')).toHaveCount(0)
  await expect(page.getByLabel('Document author')).toHaveCount(0)
  await pageSettingsToggle.click()
  await expect(page.locator('#page-settings-panel')).toHaveCount(0)
  expect(await page.locator('.workspace-grid-selected').evaluate(element => getComputedStyle(element).gridTemplateColumns.split(' ').length)).toBe(1)
  const blockListBox = await page.locator('.workspace-grid-selected .editor-block-list').boundingBox()
  const previewBox = await page.locator('.workspace-grid-selected .editor-page').boundingBox()
  expect(previewBox?.width || 0).toBeGreaterThan(blockListBox?.width || 0)
  const previewViewport = page.locator('.editor-page-viewport')
  await expect(previewViewport).toHaveAttribute('tabindex', '0')
  expect(await previewViewport.evaluate(element => element.scrollWidth)).toBeGreaterThan(await previewViewport.evaluate(element => element.clientWidth))
  expect(await page.locator('.editor-page').evaluate(element => getComputedStyle(element).fontSize)).toBe('16px')
  await page.locator('.structure-node').first().click()
  const bold = page.locator('.editor-toolbar').getByRole('button', { name: 'Bold' })
  if (await bold.getAttribute('aria-pressed') !== 'true') await bold.click()
  await page.getByLabel('Text colour').fill('#a52a2a')
  await page.locator('.editor-toolbar select').first().selectOption('Georgia')
  await page.locator('.editor-toolbar input[type="number"]').fill('24')
  await page.getByLabel('Alignment').selectOption('center')
  const localPreview = page.locator('.editor-page p').first()
  await expect(localPreview).toHaveCSS('font-family', /Georgia/)
  await expect(localPreview).toHaveCSS('font-size', '24px')
  await expect(localPreview).toHaveCSS('font-weight', '700')
  await expect(localPreview).toHaveCSS('text-align', 'center')
  await page.locator('.editor-command-bar').getByRole('button', { name: 'Save draft' }).click()
  await expect(page.locator('p.editor-feedback')).toContainText('server preview rendered', { timeout: 15000 })
  await expect(page.locator('iframe[title="Server preview"]')).toBeVisible()
  await expect(page.locator('.render-diagnostics')).toContainText('deterministic-html-0.1')
  await expect(page.locator('.render-diagnostics')).toContainText('latin')
  const serverPreview = page.frameLocator('iframe[title="Server preview"]')
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /font-family:Georgia/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /font-size:24px/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /font-weight:700/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /text-align:center/)
})

test('text boxes expose bounded Word-like layout controls and persist them to server preview', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.locator('.structure-node').first().click()
  const layout = page.getByRole('complementary', { name: 'Text layout' })
  await expect(layout).toBeVisible()
  await layout.getByLabel('Line spacing').fill('1.8')
  await layout.getByLabel('Paragraph spacing after').fill('12')
  await layout.getByLabel('First-line indent').fill('18')
  await layout.getByLabel('Tab stops').fill('64, 500r.')
  await layout.getByLabel('Tab stops').blur()
  await page.getByRole('spinbutton', { name: 'Size', exact: true }).fill('13.28')
  await page.getByRole('button', { name: 'Justify' }).click()
  await layout.getByLabel('Keep with next').check()
  const position = page.getByRole('complementary', { name: 'Text position' })
  await position.getByLabel('Place at fixed page coordinates').check()
  await position.getByLabel('Position unit').selectOption('mm')
  await position.getByLabel('Position X').fill('120')
  await position.getByLabel('Position Y').fill('240')
  await page.getByRole('complementary', { name: 'Page placement' }).getByLabel('Page number').fill('3')
  const navigator = page.locator('.preview-page-navigator')
  await expect(navigator).toBeVisible()
  await expect(navigator.getByLabel('Preview page', { exact: true })).toHaveValue('1')
  await navigator.getByLabel('Next preview page').click()
  await expect(navigator.getByLabel('Preview page', { exact: true })).toHaveValue('2')
  await page.locator('.editor-command-bar').getByRole('button', { name: 'Save draft' }).click()
  await expect(page.locator('p.editor-feedback')).toContainText('server preview rendered', { timeout: 15000 })
  const serverPreview = page.frameLocator('iframe[title="Server preview"]')
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /line-height:1.8/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /margin-bottom:12px/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /text-indent:18px/)
  await expect(serverPreview.locator('p').first()).not.toHaveAttribute('style', /tab-size/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /font-size:13.28px/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /text-align:justify/)
  await expect(layout.getByLabel('Tab stops')).toHaveValue('64, 500r.')
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /break-after:avoid/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /position:absolute/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /left:120mm/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /top:240mm/)
  await expect(serverPreview.locator('p').first()).toHaveAttribute('style', /break-before:page/)
})

test('schema fields can be inserted as meaningful bound text objects', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  const binding = page.getByRole('complementary', { name: 'Data binding' })
  const schemaInput = binding.locator('input[type="file"][accept="application/json,.json"]')
  await schemaInput.setInputFiles({ name: 'isda-fields.json', mimeType: 'application/json', buffer: Buffer.from(JSON.stringify({ type: 'object', properties: { agreement_date: { title: 'Agreement date', type: 'string', format: 'date' }, party_a: { title: 'Party A', type: 'string' } } })) })
  await expect(binding.getByLabel('Schema field')).toHaveValue('agreement_date')
  const bindingInfo = page.getByRole('complementary', { name: 'Selected schema field' })
  await expect(bindingInfo).toContainText('Agreement date')
  await expect(bindingInfo).toContainText('Type: string · Format: date')
  await binding.getByRole('button', { name: 'Insert field' }).click()
  await expect(page.locator('.structure-node').last()).toContainText('{{agreement_date}}')
  await expect(page.locator('.structure-node-kind').last()).toHaveText('text')
})

test('editor exposes contextual actions for a selected image', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await expect(page.locator('.editor-command-bar')).toBeVisible()
  await expect(page.locator('.editor-left-panel')).toBeVisible()
  const contextual = page.getByRole('complementary', { name: 'Contextual actions' })
  await expect(contextual).toBeVisible()
  await page.locator('.editor-left-panel').getByRole('button', { name: 'Add image or logo' }).click()
  await expect(contextual).toContainText('Image')
  await expect(contextual.getByRole('button', { name: 'Align left' })).toBeEnabled()
  await expect(contextual.getByRole('button', { name: 'Align center' })).toBeEnabled()
  await expect(contextual.getByRole('button', { name: 'Move left' })).toBeEnabled()
  await expect(contextual.getByRole('button', { name: 'Bold' })).toBeDisabled()
  await expect(contextual.getByRole('button', { name: 'Delete selected block' })).toBeEnabled()
  const imageActions = page.getByRole('complementary', { name: 'Image controls' })
  await imageActions.getByRole('button', { name: 'Make image bigger' }).click()
  await expect(imageActions.getByLabel('Width')).toHaveValue('256')
  await imageActions.getByRole('button', { name: 'Move down' }).click()
  await page.getByRole('button', { name: 'Move right' }).click()
  await expect(page.locator('.editor-page figure').first()).toHaveCSS('transform', /matrix\(1, 0, 0, 1, 8, 8\)/)
})

test('editor generates and displays a PDF from the current template', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await expect(page.locator('article.detail')).toBeVisible()
  const pdfResponse = page.waitForResponse(response => response.url().includes('/render-pdf') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Generate PDF' }).click()
  await expect((await pdfResponse).status()).toBe(200)
  await expect(page.getByRole('status').filter({ hasText: 'PDF generated' })).toBeVisible({ timeout: 15000 })
  await expect(page.locator('iframe[title="Generated PDF"]')).toBeVisible()
  await expect(page.getByRole('link', { name: 'Download PDF' })).toHaveAttribute('href', /^blob:/)
})

test('editor persists bounded chart, TOC, theme, and background controls', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.locator('.editor-left-panel').getByRole('button', { name: 'Add chart' }).click()
  const chartActions = page.locator('.chart-contextual-panel')
  await expect(chartActions.getByLabel('Chart type')).toBeVisible()
  await chartActions.getByLabel('Chart type').selectOption('line')
  await expect(page.locator('.editor-chart-line')).toBeVisible()
  await chartActions.getByLabel('Chart type').selectOption('pie')
  await expect(page.locator('.editor-chart-pie')).toBeVisible()
  await chartActions.getByLabel('Chart type').selectOption('line')
  await chartActions.getByLabel('Title').fill('Monthly revenue')
  await chartActions.getByLabel('Show points').uncheck()
  await expect(chartActions.getByLabel('Series 1 colour')).toBeVisible()
  await chartActions.getByLabel('Series 1 colour').fill('#112233')
  await chartActions.getByLabel('Data source').selectOption('static')
  await chartActions.getByLabel('Array path').fill('chart_rows')
  await page.getByRole('button', { name: 'Add table of contents' }).click()
  await page.getByRole('button', { name: /Page settings/ }).click()
  await page.getByLabel('Theme accent').fill('#123456')
  await page.getByLabel('Theme font').selectOption('Georgia')
  await page.getByLabel('Theme spacing').fill('1.8')
  await page.getByLabel('Page background', { exact: true }).setInputFiles({ name: 'background.png', mimeType: 'image/png', buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64') })
  const saveRequest = page.waitForRequest(request => request.url().includes('/versions') && request.method() === 'POST')
  await page.locator('.editor-command-bar').getByRole('button', { name: 'Save draft' }).click()
  const payload = (await saveRequest).postDataJSON() as { definition?: { theme?: { accent?: string; font_family?: string; spacing?: string }; page?: { background?: string }; blocks?: Array<{ type?: string; chart_type?: string; chart_title?: string; show_points?: boolean }> } }
  expect(payload.definition?.theme?.accent).toBe('#123456')
  expect(payload.definition?.theme?.font_family).toBe('Georgia')
  expect(payload.definition?.theme?.spacing).toBe('1.8')
  expect(payload.definition?.page?.background).toMatch(/^data:image\/png;base64,/)
  expect(payload.definition?.blocks?.some(block => block.type === 'chart')).toBeTruthy()
  expect(payload.definition?.blocks?.some(block => block.type === 'chart' && block.chart_type === 'line' && block.chart_title === 'Monthly revenue' && block.show_points === false)).toBeTruthy()
  expect(payload.definition?.blocks?.some(block => block.type === 'toc')).toBeTruthy()
  await expect(page.locator('p.editor-feedback')).toContainText('server preview rendered', { timeout: 15000 })
  await expect(page.frameLocator('iframe[title="Server preview"]').locator('figure.template-chart polyline')).toHaveCount(1)
  await expect(page.frameLocator('iframe[title="Server preview"]').locator('nav.template-toc')).toHaveCount(1)
  const previewCss = await page.frameLocator('iframe[title="Server preview"]').locator('style').first().textContent()
  expect(previewCss).toContain('--theme-font-family:Georgia')
  expect(previewCss).toContain('--theme-spacing:1.8')
  const pdfResponse = page.waitForResponse(response => response.url().includes('/render-pdf') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Generate PDF' }).click()
  const pdfBody = await (await pdfResponse).json() as { document_base64?: string; report?: { status?: string } }
  expect(pdfBody.document_base64).toMatch(/^JVBERi0/)
  expect(pdfBody.report?.status).toBeTruthy()
  await expect(page.locator('iframe[title="Generated PDF"]')).toBeVisible()
})

test('editor authors rich text with data fields and conditions in the contextual palette', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.locator('.editor-left-panel').getByRole('button', { name: 'Add text block' }).click()
  const panel = page.locator('.rich-text-contextual-panel')
  await expect(panel).toBeVisible()
  await panel.getByLabel('Text content').fill('Amount: ')
  await panel.getByRole('button', { name: 'Insert data field' }).click()
  await panel.getByLabel('Data path').fill('amount')
  await panel.getByLabel('Data format').selectOption('currency')
  await panel.getByLabel('Currency code').fill('CNY')
  await panel.getByRole('button', { name: 'Insert condition' }).click()
  await panel.getByLabel('Condition path').fill('value_x')
  await panel.getByLabel('Condition value').fill('a')
  await panel.getByLabel('Then text').fill(' approved')
  await expect(panel.getByRole('button', { name: /\{\{amount\}\}/ })).toBeVisible()
  await expect(panel.getByRole('button', { name: 'Condition', exact: true })).toBeVisible()
  await page.locator('.editor-command-bar').getByRole('button', { name: 'Save draft' }).click()
  await expect(page.locator('p.editor-feedback')).toContainText('server preview rendered', { timeout: 15000 })
  await expect(page.frameLocator('iframe[title="Server preview"]').locator('.rich-text-block')).toHaveCount(1)
})

test('editor applies a locked PDF page background in generated output', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await expect(page.getByRole('button', { name: 'Add locked PDF background' })).toBeVisible()
  await page.getByLabel('Locked PDF page background').setInputFiles({
    name: 'background.pdf', mimeType: 'application/pdf',
    buffer: Buffer.from('JVBERi0xLjMKJeLjz9MKMSAwIG9iago8PAovUHJvZHVjZXIgKHB5cGRmKQo+PgplbmRvYmoKMiAwIG9iago8PAovVHlwZSAvUGFnZXMKL0NvdW50IDEKL0tpZHMgWyA0IDAgUiBdCj4+CmVuZG9iagozIDAgb2JqCjw8Ci9UeXBlIC9DYXRhbG9nCi9QYWdlcyAyIDAgUgo+PgplbmRvYmoKNCAwIG9iago8PAovVHlwZSAvUGFnZQovUmVzb3VyY2VzIDw8Cj4+Ci9NZWRpYUJveCBbIDAuMCAwLjAgNjEyIDc5MiBdCi9QYXJlbnQgMiAwIFIKPj4KZW5kb2JqCnhyZWYKMCA1CjAwMDAwMDAwMDAgNjU1MzUgZiAKMDAwMDAwMDE1IDAwMDAwIG4gCjAwMDAwMDA1NCAwMDAwMCBuIAowMDAwMDAxMTMgMDAwMDAgbiAKMDAwMDAwMDE2MiAwMDAwMCBuIAp0cmFpbGVyCjw8Ci9TaXplIDUKL1Jvb3QgMyAwIFIKL0luZm8gMSAwIFIKPj4Kc3RhcnR4cmVmCjI1NgolJUVPRgo=', 'base64')
  })
  await expect(page.getByRole('button', { name: 'Replace locked PDF background' })).toBeVisible()
  const saveRequest = page.waitForRequest(request => request.url().includes('/versions') && request.method() === 'POST')
  await page.getByLabel('Editor command bar').getByRole('button', { name: 'Save draft' }).click()
  const payload = (await saveRequest).postDataJSON() as { definition?: { page?: { background_pdf?: string } } }
  expect(payload.definition?.page?.background_pdf).toMatch(/^data:application\/pdf;base64,JVBERi0/)
  await expect(page.getByLabel('Editor command bar').getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
  const pdfResponse = page.waitForResponse(response => response.url().includes('/render-pdf') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Generate PDF' }).click()
  const response = await pdfResponse
  expect(response.status()).toBe(200)
  expect((await response.json()).document_base64).toMatch(/^JVBERi0/)
  await expect(page.locator('iframe[title="Generated PDF"]')).toBeVisible()

  await page.getByRole('button', { name: 'Reset locked PDF background' }).first().click()
  await expect(page.getByRole('button', { name: 'Add locked PDF background' })).toBeVisible()
  const resetSaveRequest = page.waitForRequest(request => request.url().includes('/versions') && request.method() === 'POST')
  await page.getByLabel('Editor command bar').getByRole('button', { name: 'Save draft' }).click()
  const resetPayload = (await resetSaveRequest).postDataJSON() as { definition?: { page?: { background_pdf?: string } } }
  expect(resetPayload.definition?.page?.background_pdf).toBeUndefined()
})

test('editor adds a background component and exposes contextual lifecycle actions', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.getByRole('button', { name: 'Add locked PDF background' }).click()
  await expect(page.getByLabel('Insert objects').getByRole('button', { name: 'Locked PDF page background', exact: true })).toBeVisible()
  const replaceBackground = page.getByRole('button', { name: 'Replace locked PDF background' })
  const resetBackground = page.getByRole('button', { name: 'Reset locked PDF background' })
  await expect(replaceBackground).toBeEnabled()
  await expect(resetBackground).toBeDisabled()
  await page.getByLabel('Locked PDF page background').setInputFiles({ name: 'background.pdf', mimeType: 'application/pdf', buffer: Buffer.from('JVBERi0xLjMKJeLjz9MK', 'base64') })
  await expect(replaceBackground).toBeEnabled()
  await expect(resetBackground).toBeEnabled()
  await page.locator('.editor-block-list button').first().click()
  await expect(replaceBackground).toHaveCount(0)
  await page.locator('.editor-block-list').getByRole('button', { name: 'Locked PDF page background', exact: true }).click()
  await expect(replaceBackground).toBeEnabled()
  await resetBackground.click()
  await expect(replaceBackground).toBeEnabled()
  await expect(resetBackground).toBeDisabled()

  await page.route('**/api/templates/*/versions', route => route.abort())
  const saveRequest = page.waitForRequest(request => request.url().includes('/versions') && request.method() === 'POST')
  await page.getByLabel('Editor command bar').getByRole('button', { name: 'Save draft' }).click()
  const payload = (await saveRequest).postDataJSON() as { definition?: { page?: { background?: string; background_pdf?: string } } }
  expect(payload.definition?.page?.background).toBeUndefined()
  expect(payload.definition?.page?.background_pdf).toBeUndefined()
})

test('editor authors a bounded anchor consumed by the table of contents', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.locator('.editor-block-list .editor-block-row').first().getByRole('button', { name: /Select text block/ }).click()
  await page.getByLabel('Anchor ID').fill('intro')
  await page.getByLabel('TOC label').fill('Introduction')
  await page.getByRole('button', { name: 'Add table of contents' }).click()
  const saveRequest = page.waitForRequest(request => request.url().includes('/versions') && request.method() === 'POST')
  await page.getByRole('button', { name: 'Save draft' }).click()
  const payload = (await saveRequest).postDataJSON() as { definition?: { blocks?: Array<{ type?: string; anchor_id?: string; toc_label?: string }> } }
  expect(payload.definition?.blocks?.some(block => block.type === 'text' && block.anchor_id === 'intro' && block.toc_label === 'Introduction')).toBeTruthy()
  await expect(page.getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
  const preview = page.frameLocator('iframe[title="Server preview"]')
  await expect(preview.locator('p#intro')).toHaveCount(1)
  await expect(preview.locator('nav.template-toc a[href="#intro"]')).toHaveCount(1)
})

test('editor core controls expose names and keyboard-focusable actions', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await expect(page.locator('.editor-toolbar')).toHaveAttribute('aria-label', 'Text formatting controls')
  await expect(page.locator('.page-settings')).toHaveAttribute('aria-label', 'Page settings')
  await expect(page.locator('.structure-controls')).toHaveAttribute('aria-label', 'Structure controls')
  const grip = page.locator('.editor-block-list .block-grip').first()
  await expect(grip).toHaveAccessibleName(/Select text block/)
  await grip.focus()
  await expect(grip).toBeFocused()
  await expect(page.getByRole('button', { name: 'Delete selected block' })).toBeEnabled()
  await expect(grip).toHaveAttribute('aria-pressed', 'false')
  await grip.click()
  await expect(grip).toHaveAttribute('aria-pressed', 'true')
  const secondGrip = page.locator('.editor-block-list .block-grip').nth(1)
  await secondGrip.click({ modifiers: ['Control'] })
  await expect(grip).toHaveAttribute('aria-pressed', 'true')
  await expect(secondGrip).toHaveAttribute('aria-pressed', 'true')
})

test('editor names block textareas and supports keyboard block selection', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  const firstRow = page.locator('.editor-block-row').first()
  const textarea = firstRow.locator('textarea')
  await expect(textarea).toHaveAttribute('aria-label', /Edit text block/)
  const grip = firstRow.locator('.block-grip')
  await grip.focus()
  await page.keyboard.press('Enter')
  await expect(grip).toHaveAttribute('aria-pressed', 'true')
  await expect(firstRow).toHaveClass(/active/)
})

test('editor renders and toggles alignment guides for the active block', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  const guide = page.locator('.editor-page .alignment-guide')
  await expect(guide).toHaveClass(/alignment-guide-left/)
  await page.getByRole('button', { name: 'Align center' }).click()
  await expect(guide).toHaveClass(/alignment-guide-center/)
  const snap = page.getByRole('button', { name: 'Snap & guides' })
  await snap.click()
  await expect(guide).not.toBeVisible()
  await snap.click()
  await expect(guide).toHaveClass(/alignment-guide-center/)
})

test('editor embeds an uploaded image in the generated PDF flow', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.getByRole('button', { name: 'Add image or logo' }).click()
  const upload = page.locator('.table-editor input[type="file"]')
  await Promise.all([
    page.waitForResponse(response => response.url().includes('/api/assets') && response.request().method() === 'POST'),
    upload.setInputFiles({ name: 'logo.png', mimeType: 'image/png', buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64') }),
  ])
  await page.getByRole('button', { name: 'Align center' }).click()
  const saveRequest = page.waitForRequest(request => request.url().includes('/versions') && request.method() === 'POST')
  await page.getByRole('button', { name: 'Save draft' }).click()
  const savedPayload = (await saveRequest).postDataJSON() as { definition?: { blocks?: Array<{ type?: string; align?: string }> } }
  expect(savedPayload.definition?.blocks?.some(block => block.type === 'image' && block.align === 'center')).toBeTruthy()
  await expect(page.getByRole('status').filter({ hasText: 'server preview rendered' })).toBeVisible({ timeout: 15000 })
  await expect(page.frameLocator('iframe[title="Server preview"]').locator('figure.template-image')).toHaveAttribute('style', 'text-align:center')
  await expect(page.frameLocator('iframe[title="Server preview"]').locator('figure.template-image img')).toHaveAttribute('style', /display:inline-block;width:/)
  const pdfResponse = page.waitForResponse(response => response.url().includes('/render-pdf') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Generate PDF' }).click()
  const pdf = await pdfResponse
  await expect(pdf.status()).toBe(200)
  assertCenteredImagePdf((await pdf.json()).document_base64)
  await expect(page.getByRole('status').filter({ hasText: 'PDF generated' })).toBeVisible({ timeout: 15000 })
  await expect(page.locator('iframe[title="Generated PDF"]')).toBeVisible()
})

test('editor can remove a reusable component from the current template', async ({ page }) => {
  const componentName = 'Test removal component'
  await page.route('**/api/components', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [{ id: 'test-component', name: componentName, version: 1 }] }) })
      return
    }
    await route.continue()
  })
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  await page.getByRole('button', { name: `Add component: ${componentName}` }).click()
  await expect(page.getByRole('button', { name: 'Remove component', exact: true })).toBeEnabled()
  await expect(page.getByRole('button', { name: `Remove component: ${componentName}` })).toBeVisible({ timeout: 10000 })
  await page.getByRole('button', { name: `Remove component: ${componentName}` }).click()
  await expect(page.getByRole('button', { name: `Remove component: ${componentName}` })).not.toBeVisible()
})

test('component removal stays disabled for ordinary blocks and enables for an instance', async ({ page }) => {
  const componentName = 'Removal state component'
  await page.route('**/api/components', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [{ id: 'removal-state-component', name: componentName, version: 1 }] }) })
      return
    }
    await route.continue()
  })
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  const remove = page.getByRole('button', { name: 'Remove component', exact: true })
  await expect(remove).toBeDisabled()
  await page.locator('.editor-block-list .block-grip').first().click()
  await expect(remove).toBeDisabled()
  await page.getByRole('button', { name: `Add component: ${componentName}` }).click()
  await expect(remove).toBeEnabled()
  await page.locator('.editor-block-list .block-grip').first().click()
  await expect(remove).toBeDisabled()
  const componentGrip = page.locator('.editor-block-list .block-grip').last()
  await componentGrip.click()
  await expect(remove).toBeEnabled()
  await remove.click()
  await expect(page.locator('.editor-block-list .block-grip')).toHaveCount(3)
})

test('editor can update a reusable component from a modifier-selected block', async ({ page }) => {
  const componentName = 'Test update component'
  let updatePayload: unknown = null
  await page.route('**/api/components', async route => {
    if (route.request().method() === 'GET') {
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ items: [{ id: 'test-update-component', name: componentName, version: 1 }] }) })
      return
    }
    await route.continue()
  })
  await page.route('**/api/components/test-update-component', async route => {
    if (route.request().method() === 'PUT') {
      updatePayload = route.request().postDataJSON()
      await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify({ id: 'test-update-component', version: 2 }) })
      return
    }
    await route.continue()
  })
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  await expect(page.locator('article.detail')).toBeVisible()
  await page.getByRole('button', { name: `Add component: ${componentName}` }).click()
  const rows = page.locator('.editor-block-list .editor-block-row')
  await rows.nth(0).getByRole('button', { name: /Select text block/ }).click()
  await rows.last().getByRole('button', { name: /Select text block/ }).click({ modifiers: ['Control'] })
  await page.getByRole('button', { name: 'Update component from selection' }).click()
  await expect.poll(() => updatePayload).toMatchObject({ definition: { blocks: [{ type: 'text' }] } })
  await expect(page.getByRole('status')).toContainText('Component updated')
})

test('editor can delete the selected template block', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  await expect(page.locator('article.detail')).toBeVisible()
  const rows = page.locator('.editor-block-list .editor-block-row')
  await expect(rows.first()).toBeVisible()
  const before = await rows.count()
  await rows.first().getByRole('button', { name: /Select text block/ }).click()
  await page.getByRole('button', { name: 'Delete selected block' }).click()
  await expect(rows).toHaveCount(before - 1)
})

test('editor keyboard shortcuts undo and redo a block insertion', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  await expect(page.locator('article.detail')).toBeVisible()
  const rows = page.locator('.editor-block-list .editor-block-row')
  const before = await rows.count()
  await page.getByRole('button', { name: 'Add text block' }).click()
  await expect(rows).toHaveCount(before + 1)
  await page.keyboard.press('Control+z')
  await expect(rows).toHaveCount(before)
  await page.keyboard.press('Control+Shift+z')
  await expect(rows).toHaveCount(before + 1)
})

test('editor copies and pastes the active block with a keyboard shortcut', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  const rows = page.locator('.editor-block-row')
  await expect(rows.first()).toBeVisible()
  const before = await rows.count()
  const firstText = await rows.first().locator('textarea').inputValue()
  await rows.first().getByRole('button', { name: /Select text block/ }).click()
  await page.keyboard.press('Control+c')
  await page.keyboard.press('Control+v')
  await expect(rows).toHaveCount(before + 1)
  await expect(rows.last().locator('textarea')).toHaveValue(firstText)
})

test('editor accepts dropping a text block onto the page surface', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  const rows = page.locator('.editor-block-row')
  const firstText = await rows.first().locator('textarea').inputValue()
  await rows.first().dragTo(page.locator('.editor-page'))
  await expect(rows.last().locator('textarea')).toHaveValue(firstText)
})

test('editor inserts a repeatable table into the server preview', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.getByRole('button', { name: 'Add repeatable table' }).click()
  await page.getByRole('button', { name: 'Save draft' }).click()
  await expect(page.getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
  const preview = page.frameLocator('iframe[title="Server preview"]')
  const repeatableTable = preview.locator('table.template-table').filter({ hasText: 'Example item' }).last()
  await expect(repeatableTable.getByRole('cell', { name: 'Example item' })).toBeVisible()
  await expect(repeatableTable.locator('tbody tr')).toHaveCount(2)
  await expect(repeatableTable.locator('thead')).toContainText('Description')
  expect(await preview.locator('style').textContent()).toContain('display:table-header-group')
})

test('editor uploads an image asset and renders it in the server preview', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  await page.getByRole('button', { name: 'Add image or logo' }).click()
  const upload = page.locator('.image-contextual-palette input[type="file"]')
  await Promise.all([
    page.waitForResponse(response => response.url().includes('/api/assets') && response.request().method() === 'POST'),
    upload.setInputFiles({ name: 'logo.png', mimeType: 'image/png', buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64') }),
  ])
  await page.getByRole('button', { name: 'Save draft' }).click()
  await expect(page.getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
  await expect(page.frameLocator('iframe[title="Server preview"]').locator('img[src^="/api/assets/"]').last()).toBeVisible()
})

test('editor configures QR, Code 128, and EAN-13 blocks in the server preview', async ({ page }) => {
  test.setTimeout(90000)
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.getByRole('button', { name: 'Add QR or barcode' }).click()
  const codeEditor = page.locator('.table-editor-row').filter({ has: page.getByLabel('Code type') }).last()
  const codeType = codeEditor.getByLabel('Code type')
  const codeValue = codeEditor.getByLabel('Code value')
  const preview = page.frameLocator('iframe[title="Server preview"]')
  for (const [kind, value] of [['qr', 'ORDER-001'], ['code128', 'ABC123'], ['ean13', '5901234123457']] as const) {
    await codeType.selectOption(kind)
    await codeValue.fill(kind === 'ean13' ? value : `{{order.${kind === 'qr' ? 'id' : 'code'}}}`)
    await page.getByRole('button', { name: 'Save draft' }).click()
    await expect(page.getByRole('status').filter({ hasText: 'server preview rendered' })).toBeVisible({ timeout: 15000 })
    await expect(preview.locator(`figure[aria-label="${kind} code"] svg`)).toBeVisible()
    const pdfResponse = page.waitForResponse(response => response.url().includes('/render-pdf') && response.request().method() === 'POST')
    await page.getByRole('button', { name: 'Generate PDF' }).click()
    const pdf = await pdfResponse
    expect(pdf.status()).toBe(200)
    expect(((await pdf.json()) as { document_base64?: string }).document_base64?.length || 0).toBeGreaterThan(1000)
  }
})

test('editor inserts a repeating section and conditional block', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  await page.getByRole('button', { name: 'Add repeating section' }).click()
  await page.getByRole('button', { name: 'Add conditional block' }).click()
  await page.getByRole('button', { name: 'Save draft' }).click()
  await expect(page.getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
  const preview = page.frameLocator('iframe[title="Server preview"]')
  await expect(preview.getByText('Example item — $12.50').first()).toBeVisible()
  await expect(preview.getByText('Second item — $7.50').first()).toBeVisible()
  await expect(preview.getByText('This note is enabled.').first()).toBeVisible()
  await expect(preview.getByText('This note is disabled.').first()).not.toBeVisible()
})

test('editor persists page settings in the server preview', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  const settings = page.locator('.page-settings')
  await settings.getByLabel('Page size').selectOption('Letter')
  await settings.getByLabel('Orientation').selectOption('landscape')
  await settings.getByLabel('Margins').fill('25')
  await settings.getByLabel('Document title').fill('Quarterly report')
  await settings.getByLabel('Document author').fill('Finance')
  await settings.getByRole('textbox', { name: 'Header' }).fill('Quarterly report')
  await settings.getByRole('textbox', { name: 'Footer' }).fill('Confidential')
  await settings.getByLabel('Show page numbers').check()
  await page.getByRole('button', { name: 'Save draft' }).click()
  await expect(page.getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
  const preview = page.frameLocator('iframe[title="Server preview"]')
  expect(await preview.locator('style').textContent()).toContain('@page{size:Letter landscape;margin:25mm;')
  await expect(preview.locator('header.document-header')).toContainText('Quarterly report')
  await expect(preview.locator('footer.document-footer')).toContainText('Confidential')
  await expect(preview.locator('.page-number')).toBeVisible()
  expect(await preview.locator('title').evaluate(element => element.textContent)).toBe('Quarterly report')
  await expect(preview.locator('meta[name="author"]')).toHaveAttribute('content', 'Finance')
})

test('editor switches the server preview locale', async ({ page }) => {
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.locator('.page-settings').getByLabel('Preview locale').selectOption('de-DE')
  await page.getByRole('button', { name: 'Save draft' }).click()
  await expect(page.getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
  const preview = page.frameLocator('iframe[title="Server preview"]')
  await expect(preview.locator('html')).toHaveAttribute('lang', 'de-DE')
  const pdfResponse = page.waitForResponse(response => response.url().includes('/render-pdf') && response.request().method() === 'POST')
  await page.getByRole('button', { name: 'Generate PDF' }).click()
  const response = await pdfResponse
  expect(response.status()).toBe(200)
  const pdfBody = await response.json() as { report?: { render_locale?: string } }
  expect(pdfBody.report?.render_locale).toBe('de-DE')
  await expect(page.locator('iframe[title="Generated PDF"]')).toBeVisible()
})

test('editor exposes the remaining script preview locales', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  const controls = page.locator('.script-locale-controls')
  for (const [name, locale] of [['Hebrew', 'he'], ['Tamil', 'ta'], ['Korean', 'ko']] as const) {
    await controls.getByRole('button', { name }).click()
    await page.getByRole('button', { name: 'Save draft' }).click()
    await expect(page.getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
    await expect(page.frameLocator('iframe[title="Server preview"]').locator('html')).toHaveAttribute('lang', locale)
  }
})

test('editor persists page-flow controls in the server preview', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  await page.locator('.editor-toolbar').getByLabel('Start on new page').check()
  await page.locator('.editor-toolbar').getByLabel('Keep block together').check()
  await page.getByRole('button', { name: 'Save draft' }).click()
  await expect(page.getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
  const preview = page.frameLocator('iframe[title="Server preview"]')
  await expect(preview.locator('p[style*="break-before:page"]').first()).toBeVisible()
  await expect(preview.locator('p[style*="break-inside:avoid"]').first()).toBeVisible()
})

test('editor exposes page-flow controls on each block row', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  const rows = page.locator('.editor-block-list .editor-block-row')
  await expect(rows).not.toHaveCount(0)
  const secondRow = rows.last()
  const secondBreak = secondRow.getByLabel(/Block flow: Start on new page for/i)
  const secondKeep = secondRow.getByLabel(/Block flow: Keep block together for/i)
  await secondBreak.check()
  await secondKeep.uncheck()
  await expect(secondBreak).toBeChecked()
  await expect(secondKeep).not.toBeChecked()
})

test('editor accepts multilingual text across the supported script families', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  const text = 'العربية עברית हिन्दी தமிழ் ไทย 中文 日本語 한국어'
  const block = page.locator('.editor-block-row textarea').first()
  await block.fill(text)
  await expect(block).toHaveValue(text)
  await page.getByRole('button', { name: 'Save draft' }).click()
  await expect(page.getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
  await expect(page.frameLocator('iframe[title="Server preview"]').locator('body')).toContainText(text)
})

test('editor gives multilingual text entry an automatic direction and locale', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  await page.locator('.page-settings').getByLabel('Preview locale').selectOption('ar')
  const block = page.locator('.editor-block-row textarea').first()
  await expect(block).toHaveAttribute('dir', 'auto')
  await expect(block).toHaveAttribute('lang', 'ar')
  await block.fill('مرحبا بالعالم')
  await block.selectText()
  await expect(block).toHaveValue('مرحبا بالعالم')
})

test('editor round-trips authentic native-script input through server preview', async ({ page }) => {
  await page.goto('/')
  const sampleCard = page.locator('article.template-card').filter({ has: page.getByRole('heading', { name: 'Welcome letter' }) })
  await sampleCard.getByRole('button', { name: 'Explore template' }).click()
  const block = page.locator('.editor-block-row textarea').first()
  const scripts = ['العربية', 'עברית', 'हिन्दी', 'தமிழ்', 'ไทย', '中文 日本語 한국어']
  for (const text of scripts) {
    await block.fill(text)
    await expect(block).toHaveValue(text)
    await block.selectText()
    await page.getByRole('button', { name: 'Save draft' }).click()
    await expect(page.getByRole('status')).toContainText('server preview rendered', { timeout: 15000 })
    await expect(page.frameLocator('iframe[title="Server preview"]').locator('body')).toContainText(text)
  }
})

test('ingestion accepts multiple files and shows per-file routing status', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type="file"]').setInputFiles([
    { name: 'digital-invoice.pdf', mimeType: 'application/pdf',
      buffer: Buffer.from('%PDF-1.7 BT (Invoice Number: INV-1) Tj ET') },
    { name: 'scan-receipt.png', mimeType: 'image/png',
      buffer: Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', 'base64') },
  ])
  const first = page.locator('.ingestion-list li').filter({ hasText: 'digital-invoice.pdf' })
  const second = page.locator('.ingestion-list li').filter({ hasText: 'scan-receipt.png' })
  await expect(first).toContainText('digital')
  await expect(first.locator('.ingestion-status')).toContainText(/queued/i)
  await expect(second).toContainText('scan-receipt.png')
  await expect(second.locator('.ingestion-status')).toContainText(/queued/i)
})

test('review queue prioritizes failed fields and supports keyboard movement', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'review-queue.pdf', mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.7 BT (Total: not-a-number) Tj ET'),
  })
  const ingestion = page.locator('.ingestion-list li').filter({ hasText: 'review-queue.pdf' })
  await expect(ingestion.locator('.ingestion-status')).toContainText(/queued/i)
  await ingestion.getByRole('button', { name: 'Extract' }).click()
  await expect(page.getByRole('heading', { name: 'Review extracted fields' })).toBeVisible()
  const queue = page.locator('.review-priority-queue')
  await expect(queue.locator('.review-priority-field.failed')).toHaveCount(2)
  await expect(queue.locator('.review-priority-field').first()).toHaveClass(/failed/)
  const inputs = queue.locator('input')
  await inputs.first().focus()
  await inputs.first().press('ArrowDown')
  await expect(inputs.nth(1)).toBeFocused()
  const totalInput = page.locator('.review-priority-field').filter({ hasText: 'total' }).locator('input')
  await totalInput.focus()
  await expect(page.locator('.source-element.active')).toHaveCount(1)
})

test('reviewer can draw and persist a source box for a missing field', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'draw-source.pdf', mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.7 BT (Total: 12.00) Tj ET'),
  })
  const ingestion = page.locator('.ingestion-list li').filter({ hasText: 'draw-source.pdf' })
  await ingestion.getByRole('button', { name: 'Extract' }).click()
  await expect(page.getByRole('heading', { name: 'Review extracted fields' })).toBeVisible()
  await expect(page.locator('.source-pdf')).toBeVisible()
  const source = page.locator('.source-page').first()
  await source.scrollIntoViewIfNeeded()
  const bounds = await source.boundingBox()
  expect(bounds).not.toBeNull()
  await page.mouse.move(bounds!.x + 20, bounds!.y + 20)
  await page.mouse.down()
  await page.mouse.move(bounds!.x + 100, bounds!.y + 70)
  await page.mouse.up()
  await page.getByLabel('New field name').fill('purchase_reference')
  await page.getByRole('button', { name: 'Add field from selected source' }).click()
  await expect(page.getByRole('button', { name: /purchase reference.*no source region/i })).toBeVisible()
})

test('reviewer can select a line-item value and highlight its source', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'line-items.pdf', mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.7 BT (Invoice Number: INV-1) Tj (Total: $6.00) Tj (Widget | 2 | $3.00 | $6.00) Tj ET'),
  })
  const ingestion = page.locator('.ingestion-list li').filter({ hasText: 'line-items.pdf' })
  await ingestion.getByRole('button', { name: 'Extract' }).click()
  await expect(page.locator('.review-line-items')).toBeVisible()
  await page.locator('.review-source-value').first().click()
  await expect(page.locator('.source-element.active')).toHaveCount(1)
  await expect(page.locator('.source-field-highlight')).toHaveCount(1)
  const sourceElement = page.locator('.source-element').first()
  await sourceElement.focus()
  await sourceElement.press('Enter')
  await expect(sourceElement).toHaveAttribute('aria-pressed', 'true')
  await expect(page.locator('.source-field-highlight')).toHaveCount(1)
})

test('reviewer can save a correction and undo it from the review UI', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'undo-correction.pdf', mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.7 BT (Invoice Number: INV-1) Tj (Total: $12.00) Tj ET'),
  })
  const ingestion = page.locator('.ingestion-list li').filter({ hasText: 'undo-correction.pdf' })
  await ingestion.getByRole('button', { name: 'Extract' }).click()
  await expect(page.getByRole('heading', { name: 'Review extracted fields' })).toBeVisible()
  const totalInput = page.locator('.review-priority-field').filter({ hasText: 'total' }).locator('input')
  await expect(totalInput).toHaveValue('12.00')
  await totalInput.fill('15.00')
  await totalInput.press('Tab')
  await expect(totalInput).toHaveValue('15.00')
  await page.getByRole('button', { name: 'Undo latest correction' }).click()
  await expect(totalInput).toHaveValue('12.00')
})

test('multi-page extraction exposes completed page progress', async ({ page }) => {
  await page.goto('/')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'multi-page.pdf', mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.7 /Type /Page /Type /Page BT (Total: 12.00) Tj ET'),
  })
  const ingestion = page.locator('.ingestion-list li').filter({ hasText: 'multi-page.pdf' })
  await expect(ingestion.locator('.ingestion-progress').first()).toContainText('0/2 pages')
  await ingestion.getByRole('button', { name: 'Extract' }).click()
  await expect(ingestion.locator('.ingestion-progress').first()).toContainText('2/2 pages', { timeout: 10000 })
  await expect(page.getByRole('heading', { name: 'Review extracted fields' })).toBeVisible()
  await page.getByRole('button', { name: 'Next source page' }).click()
  await expect(page.locator('.source-preview-heading')).toContainText('Page 2 of 2')
  await page.getByRole('button', { name: 'Previous source page' }).click()
  await expect(page.locator('.source-preview-heading')).toContainText('Page 1 of 2')
})

test('source selection follows a field provenance page on multi-page results', async ({ page }) => {
  await page.route(/\/api\/ingestions\/[^/]+\/extract$/, route => route.fulfill({
    status: 202,
    contentType: 'application/json',
    body: JSON.stringify({ id: 'job-page-two' }),
  }))
  await page.route('**/api/jobs/job-page-two', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      status: 'done',
      result: {
        result_id: 'result-page-two', schema_id: 'invoice', status: 'new', revision: 1,
        fields: {
          invoice_number: {
            original_value: 'INV-2', normalized_value: 'INV-2', confidence: 0.95,
            review_status: 'new', validation: [],
            source: { page_number: 2, element_id: 'page-two-invoice', box: [72, 90, 260, 104] },
          },
        },
        tables: {},
        page_model: {
          schema_version: 1, document_id: 'source-page-two', source: { media_type: 'application/pdf', filename: 'two-page.pdf' },
          pages: [
            { page_number: 1, width: 612, height: 792, rotation: 0, elements: [], layout: {} },
            { page_number: 2, width: 612, height: 792, rotation: 0,
              elements: [{ id: 'page-two-invoice', type: 'text', text: 'Invoice Number: INV-2', box: [72, 90, 260, 104] }], layout: {} },
          ],
        },
      },
    }),
  }))
  await page.goto('/')
  await page.locator('input[type="file"]').setInputFiles({
    name: 'two-page.pdf', mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.7 /Type /Page /Type /Page BT (Invoice Number: INV-2) Tj ET'),
  })
  const ingestion = page.locator('.ingestion-list li').filter({ hasText: 'two-page.pdf' })
  await ingestion.getByRole('button', { name: 'Extract' }).click()
  await expect(page.getByRole('heading', { name: 'Review extracted fields' })).toBeVisible()
  await expect(page.locator('svg[aria-label="Page 2 source regions"]')).toBeVisible()
  await expect(page.locator('.source-element.active')).toHaveCount(1)
})

test('editor inserts a positioned rectangle shape and persists it to server preview', async ({ page }) => {
  // DD-433
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.getByRole('button', { name: 'Add line or rectangle' }).first().click()
  const panel = page.getByRole('complementary', { name: 'Shape' })
  await expect(panel).toBeVisible()
  await panel.getByLabel('Shape kind').selectOption('rectangle')
  await panel.getByLabel('Shape width mm').fill('50')
  await panel.getByLabel('Shape height mm').fill('8')
  await panel.getByLabel('Shape layer').selectOption('behind')
  await panel.getByLabel('Shape fixed position').check()
  await panel.getByLabel('Shape position X').fill('12')
  await panel.getByLabel('Shape position Y').fill('30')
  await expect(page.locator('.editor-shape-preview').first()).toBeVisible()
  await page.locator('.editor-command-bar').getByRole('button', { name: 'Save draft' }).click()
  await expect(page.locator('p.editor-feedback')).toContainText('server preview rendered', { timeout: 15000 })
  const shape = page.frameLocator('iframe[title="Server preview"]').locator('.template-shape-rectangle')
  await expect(shape).toHaveAttribute('style', /width:50mm;height:8mm/)
  await expect(shape).toHaveAttribute('style', /position:absolute;left:12mm;top:30mm;z-index:-1/)
  await expect(shape).toHaveAttribute('aria-hidden', 'true')
})

test('editor builds a two-column section with a column break and persists it to server preview', async ({ page }) => {
  // DD-435
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.getByRole('button', { name: 'Start columns' }).first().click()
  const panel = page.getByRole('complementary', { name: 'Columns' })
  await expect(panel).toBeVisible()
  await panel.getByLabel('Column gap').fill('8')
  await panel.getByLabel('Column widths').fill('60, 35')
  await panel.getByLabel('Column widths').blur()
  await page.getByRole('button', { name: 'Column break' }).first().click()
  await page.getByRole('button', { name: 'End columns' }).first().click()
  await expect(page.locator('.editor-column-marker')).toHaveCount(3)
  await page.locator('.editor-command-bar').getByRole('button', { name: 'Save draft' }).click()
  await expect(page.locator('p.editor-feedback')).toContainText('server preview rendered', { timeout: 15000 })
  const section = page.frameLocator('iframe[title="Server preview"]').locator('.template-columns')
  await expect(section).toHaveAttribute('style', /display:grid;grid-template-columns:60% 35%;column-gap:8mm/)
  await expect(section.locator('.template-column')).toHaveCount(2)
})

test('editor sets header and footer zones, distance and rule and persists them to server preview', async ({ page }) => {
  // DD-437
  await page.goto('/')
  const invoice = page.locator('.starter-card').filter({ hasText: 'Invoice' })
  await invoice.getByRole('button', { name: /Use starter.*en/ }).click()
  await page.locator('.page-settings-toggle:visible').first().click()
  const zones = page.locator('#page-settings-panel .furniture-panel')
  await expect(zones).toBeVisible()
  await zones.getByLabel('Header left', { exact: true }).fill('Quarterly report')
  await zones.getByLabel('Header right', { exact: true }).fill('Internal')
  await zones.getByLabel('Header left size').fill('14')
  await zones.getByLabel('Header left bold').check()
  await zones.getByLabel('Header distance from top edge (mm)').fill('11')
  await zones.getByLabel('Header rule', { exact: true }).check()
  await zones.getByLabel('Header rule gap above content (mm)').fill('8')
  await page.locator('.editor-command-bar').getByRole('button', { name: 'Save draft' }).click()
  await expect(page.locator('p.editor-feedback')).toContainText('server preview rendered', { timeout: 15000 })
  const preview = page.frameLocator('iframe[title="Server preview"]')
  await expect(preview.locator('header.document-header')).toContainText('Quarterly report')
  await expect(preview.locator('header.document-header')).toContainText('Internal')
  const css = await preview.locator('style').first().textContent()
  expect(css).toContain('@top-right{content:"Internal";')
  expect(css).toMatch(/@top-left\{content:"Quarterly report";[^}]*font-size:14px;[^}]*font-weight:700/)
  expect(css).toContain('vertical-align:top;padding-top:11mm;border-bottom:0.75px solid #000000;margin-bottom:8mm')
})
