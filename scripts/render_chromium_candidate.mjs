// Offline Chromium PDF renderer used by the production adapter and candidate
// comparison tooling. The manifest remains candidate evidence until native-
// reader and multilingual acceptance is recorded.
import { readFile, writeFile } from 'node:fs/promises'
import { resolve } from 'node:path'
import { chromium } from '../frontend/node_modules/playwright/index.mjs'

const [, , htmlArgument, pdfArgument, manifestArgument, screenshotArgument] = process.argv
if (!htmlArgument || !pdfArgument) {
  console.error('usage: node scripts/render_chromium_candidate.mjs INPUT.html OUTPUT.pdf [OUTPUT.json] [OUTPUT.png]')
  process.exit(2)
}

const htmlPath = resolve(htmlArgument)
const pdfPath = resolve(pdfArgument)
const manifestPath = resolve(manifestArgument || `${pdfArgument}.json`)
const screenshotPath = screenshotArgument ? resolve(screenshotArgument) : null
const html = await readFile(htmlPath, 'utf8')

function pdfText(value) {
  const utf16 = Buffer.from(`\ufeff${value}`, 'utf16le')
  for (let index = 0; index < utf16.length; index += 2) {
    const byte = utf16[index]
    utf16[index] = utf16[index + 1]
    utf16[index + 1] = byte
  }
  return `<${utf16.toString('hex').toUpperCase()}>`
}

function patchPdfMetadata(input, metadata) {
  const source = input.toString('latin1')
  const startMatch = source.match(/startxref\s+(\d+)\s+%%EOF\s*$/)
  if (!startMatch) throw new Error('Chromium PDF has no terminal startxref')
  const previousXref = Number(startMatch[1])
  const trailerStart = source.lastIndexOf('trailer', startMatch.index)
  const trailer = source.slice(trailerStart, startMatch.index)
  const sizeMatch = trailer.match(/\/Size\s+(\d+)/)
  const rootMatch = trailer.match(/\/Root\s+(\d+\s+0\s+R)/)
  if (!sizeMatch || !rootMatch) throw new Error('Chromium PDF trailer lacks size or root')
  const rootObject = rootMatch[1]
  const rootNumber = Number(rootObject.match(/^\d+/)[0])
  const rootStart = source.indexOf(`${rootNumber} 0 obj`)
  const rootEnd = source.indexOf('endobj', rootStart)
  const root = source.slice(rootStart, rootEnd)
  const pagesMatch = root.match(/\/Pages\s+(\d+\s+0\s+R)/)
  if (!pagesMatch) throw new Error('Chromium PDF catalog lacks pages')
  const size = Number(sizeMatch[1])
  const infoId = size
  const catalogId = size + 1
  const info = `${infoId} 0 obj\n<< /Title ${pdfText(metadata.title)} /Author ${pdfText(metadata.author)} >>\nendobj\n`
  const catalog = `${catalogId} 0 obj\n<< /Type /Catalog /Pages ${pagesMatch[1]} /Lang ${pdfText(metadata.language)} /ViewerPreferences << /DisplayDocTitle true >> >>\nendobj\n`
  const prefix = source.endsWith('\n') ? source : `${source}\n`
  const infoOffset = Buffer.byteLength(prefix, 'latin1')
  const catalogOffset = infoOffset + Buffer.byteLength(info, 'latin1')
  const xref = `xref\n${infoId} 2\n${String(infoOffset).padStart(10, '0')} 00000 n \n${String(catalogOffset).padStart(10, '0')} 00000 n \n`
  const xrefOffset = catalogOffset + Buffer.byteLength(catalog, 'latin1')
  const newTrailer = `trailer\n<< /Size ${size + 2} /Root ${catalogId} 0 R /Info ${infoId} 0 R /Prev ${previousXref} >>\nstartxref\n${xrefOffset}\n%%EOF\n`
  const output = Buffer.from(prefix + info + catalog + xref + newTrailer, 'latin1')
  if (!output.includes(Buffer.from(`/${'Author'} `)) || !output.includes(Buffer.from(`/${'Lang'} `))) {
    throw new Error('incremental metadata patch was not written')
  }
  return output
}

function pdfInfoValue(pdf, name) {
  const text = pdf.toString('latin1')
  const literal = [...text.matchAll(new RegExp(`/${name} \\(([^)]*)\\)`, 'g'))].at(-1)
  if (literal) return literal[1]
  const hex = [...text.matchAll(new RegExp(`/${name} <([0-9A-Fa-f]+)>`, 'g'))].at(-1)
  if (!hex) return null
  const bytes = Buffer.from(hex[1], 'hex')
  if (bytes.length >= 2 && bytes[0] === 0xfe && bytes[1] === 0xff) {
    let value = ''
    for (let index = 2; index + 1 < bytes.length; index += 2) value += String.fromCharCode((bytes[index] << 8) | bytes[index + 1])
    return value
  }
  return bytes.toString('latin1')
}

function pdfFontReport(pdf) {
  const text = pdf.toString('latin1')
  const names = [...text.matchAll(/\/(?:BaseFont|FontName)\s+\/([^\s/]+)/g)]
    .map(match => match[1])
    .filter((name, index, values) => values.indexOf(name) === index)
  const embeddedFontFiles = [...text.matchAll(/\/FontFile(?:2|3)?(?=\s|\/|\[|<|>)/g)].length
  const unicodeMaps = [...text.matchAll(/\/ToUnicode\s+/g)].length
  return {
    font_names: names,
    embedded_font_file_markers: embeddedFontFiles,
    to_unicode_map_count: unicodeMaps,
    glyph_coverage: null,
    status: 'object-inventory-only; glyph and native-reader review pending',
  }
}

const browser = await chromium.launch({ headless: true })
try {
  const page = await browser.newPage()
  const optionalAttribute = async (selector, name) => page.evaluate(
    ([targetSelector, attributeName]) => document.querySelector(targetSelector)?.getAttribute(attributeName) ?? null,
    [selector, name],
  )
  await page.route('**/*', route => route.abort())
  await page.setContent(html, { waitUntil: 'load' })
  const sourcePdf = await page.pdf({ format: 'A4', printBackground: true, preferCSSPageSize: true })
  const sourceTitle = await page.title()
  const sourceLanguage = await optionalAttribute('html', 'lang')
  const sourceAuthor = await optionalAttribute('meta[name="author"]', 'content')
  if (screenshotPath) await page.screenshot({path: screenshotPath, fullPage: true})
  const pdf = patchPdfMetadata(sourcePdf, { title: sourceTitle, author: sourceAuthor || '', language: sourceLanguage || 'en' })
  await writeFile(pdfPath, pdf)
  await writeFile(manifestPath, JSON.stringify({
    status: 'candidate',
    engine: 'chromium-playwright',
    playwright_version: '1.63.0',
    browser_version: browser.version(),
    input: htmlPath,
    output: pdfPath,
    screenshot: screenshotPath,
    network: 'disabled',
    metadata: {
      title: await page.title(),
      language: await optionalAttribute('html', 'lang'),
      author: await optionalAttribute('meta[name="author"]', 'content'),
    },
    metadata_patch: 'incremental PDF Info/catalog metadata; candidate-only',
    pdf_metadata_observed: {
      title: pdfInfoValue(pdf, 'Title'),
      author: pdfInfoValue(pdf, 'Author'),
      language: pdfInfoValue(pdf, 'Lang'),
    },
    fonts: pdfFontReport(pdf),
    native_reader_scores: null,
  }, null, 2) + '\n', 'utf8')
} finally {
  await browser.close()
}
