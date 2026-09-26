import { StrictMode, useEffect, useRef, useState } from 'react'
import type { KeyboardEvent, PointerEvent } from 'react'
import { createRoot } from 'react-dom/client'
import { useTranslation } from 'react-i18next'
import './i18n'
import './style.css'
import './editor.css'
import './reviewQueue.css'
import './tableEditor.css'
import { epicStories } from './epicStories'
import { getStoryStatus } from './storyStatus'

type Template = { id: string; name: string; schema_version: number }
type ExtractionSchemaItem = { id: string; name: string; schema_version: number; sample_url: string }
type Starter = { id: string; name: string; languages: string[]; definitions: Record<string, Record<string, unknown>> }
type PageSettings = { size: 'A3' | 'A4' | 'A5' | 'Letter'; orientation: 'portrait' | 'landscape'; marginMm: number; header: string; footer: string; showPageNumbers: boolean }
type DocumentMetadata = { title: string; author: string }
type Definition = { name: string; blocks: Array<Record<string, unknown>>; sample_data: unknown; page?: Record<string, unknown>; theme?: Record<string, unknown>; locale?: string; metadata?: Partial<DocumentMetadata> }
type EditorBlock = { id: string; text: string; bold: boolean; italic: boolean; color: string; fontFamily: string; fontSize: number; align: 'left' | 'center' | 'right'; breakBefore: boolean; keepTogether: boolean; kind?: 'text' | 'table' | 'loop' | 'if' | 'image' | 'code' | 'chart' | 'toc' | 'component'; componentId?: string; items?: string; as?: string; columns?: TableColumn[]; repeatText?: string; conditionPath?: string; conditionValue?: boolean; thenText?: string; elseText?: string; source?: string; alt?: string; width?: number; codeType?: 'qr' | 'code128' | 'ean13'; codeValue?: string; chartType?: 'bar' | 'line' | 'pie'; labelPath?: string; valuePath?: string; anchorId?: string; tocLabel?: string; tocLevel?: number }
type StoredEditorBlock = { type?: string; text?: string; component_id?: string; bold?: boolean; italic?: boolean; color?: string; font_family?: string; font_size?: number; align?: 'left' | 'center' | 'right'; break_before?: boolean; keep_together?: boolean; items?: string; as?: string; columns?: TableColumn[]; blocks?: Array<{ type?: string; text?: string }>; condition?: { path?: string; equals?: unknown }; then?: Array<{ type?: string; text?: string }>; else?: Array<{ type?: string; text?: string }>; src?: string; alt?: string; width?: number; code_type?: 'qr' | 'code128' | 'ean13'; value?: string; chart_type?: 'bar' | 'line' | 'pie'; label_path?: string; value_path?: string; anchor_id?: string; toc_label?: string; toc_level?: number }
type ReusableComponent = { id: string; name: string; version: number }
type TableColumn = { header: string; path: string; format?: 'text' | 'number' | 'currency' | 'date' | 'percent' }
type Health = { status: string; dependencies: Record<string, string> }
type Ingestion = { id: string; filename: string; route: string; status: string; pagesTotal?: number; pagesProcessed?: number; resultId?: string; error?: string }
type ReviewField = { original_value: string | null; normalized_value: unknown; confidence: number; review_status: string; absent?: boolean; validation: Array<{ code: string; message: string }>; source?: { page_number?: number; element_id?: string; box?: number[] | null } | null }
type PageElement = { id: string; type?: string; role?: 'text' | 'heading' | 'list_item' | 'table_row'; text: string; box?: number[] | null }
type PageLayout = { reading_order?: string[]; headings?: string[]; lists?: string[]; tables?: Array<{ row_ids: string[] }> }
type PageModel = { document_id?: string; source?: { media_type?: string; filename?: string; route?: string }; pages?: Array<{ page_number: number; width?: number | null; height?: number | null; rotation?: number; layout?: PageLayout; elements?: PageElement[] }> }
type SourceSelection = { elementId: string | null; pageNumber: number; box?: number[] | null }
type ReviewTable = { columns: string[]; rows: Array<{ fields: Record<string, ReviewField>; source?: ReviewField['source'] }> }
type ReviewResult = { result_id: string; schema_id?: string; status: string; revision: number; fields: Record<string, ReviewField>; tables?: Record<string, ReviewTable>; page_model?: PageModel; artifact?: string; error?: string }
type RenderFontReport = { script: string; requested_stack: string; embedded_fonts: string[]; missing_glyphs: string[]; status: string }
type RenderDiagnostics = { engine?: string; status?: string; scripts?: string[]; font_stacks?: string[]; missing_glyphs?: string[]; font_report?: RenderFontReport[] }
type PdfReport = { engine?: string; status?: string; output_bytes?: number; native_reader_review?: string; fidelity?: string; render_locale?: string }

type Epic = {
  id: string
  name: string
  weight: number
  progress: number
  status: 'verified' | 'in-progress' | 'planned'
  achievement: string
}

const epicDefinitions = [
  { id: 'E1', name: 'Platform foundation and deployment', weight: 5.5 },
  { id: 'E2', name: 'Template editor', weight: 7.3 },
  { id: 'E3', name: 'Template management and governance', weight: 6.9 },
  { id: 'E4', name: 'Rendering engine and multi-language support', weight: 8.3 },
  { id: 'E5', name: 'Data binding and template logic', weight: 6.9 },
  { id: 'E6', name: 'Output formats', weight: 6.9 },
  { id: 'E7', name: 'API, SDKs and integrations', weight: 7.3 },
  { id: 'E8', name: 'Digitization: ingestion and OCR pipeline', weight: 9.2 },
  { id: 'E9', name: 'Schema and extraction', weight: 7.3 },
  { id: 'E10', name: 'Review and correction', weight: 6.4 },
  { id: 'E11', name: 'Identity, security and compliance', weight: 7.3 },
  { id: 'E12', name: 'Operations, observability and scale', weight: 5.5 },
  { id: 'E13', name: 'AI assistance and agent integration', weight: 4.6 },
  { id: 'E14', name: 'Ecosystem, documentation and community', weight: 6.0 },
  { id: 'E15', name: 'Hosted cloud and billing', weight: 4.6 },
]

const statusScore = { implemented: 1, partial: 0.5, planned: 0 } as const
const epics: Epic[] = epicDefinitions.map(epic => {
  const stories = epicStories[epic.id] ?? []
  const counts = stories.reduce((result, story) => {
    result[getStoryStatus(story.id)] += 1
    return result
  }, { implemented: 0, partial: 0, planned: 0 } as Record<'implemented' | 'partial' | 'planned', number>)
  const completion = stories.length ? stories.reduce((sum, story) => sum + statusScore[getStoryStatus(story.id)], 0) / stories.length : 0
  const status = counts.implemented === stories.length && stories.length > 0 ? 'verified' : completion > 0 ? 'in-progress' : 'planned'
  const remaining = counts.partial + counts.planned
  return {
    ...epic,
    progress: epic.weight * completion,
    status,
    achievement: `${counts.implemented} implemented, ${counts.partial} partial, ${counts.planned} planned; ${remaining} stories still need completion evidence.`,
  }
})

const totalWeight = epics.reduce((sum, epic) => sum + epic.weight, 0)
const completedPoints = epics.reduce((sum, epic) => sum + epic.progress, 0)

function SourcePreview({ review, activeElementId, activePageNumber, activeBox, draftBox, onSelect, onDrawBox }: { review: ReviewResult; activeElementId?: string | null; activePageNumber?: number; activeBox?: number[] | null; draftBox?: number[] | null; onSelect: (elementId: string, pageNumber: number, box?: number[]) => void; onDrawBox: (box: number[], pageNumber: number) => void }) {
  const pages = review.page_model?.pages ?? []
  const [pageIndex, setPageIndex] = useState(0)
  useEffect(() => { setPageIndex(0) }, [review.result_id])
  useEffect(() => {
    if (activePageNumber == null) return
    const selectedIndex = pages.findIndex(pageItem => pageItem.page_number === activePageNumber)
    if (selectedIndex >= 0) setPageIndex(selectedIndex)
  }, [activePageNumber, pages])
  const page = pages[pageIndex]
  const elements = page?.elements ?? []
  const width = page?.width ?? 612
  const height = page?.height ?? 792
  const imageSource = review.page_model?.source?.media_type?.startsWith('image/') && review.page_model?.document_id
    ? `/api/ingestions/${encodeURIComponent(review.page_model.document_id)}/source` : null
  const pdfSource = review.page_model?.source?.media_type === 'application/pdf' && review.page_model?.document_id
    ? `/api/ingestions/${encodeURIComponent(review.page_model.document_id)}/source` : null
  const [dragStart, setDragStart] = useState<[number, number] | null>(null)
  const [dragBox, setDragBox] = useState<number[] | null>(null)
  function point(event: PointerEvent<SVGSVGElement>): [number, number] {
    const bounds = event.currentTarget.getBoundingClientRect()
    return [Math.max(0, Math.min(width, (event.clientX - bounds.left) * width / bounds.width)),
      Math.max(0, Math.min(height, (event.clientY - bounds.top) * height / bounds.height))]
  }
  function updateBox(event: PointerEvent<SVGSVGElement>, finish = false) {
    if (!dragStart) return
    const [x, y] = point(event)
    const box = [Math.min(dragStart[0], x), Math.min(dragStart[1], y), Math.max(dragStart[0], x), Math.max(dragStart[1], y)]
    setDragBox(box)
    if (finish) {
      setDragStart(null)
      if (box[2] - box[0] >= 2 && box[3] - box[1] >= 2) onDrawBox(box, page.page_number)
    }
  }
  const sourceSvg = page ? <svg className={imageSource ? 'source-page source-page-overlay' : 'source-page'} viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`Page ${page.page_number} source regions`} onPointerDown={(event) => { if (event.button === 0) { setDragStart(point(event)); setDragBox(null) } }} onPointerMove={event => updateBox(event)} onPointerUp={event => updateBox(event, true)}>
    {!imageSource && <rect className="source-page-background" x="0" y="0" width={width} height={height} />}
    {elements.map(element => {
      const box = element.box ?? []
      if (box.length !== 4) return null
      const [left, top, right, bottom] = box
      const active = element.id === activeElementId && (activePageNumber == null || activePageNumber === page.page_number)
      return <g key={element.id} className={active ? 'source-element active' : 'source-element'} data-layout-role={element.role || 'text'} onClick={(event) => { event.stopPropagation(); onSelect(element.id, page.page_number, box) }} role="button" tabIndex={0} onKeyDown={event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); onSelect(element.id, page.page_number, box) } }} aria-pressed={active} aria-label={`Source element ${element.id}${element.role ? ` (${element.role})` : ''}: ${element.text}`}>
        <rect x={left} y={top} width={Math.max(1, right - left)} height={Math.max(1, bottom - top)} />
        <title>{element.text}</title>
      </g>
    })}
    {(dragBox || (draftBox && (activePageNumber == null || activePageNumber === page.page_number))) && <rect className="source-drawn-box" x={(dragBox || draftBox)![0]} y={(dragBox || draftBox)![1]} width={(dragBox || draftBox)![2] - (dragBox || draftBox)![0]} height={(dragBox || draftBox)![3] - (dragBox || draftBox)![1]} />}
    {activeBox?.length === 4 && (activePageNumber == null || activePageNumber === page.page_number) && <rect className="source-field-highlight" x={activeBox[0]} y={activeBox[1]} width={Math.max(1, activeBox[2] - activeBox[0])} height={Math.max(1, activeBox[3] - activeBox[1])} aria-label="Selected field source box" />}
  </svg> : null
  return <div className="source-preview" aria-label="Source region preview">
    <div className="source-preview-heading"><strong>{imageSource ? 'Source page image' : pdfSource ? 'Source PDF' : 'Source regions'}</strong><span>{page ? `Page ${page.page_number} of ${pages.length}` : 'Unavailable'}</span></div>
    {pages.length > 1 && <div className="source-page-controls"><button type="button" aria-label="Previous source page" disabled={pageIndex === 0} onClick={() => setPageIndex(index => Math.max(0, index - 1))}>Previous</button><button type="button" aria-label="Next source page" disabled={pageIndex >= pages.length - 1} onClick={() => setPageIndex(index => Math.min(pages.length - 1, index + 1))}>Next</button></div>}
    {page ? imageSource ? <div className="source-image-canvas"><img className="source-page-image" src={imageSource} alt={review.page_model?.source?.filename || 'Uploaded source page'} />{sourceSvg}</div> : pdfSource ? <><iframe className="source-pdf" src={pdfSource} title={review.page_model?.source?.filename || 'Uploaded source PDF'} />{sourceSvg}</> : sourceSvg : <p className="source-preview-empty">Source coordinates are unavailable for this result.</p>}
  </div>
}

function ReviewQueue({ review, onChange, onSave, onSelect }: { review: ReviewResult; onChange: (fieldName: string, value: string) => void; onSave: (fieldName: string) => void; onSelect: (fieldName: string) => void }) {
  const { t } = useTranslation()
  const entries = Object.entries(review.fields).sort(([, left], [, right]) => {
    const priority = (field: ReviewField) => field.validation.length ? 0 : field.confidence < 0.5 ? 1 : 2
    return priority(left) - priority(right)
  })
  function move(event: KeyboardEvent<HTMLInputElement>, index: number) {
    if (!['Enter', 'ArrowDown', 'ArrowUp'].includes(event.key)) return
    event.preventDefault()
    const next = event.key === 'ArrowUp' ? index - 1 : index + 1
    const target = document.getElementById(`review-priority-${review.result_id}-${next}`)
    target?.focus()
  }
  return <div className="review-priority-queue" aria-label={t('reviewQueue')}>
    <div className="review-queue-heading"><strong>{t('reviewQueue')}</strong><span>{t('reviewQueueHint')}</span></div>
    {entries.map(([name, field], index) => <label key={name} className={field.validation.length ? 'review-priority-field failed' : field.confidence < 0.5 ? 'review-priority-field low' : 'review-priority-field'}>
      <span>{name.replaceAll('_', ' ')} <small>{field.validation.length ? t('failedRule') : field.confidence < 0.5 ? t('lowConfidence') : t('reviewed')}</small></span>
      <input id={`review-priority-${review.result_id}-${index}`} value={String(field.normalized_value ?? field.original_value ?? '')} onFocus={() => onSelect(name)} onChange={event => onChange(name, event.target.value)} onBlur={() => onSave(name)} onKeyDown={event => move(event, index)} />
      <small>{t('confidence')}: {field.confidence.toFixed(2)}{field.validation.length ? ` · ${field.validation[0].message}` : ''}</small>
    </label>)}
  </div>
}

function App() {
  const { t } = useTranslation()
  const [templates, setTemplates] = useState<Template[]>([])
  const [starters, setStarters] = useState<Starter[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [selected, setSelected] = useState<Definition | null>(null)
  const [selectedTemplateId, setSelectedTemplateId] = useState<string | null>(null)
  const [editorBlocks, setEditorBlocks] = useState<EditorBlock[]>([])
  const [components, setComponents] = useState<ReusableComponent[]>([])
  const [selectedBlockIds, setSelectedBlockIds] = useState<string[]>([])
  const [snapEnabled, setSnapEnabled] = useState(true)
  const [clipboardBlock, setClipboardBlock] = useState<EditorBlock | null>(null)
  const [history, setHistory] = useState<EditorBlock[][]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const historyReady = useRef(false)
  const [editorFeedback, setEditorFeedback] = useState<string | null>(null)
  const [editorArtifact, setEditorArtifact] = useState<string | null>(null)
  const [editorDiagnostics, setEditorDiagnostics] = useState<RenderDiagnostics | null>(null)
  const [pdfUrl, setPdfUrl] = useState<string | null>(null)
  const [pdfReport, setPdfReport] = useState<PdfReport | null>(null)
  const [pdfFeedback, setPdfFeedback] = useState<string | null>(null)
  const [pdfGenerating, setPdfGenerating] = useState(false)
  const [pageSettings, setPageSettings] = useState<PageSettings>({ size: 'A4', orientation: 'portrait', marginMm: 20, header: '', footer: '', showPageNumbers: false })
  const [themeAccent, setThemeAccent] = useState('#2f6f60')
  const [themeFontFamily, setThemeFontFamily] = useState('Noto Sans')
  const [themeSpacing, setThemeSpacing] = useState('1.45')
  const [pageBackground, setPageBackground] = useState('')
  const [pageBackgroundPdf, setPageBackgroundPdf] = useState('')
  const [documentMetadata, setDocumentMetadata] = useState<DocumentMetadata>({ title: '', author: '' })
  const [previewLocale, setPreviewLocale] = useState('en')
  const [activeBlockId, setActiveBlockId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [showProjectStatus, setShowProjectStatus] = useState(false)
  const [ingestions, setIngestions] = useState<Ingestion[]>([])
  const [uploading, setUploading] = useState(false)
  const [reviews, setReviews] = useState<Record<string, ReviewResult>>({})
  const [activeSource, setActiveSource] = useState<Record<string, SourceSelection>>({})
  const [draftSourceBoxes, setDraftSourceBoxes] = useState<Record<string, number[] | null>>({})
  const [newFieldNames, setNewFieldNames] = useState<Record<string, string>>({})
  const [extracting, setExtracting] = useState<string | null>(null)
  const [schemas, setSchemas] = useState<ExtractionSchemaItem[]>([])
  const [schemaId, setSchemaId] = useState('invoice')
  const [schemaDraft, setSchemaDraft] = useState('')
  const [schemaFeedback, setSchemaFeedback] = useState<string | null>(null)
  useEffect(() => () => { if (pdfUrl) URL.revokeObjectURL(pdfUrl) }, [pdfUrl])
  useEffect(() => {
    const controller = new AbortController()
    setLoading(true); setFailed(false)
    fetch('/api/templates', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('unavailable')
      return response.json() as Promise<{ items: Template[] }>
    }).then(result => setTemplates(result.items)).catch(() => {
      if (!controller.signal.aborted) setFailed(true)
    }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    fetch('/health/ready', { signal: controller.signal }).then(response => response.json())
      .then(result => setHealth(result)).catch(() => { if (!controller.signal.aborted) setHealth(null) })
    fetch('/api/extraction-schemas', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('unavailable')
      return response.json() as Promise<{ items: ExtractionSchemaItem[] }>
    }).then(result => setSchemas(result.items)).catch(() => undefined)
    fetch('/api/starters', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('unavailable')
      return response.json() as Promise<{ items: Starter[] }>
    }).then(result => setStarters(result.items)).catch(() => undefined)
    fetch('/api/components', { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('unavailable')
      return await response.json() as { items: ReusableComponent[] }
    }).then(result => setComponents(result.items)).catch(() => undefined)
    return () => controller.abort()
  }, [attempt])
  useEffect(() => {
    const controller = new AbortController()
    fetch(`/api/extraction-schemas/${encodeURIComponent(schemaId)}`, { signal: controller.signal }).then(response => response.json())
      .then(result => { setSchemaDraft(JSON.stringify(result, null, 2)); setSchemaFeedback(null) }).catch(() => undefined)
    return () => controller.abort()
  }, [schemaId])
  useEffect(() => {
    function onKeyDown(event: globalThis.KeyboardEvent) {
      if (!(event.ctrlKey || event.metaKey)) return
      const target = event.target as HTMLElement
      if (event.key.toLowerCase() === 'z') { event.preventDefault(); event.shiftKey ? redoEditor() : undoEditor() }
      if (event.key.toLowerCase() === 'y') { event.preventDefault(); redoEditor() }
      if (event.key.toLowerCase() === 'c' && target.closest('.editor-layout')) { event.preventDefault(); copyActiveBlock() }
      if (event.key.toLowerCase() === 'v' && target.closest('.editor-layout')) { event.preventDefault(); pasteBlock() }
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  })
  useEffect(() => {
    const active = ingestions.filter(item => !item.id.startsWith('local-') && ['queued', 'running'].includes(item.status))
    if (!active.length) return
    const timer = window.setInterval(() => {
      void Promise.all(active.map(async item => {
        const response = await fetch(`/api/ingestions/${encodeURIComponent(item.id)}`)
        if (!response.ok) return null
        return await response.json() as { id: string; status: string; route: string; pages_total: number; pages_processed: number }
      })).then(results => {
        setIngestions(current => current.map(item => {
          const update = results.find(result => result?.id === item.id)
          return update ? { ...item, status: update.status, route: update.route, pagesTotal: update.pages_total, pagesProcessed: update.pages_processed } : item
        }))
      }).catch(() => undefined)
    }, 2000)
    return () => window.clearInterval(timer)
  }, [ingestions])
  async function openTemplate(id: string, boundData?: Record<string, unknown>, renderedArtifact?: string) {
    setFailed(false)
    try {
      const response = await fetch(`/api/templates/${encodeURIComponent(id)}`)
      if (!response.ok) throw new Error('unavailable')
      const definition = await response.json() as Definition
      setPreviewLocale(typeof definition.locale === 'string' ? definition.locale : 'en')
      const page = definition.page || {}
      setPageSettings({ size: (page.size === 'A3' || page.size === 'A5' || page.size === 'Letter' ? page.size : 'A4') as PageSettings['size'], orientation: page.orientation === 'landscape' ? 'landscape' : 'portrait', marginMm: typeof page.margin_mm === 'number' ? Math.min(100, Math.max(0, page.margin_mm)) : 20, header: typeof page.header === 'string' ? page.header : '', footer: typeof page.footer === 'string' ? page.footer : '', showPageNumbers: page.show_page_numbers === true })
      setDocumentMetadata({ title: typeof definition.metadata?.title === 'string' ? definition.metadata.title : '', author: typeof definition.metadata?.author === 'string' ? definition.metadata.author : '' })
      setThemeAccent(typeof definition.theme?.accent === 'string' ? definition.theme.accent : '#2f6f60')
      setThemeFontFamily(typeof definition.theme?.font_family === 'string' ? definition.theme.font_family : 'Noto Sans')
      setThemeSpacing(typeof definition.theme?.spacing === 'string' ? definition.theme.spacing : '1.45')
      setPageBackground(typeof page.background === 'string' ? page.background : '')
      setPageBackgroundPdf(typeof page.background_pdf === 'string' ? page.background_pdf : '')
      const blocks = definition.blocks.map((block, index) => { const stored = block as StoredEditorBlock; const kind = stored.type === 'component' ? 'component' as const : stored.type === 'table' ? 'table' as const : stored.type === 'loop' ? 'loop' as const : stored.type === 'if' ? 'if' as const : stored.type === 'image' ? 'image' as const : stored.type === 'code' ? 'code' as const : stored.type === 'chart' ? 'chart' as const : stored.type === 'toc' ? 'toc' as const : 'text' as const; const nestedText = stored.blocks?.[0]?.text || ''; const thenText = stored.then?.[0]?.text || ''; const elseText = stored.else?.[0]?.text || ''; return { id: `block-${index}`, text: stored.text || (kind === 'component' ? components.find(component => component.id === stored.component_id)?.name || 'Reusable component' : kind === 'table' ? 'Repeatable table' : kind === 'loop' ? 'Repeating section' : kind === 'if' ? 'Conditional section' : kind === 'image' ? 'Image' : kind === 'code' ? 'Code' : kind === 'chart' ? 'Chart' : kind === 'toc' ? 'Table of contents' : ''), bold: Boolean(stored.bold), italic: Boolean(stored.italic), color: String(stored.color || '#203d37'), fontFamily: String(stored.font_family || 'Noto Sans'), fontSize: Number(stored.font_size || 16), align: (stored.align || 'left') as EditorBlock['align'], breakBefore: stored.break_before === true, keepTogether: stored.keep_together !== false, kind, componentId: stored.component_id, items: stored.items, as: stored.as, columns: stored.columns, repeatText: nestedText, conditionPath: stored.condition?.path, conditionValue: Boolean(stored.condition?.equals), thenText, elseText, source: stored.src, alt: stored.alt, width: stored.width, codeType: stored.code_type, codeValue: stored.value, chartType: stored.chart_type, labelPath: stored.label_path, valuePath: stored.value_path, anchorId: stored.anchor_id, tocLabel: stored.toc_label, tocLevel: stored.toc_level } })
      setSelected(boundData ? { ...definition, sample_data: boundData } : definition); setSelectedTemplateId(id); setEditorBlocks(blocks); setHistory([blocks]); setHistoryIndex(0); historyReady.current = true; setSelectedBlockIds([]); setActiveBlockId(blocks[0]?.id ?? null); setEditorFeedback(null); setEditorArtifact(renderedArtifact || null); setEditorDiagnostics(null); setPdfUrl(null); setPdfReport(null); setPdfFeedback(null)
    } catch { setFailed(true) }
  }
  async function useStarter(starter: Starter, language: string) {
    const definition = starter.definitions[language]
    if (!definition) return
    const response = await fetch('/api/templates', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ name: definition.name || `${starter.name} (${language})`, definition }) })
    if (!response.ok) return
    const created = await response.json() as { id: string }
    setAttempt(value => value + 1)
    await openTemplate(created.id)
  }
  function updateActiveBlock(change: Partial<EditorBlock>) {
    if (!activeBlockId) return
    updateEditorBlocks(blocks => blocks.map(block => block.id === activeBlockId ? { ...block, ...change } : block))
  }
  function updateEditorBlocks(updater: (blocks: EditorBlock[]) => EditorBlock[]) {
    setEditorBlocks(previous => {
      const next = updater(previous)
      if (historyReady.current && JSON.stringify(next) !== JSON.stringify(previous)) {
        setHistory(current => [...current.slice(0, historyIndex + 1), next].slice(-50))
        setHistoryIndex(current => Math.min(49, current + 1))
      }
      return next
    })
  }
  function undoEditor() {
    setHistoryIndex(index => { const next = Math.max(0, index - 1); const snapshot = history[next]; if (snapshot) setEditorBlocks(snapshot); return next })
  }
  function redoEditor() {
    setHistoryIndex(index => { const next = Math.min(history.length - 1, index + 1); const snapshot = history[next]; if (snapshot) setEditorBlocks(snapshot); return next })
  }
  function copyActiveBlock() { const block = editorBlocks.find(item => item.id === activeBlockId); if (block) setClipboardBlock(block) }
  function pasteBlock() { if (!clipboardBlock) return; const copy = { ...clipboardBlock, id: `block-${Date.now()}` }; updateEditorBlocks(blocks => [...blocks, copy]); setActiveBlockId(copy.id) }
  function alignSelected(align: EditorBlock['align']) { const ids = selectedBlockIds.length ? selectedBlockIds : activeBlockId ? [activeBlockId] : []; updateEditorBlocks(blocks => blocks.map(block => ids.includes(block.id) ? { ...block, align } : block)) }
  function removeEditorBlock(blockId: string) { updateEditorBlocks(blocks => blocks.filter(block => block.id !== blockId)); setActiveBlockId(current => current === blockId ? null : current); setSelectedBlockIds(current => current.filter(id => id !== blockId)) }
  async function createComponentFromSelection() {
    const blocks = editorBlocks.filter(block => selectedBlockIds.includes(block.id) || block.id === activeBlockId)
    if (!blocks.length) return
    const name = window.prompt('Component name')?.trim()
    if (!name) return
    const definition = { blocks: blocks.map(({ id, kind, componentId, fontFamily, fontSize, breakBefore, keepTogether, ...block }) => ({ ...block, type: kind === 'text' || !kind ? 'text' : kind, ...(componentId ? { component_id: componentId } : {}), ...(fontFamily ? { font_family: fontFamily } : {}), ...(fontSize ? { font_size: fontSize } : {}), break_before: breakBefore, keep_together: keepTogether })) }
    const response = await fetch('/api/components', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ name, definition }) })
    if (!response.ok) return
    const created = await response.json() as ReusableComponent
    setComponents(current => [...current, created].sort((left, right) => left.name.localeCompare(right.name)))
    const block: EditorBlock = { id: `component-${Date.now()}`, text: name, bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left', breakBefore: false, keepTogether: true, kind: 'component', componentId: created.id }
    updateEditorBlocks(current => [...current, block]); setActiveBlockId(block.id)
  }
  async function updateComponentFromSelection() {
    const target = editorBlocks.find(block => block.id === activeBlockId && block.kind === 'component')
    if (!target?.componentId) return
    const blocks = editorBlocks.filter(block => selectedBlockIds.includes(block.id) && block.id !== target.id)
    if (!blocks.length) return
    const definition = { blocks: blocks.map(({ id, kind, componentId, fontFamily, fontSize, breakBefore, keepTogether, ...block }) => ({ ...block, type: kind === 'text' || !kind ? 'text' : kind, ...(componentId ? { component_id: componentId } : {}), ...(fontFamily ? { font_family: fontFamily } : {}), ...(fontSize ? { font_size: fontSize } : {}), break_before: breakBefore, keep_together: keepTogether })) }
    const response = await fetch(`/api/components/${encodeURIComponent(target.componentId)}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ definition }) })
    if (response.ok) setEditorFeedback(t('componentUpdated'))
  }
  function addComponent(component: ReusableComponent) { const block: EditorBlock = { id: `component-${Date.now()}`, text: component.name, bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left', breakBefore: false, keepTogether: true, kind: 'component', componentId: component.id }; updateEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id) }
  function addTextBlock() {
    const block = { id: `block-${Date.now()}`, text: 'New text block', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left' as const, breakBefore: false, keepTogether: true }
    updateEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id)
  }
  function addTableBlock() {
    const block = { id: `table-${Date.now()}`, text: 'Repeatable table', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left' as const, breakBefore: false, keepTogether: true, kind: 'table' as const, items: 'rows', columns: [{ header: 'Description', path: 'description', format: 'text' as const }, { header: 'Amount', path: 'amount', format: 'currency' as const }] }
    updateEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id); setSelected(current => current ? { ...current, sample_data: { ...(current.sample_data as Record<string, unknown>), rows: [{ description: 'Example item', amount: 12.5 }, { description: 'Second item', amount: 7.5 }] } } : current)
  }
  function addRepeatBlock() {
    const block = { id: `loop-${Date.now()}`, text: 'Repeating section', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left' as const, breakBefore: false, keepTogether: true, kind: 'loop' as const, items: 'rows', as: 'row', repeatText: '{{row.description}} — {{currency(row.amount)}}' }
    setEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id); setSelected(current => current ? { ...current, sample_data: { ...(current.sample_data as Record<string, unknown>), rows: [{ description: 'Example item', amount: 12.5 }, { description: 'Second item', amount: 7.5 }] } } : current)
  }
  function addConditionalBlock() {
    const block = { id: `if-${Date.now()}`, text: 'Conditional section', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left' as const, breakBefore: false, keepTogether: true, kind: 'if' as const, conditionPath: 'show_note', conditionValue: true, thenText: 'This note is enabled.', elseText: 'This note is disabled.' }
    updateEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id); setSelected(current => current ? { ...current, sample_data: { ...(current.sample_data as Record<string, unknown>), show_note: true } } : current)
  }
  function addImageBlock() {
    const block = { id: `image-${Date.now()}`, text: 'Image', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left' as const, breakBefore: false, keepTogether: true, kind: 'image' as const, source: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=', alt: 'Image', width: 240 }
    setEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id); setSelectedBlockIds([])
  }
  function addCodeBlock() {
    const block = { id: `code-${Date.now()}`, text: 'QR code', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left' as const, breakBefore: false, keepTogether: true, kind: 'code' as const, codeType: 'qr' as const, codeValue: '{{order.id}}', width: 220 }
    setEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id)
    setSelected(current => current ? { ...current, sample_data: { ...(current.sample_data as Record<string, unknown>), order: { id: 'ORDER-001', code: 'ABC123', ean: '5901234123457' } } } : current)
  }
  function addChartBlock() {
    const block: EditorBlock = { id: `chart-${Date.now()}`, text: 'Chart', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left', breakBefore: false, keepTogether: true, kind: 'chart', items: 'chart_rows', chartType: 'bar', labelPath: 'label', valuePath: 'value', alt: 'Data chart' }
    updateEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id)
    setSelected(current => current ? { ...current, sample_data: { ...(current.sample_data as Record<string, unknown>), chart_rows: [{ label: 'A', value: 10 }, { label: 'B', value: 20 }] } } : current)
  }
  function addTocBlock() {
    const block: EditorBlock = { id: `toc-${Date.now()}`, text: 'Table of contents', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left', breakBefore: false, keepTogether: true, kind: 'toc' }
    updateEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id)
  }
  async function generateSampleData() {
    if (!selectedTemplateId) return
    const response = await fetch(`/api/templates/${encodeURIComponent(selectedTemplateId)}/sample-data`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ draft: true, locale: previewLocale }) })
    if (!response.ok) return
    const body = await response.json() as { sample_data: Record<string, unknown> }
    setSelected(current => current ? { ...current, sample_data: body.sample_data } : current)
    setEditorFeedback(t('sampleDataGenerated'))
  }
  async function saveEditorDraft(): Promise<boolean> {
    if (!selectedTemplateId || !selected) return false
    const definition = { ...selected, metadata: documentMetadata, theme: { ...(selected.theme || {}), accent: themeAccent, font_family: themeFontFamily, spacing: themeSpacing }, page: { size: pageSettings.size, orientation: pageSettings.orientation, margin_mm: pageSettings.marginMm, header: pageSettings.header, footer: pageSettings.footer, show_page_numbers: pageSettings.showPageNumbers, ...(pageBackground ? { background: pageBackground } : {}) }, blocks: editorBlocks.map(({ id, fontFamily, fontSize, kind, componentId, items, as, columns, repeatText, conditionPath, conditionValue, thenText, elseText, source, alt, width, codeType, codeValue, chartType, labelPath, valuePath, anchorId, tocLabel, tocLevel, breakBefore, keepTogether, ...block }) => kind === 'component' ? ({ type: 'component', component_id: componentId, break_before: breakBefore, keep_together: keepTogether }) : kind === 'table' ? ({ type: 'table', items: items || 'rows', columns: columns || [], break_before: breakBefore, keep_together: keepTogether }) : kind === 'loop' ? ({ type: 'loop', items: items || 'rows', as: as || 'row', blocks: [{ type: 'text', text: repeatText || '' }], break_before: breakBefore, keep_together: keepTogether }) : kind === 'if' ? ({ type: 'if', condition: { path: conditionPath || 'show_note', equals: conditionValue === true }, then: [{ type: 'text', text: thenText || '' }], else: [{ type: 'text', text: elseText || '' }], break_before: breakBefore, keep_together: keepTogether }) : kind === 'image' ? ({ type: 'image', src: source || '', alt: alt || 'Image', width: width || 240, align: block.align || 'left', break_before: breakBefore, keep_together: keepTogether }) : kind === 'code' ? ({ type: 'code', code_type: codeType || 'qr', value: codeValue || '', width: width || 220, align: block.align || 'left', break_before: breakBefore, keep_together: keepTogether }) : kind === 'chart' ? ({ type: 'chart', items: items || 'rows', chart_type: chartType || 'bar', label_path: labelPath || 'label', value_path: valuePath || 'value', alt: alt || 'Data chart', break_before: breakBefore, keep_together: keepTogether }) : kind === 'toc' ? ({ type: 'toc', break_before: breakBefore, keep_together: keepTogether }) : ({ ...block, type: 'text', ...(anchorId ? { anchor_id: anchorId, toc_label: tocLabel || block.text, toc_level: tocLevel || 1 } : {}), font_family: fontFamily, font_size: fontSize, break_before: breakBefore, keep_together: keepTogether })) }
    if (pageBackgroundPdf) (definition.page as Record<string, unknown>).background_pdf = pageBackgroundPdf
    const versionResponse = await fetch(`/api/templates/${encodeURIComponent(selectedTemplateId)}/versions`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ definition, change_summary: 'Saved from workspace editor' }) })
    if (!versionResponse.ok) { setEditorFeedback(t('editorSaveFailed')); return false }
    const renderResponse = await fetch(`/api/templates/${encodeURIComponent(selectedTemplateId)}/render`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ draft: true, data: selected.sample_data, locale: previewLocale }) })
    let rendered = await renderResponse.json() as RenderDiagnostics & { artifact?: string; id?: string; result?: (RenderDiagnostics & { artifact?: string }); error?: string }
    if (renderResponse.status === 202 && rendered.id) {
      for (let attempt = 0; attempt < 150; attempt += 1) {
        await new Promise(resolve => window.setTimeout(resolve, 200))
        const jobResponse = await fetch(`/api/jobs/${encodeURIComponent(rendered.id)}`)
        if (!jobResponse.ok) throw new Error('render job unavailable')
        const job = await jobResponse.json() as { status: string; result?: RenderDiagnostics & { artifact?: string }; error?: string }
        if (job.status === 'done') { rendered = { ...rendered, ...job.result, status: job.status, artifact: job.result?.artifact }; break }
        if (job.status === 'failed') throw new Error(job.error || 'render job failed')
      }
    }
    const artifact = rendered.artifact || rendered.result?.artifact || null
    setEditorArtifact(renderResponse.ok && artifact ? artifact : null)
    setEditorDiagnostics(renderResponse.ok ? rendered : null)
    setEditorFeedback(renderResponse.ok && artifact ? t('editorSaved') : t('editorRenderFailed'))
    return renderResponse.ok && Boolean(artifact)
  }
  async function generatePdf() {
    if (!selectedTemplateId || !selected || pdfGenerating) return
    setPdfGenerating(true)
    setPdfFeedback(null)
    try {
      const saved = await saveEditorDraft()
      if (!saved) throw new Error(t('editorSaveFailed'))
      const response = await fetch(`/api/templates/${encodeURIComponent(selectedTemplateId)}/render-pdf`, {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ draft: true, data: selected.sample_data, locale: previewLocale }),
      })
      const body = await response.json() as { document_base64?: string; report?: PdfReport; detail?: string }
      if (!response.ok || !body.document_base64) throw new Error(body.detail || t('pdfGenerateFailed'))
      const binary = atob(body.document_base64)
      const bytes = Uint8Array.from(binary, character => character.charCodeAt(0))
      const nextUrl = URL.createObjectURL(new Blob([bytes], { type: 'application/pdf' }))
      setPdfUrl(previous => { if (previous) URL.revokeObjectURL(previous); return nextUrl })
      setPdfReport(body.report || null)
      setPdfFeedback(t('pdfGenerated'))
    } catch (error) {
      setPdfFeedback(error instanceof Error ? error.message : t('pdfGenerateFailed'))
      setPdfReport(null)
    } finally {
      setPdfGenerating(false)
    }
  }
  function moveBlock(sourceId: string, targetId: string) {
    if (sourceId === targetId) return
    setEditorBlocks(blocks => { const source = blocks.find(block => block.id === sourceId); if (!source) return blocks; const remaining = blocks.filter(block => block.id !== sourceId); const targetIndex = remaining.findIndex(block => block.id === targetId); remaining.splice(targetIndex, 0, source); return remaining })
  }
  function dropBlockOnPage(sourceId: string) {
    setEditorBlocks(blocks => {
      const source = blocks.find(block => block.id === sourceId)
      if (!source) return blocks
      return [...blocks.filter(block => block.id !== sourceId), source]
    })
    setActiveBlockId(sourceId)
  }
  async function uploadFiles(files: FileList | null) {
    if (!files?.length) return
    setUploading(true)
    const pending = Array.from(files).map(file => ({ id: `local-${file.name}-${file.lastModified}`, filename: file.name, route: 'pending', status: 'uploading' }))
    setIngestions(current => [...pending, ...current])
    for (const [index, file] of Array.from(files).entries()) {
      const localId = pending[index].id
      try {
        const response = await fetch(`/api/ingestions?filename=${encodeURIComponent(file.name)}`, { method: 'POST', headers: { 'content-type': file.type || 'application/octet-stream' }, body: file })
        const body = await response.json() as { id?: string; route?: string; status?: string; pages_total?: number; pages_processed?: number; detail?: string }
        if (!response.ok) throw new Error(body.detail || t('uploadFailed'))
        setIngestions(current => current.map(item => item.id === localId ? { id: body.id!, filename: file.name, route: body.route || 'unknown', status: body.status || 'queued', pagesTotal: body.pages_total, pagesProcessed: body.pages_processed } : item))
      } catch (error) {
        setIngestions(current => current.map(item => item.id === localId ? { ...item, route: 'unknown', status: 'failed', error: error instanceof Error ? error.message : t('uploadFailed') } : item))
      }
    }
    setUploading(false)
  }
  async function extractDocument(item: Ingestion) {
    setExtracting(item.id)
    try {
      let extractionPayload: { schema_id: string; schema?: unknown } = { schema_id: schemaId }
      try { extractionPayload = { schema_id: schemaId, schema: JSON.parse(schemaDraft) as unknown } } catch { /* use bundled schema when the draft is not JSON */ }
      const response = await fetch(`/api/ingestions/${encodeURIComponent(item.id)}/extract`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ ...extractionPayload, async: true }) })
      const queued = await response.json() as { id?: string; detail?: string }
      if (!response.ok || !queued.id) throw new Error(queued.detail || t('extractionFailed'))
      setIngestions(current => current.map(entry => entry.id === item.id ? { ...entry, status: 'running', pagesProcessed: 0 } : entry))
      let result: ReviewResult | null = null
      for (let attempt = 0; attempt < 150; attempt += 1) {
        await new Promise(resolve => window.setTimeout(resolve, 200))
        const [jobResponse, ingestionResponse] = await Promise.all([
          fetch(`/api/jobs/${encodeURIComponent(queued.id)}`),
          fetch(`/api/ingestions/${encodeURIComponent(item.id)}`),
        ])
        if (ingestionResponse.ok) {
          const progress = await ingestionResponse.json() as { status: string; route: string; pages_total: number; pages_processed: number }
          setIngestions(current => current.map(entry => entry.id === item.id ? { ...entry, status: progress.status, route: progress.route, pagesTotal: progress.pages_total, pagesProcessed: progress.pages_processed } : entry))
        }
        if (!jobResponse.ok) throw new Error(t('extractionFailed'))
        const job = await jobResponse.json() as { status: string; result?: ReviewResult; error?: string }
        if (job.status === 'done') { result = job.result || null; break }
        if (job.status === 'failed') throw new Error(job.error || t('extractionFailed'))
      }
      if (!result) throw new Error(t('extractionFailed'))
      result.revision = result.revision || 1
      setReviews(current => ({ ...current, [result.result_id]: result }))
      const firstSource = Object.values(result.fields)[0]?.source
      setActiveSource(current => ({ ...current, [result.result_id]: { elementId: firstSource?.element_id ?? null, pageNumber: firstSource?.page_number ?? 1, box: firstSource?.box ?? null } }))
      setIngestions(current => current.map(entry => entry.id === item.id ? { ...entry, resultId: result.result_id } : entry))
    } catch (error) {
      setIngestions(current => current.map(entry => entry.id === item.id ? { ...entry, error: error instanceof Error ? error.message : t('extractionFailed') } : entry))
    } finally { setExtracting(null) }
  }
  async function validateSchemaDraft() {
    try {
      const schema = JSON.parse(schemaDraft) as unknown
      const response = await fetch('/api/extraction-schemas/validate', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ schema }) })
      const body = await response.json() as { valid?: boolean; detail?: string }
      setSchemaFeedback(response.ok && body.valid ? t('schemaValid') : body.detail || t('schemaInvalid'))
    } catch { setSchemaFeedback(t('schemaJsonInvalid')) }
  }
  async function uploadAsset(file: File, blockId: string) {
    const response = await fetch(`/api/assets?filename=${encodeURIComponent(file.name)}`, { method: 'POST', headers: { 'content-type': file.type }, body: file })
    const body = await response.json() as { url?: string; detail?: string }
    if (!response.ok || !body.url) throw new Error(body.detail || 'asset upload failed')
    setEditorBlocks(blocks => blocks.map(block => block.id === blockId ? { ...block, source: body.url } : block))
  }
  function changeReviewField(resultId: string, fieldName: string, value: string) {
    setReviews(current => ({ ...current, [resultId]: { ...current[resultId], fields: { ...current[resultId].fields, [fieldName]: { ...current[resultId].fields[fieldName], normalized_value: value, review_status: 'in_review' } } } }))
  }
  function selectReviewSource(resultId: string, fieldName: string) {
    const source = reviews[resultId]?.fields[fieldName]?.source
    selectReviewSourceValue(resultId, source)
  }
  function selectReviewSourceValue(resultId: string, source: ReviewField['source']) {
    setActiveSource(current => ({ ...current, [resultId]: { elementId: source?.element_id ?? null, pageNumber: source?.page_number ?? 1, box: source?.box ?? null } }))
  }
  async function saveReviewField(resultId: string, fieldName: string, absent = false) {
    const review = reviews[resultId]
    if (!review) return
    const field = review.fields[fieldName]
    const response = await fetch(`/api/extractions/${encodeURIComponent(resultId)}/fields/${encodeURIComponent(fieldName)}`, { method: 'PATCH', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ expected_revision: review.revision, value: absent ? null : field.normalized_value, absent, actor: 'workspace-reviewer' }) })
    const body = await response.json() as { revision?: number; status?: string; detail?: string }
    if (!response.ok) { setReviews(current => ({ ...current, [resultId]: { ...current[resultId], error: body.detail || t('saveFailed') } })); return }
    setReviews(current => ({ ...current, [resultId]: { ...current[resultId], revision: body.revision || review.revision, status: body.status || 'in_review', error: undefined } }))
  }
  async function addReviewField(resultId: string) {
    const review = reviews[resultId]
    const name = (newFieldNames[resultId] || '').trim()
    const selection = activeSource[resultId]
    const pages = review?.page_model?.pages ?? []
    const sourcePage = pages.find(item => item.page_number === selection?.pageNumber) ?? pages[0]
    const element = pages.flatMap(item => item.elements ?? []).find(item => item.id === selection?.elementId)
    const drawnBox = draftSourceBoxes[resultId]
    if (!review || !name || (!element && !drawnBox)) {
      setReviews(current => ({ ...current, [resultId]: { ...current[resultId], error: t('addFieldRequiresNameAndSource') } }))
      return
    }
    const response = await fetch(`/api/extractions/${encodeURIComponent(resultId)}/fields`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ field: name, expected_revision: review.revision, value: element?.text || null, source: { page_number: sourcePage?.page_number ?? selection?.pageNumber ?? 1, element_id: element?.id, box: element?.box || drawnBox } }) })
    const body = await response.json() as { revision?: number; detail?: string }
    if (!response.ok) { setReviews(current => ({ ...current, [resultId]: { ...current[resultId], error: body.detail || t('saveFailed') } })); return }
    const refreshed = await fetch(`/api/extractions/${encodeURIComponent(resultId)}`).then(result => result.json() as Promise<ReviewResult>)
    setReviews(current => ({ ...current, [resultId]: { ...refreshed, error: undefined } }))
    setNewFieldNames(current => ({ ...current, [resultId]: '' }))
    setDraftSourceBoxes(current => ({ ...current, [resultId]: null }))
  }
  async function undoReviewField(resultId: string) {
    const review = reviews[resultId]
    if (!review) return
    const response = await fetch(`/api/extractions/${encodeURIComponent(resultId)}/undo`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ expected_revision: review.revision }) })
    const body = await response.json() as { detail?: string }
    if (!response.ok) { setReviews(current => ({ ...current, [resultId]: { ...current[resultId], error: body.detail || t('undoFailed') } })); return }
    const refreshed = await fetch(`/api/extractions/${encodeURIComponent(resultId)}`).then(result => result.json() as Promise<ReviewResult>)
    setReviews(current => ({ ...current, [resultId]: { ...refreshed, error: undefined } }))
  }
  async function changeReviewStatus(resultId: string, status: 'approved' | 'rejected') {
    const response = await fetch(`/api/extractions/${encodeURIComponent(resultId)}/review`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ status }) })
    const body = await response.json() as { status?: string; detail?: string }
    setReviews(current => ({ ...current, [resultId]: { ...current[resultId], status: response.ok ? body.status || status : current[resultId].status, error: response.ok ? undefined : body.detail || t('saveFailed') } }))
  }
  async function renderApproved(resultId: string) {
    const template = templates[0]
    if (!template) return
    const response = await fetch(`/api/templates/${encodeURIComponent(template.id)}/render-approved`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ extraction_id: resultId }) })
    const body = await response.json() as { artifact?: string; data?: Record<string, unknown>; detail?: string }
    if (response.ok && body.artifact && body.data) {
      await openTemplate(template.id, body.data, body.artifact)
    }
    setReviews(current => ({ ...current, [resultId]: { ...current[resultId], artifact: response.ok ? body.artifact : undefined, error: response.ok ? undefined : body.detail || t('renderFailed') } }))
  }
  return <>
    <header><a className="brand" href="/"><span className="mark" aria-hidden="true">D</span>{t('brand')}</a><span className="workspace">{t('workspace')}</span></header>
    <main>
      <section className="intro"><p className="eyebrow">{t('eyebrow')}</p><h1>{t('heading')}</h1><p>{t('description')}</p></section>
      {showProjectStatus ? <section className="project-status-view" aria-labelledby="project-status-title">
        <a className="back-link" href="/" onClick={event => { event.preventDefault(); setShowProjectStatus(false) }}>{t('backToWorkspace')}</a>
        <div className="project-status-heading"><div><p className="eyebrow">{t('projectEyebrow')}</p><h2 id="project-status-title">{t('projectStatus')}</h2></div><span className="status-date">{t('statusSnapshot')}</span></div>
        <div className="overall-status"><span>{t('overallStatus')}</span><strong>{completedPoints.toFixed(1)}%</strong><div className="progress-track" role="progressbar" aria-label={t('overallProgress')} aria-valuemin={0} aria-valuemax={100} aria-valuenow={completedPoints}><span style={{ width: `${completedPoints}%` }} /></div></div>
        <div className="table-wrap"><table className="story-table"><caption>{t('epicTableCaption')}</caption><thead><tr><th scope="col">{t('storyId')}</th><th scope="col">{t('story')}</th><th scope="col">{t('priority')}</th><th scope="col">{t('size')}</th><th scope="col">{t('storyStatus')}</th></tr></thead><tbody>{epics.map(epic => <><tr className="epic-group" key={`${epic.id}-group`}><th colSpan={5} scope="colgroup"><span className="epic-group-id">{epic.id}</span><span className="epic-group-name">{epic.name}</span><span className={`epic-status ${epic.status}`}>{t(epic.status)}</span><span className="epic-group-meta">{t('weight')}: {epic.weight.toFixed(1)} · {epic.progress.toFixed(1)} {t('of')} {epic.weight.toFixed(1)}</span></th></tr>{(epicStories[epic.id] ?? []).map(item => { const status = getStoryStatus(item.id); return <tr key={item.id}><th scope="row" className="story-id">{item.id}</th><td className="story-title">{item.story}</td><td><span className={`priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span></td><td className="story-size">{item.size}</td><td><span className={`story-status ${status}`}>{t(`storyStatus.${status}`)}</span></td></tr> })}</>)}</tbody></table></div>
      </section> : <>
      <section className="project-status-banner" aria-labelledby="project-status-link-title"><div><p className="eyebrow">{t('projectEyebrow')}</p><h2 id="project-status-link-title">{t('projectStatus')}</h2><p>{t('projectNote')}</p></div><a href="#project-status" onClick={event => { event.preventDefault(); setShowProjectStatus(true) }}>{t('viewProjectStatus')} <span aria-hidden="true">&rarr;</span></a></section>
      <section className="ingestion-panel" aria-labelledby="ingestion-title">
        <div><p className="eyebrow">{t('ingestionEyebrow')}</p><h2 id="ingestion-title">{t('ingestionTitle')}</h2><p>{t('ingestionNote')}</p></div>
         <label className="upload-control">{uploading ? t('uploading') : t('chooseFiles')}<input type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff" disabled={uploading} onChange={event => { void uploadFiles(event.target.files); event.currentTarget.value = '' }} /></label>
         <div className="schema-controls"><label>{t('extractionSchema')} <select value={schemaId} onChange={event => setSchemaId(event.target.value)}>{schemas.map(schema => <option key={schema.id} value={schema.id}>{schema.name}</option>)}</select></label><details><summary>{t('editSchema')}</summary><textarea aria-label={t('schemaJson')} value={schemaDraft} onChange={event => setSchemaDraft(event.target.value)} /><button type="button" onClick={() => void validateSchemaDraft()}>{t('validateSchema')}</button>{schemaFeedback && <small role="status">{schemaFeedback}</small>}</details></div>
        {ingestions.length > 0 && <ul className="ingestion-list">{ingestions.map(item => <li key={item.id}><span className="ingestion-filename">{item.filename}</span><span className={`ingestion-status ${item.status}`}>{item.status === 'queued' ? t('queued') : item.status === 'uploading' ? t('uploading') : item.status === 'failed' ? t('failed') : item.status}</span><span className="ingestion-route">{item.route}</span>{item.pagesTotal !== undefined && <span className="ingestion-progress">{item.pagesProcessed ?? 0}/{item.pagesTotal} {t('pages')}</span>}{item.id && !item.id.startsWith('local-') && !item.resultId && <button className="ingestion-action" type="button" disabled={extracting === item.id} onClick={() => void extractDocument(item)}>{extracting === item.id ? t('extracting') : t('extract')}</button>}{item.resultId && <span className="ingestion-progress">{t('reviewReady')}</span>}{item.error && <small>{item.error}</small>}</li>)}</ul>}
         {Object.values(reviews).map(review => <article className="review-card" key={review.result_id} aria-labelledby={`review-${review.result_id}`}><div className="review-card-heading"><div><p className="eyebrow">{t('reviewEyebrow')}</p><h3 id={`review-${review.result_id}`}>{t('reviewTitle')}</h3></div><span className={`review-state ${review.status}`}>{review.status}</span></div><p className="review-note">{t('reviewNote')}</p><div className="review-fields">{Object.entries(review.fields).map(([name, field]) => <label key={name}><span>{name.replaceAll('_', ' ')}</span><input value={String(field.normalized_value ?? field.original_value ?? '')} onFocus={() => selectReviewSource(review.result_id, name)} onChange={event => changeReviewField(review.result_id, name, event.target.value)} onBlur={() => void saveReviewField(review.result_id, name)} /><small>{t('confidence')}: {field.confidence.toFixed(2)}{field.validation.length ? ` · ${field.validation[0].message}` : ''}</small><button type="button" className="review-absent" onClick={() => void saveReviewField(review.result_id, name, true)}>{t('markAbsent')}</button></label>)}</div>{Object.entries(review.tables ?? {}).map(([tableName, table]) => <section className="review-line-items" key={tableName} aria-label={`${tableName} extracted values`}><h4>{tableName.replaceAll('_', ' ')}</h4><table><thead><tr>{table.columns.map(column => <th scope="col" key={column}>{column.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{table.rows.map((row, rowIndex) => <tr key={`${tableName}-${rowIndex}`}>{table.columns.map(column => { const field = row.fields[column]; return <td key={column}><button type="button" className="review-source-value" onClick={() => selectReviewSourceValue(review.result_id, field?.source)}>{String(field?.normalized_value ?? field?.original_value ?? '')}</button></td> })}</tr>)}</tbody></table></section>)}<div className="review-actions"><button type="button" onClick={() => void changeReviewStatus(review.result_id, 'approved')}>{t('approve')}</button><button type="button" onClick={() => void changeReviewStatus(review.result_id, 'rejected')}>{t('reject')}</button>{review.status === 'approved' && <button type="button" onClick={() => void renderApproved(review.result_id)} disabled={!templates.length}>{t('sendToTemplate')}</button>}</div>{review.artifact && <pre className="review-artifact">{review.artifact}</pre>}{review.error && <p className="error" role="alert">{review.error}</p>}</article>)}
         {Object.values(reviews).map(review => <div className="review-source-stack" key={`${review.result_id}-source`}><SourcePreview review={review} activeElementId={activeSource[review.result_id]?.elementId} activePageNumber={activeSource[review.result_id]?.pageNumber} activeBox={activeSource[review.result_id]?.box} draftBox={draftSourceBoxes[review.result_id]} onSelect={(elementId, pageNumber, box) => setActiveSource(current => ({ ...current, [review.result_id]: { elementId, pageNumber, box: box ?? null } }))} onDrawBox={(box, pageNumber) => { setActiveSource(current => ({ ...current, [review.result_id]: { elementId: null, pageNumber, box: null } })); setDraftSourceBoxes(current => ({ ...current, [review.result_id]: box })) }} /><div><ReviewQueue review={review} onChange={(name, value) => changeReviewField(review.result_id, name, value)} onSave={name => void saveReviewField(review.result_id, name)} onSelect={name => selectReviewSource(review.result_id, name)} /><div className="review-manual-actions"><label>{t('newFieldName')}<input value={newFieldNames[review.result_id] || ''} onChange={event => setNewFieldNames(current => ({ ...current, [review.result_id]: event.target.value }))} /></label><button type="button" onClick={() => void addReviewField(review.result_id)}>{t('addMissingField')}</button><button type="button" onClick={() => void undoReviewField(review.result_id)}>{t('undoCorrection')}</button></div><div className="source-field-links" aria-label="Extracted field source links">{Object.entries(review.fields).map(([name, field]) => { const active = field.source?.element_id === activeSource[review.result_id]?.elementId && field.source?.page_number === activeSource[review.result_id]?.pageNumber; return <button type="button" aria-pressed={active} className={active ? 'active' : ''} key={name} onClick={() => selectReviewSource(review.result_id, name)}>{name.replaceAll('_', ' ')}{field.source?.element_id ? ` (${field.source.element_id})` : ' (no source region)'}</button> })}</div></div></div>)}
       </section>
      {!selected && <section className="starter-gallery" aria-labelledby="starter-gallery-title"><div className="section-title"><div><p className="eyebrow">{t('starterEyebrow')}</p><h2 id="starter-gallery-title">{t('starterGallery')}</h2></div></div><p className="starter-gallery-note">{t('starterGalleryNote')}</p><div className="starter-grid">{starters.map(starter => <article className="starter-card" key={starter.id}><h3>{starter.name}</h3><div className="starter-languages">{starter.languages.map(language => <button type="button" key={language} onClick={() => void useStarter(starter, language)}>{t('useStarter')} · {language}</button>)}</div></article>)}</div></section>}
      <div className="workspace-grid">
        <section aria-labelledby="templates-title" className="library">
          <div className="section-title"><h2 id="templates-title">{t('templates')}</h2><span className="count">{templates.length}</span></div>
          {loading && <p role="status">{t('loading')}</p>}
          {failed && <div role="alert" className="error"><p>{t('error')}</p><button onClick={() => setAttempt(value => value + 1)}>{t('retry')}</button></div>}
          {!loading && !failed && !selected && templates.length === 0 && <p>{t('empty')}</p>}
          {selected ? <article className="detail">
            <button className="text-button" onClick={() => setSelected(null)}>{t('back')}</button>
            <h3>{selected.name}</h3><h4>{t('structure')}</h4>
            <div className="editor-note">{t('editorDraftNote')}</div>
            <div className="editor-toolbar" aria-label={t('editorToolbar')}>
              <button type="button" onClick={undoEditor} disabled={historyIndex <= 0} aria-label="Undo">↶ {t('undo')}</button><button type="button" onClick={redoEditor} disabled={historyIndex < 0 || historyIndex >= history.length - 1} aria-label="Redo">↷ {t('redo')}</button><button type="button" onClick={copyActiveBlock} aria-label="Copy block">{t('copy')}</button><button type="button" onClick={pasteBlock} disabled={!clipboardBlock} aria-label="Paste block">{t('paste')}</button><button type="button" onClick={() => setSnapEnabled(value => !value)} aria-pressed={snapEnabled}>{t('snap')}</button><button type="button" onClick={() => alignSelected('left')}>{t('alignLeft')}</button><button type="button" onClick={() => alignSelected('center')}>{t('alignCenter')}</button><button type="button" onClick={() => alignSelected('right')}>{t('alignRight')}</button>
              <button type="button" onClick={() => updateActiveBlock({ bold: !editorBlocks.find(block => block.id === activeBlockId)?.bold })} aria-pressed={Boolean(editorBlocks.find(block => block.id === activeBlockId)?.bold)}>{t('bold')}</button>
              <button type="button" onClick={() => updateActiveBlock({ italic: !editorBlocks.find(block => block.id === activeBlockId)?.italic })} aria-pressed={Boolean(editorBlocks.find(block => block.id === activeBlockId)?.italic)}>{t('italic')}</button>
              <label>{t('textColor')} <input type="color" value={editorBlocks.find(block => block.id === activeBlockId)?.color ?? '#203d37'} onChange={event => updateActiveBlock({ color: event.target.value })} /></label>
              <label>{t('font')} <select value={editorBlocks.find(block => block.id === activeBlockId)?.fontFamily ?? 'Noto Sans'} onChange={event => updateActiveBlock({ fontFamily: event.target.value })}><option>Noto Sans</option><option>Arial</option><option>Georgia</option></select></label>
              <label>{t('fontSize')} <input type="number" min="8" max="96" value={editorBlocks.find(block => block.id === activeBlockId)?.fontSize ?? 16} onChange={event => updateActiveBlock({ fontSize: Math.min(96, Math.max(8, Number(event.target.value) || 16)) })} /></label>
              <label>{t('alignment')} <select value={editorBlocks.find(block => block.id === activeBlockId)?.align ?? 'left'} onChange={event => updateActiveBlock({ align: event.target.value as EditorBlock['align'] })}><option value="left">{t('left')}</option><option value="center">{t('center')}</option><option value="right">{t('right')}</option></select></label>
              <label><input type="checkbox" checked={Boolean(editorBlocks.find(block => block.id === activeBlockId)?.breakBefore)} onChange={event => updateActiveBlock({ breakBefore: event.target.checked })} /> {t('pageBreakBefore')}</label>
              <label><input type="checkbox" checked={editorBlocks.find(block => block.id === activeBlockId)?.keepTogether !== false} onChange={event => updateActiveBlock({ keepTogether: event.target.checked })} /> {t('keepTogether')}</label>
              <button type="button" onClick={addTextBlock}>{t('addTextBlock')}</button>
              <button type="button" onClick={addTableBlock}>{t('addTableBlock')}</button>
              <button type="button" onClick={addRepeatBlock}>{t('addRepeatBlock')}</button>
              <button type="button" onClick={addConditionalBlock}>{t('addConditionalBlock')}</button>
              <button type="button" onClick={addImageBlock}>{t('addImageBlock')}</button>
              <button type="button" onClick={addCodeBlock}>{t('addCodeBlock')}</button>
              <button type="button" onClick={addChartBlock}>{t('addChartBlock')}</button>
              <button type="button" onClick={addTocBlock}>{t('addTocBlock')}</button>
              <button type="button" onClick={() => void generateSampleData()}>{t('generateSampleData')}</button>
              <button type="button" onClick={() => void saveEditorDraft()}>{t('saveDraft')}</button>
              <button type="button" onClick={() => void generatePdf()} disabled={pdfGenerating}>{pdfGenerating ? t('generatingPdf') : t('generatePdf')}</button>
            </div>
            <div className="page-settings" aria-label={t('pageSettings')}><h4>{t('pageSettings')}</h4><div className="page-settings-grid"><label>{t('previewLocale')} <select value={previewLocale} onChange={event => setPreviewLocale(event.target.value)}><option value="en">English</option><option value="en-GB">English (UK)</option><option value="de-DE">Deutsch</option><option value="ar">العربية</option><option value="hi">हिन्दी</option><option value="th">ไทย</option><option value="zh-CN">中文</option><option value="ja-JP">日本語</option></select></label><label>{t('documentTitle')} <input value={documentMetadata.title} onChange={event => setDocumentMetadata(current => ({ ...current, title: event.target.value }))} /></label><label>{t('documentAuthor')} <input value={documentMetadata.author} onChange={event => setDocumentMetadata(current => ({ ...current, author: event.target.value }))} /></label><label>{t('pageSize')} <select value={pageSettings.size} onChange={event => setPageSettings(current => ({ ...current, size: event.target.value as PageSettings['size'] }))}><option value="A3">A3</option><option value="A4">A4</option><option value="A5">A5</option><option value="Letter">Letter</option></select></label><label>{t('orientation')} <select value={pageSettings.orientation} onChange={event => setPageSettings(current => ({ ...current, orientation: event.target.value as PageSettings['orientation'] }))}><option value="portrait">{t('portrait')}</option><option value="landscape">{t('landscape')}</option></select></label><label>{t('margins')} <input type="number" min="0" max="100" value={pageSettings.marginMm} onChange={event => setPageSettings(current => ({ ...current, marginMm: Math.min(100, Math.max(0, Number(event.target.value) || 0)) }))} /> mm</label><label>{t('pageHeader')} <input value={pageSettings.header} onChange={event => setPageSettings(current => ({ ...current, header: event.target.value }))} /></label><label>{t('pageFooter')} <input value={pageSettings.footer} onChange={event => setPageSettings(current => ({ ...current, footer: event.target.value }))} /></label><label><input type="checkbox" checked={pageSettings.showPageNumbers} onChange={event => setPageSettings(current => ({ ...current, showPageNumbers: event.target.checked }))} /> {t('pageNumbers')}</label><label>{t('themeAccent')} <input type="color" value={themeAccent} onChange={event => setThemeAccent(event.target.value)} /></label><label>{t('pageBackground')} <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" onChange={event => { const file = event.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = () => setPageBackground(String(reader.result || '')); reader.readAsDataURL(file) } event.currentTarget.value = '' }} /></label></div></div>
            <div className="pdf-background-control"><label>{t('pdfBackground')} <input type="file" accept="application/pdf,.pdf" onChange={event => { const file = event.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = () => setPageBackgroundPdf(String(reader.result || '')); reader.readAsDataURL(file) } event.currentTarget.value = '' }} /></label></div>
            <div className="structure-controls" aria-label={t('structureControls')}><label>{t('anchorId')} <input value={editorBlocks.find(block => block.id === activeBlockId)?.anchorId || ''} onChange={event => updateActiveBlock({ anchorId: event.target.value })} placeholder="section-1" /></label><label>{t('tocLabel')} <input value={editorBlocks.find(block => block.id === activeBlockId)?.tocLabel || ''} onChange={event => updateActiveBlock({ tocLabel: event.target.value })} placeholder={t('tocLabelPlaceholder')} /></label><label>{t('tocLevel')} <input type="number" min="1" max="6" value={editorBlocks.find(block => block.id === activeBlockId)?.tocLevel || 1} onChange={event => updateActiveBlock({ tocLevel: Math.min(6, Math.max(1, Number(event.target.value) || 1)) })} /></label></div>
            <div className="theme-controls" aria-label={t('themeControls')}><label>{t('themeFont')} <select value={themeFontFamily} onChange={event => setThemeFontFamily(event.target.value)}><option>Noto Sans</option><option>Arial</option><option>Georgia</option></select></label><label>{t('themeSpacing')} <input type="number" min="0.8" max="2" step="0.05" value={themeSpacing} onChange={event => setThemeSpacing(event.target.value)} /></label></div>
            {editorBlocks.find(block => block.id === activeBlockId)?.kind === 'chart' && <div className="chart-controls" aria-label={t('chartControls')}><label>{t('chartType')} <select value={editorBlocks.find(block => block.id === activeBlockId)?.chartType || 'bar'} onChange={event => updateActiveBlock({ chartType: event.target.value as EditorBlock['chartType'] })}><option value="bar">Bar</option><option value="line">Line</option><option value="pie">Pie</option></select></label><label>{t('chartItems')} <input value={editorBlocks.find(block => block.id === activeBlockId)?.items || 'chart_rows'} onChange={event => updateActiveBlock({ items: event.target.value })} /></label><label>{t('chartLabelPath')} <input value={editorBlocks.find(block => block.id === activeBlockId)?.labelPath || 'label'} onChange={event => updateActiveBlock({ labelPath: event.target.value })} /></label><label>{t('chartValuePath')} <input value={editorBlocks.find(block => block.id === activeBlockId)?.valuePath || 'value'} onChange={event => updateActiveBlock({ valuePath: event.target.value })} /></label></div>}
            <div className="component-removal-toolbar" aria-label={t('reusableComponents')}><button type="button" disabled={!editorBlocks.some(block => block.id === activeBlockId && block.kind === 'component')} onClick={() => { const target = editorBlocks.find(block => block.id === activeBlockId && block.kind === 'component'); if (target) removeEditorBlock(target.id) }}>{t('removeComponent')}</button><button type="button" disabled={!activeBlockId} onClick={() => activeBlockId && removeEditorBlock(activeBlockId)}>{t('deleteBlock')}</button></div>
            {editorFeedback && <p className="editor-feedback" role="status">{editorFeedback}</p>}
            <div className="script-locale-controls" aria-label={t('additionalScriptLocales')}><span>{t('additionalScriptLocales')}</span><button type="button" onClick={() => setPreviewLocale('he')}>{t('hebrew')}</button><button type="button" onClick={() => setPreviewLocale('ta')}>{t('tamil')}</button><button type="button" onClick={() => setPreviewLocale('ko')}>{t('korean')}</button></div>
            <div className="component-controls" aria-label={t('reusableComponents')}><button type="button" onClick={() => void createComponentFromSelection()}>{t('saveAsComponent')}</button><button type="button" onClick={() => void updateComponentFromSelection()} disabled={!editorBlocks.some(block => block.id === activeBlockId && block.kind === 'component') || selectedBlockIds.length < 2}>{t('updateComponent')}</button>{components.map(component => <button type="button" key={component.id} onClick={() => addComponent(component)}>{t('addComponent')}: {component.name}</button>)}{editorBlocks.filter(block => block.kind === 'component').map(block => <button className="remove-component" type="button" key={`remove-${block.id}`} onClick={() => removeEditorBlock(block.id)}>{t('removeComponent')}: {block.text}</button>)}</div>
            <div className="editor-layout"><div className="editor-block-list" aria-label={t('textBlocks')}>{editorBlocks.map(block => <div className={`editor-block-row ${block.id === activeBlockId ? 'active' : ''}`} key={block.id} draggable onDragStart={event => event.dataTransfer.setData('text/plain', block.id)} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); moveBlock(event.dataTransfer.getData('text/plain'), block.id) }}><button className="block-grip" type="button" onClick={event => { setActiveBlockId(block.id); setSelectedBlockIds(current => event.ctrlKey || event.metaKey ? current.includes(block.id) ? current.filter(id => id !== block.id) : [...current, block.id] : [block.id]) }} aria-label={`${t('selectBlock')} ${block.text}`} aria-pressed={selectedBlockIds.includes(block.id)}>⠿</button><textarea aria-label={`${t('editBlock')} ${block.text}`} lang={previewLocale} dir="auto" value={block.text} onFocus={() => setActiveBlockId(block.id)} onChange={event => { setActiveBlockId(block.id); setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, text: event.target.value } : item)) }} /><div className="block-flow-controls"><label><input type="checkbox" aria-label={`Block flow: ${t('pageBreakBefore')} for ${block.text}`} checked={block.breakBefore} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, breakBefore: event.target.checked } : item))} /> {t('pageBreakBefore')}</label><label><input type="checkbox" aria-label={`Block flow: ${t('keepTogether')} for ${block.text}`} checked={block.keepTogether} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, keepTogether: event.target.checked } : item))} /> {t('keepTogether')}</label></div></div>)}</div><div className="editor-page" aria-label={t('preview')} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); dropBlockOnPage(event.dataTransfer.getData('text/plain')) }}><span className="page-label">{t('localPreview')}</span>{snapEnabled && <span className={`alignment-guide alignment-guide-${editorBlocks.find(block => block.id === activeBlockId)?.align || 'left'}`} aria-hidden="true" />}{editorBlocks.map(block => block.kind === 'image' ? <figure key={block.id} className="editor-image-preview" style={{ textAlign: block.align }}><img src={block.source} alt={block.alt || 'Image preview'} style={{ width: `${Math.min(block.width || 240, 280)}px` }} /></figure> : <p key={block.id} dir="auto" style={{ fontWeight: block.bold ? 700 : 400, fontStyle: block.italic ? 'italic' : 'normal', color: block.color, fontFamily: block.fontFamily, fontSize: `${block.fontSize}px`, textAlign: block.align }}>{block.text}</p>)}</div></div>
            {editorBlocks.some(block => block.kind === 'table' || block.kind === 'loop' || block.kind === 'if' || block.kind === 'image' || block.kind === 'code') && <div className="table-editor" aria-label={t('logicBlocks')}><h4>{t('logicBlocks')}</h4>{editorBlocks.filter(block => block.kind === 'table' || block.kind === 'loop' || block.kind === 'if' || block.kind === 'image' || block.kind === 'code').map(block => block.kind === 'code' ? <div className="table-editor-row" key={block.id}><label>{t('codeType')} <select value={block.codeType || 'qr'} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, codeType: event.target.value as EditorBlock['codeType'] } : item))}><option value="qr">QR</option><option value="code128">Code 128</option><option value="ean13">EAN-13</option></select></label><label>{t('codeValue')} <input value={block.codeValue || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, codeValue: event.target.value } : item))} /></label><label>{t('imageWidth')} <input type="number" min="40" max="1200" value={block.width || 220} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, width: Math.min(1200, Math.max(40, Number(event.target.value) || 220)) } : item))} /></label></div> : block.kind === 'image' ? <div className="table-editor-row" key={block.id}><label>{t('imageSource')} <input value={block.source || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, source: event.target.value } : item))} /></label><label>{t('imageUpload')} <input type="file" accept="image/png,image/jpeg,image/gif,image/webp,image/svg+xml" onChange={event => { const file = event.target.files?.[0]; if (file) void uploadAsset(file, block.id).catch(() => undefined); event.currentTarget.value = '' }} /></label><label>{t('imageAlt')} <input value={block.alt || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, alt: event.target.value } : item))} /></label><label>{t('imageWidth')} <input type="number" min="1" max="1200" value={block.width || 240} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, width: Math.min(1200, Math.max(1, Number(event.target.value) || 240)) } : item))} /></label><label>{t('alignment')} <select value={block.align} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, align: event.target.value as EditorBlock['align'] } : item))}><option value="left">{t('left')}</option><option value="center">{t('center')}</option><option value="right">{t('right')}</option></select></label></div> : block.kind === 'table' ? <div className="table-editor-row" key={block.id}><label>{t('tableItems')} <input value={block.items || 'rows'} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, items: event.target.value } : item))} /></label><label>{t('tableColumns')} <textarea value={JSON.stringify(block.columns || [], null, 2)} onChange={event => { try { const columns = JSON.parse(event.target.value) as TableColumn[]; setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, columns } : item)) } catch { /* keep the last valid table contract */ } }} /></label></div> : block.kind === 'loop' ? <div className="table-editor-row" key={block.id}><label>{t('repeatItems')} <input value={block.items || 'rows'} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, items: event.target.value } : item))} /></label><label>{t('repeatText')} <input value={block.repeatText || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, repeatText: event.target.value } : item))} /></label></div> : <div className="table-editor-row" key={block.id}><label>{t('conditionPath')} <input value={block.conditionPath || 'show_note'} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, conditionPath: event.target.value } : item))} /></label><label>{t('thenText')} <input value={block.thenText || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, thenText: event.target.value } : item))} /></label><label>{t('elseText')} <input value={block.elseText || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, elseText: event.target.value } : item))} /></label><label><input type="checkbox" checked={block.conditionValue === true} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, conditionValue: event.target.checked } : item))} /> {t('conditionEnabled')}</label></div>)}</div>}
            {editorArtifact && <details open className="editor-output"><summary>{t('serverPreview')}</summary><iframe title={t('serverPreview')} srcDoc={editorArtifact} sandbox="" />{editorDiagnostics && <section className="render-diagnostics" aria-label={t('renderDiagnostics')}><h4>{t('renderDiagnostics')}</h4><dl><div><dt>{t('renderEngine')}</dt><dd>{editorDiagnostics.engine || '—'}</dd></div><div><dt>{t('renderStatus')}</dt><dd>{editorDiagnostics.status || '—'}</dd></div><div><dt>{t('detectedScripts')}</dt><dd>{editorDiagnostics.scripts?.join(', ') || '—'}</dd></div><div><dt>{t('fontStacks')}</dt><dd>{editorDiagnostics.font_stacks?.join(' | ') || '—'}</dd></div></dl>{(editorDiagnostics.font_report || []).length > 0 && <table><thead><tr><th>{t('script')}</th><th>{t('requestedStack')}</th><th>{t('embeddedFonts')}</th><th>{t('missingGlyphs')}</th><th>{t('diagnosticStatus')}</th></tr></thead><tbody>{editorDiagnostics.font_report?.map(report => <tr key={report.script}><th scope="row">{report.script}</th><td>{report.requested_stack}</td><td>{report.embedded_fonts.join(', ') || '—'}</td><td>{report.missing_glyphs.join(', ') || '—'}</td><td>{report.status}</td></tr>)}</tbody></table>}</section>}</details>}
            {pdfFeedback && <p className="editor-feedback" role="status">{pdfFeedback}</p>}
            {pdfUrl && <section className="pdf-output" aria-label={t('pdfPreview')}><div className="pdf-output-heading"><h4>{t('pdfPreview')}</h4><a href={pdfUrl} download={`${(documentMetadata.title || selected.name || 'document').replace(/[^A-Za-z0-9_-]+/g, '-').toLowerCase()}.pdf`}>{t('downloadPdf')}</a></div><iframe title={t('pdfPreview')} src={pdfUrl} /><p className="muted">{pdfReport?.engine || '—'} · {pdfReport?.output_bytes ? `${pdfReport.output_bytes} bytes` : ''}</p></section>}
            <h4>{t('data')}</h4><pre>{JSON.stringify(selected.sample_data, null, 2)}</pre><p className="muted">{t('future')}</p>
          </article> : templates.map(template => <article className="template-card" key={template.id}>
            <div className="paper-preview" aria-hidden="true"><div className="paper"><span className="paper-brand" /><span className="line short" /><span className="line" /><span className="line" /><span className="line medium" /><span className="paper-sign" /></div></div>
            <div className="card-body"><span className="tag">{t('sample')}</span><h3>{template.id === 'sample-welcome' ? t('letter') : template.name}</h3><p>{t('letterDescription')}</p><button onClick={() => void openTemplate(template.id)}>{t('open')}<span aria-hidden="true"> &rarr;</span></button></div>
          </article>)}
        </section>
        <aside className="status-panel" aria-labelledby="status-title"><h2 id="status-title">{t('status')}</h2>
          <p className="connection"><span className={`dot ${health?.status === 'ready' ? 'green' : ''}`} />{health ? t(health.status === 'ready' ? 'ready' : 'unavailable') : t(loading ? 'starting' : 'unknownStatus')}</p>
          {health && <dl>{Object.entries(health.dependencies).map(([key, value]) => <div key={key}><dt>{t(key)}</dt><dd>{t(value === 'ready' ? 'ready' : 'unavailable')}</dd></div>)}</dl>}
          <a href="/docs">{t('api')} <span aria-hidden="true">&nearr;</span></a>
        </aside>
      </div></>}
    </main>
    <footer>{t('footer')}</footer>
  </>
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
