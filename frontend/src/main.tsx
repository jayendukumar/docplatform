import { StrictMode, useEffect, useRef, useState } from 'react'
import type { CSSProperties, KeyboardEvent, PointerEvent } from 'react'
import { createRoot } from 'react-dom/client'
import { useTranslation } from 'react-i18next'
import './i18n'
import './style.css'
import './editor.css'
import './reviewQueue.css'
import './tableEditor.css'
import { epicStories } from './epicStories'
import { getStoryStatus } from './storyStatus'
import { ChartContextualPanel } from './ChartContextualPanel'
import { RichTextContextualPanel } from './RichTextContextualPanel'
import { pickTableStyle, TableStylePanel, type TableStyle } from './TableStylePanel'
import { pickShapeStyle, ShapePanel, shapePreviewStyle, type ShapeStyle } from './ShapePanel'
import { ColumnsPanel, pickColumnsStyle, type ColumnsStyle } from './ColumnsPanel'
import { FurniturePanel, pickFurniture, type FurnitureSettings } from './FurniturePanel'
import { formatTabStops, parseTabStops, tabStopPosition, type TabStop } from './tabStops'
import { defaultRichText, richTextPlainText } from './richText'
import type { RichTextDocument, RichTextParagraph } from './richText'

type Template = { id: string; name: string; schema_version: number }
type TemplateVersion = { id: string; version: number; status: string; change_summary?: string; created_at?: string }
type ExtractionSchemaItem = { id: string; name: string; schema_version: number; sample_url: string }
type Starter = { id: string; name: string; languages: string[]; definitions: Record<string, Record<string, unknown>> }
type PageSettings = { size: 'A3' | 'A4' | 'A5' | 'Letter'; orientation: 'portrait' | 'landscape'; marginTopMm: number; marginRightMm: number; marginBottomMm: number; marginLeftMm: number; header: string; footer: string; headerComponentId: string; footerComponentId: string; showPageNumbers: boolean; headerAlign: BoxAlign; footerAlign: BoxAlign; pageNumberPosition: PageNumberPosition; pageNumberFormat: string; headerFooterFontSize: number; furniture: FurnitureSettings }
type BoxAlign = 'left' | 'center' | 'right'
type PageNumberPosition = `${'header' | 'footer'}-${BoxAlign}`
const BOX_ALIGNS: BoxAlign[] = ['left', 'center', 'right']
const PAGE_NUMBER_POSITIONS = (['header', 'footer'] as const).flatMap(band => BOX_ALIGNS.map(align => `${band}-${align}` as PageNumberPosition))
type DocumentMetadata = { title: string; author: string }
type Definition = { name: string; blocks: Array<Record<string, unknown>>; sample_data: unknown; page?: Record<string, unknown>; theme?: Record<string, unknown>; locale?: string; metadata?: Partial<DocumentMetadata>; data_schema?: Record<string, unknown>; data_schema_id?: string; data_schema_version?: number }
type IsdaSemantic = { semantic_kind?: 'clause' | 'field' | 'schedule' | 'signature'; semantic_id?: string; field_path?: string; field_role?: string }
type EditorBlock = { id: string; text: string; bold: boolean; italic: boolean; color: string; fontFamily: string; fontSize: number; align: 'left' | 'center' | 'right' | 'justify'; offsetX?: number; offsetY?: number; breakBefore: boolean; keepTogether: boolean; lineHeight?: number; paragraphSpacingBefore?: number; paragraphSpacingAfter?: number; firstLineIndent?: number; leftIndent?: number; rightIndent?: number; tabStops?: TabStop[]; keepWithNext?: boolean; breakAfter?: boolean; richText?: RichTextDocument; kind?: 'text' | 'table' | 'loop' | 'if' | 'image' | 'code' | 'chart' | 'toc' | 'component' | 'shape' | 'columns' | 'column_break' | 'columns_end' | 'pdf_background' | 'page_background'; componentId?: string; items?: string; as?: string; columns?: TableColumn[]; tableStyle?: TableStyle; shapeStyle?: ShapeStyle; columnsStyle?: ColumnsStyle; rowConditionPath?: string; rowConditionValue?: string; repeatText?: string; conditionPath?: string; conditionValue?: boolean; thenText?: string; elseText?: string; source?: string; alt?: string; width?: number; codeType?: 'qr' | 'code128' | 'ean13'; codeValue?: string; chartType?: 'bar' | 'line' | 'pie'; chartOrientation?: 'vertical' | 'horizontal'; showLegend?: boolean; showGrid?: boolean; showPoints?: boolean; donut?: boolean; chartTitle?: string; xAxisLabel?: string; yAxisLabel?: string; labelPath?: string; valuePath?: string; seriesPath?: string; chartDataMode?: 'bound' | 'static'; staticData?: Array<Record<string, unknown>>; colors?: string[]; backgroundColor?: string; gridColor?: string; axisColor?: string; showValues?: boolean; stacked?: boolean; anchorId?: string; tocLabel?: string; tocLevel?: number } & IsdaSemantic
type StoredEditorBlock = { type?: string; text?: string; paragraphs?: RichTextParagraph[]; component_id?: string; bold?: boolean; italic?: boolean; color?: string; font_family?: string; font_size?: number; align?: 'left' | 'center' | 'right'; offset_x?: number; offset_y?: number; break_before?: boolean; keep_together?: boolean; line_height?: number; paragraph_spacing_before?: number; paragraph_spacing_after?: number; first_line_indent?: number; left_indent?: number; right_indent?: number; tab_stops?: number[]; keep_with_next?: boolean; break_after?: boolean; items?: string; as?: string; columns?: TableColumn[]; tableStyle?: TableStyle; shapeStyle?: ShapeStyle; columnsStyle?: ColumnsStyle; blocks?: Array<{ type?: string; text?: string }>; condition?: { path?: string; equals?: unknown }; then?: Array<{ type?: string; text?: string }>; else?: Array<{ type?: string; text?: string }>; src?: string; alt?: string; width?: number; code_type?: 'qr' | 'code128' | 'ean13'; value?: string; chart_type?: 'bar' | 'line' | 'pie'; chart_orientation?: 'vertical' | 'horizontal'; show_legend?: boolean; show_grid?: boolean; show_points?: boolean; donut?: boolean; chart_title?: string; x_axis_label?: string; y_axis_label?: string; label_path?: string; value_path?: string; series_path?: string; data_mode?: 'bound' | 'static'; static_data?: Array<Record<string, unknown>>; colors?: string[]; background_color?: string; grid_color?: string; axis_color?: string; show_values?: boolean; stacked?: boolean; anchor_id?: string; toc_label?: string; toc_level?: number; semantic_kind?: IsdaSemantic['semantic_kind']; semantic_id?: string; field_path?: string; field_role?: string }
type ReusableComponent = { id: string; name: string; version: number }
type ComponentPart = Record<string, unknown> & { __id: string }
type TableColumn = { header: string; path: string; format?: 'text' | 'number' | 'currency' | 'date' | 'percent'; width?: number; align?: 'left' | 'center' | 'right' }
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
type PositionFields = { positionMode?: 'flow' | 'absolute'; positionUnit?: 'px' | 'mm'; positionX?: number; positionY?: number }
type PageFields = { pageNumber?: number }
type TableRowFilterFields = { rowConditionPath?: string; rowConditionValue?: string }

function pageDimensions(settings: PageSettings) {
  const sizes = { A3: [297, 420], A4: [210, 297], A5: [148, 210], Letter: [216, 279] } as const
  const [short, long] = sizes[settings.size]
  return settings.orientation === 'landscape' ? { width: long, height: short } : { width: short, height: long }
}

function structureLabel(block: EditorBlock, index: number) {
  const text = block.text.replace(/[\u200B\u200C\u200D]/g, '').replace(/u\{200B\}/g, '').trim()
  if (block.kind === 'pdf_background') return block.text || 'Locked source PDF'
  if (block.kind === 'page_background') return 'Page background image'
  if (block.kind === 'component') return `Reusable component · ${text || block.componentId || 'unnamed'}`
  if (block.kind === 'table') return `Repeatable table · ${block.items || 'rows'}`
  if (block.kind === 'loop') return `Repeating section · ${block.items || 'rows'}`
  if (block.kind === 'if') return `Conditional section · ${block.conditionPath || 'condition'}`
  if (block.kind === 'image') return `Image · ${block.alt || 'untitled image'}`
  if (block.kind === 'code') return `${String(block.codeType || 'qr').toUpperCase()} code · ${block.codeValue || 'bound value'}`
  if (block.kind === 'chart') return `Chart · ${block.chartTitle || block.chartType || 'data chart'}`
  if (block.kind === 'toc') return 'Table of contents'
  if (block.semantic_kind === 'field') return `Field · ${block.field_role || block.field_path || text}`
  if (block.semantic_kind === 'signature') return `Signature · ${block.field_role || block.semantic_id || text}`
  if (block.semantic_kind === 'schedule') return `Schedule · ${text || block.semantic_id || 'section'}`
  if (block.semantic_kind === 'clause') return `Clause · ${text || block.semantic_id || 'clause'}`
  if (block.richText) return `Rich text · ${text || 'formatted text'}`
  return text || `Text block · ${index + 1}`
}

function schemaFieldPaths(schema: Record<string, unknown> | null, prefix = ''): string[] {
  if (!schema || typeof schema !== 'object') return []
  const properties = schema.properties
  if (!properties || typeof properties !== 'object' || Array.isArray(properties)) return prefix ? [prefix] : []
  return Object.entries(properties as Record<string, unknown>).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    const child = value && typeof value === 'object' && !Array.isArray(value) ? schemaFieldPaths(value as Record<string, unknown>, path) : []
    return child.length ? child : [path]
  }).slice(0, 100)
}

type SchemaFieldDetail = { path: string; title: string; type: string; format?: string }

function schemaFieldDetails(schema: Record<string, unknown> | null, prefix = ''): SchemaFieldDetail[] {
  if (!schema || typeof schema !== 'object') return []
  const properties = schema.properties
  if (!properties || typeof properties !== 'object' || Array.isArray(properties)) return []
  return Object.entries(properties as Record<string, unknown>).flatMap(([key, value]) => {
    const path = prefix ? `${prefix}.${key}` : key
    const definition = value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
    const nested = schemaFieldDetails(definition, path)
    if (nested.length) return nested
    const rawType = definition.type
    const type = Array.isArray(rawType) ? rawType.filter(item => item !== 'null').join(' | ') : typeof rawType === 'string' ? rawType : 'string'
    return [{ path, title: typeof definition.title === 'string' ? definition.title : key.replaceAll('_', ' '), type, format: typeof definition.format === 'string' ? definition.format : undefined }]
  }).slice(0, 100)
}

function valueAtPath(value: unknown, path: string): unknown {
  return path.split('.').reduce<unknown>((current, part) => current && typeof current === 'object' && !Array.isArray(current) ? (current as Record<string, unknown>)[part] : undefined, value)
}

function componentPartLabel(part: Record<string, unknown>, index: number): string {
  const type = String(part.type || 'text')
  if (type === 'rich_text') {
    const paragraphs = Array.isArray(part.paragraphs) ? part.paragraphs as Array<Record<string, unknown>> : []
    const text = paragraphs.flatMap(paragraph => Array.isArray(paragraph.runs) ? paragraph.runs as Array<Record<string, unknown>> : []).map(run => run.type === 'binding' ? `{{${String(run.path || 'field')}}}` : String(run.text || '')).join('').trim()
    return `Rich text · ${text || 'formatted content'}`
  }
  if (type === 'text') return `Text · ${String(part.text || `text ${index + 1}`)}`
  if (type === 'table') return `Table · ${String(part.items || 'rows')}`
  if (type === 'image') return `Image · ${String(part.alt || 'untitled image')}`
  if (type === 'component') return `Nested component · ${String(part.component_id || 'unnamed')}`
  return `${type.replaceAll('_', ' ')} · ${String(part.text || part.value || part.items || 'configured object')}`
}

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
  const [componentParts, setComponentParts] = useState<ComponentPart[]>([])
  const [activeComponentPartId, setActiveComponentPartId] = useState<string | null>(null)
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
  const [pageSettings, setPageSettings] = useState<PageSettings>({ size: 'A4', orientation: 'portrait', marginTopMm: 20, marginRightMm: 20, marginBottomMm: 20, marginLeftMm: 20, header: '', footer: '', headerComponentId: '', footerComponentId: '', showPageNumbers: false, headerAlign: 'left', footerAlign: 'left', pageNumberPosition: 'footer-right', pageNumberFormat: '{page}', headerFooterFontSize: 12, furniture: {} })
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
  const [pageSettingsOpen, setPageSettingsOpen] = useState(false)
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
  const [templateSchema, setTemplateSchema] = useState<Record<string, unknown> | null>(null)
  const [templateSchemaFeedback, setTemplateSchemaFeedback] = useState<string | null>(null)
  const [selectedBindingPath, setSelectedBindingPath] = useState('')
  const [templateVersions, setTemplateVersions] = useState<TemplateVersion[]>([])
  const [previewPage, setPreviewPage] = useState(1)
  const [templateSettingsOpen, setTemplateSettingsOpen] = useState(false)
  const [recentTemplateIds, setRecentTemplateIds] = useState<string[]>(() => { try { return JSON.parse(localStorage.getItem('docplatform.recentTemplates') || '[]') as string[] } catch { return [] } })
  useEffect(() => {
    const block = editorBlocks.find(item => item.id === activeBlockId)
    if (block?.kind !== 'component' || !block.componentId) {
      setComponentParts([])
      setActiveComponentPartId(null)
      return
    }
    const controller = new AbortController()
    fetch(`/api/components/${encodeURIComponent(block.componentId)}`, { signal: controller.signal }).then(async response => {
      if (!response.ok) throw new Error('component unavailable')
      return response.json() as Promise<{ definition?: { blocks?: Array<Record<string, unknown>> } }>
    }).then(body => setComponentParts((body.definition?.blocks || []).map((part, index) => ({ ...part, __originalText: part.text, text: componentPartLabel(part, index), __id: `part-${index}` })))).catch(() => {
      if (!controller.signal.aborted) setComponentParts([])
    })
    return () => controller.abort()
  }, [activeBlockId, editorBlocks])
  useEffect(() => {
    setPreviewPage(1)
  }, [selectedTemplateId])
  useEffect(() => {
    if (!selectedTemplateId) { setTemplateVersions([]); return }
    const controller = new AbortController()
    fetch(`/api/templates/${encodeURIComponent(selectedTemplateId)}/versions`, { signal: controller.signal }).then(response => response.ok ? response.json() as Promise<{ items?: TemplateVersion[] }> : { items: [] }).then(body => setTemplateVersions(Array.isArray(body.items) ? body.items : [])).catch(() => { if (!controller.signal.aborted) setTemplateVersions([]) })
    return () => controller.abort()
  }, [selectedTemplateId])
  useEffect(() => {
    const page = document.querySelector('.editor-page')
    if (!page) return
    const handleCanvasSelection = (event: Event) => {
      const target = event.target as HTMLElement
      const image = target.closest('.editor-image-preview')
      if (image) {
        const imageIndex = Array.from(page.querySelectorAll('.editor-image-preview')).indexOf(image)
        const imageBlocks = editorBlocks.filter(block => block.kind === 'image')
        setActiveBlockId(imageBlocks[imageIndex]?.id || null)
        return
      }
      const chart = target.closest('.editor-chart-preview')
      if (chart) {
        setActiveBlockId(chart.getAttribute('data-block-id'))
        return
      }
      const table = target.closest('.editor-table-preview')
      if (table) {
        setActiveBlockId(table.getAttribute('data-block-id'))
        return
      }
      const paragraph = target.closest('.editor-page p')
      if (paragraph) {
        const block = editorBlocks.find(item => item.text === paragraph.textContent)
        if (block) setActiveBlockId(block.id)
      }
    }
    page.addEventListener('click', handleCanvasSelection)
    return () => page.removeEventListener('click', handleCanvasSelection)
  }, [editorBlocks])
  useEffect(() => {
    const page = document.querySelector('.editor-page')
    if (!page) return
    const content = Array.from(page.children).filter(element => !element.classList.contains('page-label') && !element.classList.contains('alignment-guide') && !element.classList.contains('locked-background-frame')) as HTMLElement[]
    content.forEach((element, index) => {
      const block = editorBlocks[index] as EditorBlock & PageFields | undefined
      element.style.display = block?.pageNumber && block.pageNumber !== previewPage ? 'none' : ''
    })
  }, [editorBlocks, previewPage])
  useEffect(() => {
    const page = document.querySelector('.editor-page')
    if (!page) return
    page.querySelector('.locked-background-frame')?.remove()
    if (pageBackgroundPdf) {
      const frame = document.createElement('iframe')
      frame.className = 'locked-background-frame'
      frame.title = 'Locked source PDF preview'
      frame.src = pageBackgroundPdf
      page.prepend(frame)
    }
  }, [pageBackgroundPdf, selectedTemplateId])
  useEffect(() => {
    document.querySelectorAll<HTMLElement>('.editor-page p').forEach((paragraph, index) => {
      const block = editorBlocks[index]
      if (!block) return
      const positioned = block as EditorBlock & PositionFields
      paragraph.style.position = positioned.positionMode === 'absolute' ? 'absolute' : 'relative'
      const unit = positioned.positionUnit || 'px'
      paragraph.style.left = positioned.positionMode === 'absolute' ? `${positioned.positionX || 0}${unit}` : ''
      paragraph.style.top = positioned.positionMode === 'absolute' ? `${positioned.positionY || 0}${unit}` : ''
      paragraph.style.lineHeight = block.lineHeight ? String(block.lineHeight) : ''
      paragraph.style.marginTop = typeof block.paragraphSpacingBefore === 'number' ? `${block.paragraphSpacingBefore}px` : ''
      paragraph.style.marginBottom = typeof block.paragraphSpacingAfter === 'number' ? `${block.paragraphSpacingAfter}px` : ''
      paragraph.style.textIndent = typeof block.firstLineIndent === 'number' ? `${block.firstLineIndent}px` : ''
      paragraph.style.paddingLeft = typeof block.leftIndent === 'number' ? `${block.leftIndent}px` : ''
      paragraph.style.paddingRight = typeof block.rightIndent === 'number' ? `${block.rightIndent}px` : ''
      paragraph.style.breakAfter = block.breakAfter ? 'page' : block.keepWithNext ? 'avoid' : ''
      paragraph.style.breakInside = block.keepTogether ? 'avoid' : ''
      if (block.tabStops?.length) paragraph.style.tabSize = `${Math.max(1, Math.min(2000, tabStopPosition(block.tabStops[0])))}px`
    })
  }, [editorBlocks])
  useEffect(() => {
    const insertLabels = new Set([t('addTextBlock'), t('addTableBlock'), t('addRepeatBlock'), t('addConditionalBlock'), t('addImageBlock'), t('addCodeBlock'), t('addChartBlock'), t('addTocBlock')])
    document.querySelectorAll('.editor-toolbar button').forEach(button => {
      if (insertLabels.has(button.textContent?.trim() || '')) button.classList.add('legacy-insert-action')
    })
  }, [t, selectedTemplateId])
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
    if (!selected || !selectedTemplateId) return
    const storedBlocks = selected.blocks as StoredEditorBlock[]
    setEditorBlocks(current => {
      const lockedSource = Boolean(pageBackgroundPdf)
      const normalized = current.filter(block => block.kind !== 'pdf_background' && block.kind !== 'page_background').filter(block => !lockedSource || block.kind !== 'text' || block.text.replace(/[\u200B\u200C\u200D]/g, '').replace(/u\{200B\}/g, '').trim()).map((block, index) => {
      const stored = storedBlocks[index]
      if (stored?.type !== 'rich_text' || !Array.isArray(stored.paragraphs)) return block
      const richText: RichTextDocument = { version: 1, paragraphs: stored.paragraphs }
      return { ...block, richText, text: richTextPlainText(richText) }
      })
      if (typeof selected.page?.background_pdf === 'string' && selected.page.background_pdf) { const background = backgroundBlock('pdf_background', lockedSource ? 'Locked source PDF · 36 pages' : undefined); normalized.push(background); setActiveBlockId(background.id); setSelectedBlockIds([background.id]) }
      else if (typeof selected.page?.background === 'string' && selected.page.background) { const background = backgroundBlock('page_background'); normalized.push(background); setActiveBlockId(background.id); setSelectedBlockIds([background.id]) }
      return normalized
    })
  }, [selected, selectedTemplateId, pageBackgroundPdf])
  useEffect(() => {
    const kind = pageBackgroundPdf ? 'pdf_background' : pageBackground ? 'page_background' : null
    if (!selectedTemplateId || !kind) return
    setEditorBlocks(current => {
      const existing = current.find(block => block.kind === kind)
      if (existing) { setActiveBlockId(existing.id); setSelectedBlockIds([existing.id]); return current }
      const background = backgroundBlock(kind)
      setActiveBlockId(background.id); setSelectedBlockIds([background.id])
      return [...current, background]
    })
  }, [selectedTemplateId, pageBackgroundPdf, pageBackground])
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
      const legacyMargin = typeof page.margin_mm === 'number' ? Math.min(100, Math.max(0, page.margin_mm)) : 20
      const margin = (key: string) => typeof page[key] === 'number' ? Math.min(100, Math.max(0, page[key] as number)) : legacyMargin
      setPageSettings({ size: (page.size === 'A3' || page.size === 'A5' || page.size === 'Letter' ? page.size : 'A4') as PageSettings['size'], orientation: page.orientation === 'landscape' ? 'landscape' : 'portrait', marginTopMm: margin('margin_top_mm'), marginRightMm: margin('margin_right_mm'), marginBottomMm: margin('margin_bottom_mm'), marginLeftMm: margin('margin_left_mm'), header: typeof page.header === 'string' ? page.header : '', footer: typeof page.footer === 'string' ? page.footer : '', headerComponentId: typeof page.header_component_id === 'string' ? page.header_component_id : '', footerComponentId: typeof page.footer_component_id === 'string' ? page.footer_component_id : '', showPageNumbers: page.show_page_numbers === true, headerAlign: BOX_ALIGNS.includes(page.header_align as BoxAlign) ? page.header_align as BoxAlign : 'left', footerAlign: BOX_ALIGNS.includes(page.footer_align as BoxAlign) ? page.footer_align as BoxAlign : 'left', pageNumberPosition: PAGE_NUMBER_POSITIONS.includes(page.page_number_position as PageNumberPosition) ? page.page_number_position as PageNumberPosition : 'footer-right', pageNumberFormat: typeof page.page_number_format === 'string' && page.page_number_format ? page.page_number_format : '{page}', headerFooterFontSize: typeof page.header_footer_font_size === 'number' ? page.header_footer_font_size : 12, furniture: pickFurniture(page as Record<string, unknown>) })
      setDocumentMetadata({ title: typeof definition.metadata?.title === 'string' ? definition.metadata.title : '', author: typeof definition.metadata?.author === 'string' ? definition.metadata.author : '' })
      setThemeAccent(typeof definition.theme?.accent === 'string' ? definition.theme.accent : '#2f6f60')
      setThemeFontFamily(typeof definition.theme?.font_family === 'string' ? definition.theme.font_family : 'Noto Sans')
      setThemeSpacing(typeof definition.theme?.spacing === 'string' ? definition.theme.spacing : '1.45')
      setPageBackground(typeof page.background === 'string' ? page.background : '')
      setPageBackgroundPdf(typeof page.background_pdf === 'string' ? page.background_pdf : '')
      setTemplateSchema(typeof definition.data_schema === 'object' && definition.data_schema !== null ? definition.data_schema : null)
      setTemplateSchemaFeedback(null)
      const blocks = definition.blocks.map((block, index) => { const stored = block as StoredEditorBlock; const kind = stored.type === 'component' ? 'component' as const : stored.type === 'table' ? 'table' as const : stored.type === 'loop' ? 'loop' as const : stored.type === 'if' ? 'if' as const : stored.type === 'image' ? 'image' as const : stored.type === 'shape' ? 'shape' as const : stored.type === 'columns' ? 'columns' as const : stored.type === 'column_break' ? 'column_break' as const : stored.type === 'columns_end' ? 'columns_end' as const : stored.type === 'code' ? 'code' as const : stored.type === 'chart' ? 'chart' as const : stored.type === 'toc' ? 'toc' as const : 'text' as const; const nestedText = stored.blocks?.[0]?.text || ''; const thenText = stored.then?.[0]?.text || ''; const elseText = stored.else?.[0]?.text || ''; const richText = stored.type === 'rich_text' && Array.isArray(stored.paragraphs) ? { version: 1 as const, paragraphs: stored.paragraphs } : undefined; return { id: `block-${index}`, text: richText ? richTextPlainText(richText) : stored.text || (kind === 'component' ? components.find(component => component.id === stored.component_id)?.name || 'Reusable component' : kind === 'table' ? 'Repeatable table' : kind === 'loop' ? 'Repeating section' : kind === 'if' ? 'Conditional section' : kind === 'image' ? 'Image' : kind === 'shape' ? 'Shape' : kind === 'columns' ? 'Start columns' : kind === 'column_break' ? 'Column break' : kind === 'columns_end' ? 'End columns' : kind === 'code' ? 'Code' : kind === 'chart' ? 'Chart' : kind === 'toc' ? 'Table of contents' : ''), bold: Boolean(stored.bold), italic: Boolean(stored.italic), color: String(stored.color || '#203d37'), fontFamily: String(stored.font_family || 'Noto Sans'), fontSize: Number(stored.font_size || 16), align: (stored.align || 'left') as EditorBlock['align'], offsetX: Math.min(160, Math.max(-160, Number(stored.offset_x || 0))), offsetY: Math.min(160, Math.max(-160, Number(stored.offset_y || 0))), breakBefore: stored.break_before === true, keepTogether: stored.keep_together !== false, lineHeight: typeof stored.line_height === 'number' ? stored.line_height : undefined, paragraphSpacingBefore: typeof stored.paragraph_spacing_before === 'number' ? stored.paragraph_spacing_before : undefined, paragraphSpacingAfter: typeof stored.paragraph_spacing_after === 'number' ? stored.paragraph_spacing_after : undefined, firstLineIndent: typeof stored.first_line_indent === 'number' ? stored.first_line_indent : undefined, leftIndent: typeof stored.left_indent === 'number' ? stored.left_indent : undefined, rightIndent: typeof stored.right_indent === 'number' ? stored.right_indent : undefined, tabStops: Array.isArray(stored.tab_stops) ? stored.tab_stops : undefined, keepWithNext: stored.keep_with_next === true, breakAfter: stored.break_after === true, richText, kind, componentId: stored.component_id, items: stored.items, as: stored.as, columns: stored.columns, tableStyle: kind === 'table' ? pickTableStyle(stored as Record<string, unknown>) : undefined, shapeStyle: kind === 'shape' ? pickShapeStyle(stored as Record<string, unknown>) : undefined, columnsStyle: kind === 'columns' ? pickColumnsStyle(stored as Record<string, unknown>) : undefined, repeatText: nestedText, conditionPath: stored.condition?.path, conditionValue: Boolean(stored.condition?.equals), thenText, elseText, source: stored.src, alt: stored.alt, width: stored.width, codeType: stored.code_type, codeValue: stored.value, chartType: stored.chart_type, chartOrientation: (stored.chart_orientation === 'horizontal' ? 'horizontal' : 'vertical') as EditorBlock['chartOrientation'], showLegend: stored.show_legend !== false, showGrid: stored.show_grid !== false, showPoints: stored.show_points !== false, donut: stored.donut === true, chartTitle: stored.chart_title || '', xAxisLabel: stored.x_axis_label || '', yAxisLabel: stored.y_axis_label || '', labelPath: stored.label_path, valuePath: stored.value_path, seriesPath: stored.series_path, chartDataMode: (stored.data_mode === 'static' ? 'static' : 'bound') as EditorBlock['chartDataMode'], staticData: Array.isArray(stored.static_data) ? stored.static_data : undefined, colors: stored.colors, backgroundColor: stored.background_color || '#ffffff', gridColor: stored.grid_color || '#d9e2df', axisColor: stored.axis_color || '#203d37', showValues: stored.show_values === true, stacked: stored.stacked === true, anchorId: stored.anchor_id, tocLabel: stored.toc_label, tocLevel: stored.toc_level, semantic_kind: stored.semantic_kind, semantic_id: stored.semantic_id, field_path: stored.field_path, field_role: stored.field_role } })
      blocks.forEach((block, index) => { const stored = definition.blocks[index] as StoredEditorBlock & { position_mode?: string; position_unit?: string; position_x?: number; position_y?: number; page_number?: number }; const positioned = block as EditorBlock & PositionFields & PageFields; positioned.positionMode = stored.position_mode === 'absolute' ? 'absolute' : 'flow'; positioned.positionUnit = stored.position_unit === 'mm' ? 'mm' : 'px'; positioned.positionX = typeof stored.position_x === 'number' ? stored.position_x : undefined; positioned.positionY = typeof stored.position_y === 'number' ? stored.position_y : undefined; positioned.pageNumber = typeof stored.page_number === 'number' ? Math.min(1000, Math.max(1, Math.round(stored.page_number))) : undefined })
      blocks.forEach((block, index) => { const stored = definition.blocks[index] as StoredEditorBlock & { row_condition?: { path?: string; equals?: unknown } }; const filtered = block as EditorBlock & TableRowFilterFields; filtered.rowConditionPath = stored.row_condition?.path || ''; filtered.rowConditionValue = stored.row_condition?.equals === undefined ? '' : String(stored.row_condition.equals) })
      const visibleBlocks = typeof page.background_pdf === 'string' && page.background_pdf
        ? [...blocks.filter(block => block.kind !== 'text' || block.text.replace(/[\u200B\u200C\u200D]/g, '').trim()), backgroundBlock('pdf_background', 'Locked source PDF · 36 pages')]
        : blocks
      setSelected(boundData ? { ...definition, sample_data: boundData } : definition); setSelectedTemplateId(id); setRecentTemplateIds(current => { const next = [id, ...current.filter(item => item !== id)].slice(0, 10); localStorage.setItem('docplatform.recentTemplates', JSON.stringify(next)); return next }); setEditorBlocks(visibleBlocks); setHistory([visibleBlocks]); setHistoryIndex(0); historyReady.current = true; setSelectedBlockIds([]); setActiveBlockId(visibleBlocks[0]?.id ?? null); setPageSettingsOpen(false); setTemplateSettingsOpen(false); setEditorFeedback(null); setEditorArtifact(renderedArtifact || null); setEditorDiagnostics(null); setPdfUrl(null); setPdfReport(null); setPdfFeedback(null)
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
    const definition = { blocks: blocks.map(({ id, kind, componentId, fontFamily, fontSize, offsetX, breakBefore, keepTogether, ...block }) => ({ ...block, type: kind === 'text' || !kind ? 'text' : kind, ...(componentId ? { component_id: componentId } : {}), ...(fontFamily ? { font_family: fontFamily } : {}), ...(fontSize ? { font_size: fontSize } : {}), ...(typeof offsetX === 'number' ? { offset_x: offsetX } : {}), line_height: block.lineHeight, paragraph_spacing_before: block.paragraphSpacingBefore, paragraph_spacing_after: block.paragraphSpacingAfter, first_line_indent: block.firstLineIndent, left_indent: block.leftIndent, right_indent: block.rightIndent, tab_stops: block.tabStops, keep_with_next: block.keepWithNext, break_after: block.breakAfter, break_before: breakBefore, keep_together: keepTogether })) }
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
    const definition = { blocks: blocks.map(({ id, kind, componentId, fontFamily, fontSize, offsetX, breakBefore, keepTogether, ...block }) => ({ ...block, type: kind === 'text' || !kind ? 'text' : kind, ...(componentId ? { component_id: componentId } : {}), ...(fontFamily ? { font_family: fontFamily } : {}), ...(fontSize ? { font_size: fontSize } : {}), ...(typeof offsetX === 'number' ? { offset_x: offsetX } : {}), line_height: block.lineHeight, paragraph_spacing_before: block.paragraphSpacingBefore, paragraph_spacing_after: block.paragraphSpacingAfter, first_line_indent: block.firstLineIndent, left_indent: block.leftIndent, right_indent: block.rightIndent, tab_stops: block.tabStops, keep_with_next: block.keepWithNext, break_after: block.breakAfter, break_before: breakBefore, keep_together: keepTogether })) }
    const response = await fetch(`/api/components/${encodeURIComponent(target.componentId)}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ definition }) })
    if (response.ok) setEditorFeedback(t('componentUpdated'))
  }
  function addComponent(component: ReusableComponent) { const block: EditorBlock = { id: `component-${Date.now()}`, text: component.name, bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left', breakBefore: false, keepTogether: true, kind: 'component', componentId: component.id }; updateEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id) }
  function backgroundBlock(kind: 'pdf_background' | 'page_background', label?: string): EditorBlock { return { id: `${kind}-${Date.now()}`, text: label || (kind === 'pdf_background' ? t('pdfBackground') : t('pageBackground')), bold: false, italic: false, color: 'transparent', fontFamily: 'Noto Sans', fontSize: 0, align: 'left', breakBefore: false, keepTogether: true, kind } }
  function ensurePdfBackgroundBlock() { const existing = editorBlocks.find(block => block.kind === 'pdf_background'); const block = existing || backgroundBlock('pdf_background'); updateEditorBlocks(blocks => existing ? blocks : [...blocks, block]); setActiveBlockId(block.id); setSelectedBlockIds([block.id]); return block }
  function addPdfBackgroundBlock() { ensurePdfBackgroundBlock(); window.setTimeout(() => document.getElementById('locked-pdf-background-input')?.click(), 0) }
  function addTextBlock() {
    const richText = defaultRichText()
    const block = { id: `block-${Date.now()}`, text: richTextPlainText(richText), richText, bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left' as const, breakBefore: false, keepTogether: true, kind: 'text' as const }
    updateEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id); setSelectedBlockIds([block.id]); setActiveComponentPartId(null)
  }
  function addBoundField(path: string) {
    const cleanPath = path.trim()
    if (!cleanPath) return
    const richText: RichTextDocument = { version: 1, paragraphs: [{ align: 'left', runs: [{ type: 'binding', path: cleanPath, format: 'text', style: {} }] }] }
    const block: EditorBlock = { id: `field-${Date.now()}`, text: `{{${cleanPath}}}`, richText, bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left', breakBefore: false, keepTogether: true, kind: 'text' }
    updateEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id); setSelectedBlockIds([block.id]); setActiveComponentPartId(null)
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
    setEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id); setSelectedBlockIds([block.id]); setActiveComponentPartId(null)
  }
  function addColumnMarker(kind: 'columns' | 'column_break' | 'columns_end') {
    const label = kind === 'columns' ? 'Start columns' : kind === 'column_break' ? 'Column break' : 'End columns'
    const block = { id: `${kind}-${Date.now()}`, text: label, bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left' as const, breakBefore: false, keepTogether: false, kind, ...(kind === 'columns' ? { columnsStyle: { count: 2, gap_mm: 6 } } : {}) }
    setEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id); setSelectedBlockIds([block.id]); setActiveComponentPartId(null)
  }
  function addShapeBlock() {
    const block = { id: `shape-${Date.now()}`, text: 'Shape', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left' as const, breakBefore: false, keepTogether: false, kind: 'shape' as const, shapeStyle: { shape: 'line' as const, stroke_width: 1 } }
    setEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id); setSelectedBlockIds([block.id]); setActiveComponentPartId(null)
  }
  function addCodeBlock() {
    const block = { id: `code-${Date.now()}`, text: 'QR code', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left' as const, breakBefore: false, keepTogether: true, kind: 'code' as const, codeType: 'qr' as const, codeValue: '{{order.id}}', width: 220 }
    setEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id)
    setSelected(current => current ? { ...current, sample_data: { ...(current.sample_data as Record<string, unknown>), order: { id: 'ORDER-001', code: 'ABC123', ean: '5901234123457' } } } : current)
  }
  function addChartBlock() {
    const block: EditorBlock = { id: `chart-${Date.now()}`, text: 'Chart', bold: false, italic: false, color: '#203d37', fontFamily: 'Noto Sans', fontSize: 16, align: 'left', breakBefore: false, keepTogether: true, kind: 'chart', items: 'chart_rows', chartType: 'bar', chartOrientation: 'vertical', showLegend: true, showGrid: true, showPoints: true, donut: false, chartTitle: '', xAxisLabel: '', yAxisLabel: '', labelPath: 'label', valuePath: 'value', seriesPath: '', chartDataMode: 'bound', staticData: [{ label: 'A', value: 10 }, { label: 'B', value: 20 }], colors: ['#2f6f63', '#d97941', '#4d78a8'], backgroundColor: '#ffffff', gridColor: '#d9e2df', axisColor: '#203d37', showValues: false, stacked: false, alt: 'Data chart' }
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
  async function restoreTemplateVersion(versionId: string) {
    if (!selectedTemplateId) return
    const response = await fetch(`/api/templates/${encodeURIComponent(selectedTemplateId)}/restore/${encodeURIComponent(versionId)}`, { method: 'POST' })
    if (!response.ok) { setEditorFeedback('Unable to restore this version'); return }
    setEditorFeedback('Version restored as a new draft')
    await openTemplate(selectedTemplateId)
  }
  async function saveEditorDraft(): Promise<boolean> {
    if (!selectedTemplateId || !selected) return false
    const definition = { ...selected, data_schema: templateSchema || undefined, data_schema_id: templateSchema ? String(templateSchema.$id || selected.data_schema_id || 'template-schema') : undefined, data_schema_version: templateSchema ? Number(templateSchema['x-docplatform-schema-version'] || selected.data_schema_version || 1) : undefined, metadata: documentMetadata, theme: { ...(selected.theme || {}), accent: themeAccent, font_family: themeFontFamily, spacing: themeSpacing }, page: { size: pageSettings.size, orientation: pageSettings.orientation, margin_top_mm: pageSettings.marginTopMm, margin_right_mm: pageSettings.marginRightMm, margin_bottom_mm: pageSettings.marginBottomMm, margin_left_mm: pageSettings.marginLeftMm, margin_mm: pageSettings.marginTopMm, header: pageSettings.header, footer: pageSettings.footer, ...(pageSettings.headerComponentId ? { header_component_id: pageSettings.headerComponentId } : {}), ...(pageSettings.footerComponentId ? { footer_component_id: pageSettings.footerComponentId } : {}), show_page_numbers: pageSettings.showPageNumbers, header_align: pageSettings.headerAlign, footer_align: pageSettings.footerAlign, page_number_position: pageSettings.pageNumberPosition, page_number_format: pageSettings.pageNumberFormat, header_footer_font_size: pageSettings.headerFooterFontSize, ...pageSettings.furniture, ...(pageBackground ? { background: pageBackground } : {}) }, blocks: editorBlocks.filter(block => block.kind !== 'pdf_background' && block.kind !== 'page_background').map(({ id, fontFamily, fontSize, offsetX, offsetY, richText, kind, componentId, items, as, columns, rowConditionPath, rowConditionValue, repeatText, conditionPath, conditionValue, thenText, elseText, source, alt, width, codeType, codeValue, chartType, chartOrientation, showLegend, showGrid, showPoints, donut, chartTitle, xAxisLabel, yAxisLabel, labelPath, valuePath, seriesPath, chartDataMode, staticData, colors, backgroundColor, gridColor, axisColor, showValues, stacked, anchorId, tocLabel, tocLevel, breakBefore, keepTogether, ...block }) => kind === 'component' ? ({ type: 'component', component_id: componentId, offset_x: offsetX || 0, offset_y: offsetY || 0, break_before: breakBefore, keep_together: keepTogether }) : kind === 'table' ? ({ type: 'table', items: items || 'rows', columns: columns || [], ...(block.tableStyle || {}), ...(rowConditionPath ? { row_condition: { path: rowConditionPath, equals: rowConditionValue || '' } } : {}), offset_x: offsetX || 0, offset_y: offsetY || 0, break_before: breakBefore, keep_together: keepTogether }) : kind === 'loop' ? ({ type: 'loop', items: items || 'rows', as: as || 'row', blocks: [{ type: 'text', text: repeatText || '' }], offset_x: offsetX || 0, offset_y: offsetY || 0, break_before: breakBefore, keep_together: keepTogether }) : kind === 'if' ? ({ type: 'if', condition: { path: conditionPath || 'show_note', equals: conditionValue === true }, then: [{ type: 'text', text: thenText || '' }], else: [{ type: 'text', text: elseText || '' }], offset_x: offsetX || 0, offset_y: offsetY || 0, break_before: breakBefore, keep_together: keepTogether }) : kind === 'shape' ? ({ type: 'shape', shape: 'line', ...(block.shapeStyle || {}) }) : kind === 'columns' ? ({ type: 'columns', count: 2, ...(block.columnsStyle || {}) }) : kind === 'column_break' ? ({ type: 'column_break' }) : kind === 'columns_end' ? ({ type: 'columns_end' }) : kind === 'image' ? ({ type: 'image', src: source || '', alt: alt || 'Image', width: width || 240, align: block.align || 'left', offset_x: offsetX || 0, offset_y: offsetY || 0, break_before: breakBefore, keep_together: keepTogether }) : kind === 'code' ? ({ type: 'code', code_type: codeType || 'qr', value: codeValue || '', width: width || 220, align: block.align || 'left', offset_x: offsetX || 0, offset_y: offsetY || 0, break_before: breakBefore, keep_together: keepTogether }) : kind === 'chart' ? ({ type: 'chart', items: items || 'chart_rows', data_mode: chartDataMode || 'bound', static_data: staticData || [], chart_type: chartType || 'bar', chart_orientation: chartOrientation || 'vertical', show_legend: showLegend !== false, show_grid: showGrid !== false, show_points: showPoints !== false, donut: donut === true, chart_title: chartTitle || '', x_axis_label: xAxisLabel || '', y_axis_label: yAxisLabel || '', label_path: labelPath || 'label', value_path: valuePath || 'value', series_path: seriesPath || '', colors: colors || [], background_color: backgroundColor || '#ffffff', grid_color: gridColor || '#d9e2df', axis_color: axisColor || '#203d37', show_values: showValues === true, stacked: stacked === true, alt: alt || 'Data chart', offset_x: offsetX || 0, offset_y: offsetY || 0, break_before: breakBefore, keep_together: keepTogether }) : kind === 'toc' ? ({ type: 'toc', offset_x: offsetX || 0, offset_y: offsetY || 0, break_before: breakBefore, keep_together: keepTogether }) : richText ? ({ type: 'rich_text', paragraphs: richText.paragraphs, offset_x: offsetX || 0, offset_y: offsetY || 0, break_before: breakBefore, keep_together: keepTogether }) : ({ ...block, type: 'text', ...(anchorId ? { anchor_id: anchorId, toc_label: tocLabel || block.text, toc_level: tocLevel || 1 } : {}), font_family: fontFamily, font_size: fontSize, offset_x: offsetX || 0, offset_y: offsetY || 0, break_before: breakBefore, keep_together: keepTogether })) }
    const editableBlocks = editorBlocks.filter(block => block.kind !== 'pdf_background' && block.kind !== 'page_background')
    definition.blocks = definition.blocks.map((block, index) => {
      const source = editableBlocks[index]
      const positioned = source as EditorBlock & PositionFields
      const paged = source as EditorBlock & PositionFields & PageFields
      return source ? { ...block, line_height: source.lineHeight, paragraph_spacing_before: source.paragraphSpacingBefore, paragraph_spacing_after: source.paragraphSpacingAfter, first_line_indent: source.firstLineIndent, left_indent: source.leftIndent, right_indent: source.rightIndent, tab_stops: source.tabStops, keep_with_next: source.keepWithNext, break_after: source.breakAfter, position_mode: positioned.positionMode, position_unit: positioned.positionUnit, position_x: positioned.positionX, position_y: positioned.positionY, page_number: paged.pageNumber } : block
    })
    definition.blocks = definition.blocks.map((block, index) => {
      const source = editableBlocks[index]
      return source ? { ...block, ...(source.semantic_kind ? { semantic_kind: source.semantic_kind, semantic_id: source.semantic_id } : {}), ...(source.field_path ? { field_path: source.field_path, field_role: source.field_role } : {}) } : block
    })
    const pageDefinition = definition.page as Record<string, unknown>
    delete pageDefinition.background_pdf
    if (pageBackgroundPdf) pageDefinition.background_pdf = pageBackgroundPdf
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
    if (renderResponse.ok && selectedTemplateId) setRecentTemplateIds(current => { const next = [selectedTemplateId, ...current.filter(item => item !== selectedTemplateId)].slice(0, 10); localStorage.setItem('docplatform.recentTemplates', JSON.stringify(next)); return next })
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
  function moveActiveBlock(direction: -1 | 1) {
    if (!activeBlockId) return
    const step = 8
    updateActiveBlock({ offsetX: Math.max(-160, Math.min(160, (activeBlock?.offsetX || 0) + direction * step)) })
  }
  async function persistComponentParts(nextParts: ComponentPart[]) {
    const parent = editorBlocks.find(block => block.id === activeBlockId)
    if (!parent?.componentId) return
    const definition = { blocks: nextParts.map(({ __id, __label, __originalText, ...part }) => ({ ...part, ...(__originalText !== undefined ? { text: __originalText } : {}) })) }
    const response = await fetch(`/api/components/${encodeURIComponent(parent.componentId)}`, { method: 'PUT', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ definition }) })
    if (response.ok) {
      setComponentParts(nextParts)
      setEditorFeedback(t('componentUpdated'))
    }
  }
  function alignActiveObject(align: EditorBlock['align']) {
    if (activeComponentPartId) {
      void persistComponentParts(componentParts.map(part => part.__id === activeComponentPartId ? { ...part, align } : part))
      return
    }
    alignSelected(align)
  }
  function moveActiveObject(direction: -1 | 1) {
    if (activeComponentPartId) {
      const next = componentParts.map(part => part.__id === activeComponentPartId ? { ...part, offset_x: Math.max(-160, Math.min(160, Number(part.offset_x || 0) + direction * 8)) } : part)
      void persistComponentParts(next)
      return
    }
    moveActiveBlock(direction)
  }
  function moveActiveImageVertical(direction: -1 | 1) {
    if (!activeBlockId || activeKind !== 'image') return
    updateActiveBlock({ offsetY: Math.max(-160, Math.min(160, (activeBlock?.offsetY || 0) + direction * 8)) })
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
  function validateTemplateJsonSchema(schema: unknown): string | null {
    if (!schema || typeof schema !== 'object' || Array.isArray(schema)) return 'Schema root must be a JSON object.'
    const root = schema as Record<string, unknown>
    if (root.type !== 'object') return 'Template schema root must have type "object".'
    if (root.properties !== undefined && (!root.properties || typeof root.properties !== 'object' || Array.isArray(root.properties))) return 'Schema properties must be an object.'
    if (root.required !== undefined && (!Array.isArray(root.required) || root.required.some(value => typeof value !== 'string'))) return 'Schema required must be an array of field names.'
    const visit = (node: unknown, path: string): string | null => {
      if (!node || typeof node !== 'object' || Array.isArray(node)) return `${path} must be an object.`
      const value = node as Record<string, unknown>
      if (value.type !== undefined && !['object', 'array', 'string', 'number', 'integer', 'boolean', 'null'].includes(String(value.type))) return `${path}.type is not supported.`
      if (value.type === 'object' && value.properties !== undefined && (!value.properties || typeof value.properties !== 'object' || Array.isArray(value.properties))) return `${path}.properties must be an object.`
      if (value.type === 'array' && value.items !== undefined) return visit(value.items, `${path}.items`)
      if (value.type === 'object' && value.properties && typeof value.properties === 'object') for (const [key, child] of Object.entries(value.properties as Record<string, unknown>)) { const error = visit(child, `${path}.properties.${key}`); if (error) return error }
      return null
    }
    return visit(schema, '$')
  }
  async function validateTemplateSchemaUpload(file: File) {
    try {
      const parsed = JSON.parse(await file.text()) as unknown
      const error = validateTemplateJsonSchema(parsed)
      if (error) { setTemplateSchemaFeedback(error); return }
      setTemplateSchema(parsed as Record<string, unknown>); setTemplateSchemaFeedback(t('templateSchemaValid'))
    } catch { setTemplateSchemaFeedback(t('templateSchemaJsonInvalid')) }
  }
  async function saveTemplateAs() {
    if (!selected) return
    const name = window.prompt(t('templateNamePrompt'), selected.name)?.trim()
    if (!name) return
    const folder = window.prompt(t('templateFolderPrompt'), '')?.trim() || ''
    if (!(await saveEditorDraft())) return
    const currentResponse = selectedTemplateId ? await fetch(`/api/templates/${encodeURIComponent(selectedTemplateId)}?draft=true`) : null
    const currentDefinition = currentResponse?.ok ? await currentResponse.json() as Definition : selected
    const definition = { ...currentDefinition, name, data_schema: templateSchema || undefined, data_schema_id: templateSchema ? String(templateSchema.$id || selected.data_schema_id || 'template-schema') : undefined, data_schema_version: templateSchema ? Number(templateSchema['x-docplatform-schema-version'] || selected.data_schema_version || 1) : undefined }
    const response = await fetch('/api/templates', { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ name, folder, definition }) })
    if (!response.ok) { setEditorFeedback(t('templateSaveFailed')); return }
    const body = await response.json() as { id?: string }
    if (body.id) { setAttempt(value => value + 1); await openTemplate(body.id); setEditorFeedback(t('templateSaved')) }
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
  const activeBlock = editorBlocks.find(block => block.id === activeBlockId) || null
  const activeKind = activeBlock?.kind || 'text'
  const activePart = componentParts.find(part => part.__id === activeComponentPartId) || null
  const contextKind = activePart ? String(activePart.type || 'text') : activeKind
  const isVisualBlock = contextKind === 'image' || contextKind === 'code' || contextKind === 'chart'
  function chartPreviewGraphic(block: EditorBlock) {
    const colors = block.colors || ['#2f6f63', '#d97941', '#4d78a8']
    if (block.chartType === 'line') return <svg className="editor-chart-line" viewBox="0 0 180 52" aria-hidden="true"><polyline points="4,42 60,24 116,34 176,10" style={{ stroke: colors[0] }} />{block.showPoints !== false && <><circle cx="4" cy="42" r="3" style={{ fill: colors[0] }} /><circle cx="60" cy="24" r="3" style={{ fill: colors[0] }} /><circle cx="116" cy="34" r="3" style={{ fill: colors[0] }} /><circle cx="176" cy="10" r="3" style={{ fill: colors[0] }} /></>}</svg>
    if (block.chartType === 'pie') return <span className={`editor-chart-pie ${block.donut ? 'donut' : ''}`} style={{ background: `conic-gradient(${colors[0]} 0 34%, ${colors[1]} 34% 68%, ${colors[2]} 68% 100%)` }} aria-hidden="true" />
    return <div className={`editor-chart-bars ${block.chartOrientation === 'horizontal' ? 'horizontal' : ''}`} aria-hidden="true"><i style={{ background: colors[0] }} /><i style={{ background: colors[1] }} /><i style={{ background: colors[2] }} /></div>
  }
  function tablePreview(block: EditorBlock) {
    const source = selected?.sample_data && typeof selected.sample_data === 'object' ? selected.sample_data as Record<string, unknown> : {}
    const tableFields = block as EditorBlock & TableRowFilterFields
    const rows = String(block.items || 'rows').split('.').reduce<unknown>((value, key) => value && typeof value === 'object' ? (value as Record<string, unknown>)[key] : undefined, source)
    const valueFor = (item: unknown, path: string) => path.split('.').reduce<unknown>((value, key) => value && typeof value === 'object' ? (value as Record<string, unknown>)[key] : undefined, item)
    const columns = block.columns || []
    const items = Array.isArray(rows) ? rows.filter(item => !tableFields.rowConditionPath || String(valueFor(item, tableFields.rowConditionPath)) === (tableFields.rowConditionValue || '')).slice(0, 5) : []
    return <div key={block.id} className={`editor-table-preview ${block.id === activeBlockId ? 'active' : ''}`} data-block-id={block.id}><table><colgroup>{columns.map((column, index) => <col key={`${column.path}-${index}`} style={column.width ? { width: `${column.width}%` } : undefined} />)}</colgroup><thead><tr>{columns.map((column, index) => <th key={`${column.path}-${index}`}>{column.header || column.path}</th>)}</tr></thead><tbody>{items.length ? items.map((item, rowIndex) => <tr key={rowIndex}>{columns.map((column, columnIndex) => <td key={`${column.path}-${columnIndex}`}>{String(valueFor(item, column.path) ?? '—')}</td>)}</tr>) : <tr><td colSpan={Math.max(columns.length, 1)} className="editor-table-empty">No sample rows at <code>{block.items || 'rows'}</code></td></tr>}</tbody></table><small>Bound to <code>{block.items || 'rows'}</code></small></div>
  }
  const editorPageSettingsPanel = pageSettingsOpen && <div id="editor-page-settings-panel" className="page-settings" aria-label={t('pageSettings')}><h4>{t('pageSettings')}</h4><div className="page-settings-grid"><label>{t('previewLocale')} <select value={previewLocale} onChange={event => setPreviewLocale(event.target.value)}><option value="en">English</option><option value="en-GB">English (UK)</option><option value="de-DE">Deutsch</option><option value="ar">العربية</option><option value="hi">हिन्दी</option><option value="th">ไทย</option><option value="zh-CN">中文</option><option value="ja-JP">日本語</option></select></label><label>{t('pageSize')} <select value={pageSettings.size} onChange={event => setPageSettings(current => ({ ...current, size: event.target.value as PageSettings['size'] }))}><option value="A3">A3</option><option value="A4">A4</option><option value="A5">A5</option><option value="Letter">Letter</option></select></label><label>{t('orientation')} <select value={pageSettings.orientation} onChange={event => setPageSettings(current => ({ ...current, orientation: event.target.value as PageSettings['orientation'] }))}><option value="portrait">{t('portrait')}</option><option value="landscape">{t('landscape')}</option></select></label><label>{t('topMargin')} <input type="number" min="0" max="100" value={pageSettings.marginTopMm} onChange={event => setPageSettings(current => ({ ...current, marginTopMm: Math.min(100, Math.max(0, Number(event.target.value) || 0)) }))} /> mm</label><label>{t('rightMargin')} <input type="number" min="0" max="100" value={pageSettings.marginRightMm} onChange={event => setPageSettings(current => ({ ...current, marginRightMm: Math.min(100, Math.max(0, Number(event.target.value) || 0)) }))} /> mm</label><label>{t('bottomMargin')} <input type="number" min="0" max="100" value={pageSettings.marginBottomMm} onChange={event => setPageSettings(current => ({ ...current, marginBottomMm: Math.min(100, Math.max(0, Number(event.target.value) || 0)) }))} /> mm</label><label>{t('leftMargin')} <input type="number" min="0" max="100" value={pageSettings.marginLeftMm} onChange={event => setPageSettings(current => ({ ...current, marginLeftMm: Math.min(100, Math.max(0, Number(event.target.value) || 0)) }))} /> mm</label><label>{t('headerComponent')} <select value={pageSettings.headerComponentId} onChange={event => setPageSettings(current => ({ ...current, headerComponentId: event.target.value }))}><option value="">{t('noComponent')}</option>{components.map(component => <option key={component.id} value={component.id}>{component.name}</option>)}</select></label><label>{t('footerComponent')} <select value={pageSettings.footerComponentId} onChange={event => setPageSettings(current => ({ ...current, footerComponentId: event.target.value }))}><option value="">{t('noComponent')}</option>{components.map(component => <option key={component.id} value={component.id}>{component.name}</option>)}</select></label><label><input type="checkbox" checked={pageSettings.showPageNumbers} onChange={event => setPageSettings(current => ({ ...current, showPageNumbers: event.target.checked }))} /> {t('pageNumbers')}</label><label>{t('headerAlign')} <select aria-label={t('headerAlign')} value={pageSettings.headerAlign} onChange={event => setPageSettings(current => ({ ...current, headerAlign: event.target.value as BoxAlign }))}>{BOX_ALIGNS.map(align => <option key={align} value={align}>{t(align)}</option>)}</select></label><label>{t('footerAlign')} <select aria-label={t('footerAlign')} value={pageSettings.footerAlign} onChange={event => setPageSettings(current => ({ ...current, footerAlign: event.target.value as BoxAlign }))}>{BOX_ALIGNS.map(align => <option key={align} value={align}>{t(align)}</option>)}</select></label><label>{t('pageNumberPosition')} <select aria-label={t('pageNumberPosition')} value={pageSettings.pageNumberPosition} onChange={event => setPageSettings(current => ({ ...current, pageNumberPosition: event.target.value as PageNumberPosition }))}>{PAGE_NUMBER_POSITIONS.map(position => <option key={position} value={position}>{position}</option>)}</select></label><label>{t('pageNumberFormat')} <input aria-label={t('pageNumberFormat')} maxLength={40} placeholder="Page {page} of {pages}" value={pageSettings.pageNumberFormat} onChange={event => setPageSettings(current => ({ ...current, pageNumberFormat: event.target.value }))} /></label><label>{t('headerFooterFontSize')} <input aria-label={t('headerFooterFontSize')} type="number" min="6" max="48" step="0.01" value={pageSettings.headerFooterFontSize} onChange={event => setPageSettings(current => ({ ...current, headerFooterFontSize: Math.min(48, Math.max(6, Math.round((Number(event.target.value) || 12) * 100) / 100)) }))} /></label><FurniturePanel value={pageSettings.furniture} onChange={furniture => setPageSettings(current => ({ ...current, furniture }))} /><label>{t('themeAccent')} <input type="color" value={themeAccent} onChange={event => setThemeAccent(event.target.value)} /></label><label>{t('pageBackground')} <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" onChange={event => { const file = event.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = () => setPageBackground(String(reader.result || '')); reader.readAsDataURL(file) } event.currentTarget.value = '' }} /></label></div></div>
  const textLayoutPalette = activeKind === 'text' && activeBlock ? <aside className="contextual-palette text-layout-palette" aria-label="Text layout"><h4>Text layout</h4><div className="text-layout-grid"><label>Line spacing <input aria-label="Line spacing" type="number" min="0.8" max="3" step="0.05" value={activeBlock.lineHeight ?? 1.45} onChange={event => updateActiveBlock({ lineHeight: Math.min(3, Math.max(0.8, Number(event.target.value) || 1.45)) })} /></label><label>Before <input aria-label="Paragraph spacing before" type="number" min="0" max="120" value={activeBlock.paragraphSpacingBefore ?? 0} onChange={event => updateActiveBlock({ paragraphSpacingBefore: Math.min(120, Math.max(0, Number(event.target.value) || 0)) })} /> px</label><label>After <input aria-label="Paragraph spacing after" type="number" min="0" max="120" value={activeBlock.paragraphSpacingAfter ?? 16} onChange={event => updateActiveBlock({ paragraphSpacingAfter: Math.min(120, Math.max(0, Number(event.target.value) || 0)) })} /> px</label><label>First-line indent <input aria-label="First-line indent" type="number" min="-240" max="240" value={activeBlock.firstLineIndent ?? 0} onChange={event => updateActiveBlock({ firstLineIndent: Math.min(240, Math.max(-240, Number(event.target.value) || 0)) })} /> px</label><label>Left indent <input aria-label="Left indent" type="number" min="0" max="240" value={activeBlock.leftIndent ?? 0} onChange={event => updateActiveBlock({ leftIndent: Math.min(240, Math.max(0, Number(event.target.value) || 0)) })} /> px</label><label>Right indent <input aria-label="Right indent" type="number" min="0" max="240" value={activeBlock.rightIndent ?? 0} onChange={event => updateActiveBlock({ rightIndent: Math.min(240, Math.max(0, Number(event.target.value) || 0)) })} /> px</label></div><label className="text-layout-wide">Tab stops (px from left indent; r = right-aligned; . _ - = leader) <input aria-label="Tab stops" defaultValue={formatTabStops(activeBlock.tabStops)} key={`${activeBlock.id}-tabs`} placeholder="48, 500r." onBlur={event => updateActiveBlock({ tabStops: parseTabStops(event.target.value) })} /></label><label className="text-layout-check"><input type="checkbox" checked={activeBlock.keepWithNext === true} onChange={event => updateActiveBlock({ keepWithNext: event.target.checked })} /> Keep with next</label><label className="text-layout-check"><input type="checkbox" checked={activeBlock.breakAfter === true} onChange={event => updateActiveBlock({ breakAfter: event.target.checked })} /> Page break after</label></aside> : null
  const templateFieldPaths = schemaFieldPaths(templateSchema)
  const templateFieldDetails = schemaFieldDetails(templateSchema)
  const bindingPath = selectedBindingPath || templateFieldPaths[0] || ''
  const bindingDetail = templateFieldDetails.find(field => field.path === bindingPath)
  const bindingSample = bindingPath ? valueAtPath(selected?.sample_data, bindingPath) : undefined
  const bindingPalette = <aside className="contextual-palette binding-palette" aria-label="Data binding"><h4>Insert bound field</h4>{templateFieldPaths.length ? <><p className="muted">Choose a schema field and insert it as an editable rich-text object.</p><div><select aria-label="Schema field" value={bindingPath} onChange={event => setSelectedBindingPath(event.target.value)}>{templateFieldPaths.map(path => <option key={path} value={path}>{path}</option>)}</select><button type="button" onClick={() => addBoundField(bindingPath)}>Insert field</button></div></> : <><p className="muted">Upload a template schema to choose fields without typing paths manually.</p><label>Schema JSON <input type="file" accept="application/json,.json" onChange={event => { const file = event.target.files?.[0]; if (file) void validateTemplateSchemaUpload(file); event.currentTarget.value = '' }} /></label>{templateSchemaFeedback && <small role="status">{templateSchemaFeedback}</small>}</>}</aside>
  const bindingInfoPalette = bindingDetail ? <aside className="contextual-palette binding-info-palette" aria-label="Selected schema field"><h4>Selected field</h4><p><strong>{bindingDetail.title}</strong><br /><code>{bindingDetail.path}</code></p><small>Type: {bindingDetail.type}{bindingDetail.format ? ` · Format: ${bindingDetail.format}` : ''}</small><p className="binding-sample">Sample: <strong>{bindingSample === undefined || bindingSample === null ? '—' : String(bindingSample)}</strong></p></aside> : null
  const activePosition = activeBlock as (EditorBlock & PositionFields) | null
  const positionPalette = activeKind === 'text' && activeBlock ? <aside className="contextual-palette position-palette" aria-label="Text position"><h4>Text position</h4><label><input type="checkbox" checked={activePosition?.positionMode === 'absolute'} onChange={event => updateActiveBlock({ positionMode: event.target.checked ? 'absolute' : 'flow' } as Partial<EditorBlock>)} /> Place at fixed page coordinates</label>{activePosition?.positionMode === 'absolute' && <><label>Unit <select aria-label="Position unit" value={activePosition.positionUnit || 'px'} onChange={event => updateActiveBlock({ positionUnit: event.target.value as PositionFields['positionUnit'] } as Partial<EditorBlock>)}><option value="mm">Millimetres (page-aware)</option><option value="px">Pixels (legacy)</option></select></label><div className="position-grid"><label>X <input aria-label="Position X" type="number" min="0" max={activePosition.positionUnit === 'mm' ? 320 : 1200} step={activePosition.positionUnit === 'mm' ? 0.1 : 1} value={activePosition.positionX ?? 0} onChange={event => updateActiveBlock({ positionX: Math.min(activePosition.positionUnit === 'mm' ? 320 : 1200, Math.max(0, Number(event.target.value) || 0)) } as Partial<EditorBlock>)} /> {activePosition.positionUnit || 'px'}</label><label>Y <input aria-label="Position Y" type="number" min="0" max={activePosition.positionUnit === 'mm' ? 450 : 2000} step={activePosition.positionUnit === 'mm' ? 0.1 : 1} value={activePosition.positionY ?? 0} onChange={event => updateActiveBlock({ positionY: Math.min(activePosition.positionUnit === 'mm' ? 450 : 2000, Math.max(0, Number(event.target.value) || 0)) } as Partial<EditorBlock>)} /> {activePosition.positionUnit || 'px'}</label></div></>}<small className="muted">Millimetres are measured from the page content origin and remain stable across preview and PDF output.</small></aside> : null
  const activePageFields = activeBlock as (EditorBlock & PageFields) | null
  const pagePalette = activeKind === 'text' && activeBlock ? <aside className="contextual-palette page-placement-palette" aria-label="Page placement"><h4>Page placement</h4><label>Page number <input aria-label="Page number" type="number" min="1" max="1000" value={activePageFields?.pageNumber ?? 1} onChange={event => updateActiveBlock({ pageNumber: Math.min(1000, Math.max(1, Math.round(Number(event.target.value) || 1))) } as Partial<EditorBlock>)} /></label><small className="muted">Assign this editable object to a physical document page. The PDF renderer inserts a page break when the page changes.</small></aside> : null
  const tablePalette = activeKind === 'table' && activeBlock ? <aside className="contextual-palette table-layout-palette" aria-label="Table layout"><h4>Table layout</h4><p className="muted">Set relative column widths for the editable table. Values are percentages of the table width.</p>{(activeBlock.columns || []).map((column, index) => <label key={`${column.path}-${index}`}><span>{column.header || column.path}</span><input aria-label={`Width for ${column.header || column.path}`} type="number" min="5" max="100" value={column.width ?? ''} placeholder="auto" onChange={event => { const width = Number(event.target.value); const columns = (activeBlock.columns || []).map((item, columnIndex) => columnIndex === index ? { ...item, width: Number.isFinite(width) && width >= 5 ? Math.min(100, width) : undefined } : item); updateActiveBlock({ columns }) }} /> %</label>)}</aside> : null
  const tableColumnEditor = activeKind === 'table' && activeBlock ? <aside className="contextual-palette table-column-editor" aria-label="Table columns"><div className="table-column-editor-heading"><h4>Table columns</h4><button type="button" onClick={() => updateActiveBlock({ columns: [...(activeBlock.columns || []), { header: 'New column', path: 'field', format: 'text' }] })}>Add column</button></div><p className="muted">Edit the visible label and data path without learning the table JSON contract.</p>{(activeBlock.columns || []).map((column, index) => <div className="table-column-row" key={`${column.path}-${index}`}><strong>Column {index + 1}</strong><label>Header <input aria-label={`Column ${index + 1} header`} value={column.header} onChange={event => updateActiveBlock({ columns: (activeBlock.columns || []).map((item, columnIndex) => columnIndex === index ? { ...item, header: event.target.value } : item) })} /></label><label>Data path <input aria-label={`Column ${index + 1} path`} value={column.path} onChange={event => updateActiveBlock({ columns: (activeBlock.columns || []).map((item, columnIndex) => columnIndex === index ? { ...item, path: event.target.value } : item) })} /></label><label>Format <select aria-label={`Column ${index + 1} format`} value={column.format || 'text'} onChange={event => updateActiveBlock({ columns: (activeBlock.columns || []).map((item, columnIndex) => columnIndex === index ? { ...item, format: event.target.value as TableColumn['format'] } : item) })}><option value="text">Text</option><option value="number">Number</option><option value="currency">Currency</option><option value="date">Date</option><option value="percent">Percent</option></select></label><label>Align <select aria-label={`Column ${index + 1} align`} value={column.align || 'left'} onChange={event => updateActiveBlock({ columns: (activeBlock.columns || []).map((item, columnIndex) => columnIndex === index ? { ...item, align: event.target.value as TableColumn['align'] } : item) })}><option value="left">Left</option><option value="center">Center</option><option value="right">Right</option></select></label><div className="table-column-order"><button type="button" aria-label={`Move column ${index + 1} up`} disabled={index === 0} onClick={() => { const columns = [...(activeBlock.columns || [])]; [columns[index - 1], columns[index]] = [columns[index], columns[index - 1]]; updateActiveBlock({ columns }) }}>↑</button><button type="button" aria-label={`Move column ${index + 1} down`} disabled={index === (activeBlock.columns || []).length - 1} onClick={() => { const columns = [...(activeBlock.columns || [])]; [columns[index], columns[index + 1]] = [columns[index + 1], columns[index]]; updateActiveBlock({ columns }) }}>↓</button></div><button type="button" className="table-column-remove" disabled={(activeBlock.columns || []).length <= 1} onClick={() => updateActiveBlock({ columns: (activeBlock.columns || []).filter((_, columnIndex) => columnIndex !== index) })}>Remove</button></div>)}<TableStylePanel value={activeBlock.tableStyle || {}} columns={(activeBlock.columns || []).length} onChange={tableStyle => updateActiveBlock({ tableStyle })} /></aside> : null
  const activeTableFilter = activeBlock as (EditorBlock & TableRowFilterFields) | null
  const tableFilterPalette = activeKind === 'table' && activeBlock ? <aside className="contextual-palette table-filter-palette" aria-label="Table row filter"><h4>Row filter</h4><p className="muted">Optionally include only rows whose field equals the value below.</p><label>Field path <input aria-label="Row filter path" value={activeTableFilter?.rowConditionPath || ''} placeholder="covered_by_section_3d" onChange={event => updateActiveBlock({ rowConditionPath: event.target.value } as Partial<EditorBlock>) } /></label><label>Equals <input aria-label="Row filter value" value={activeTableFilter?.rowConditionValue || ''} placeholder="Yes" onChange={event => updateActiveBlock({ rowConditionValue: event.target.value } as Partial<EditorBlock>) } /></label><button type="button" onClick={() => updateActiveBlock({ rowConditionPath: '', rowConditionValue: '' } as Partial<EditorBlock>)}>Clear filter</button></aside> : null
  const previewPageCount = Math.max(1, ...editorBlocks.map(block => (block as EditorBlock & PageFields).pageNumber || 1))
  const previewNavigator = previewPageCount > 1 ? <div className="preview-page-navigator" aria-label="Preview page navigation"><button type="button" aria-label="Previous preview page" disabled={previewPage <= 1} onClick={() => setPreviewPage(page => Math.max(1, page - 1))}>←</button><label>Page <select aria-label="Preview page" value={previewPage} onChange={event => setPreviewPage(Number(event.target.value))}>{Array.from({ length: previewPageCount }, (_, index) => <option key={index + 1} value={index + 1}>{index + 1}</option>)}</select> of {previewPageCount}</label><button type="button" aria-label="Next preview page" disabled={previewPage >= previewPageCount} onClick={() => setPreviewPage(page => Math.min(previewPageCount, page + 1))}>→</button></div> : null
  const versionHistoryPanel = <aside className="version-history-panel" aria-label="Template version history"><div className="version-history-heading"><h4>Version history</h4><span>{templateVersions.length}</span></div>{templateVersions.length ? <ol>{templateVersions.map(version => <li key={version.id}><div><strong>v{version.version}</strong><small>{version.status}{version.change_summary ? ` · ${version.change_summary}` : ''}</small></div><button type="button" onClick={() => void restoreTemplateVersion(version.id)}>Restore as draft</button></li>)}</ol> : <p className="muted">No saved versions yet.</p>}</aside>
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
      <section className="workspace-status-row" aria-label="Workspace overview">
        <aside className="status-panel" aria-labelledby="status-title"><h2 id="status-title">{t('status')}</h2>
          <p className="connection"><span className={`dot ${health?.status === 'ready' ? 'green' : ''}`} />{health ? t(health.status === 'ready' ? 'ready' : 'unavailable') : t(loading ? 'starting' : 'unknownStatus')}</p>
          {health && <dl>{Object.entries(health.dependencies).map(([key, value]) => <div key={key}><dt>{t(key)}</dt><dd>{t(value === 'ready' ? 'ready' : 'unavailable')}</dd></div>)}</dl>}
          <a href="/docs">{t('api')} <span aria-hidden="true">&nearr;</span></a>
        </aside>
        <section className="project-status-banner" aria-labelledby="project-status-link-title"><div><p className="eyebrow">{t('projectEyebrow')}</p><h2 id="project-status-link-title">{t('projectStatus')}</h2><p>{t('projectNote')}</p></div><a href="#project-status" onClick={event => { event.preventDefault(); setShowProjectStatus(true) }}>{t('viewProjectStatus')} <span aria-hidden="true">&rarr;</span></a></section>
      </section>
      <section className="ingestion-panel" aria-labelledby="ingestion-title">
        <div><p className="eyebrow">{t('ingestionEyebrow')}</p><h2 id="ingestion-title">{t('ingestionTitle')}</h2><p>{t('ingestionNote')}</p></div>
         <label className="upload-control">{uploading ? t('uploading') : t('chooseFiles')}<input type="file" multiple accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff" disabled={uploading} onChange={event => { void uploadFiles(event.target.files); event.currentTarget.value = '' }} /></label>
         <div className="schema-controls"><label>{t('extractionSchema')} <select value={schemaId} onChange={event => setSchemaId(event.target.value)}>{schemas.map(schema => <option key={schema.id} value={schema.id}>{schema.name}</option>)}</select></label><details><summary>{t('editSchema')}</summary><textarea aria-label={t('schemaJson')} value={schemaDraft} onChange={event => setSchemaDraft(event.target.value)} /><button type="button" onClick={() => void validateSchemaDraft()}>{t('validateSchema')}</button>{schemaFeedback && <small role="status">{schemaFeedback}</small>}</details></div>
        {ingestions.length > 0 && <ul className="ingestion-list">{ingestions.map(item => <li key={item.id}><span className="ingestion-filename">{item.filename}</span><span className={`ingestion-status ${item.status}`}>{item.status === 'queued' ? t('queued') : item.status === 'uploading' ? t('uploading') : item.status === 'failed' ? t('failed') : item.status}</span><span className="ingestion-route">{item.route}</span>{item.pagesTotal !== undefined && <span className="ingestion-progress">{item.pagesProcessed ?? 0}/{item.pagesTotal} {t('pages')}</span>}{item.id && !item.id.startsWith('local-') && !item.resultId && <button className="ingestion-action" type="button" disabled={extracting === item.id} onClick={() => void extractDocument(item)}>{extracting === item.id ? t('extracting') : t('extract')}</button>}{item.resultId && <span className="ingestion-progress">{t('reviewReady')}</span>}{item.error && <small>{item.error}</small>}</li>)}</ul>}
         {Object.values(reviews).map(review => <article className="review-card" key={review.result_id} aria-labelledby={`review-${review.result_id}`}><div className="review-card-heading"><div><p className="eyebrow">{t('reviewEyebrow')}</p><h3 id={`review-${review.result_id}`}>{t('reviewTitle')}</h3></div><span className={`review-state ${review.status}`}>{review.status}</span></div><p className="review-note">{t('reviewNote')}</p><div className="review-fields">{Object.entries(review.fields).map(([name, field]) => <label key={name}><span>{name.replaceAll('_', ' ')}</span><input value={String(field.normalized_value ?? field.original_value ?? '')} onFocus={() => selectReviewSource(review.result_id, name)} onChange={event => changeReviewField(review.result_id, name, event.target.value)} onBlur={() => void saveReviewField(review.result_id, name)} /><small>{t('confidence')}: {field.confidence.toFixed(2)}{field.validation.length ? ` · ${field.validation[0].message}` : ''}</small><button type="button" className="review-absent" onClick={() => void saveReviewField(review.result_id, name, true)}>{t('markAbsent')}</button></label>)}</div>{Object.entries(review.tables ?? {}).map(([tableName, table]) => <section className="review-line-items" key={tableName} aria-label={`${tableName} extracted values`}><h4>{tableName.replaceAll('_', ' ')}</h4><table><thead><tr>{table.columns.map(column => <th scope="col" key={column}>{column.replaceAll('_', ' ')}</th>)}</tr></thead><tbody>{table.rows.map((row, rowIndex) => <tr key={`${tableName}-${rowIndex}`}>{table.columns.map(column => { const field = row.fields[column]; return <td key={column}><button type="button" className="review-source-value" onClick={() => selectReviewSourceValue(review.result_id, field?.source)}>{String(field?.normalized_value ?? field?.original_value ?? '')}</button></td> })}</tr>)}</tbody></table></section>)}<div className="review-actions"><button type="button" onClick={() => void changeReviewStatus(review.result_id, 'approved')}>{t('approve')}</button><button type="button" onClick={() => void changeReviewStatus(review.result_id, 'rejected')}>{t('reject')}</button>{review.status === 'approved' && <button type="button" onClick={() => void renderApproved(review.result_id)} disabled={!templates.length}>{t('sendToTemplate')}</button>}</div>{review.artifact && <pre className="review-artifact">{review.artifact}</pre>}{review.error && <p className="error" role="alert">{review.error}</p>}</article>)}
         {Object.values(reviews).map(review => <div className="review-source-stack" key={`${review.result_id}-source`}><SourcePreview review={review} activeElementId={activeSource[review.result_id]?.elementId} activePageNumber={activeSource[review.result_id]?.pageNumber} activeBox={activeSource[review.result_id]?.box} draftBox={draftSourceBoxes[review.result_id]} onSelect={(elementId, pageNumber, box) => setActiveSource(current => ({ ...current, [review.result_id]: { elementId, pageNumber, box: box ?? null } }))} onDrawBox={(box, pageNumber) => { setActiveSource(current => ({ ...current, [review.result_id]: { elementId: null, pageNumber, box: null } })); setDraftSourceBoxes(current => ({ ...current, [review.result_id]: box })) }} /><div><ReviewQueue review={review} onChange={(name, value) => changeReviewField(review.result_id, name, value)} onSave={name => void saveReviewField(review.result_id, name)} onSelect={name => selectReviewSource(review.result_id, name)} /><div className="review-manual-actions"><label>{t('newFieldName')}<input value={newFieldNames[review.result_id] || ''} onChange={event => setNewFieldNames(current => ({ ...current, [review.result_id]: event.target.value }))} /></label><button type="button" onClick={() => void addReviewField(review.result_id)}>{t('addMissingField')}</button><button type="button" onClick={() => void undoReviewField(review.result_id)}>{t('undoCorrection')}</button></div><div className="source-field-links" aria-label="Extracted field source links">{Object.entries(review.fields).map(([name, field]) => { const active = field.source?.element_id === activeSource[review.result_id]?.elementId && field.source?.page_number === activeSource[review.result_id]?.pageNumber; return <button type="button" aria-pressed={active} className={active ? 'active' : ''} key={name} onClick={() => selectReviewSource(review.result_id, name)}>{name.replaceAll('_', ' ')}{field.source?.element_id ? ` (${field.source.element_id})` : ' (no source region)'}</button> })}</div></div></div>)}
       </section>
      {!selected && <section className="starter-gallery" aria-labelledby="starter-gallery-title"><div className="section-title"><div><p className="eyebrow">{t('starterEyebrow')}</p><h2 id="starter-gallery-title">{t('starterGallery')}</h2></div></div><p className="starter-gallery-note">{t('starterGalleryNote')}</p><div className="starter-grid">{starters.map(starter => <article className="starter-card" key={starter.id}><h3>{starter.name}</h3><div className="starter-languages">{starter.languages.map(language => <button type="button" key={language} onClick={() => void useStarter(starter, language)}>{t('useStarter')} · {language}</button>)}</div></article>)}</div></section>}
       {!selected && <section className="my-templates" aria-labelledby="my-templates-title"><div className="section-title"><h2 id="my-templates-title">{t('myTemplates')}</h2><span className="count">{Math.min(10, recentTemplateIds.length)}</span></div><p className="muted">{t('latestEdited')}</p><div className="recent-template-list">{recentTemplateIds.map(id => templates.find(template => template.id === id)).filter((template): template is Template => Boolean(template)).map(template => <button type="button" key={template.id} onClick={() => void openTemplate(template.id)}>{template.name}</button>)}</div></section>}
       <div className={`workspace-grid ${selected ? 'workspace-grid-selected' : ''}`}>
        <section aria-labelledby="templates-title" className="library">
          <div className="section-title"><h2 id="templates-title">{t('templates')}</h2><span className="count">{templates.length}</span></div>
          {loading && <p role="status">{t('loading')}</p>}
          {failed && <div role="alert" className="error"><p>{t('error')}</p><button onClick={() => setAttempt(value => value + 1)}>{t('retry')}</button></div>}
          {!loading && !failed && !selected && templates.length === 0 && <p>{t('empty')}</p>}
          {selected ? <article className="detail">
    {textLayoutPalette}
    {bindingPalette}
    {bindingInfoPalette}
    {positionPalette}
    {pagePalette}
    {tablePalette}
    {tableColumnEditor}{activeKind === 'columns' && activeBlock && <ColumnsPanel value={activeBlock.columnsStyle || {}} onChange={columnsStyle => updateActiveBlock({ columnsStyle })} />}{activeKind === 'shape' && activeBlock && <ShapePanel value={activeBlock.shapeStyle || {}} placement={activeBlock as EditorBlock & PositionFields} onChange={shapeStyle => updateActiveBlock({ shapeStyle })} onPlacement={patch => updateActiveBlock(patch as Partial<EditorBlock>)} />}
    {tableFilterPalette}
            {previewNavigator}
            {versionHistoryPanel}
            <button className="text-button" onClick={() => setSelected(null)}>{t('back')}</button>
            <h3>{selected.name}</h3><h4>{t('structure')}</h4>
             <div className="editor-note">{t('editorDraftNote')}</div>
             <div className="editor-settings-drawer-row" aria-label={t('editorSettings')}><div className="editor-settings-drawer-actions"><button type="button" className="page-settings-toggle" aria-expanded={pageSettingsOpen} aria-controls="editor-page-settings-panel" onClick={() => setPageSettingsOpen(value => !value)}>{t('pageSettings')} <span aria-hidden="true">{pageSettingsOpen ? '−' : '+'}</span></button><button type="button" className="page-settings-toggle" aria-expanded={templateSettingsOpen} aria-controls="editor-template-settings-panel" onClick={() => setTemplateSettingsOpen(value => !value)}>{t('templateSettings')} <span aria-hidden="true">{templateSettingsOpen ? '−' : '+'}</span></button></div>{false && pageSettingsOpen && editorPageSettingsPanel}{templateSettingsOpen && <div id="editor-template-settings-panel" className="page-settings" aria-label={t('templateSettings')}><h4>{t('templateSettings')}</h4><label>{t('templateSchemaUpload')} <input type="file" accept="application/json,.json" onChange={event => { const file = event.target.files?.[0]; if (file) void validateTemplateSchemaUpload(file); event.currentTarget.value = '' }} /></label>{templateSchemaFeedback && <p className="editor-feedback" role="status">{templateSchemaFeedback}</p>}<small>{templateSchema ? `${t('templateSchemaBound')} · ${String(templateSchema.$id || selected?.data_schema_id || 'template-schema')} v${String(templateSchema['x-docplatform-schema-version'] || selected?.data_schema_version || 1)}` : t('templateSchemaNotBound')}</small></div>}</div>
            <div className="template-settings-shell"><button type="button" className="page-settings-toggle" aria-expanded={templateSettingsOpen} aria-controls="template-settings-panel" onClick={() => setTemplateSettingsOpen(value => !value)}>{t('templateSettings')} <span aria-hidden="true">{templateSettingsOpen ? '−' : '+'}</span></button>{templateSettingsOpen && <div id="template-settings-panel" className="page-settings" aria-label={t('templateSettings')}><h4>{t('templateSettings')}</h4><label>{t('templateSchemaUpload')} <input type="file" accept="application/json,.json" onChange={event => { const file = event.target.files?.[0]; if (file) void validateTemplateSchemaUpload(file); event.currentTarget.value = '' }} /></label>{templateSchemaFeedback && <p className="editor-feedback" role="status">{templateSchemaFeedback}</p>}<small>{templateSchema ? `${t('templateSchemaBound')} · ${String(templateSchema.$id || selected?.data_schema_id || 'template-schema')} v${String(templateSchema['x-docplatform-schema-version'] || selected?.data_schema_version || 1)}` : t('templateSchemaNotBound')}</small></div>}</div>
            {activeKind === 'chart' && activeBlock && <ChartContextualPanel block={activeBlock} update={updateActiveBlock} align={alignSelected} move={value => moveActiveObject(value as -1 | 1)} remove={() => activeBlockId && removeEditorBlock(activeBlockId)} />}
            {activeBlock?.richText && <RichTextContextualPanel document={activeBlock.richText} update={document => updateActiveBlock({ richText: document, text: richTextPlainText(document) })} align={alignSelected} move={value => moveActiveObject(value)} remove={() => activeBlockId && removeEditorBlock(activeBlockId)} />}
            {activeKind === 'component' && <aside className="component-child-palette" aria-label={t('componentChildren')}><h4>{t('componentChildren')}</h4>{componentParts.length ? <>{componentParts.map((part, index) => <button type="button" className={part.__id === activeComponentPartId ? 'active' : ''} key={part.__id} onClick={() => setActiveComponentPartId(part.__id)}>{index + 1}. {String(part.text || part.type || 'child object')}</button>)}<div className="component-child-actions"><button type="button" disabled={!activeComponentPartId} onClick={() => alignActiveObject('left')}>{t('alignLeft')}</button><button type="button" disabled={!activeComponentPartId} onClick={() => alignActiveObject('center')}>{t('alignCenter')}</button><button type="button" disabled={!activeComponentPartId} onClick={() => alignActiveObject('right')}>{t('alignRight')}</button><button type="button" disabled={!activeComponentPartId} onClick={() => moveActiveObject(-1)}>{t('moveLeft')}</button><button type="button" disabled={!activeComponentPartId} onClick={() => moveActiveObject(1)}>{t('moveRight')}</button></div></> : <p className="muted">{t('componentChildrenUnavailable')}</p>}</aside>}
              <div className="editor-command-bar editor-settings-row" aria-label={t('editorCommandBar')}><div className="editor-settings-actions"><button type="button" onClick={undoEditor} disabled={historyIndex <= 0}>{t('undo')}</button><button type="button" onClick={redoEditor} disabled={historyIndex < 0 || historyIndex >= history.length - 1}>{t('redo')}</button><button type="button" onClick={copyActiveBlock}>{t('copy')}</button><button type="button" onClick={pasteBlock} disabled={!clipboardBlock}>{t('paste')}</button><button type="button" onClick={() => void saveEditorDraft()}>{t('saveDraft')}</button><button type="button" onClick={saveTemplateAs}>{t('saveTemplate')}</button><button type="button" className="page-settings-toggle" aria-expanded={pageSettingsOpen} aria-controls="page-settings-panel" onClick={() => setPageSettingsOpen(value => !value)}>{t('pageSettings')} <span aria-hidden="true">{pageSettingsOpen ? '−' : '+'}</span></button></div><span>{editorFeedback || t('readyToEdit')}</span></div>
            <aside className="editor-left-panel" aria-label={t('insertObjects')}><h4>{t('insertObjects')}</h4><div className="object-insert-grid"><button type="button" onClick={addTextBlock}>{t('addTextBlock')}</button><button type="button" onClick={addTableBlock}>{t('addTableBlock')}</button><button type="button" onClick={addRepeatBlock}>{t('addRepeatBlock')}</button><button type="button" onClick={addConditionalBlock}>{t('addConditionalBlock')}</button><button type="button" onClick={addImageBlock}>{t('addImageBlock')}</button><button type="button" onClick={addCodeBlock}>{t('addCodeBlock')}</button><button type="button" onClick={addShapeBlock}>{t('addShapeBlock')}</button><button type="button" onClick={() => addColumnMarker('columns')}>{t('addColumns')}</button><button type="button" onClick={() => addColumnMarker('column_break')}>{t('addColumnBreak')}</button><button type="button" onClick={() => addColumnMarker('columns_end')}>{t('addColumnsEnd')}</button><button type="button" onClick={addChartBlock}>{t('addChart')}</button><button type="button" onClick={addTocBlock}>{t('addTocBlock')}</button><button type="button" onClick={addPdfBackgroundBlock}>{t('addPdfBackground')}</button></div><h4>{t('documentStructure')}</h4><div className="editor-block-list" aria-label={t('textBlocks')}>{editorBlocks.map((block, index) => { const label = structureLabel(block, index); return <button type="button" className={`structure-node ${block.id === activeBlockId ? 'active' : ''}`} key={block.id} onClick={event => { setActiveBlockId(block.id); const pageNumber = (block as EditorBlock & PageFields).pageNumber; if (pageNumber) setPreviewPage(pageNumber); setSelectedBlockIds(current => event.ctrlKey || event.metaKey ? current.includes(block.id) ? current.filter(id => id !== block.id) : [...current, block.id] : [block.id]) }} aria-pressed={selectedBlockIds.includes(block.id)} aria-label={label} data-semantic-id={block.semantic_id || undefined} data-semantic-kind={block.semantic_kind || undefined} data-page-number={(block as EditorBlock & PageFields).pageNumber || undefined}><span className="structure-node-kind">{block.kind || 'text'}</span><span className="structure-node-label">{label}</span></button> })}</div><h4>{t('layers')}</h4><p className="muted">{t('layerHint')}</p></aside>
            <aside className="contextual-palette" aria-label={t('contextualActions')}><h4>{t('contextualActions')}</h4><p className="selected-object">{activeBlock ? `${t('selectedObject')}: ${activeBlock.text || activeKind}` : t('noObjectSelected')}</p>{activeKind === 'pdf_background' && <div className="contextual-action-group"><span>{t('pdfBackground')}</span><div><button type="button" onClick={() => document.getElementById('locked-pdf-background-input')?.click()}>{t('replacePdfBackground')}</button><button type="button" className="danger-action" disabled={!pageBackgroundPdf} onClick={() => setPageBackgroundPdf('')}>{t('resetPdfBackground')}</button></div><small>{pageBackgroundPdf ? t('pdfBackgroundSet') : t('noPdfBackground')}</small></div>}{activeKind === 'page_background' && <div className="contextual-action-group"><span>{t('pageBackground')}</span><div><button type="button" className="danger-action" disabled={!pageBackground} onClick={() => setPageBackground('')}>{t('resetPageBackground')}</button></div><small>{pageBackground ? t('pageBackground') : t('noPdfBackground')}</small></div>}<div className="contextual-action-group"><span>{t('alignment')}</span><div><button type="button" disabled={!activeBlock} onClick={() => alignSelected('left')}>{t('alignLeft')}</button><button type="button" disabled={!activeBlock} onClick={() => alignSelected('center')}>{t('alignCenter')}</button><button type="button" disabled={!activeBlock} onClick={() => alignSelected('right')}>{t('alignRight')}</button><button type="button" disabled={!activeBlock || (activeKind !== 'text' && !activeBlock.richText)} onClick={() => alignSelected('justify')}>{t('alignJustify')}</button></div></div><div className="contextual-action-group"><span>{t('position')}</span><div><button type="button" disabled={!activeBlock} onClick={() => moveActiveObject(-1)}>{t('moveLeft')}</button><button type="button" disabled={!activeBlock} onClick={() => moveActiveObject(1)}>{t('moveRight')}</button></div><small>{activeBlock ? `${activeBlock.offsetX || 0}px` : '—'}</small></div>{activeKind === 'text' && <div className="contextual-action-group"><span>{t('textFormatting')}</span><div><label>{t('font')} <select aria-label={t('font')} disabled={!activeBlock} value={activeBlock?.fontFamily || 'Noto Sans'} onChange={event => updateActiveBlock({ fontFamily: event.target.value })}><option>Noto Sans</option><option>Arial</option><option>Georgia</option></select></label><label>{t('fontSize')} <input aria-label={t('fontSize')} disabled={!activeBlock} type="number" min="8" max="96" step="0.01" value={activeBlock?.fontSize || 16} onChange={event => updateActiveBlock({ fontSize: Math.min(96, Math.max(8, Math.round((Number(event.target.value) || 16) * 100) / 100)) })} /></label></div></div>}{activeKind === 'chart' && activeBlock && <div className="contextual-action-group chart-contextual-actions"><span>{t('chartControls')}</span><label>{t('chartType')} <select aria-label={t('chartType')} value={activeBlock.chartType || 'bar'} onChange={event => updateActiveBlock({ chartType: event.target.value as EditorBlock['chartType'] })}><option value="bar">Bar</option><option value="line">Line</option><option value="pie">Pie</option></select></label>{activeBlock.chartType === 'bar' && <label>{t('chartOrientation')} <select aria-label={t('chartOrientation')} value={activeBlock.chartOrientation || 'vertical'} onChange={event => updateActiveBlock({ chartOrientation: event.target.value as EditorBlock['chartOrientation'] })}><option value="vertical">{t('vertical')}</option><option value="horizontal">{t('horizontal')}</option></select></label>}{activeBlock.chartType === 'line' && <label><input aria-label={t('showPoints')} type="checkbox" checked={activeBlock.showPoints !== false} onChange={event => updateActiveBlock({ showPoints: event.target.checked })} /> {t('showPoints')}</label>}{activeBlock.chartType === 'pie' && <label><input aria-label={t('donut')} type="checkbox" checked={activeBlock.donut === true} onChange={event => updateActiveBlock({ donut: event.target.checked })} /> {t('donut')}</label>}<label>{t('chartTitle')} <input aria-label={t('chartTitle')} value={activeBlock.chartTitle || ''} onChange={event => updateActiveBlock({ chartTitle: event.target.value })} /></label><label>{t('showLegend')} <input aria-label={t('showLegend')} type="checkbox" checked={activeBlock.showLegend !== false} onChange={event => updateActiveBlock({ showLegend: event.target.checked })} /> {t('showLegend')}</label></div>}<div className="contextual-action-group"><span>{t('properties')}</span><div><button type="button" disabled={!activeBlock || activeKind !== 'text'} onClick={() => updateActiveBlock({ bold: !activeBlock?.bold })}>{t('bold')}</button><button type="button" disabled={!activeBlock || !isVisualBlock} onClick={() => setEditorFeedback(t('visualObjectSelected'))}>{t('objectProperties')}</button><button type="button" className="danger-action" disabled={!activeBlock} onClick={() => activeBlockId && removeEditorBlock(activeBlockId)}>{t('deleteBlock')}</button></div></div><p className="muted">{activeKind === 'component' ? t('compositeComponentHint') : t('contextualActionHint')}</p></aside>
             {activeKind === 'image' && activeBlock && <aside className="contextual-palette image-contextual-palette" aria-label={t('imageControls')}><h4>{t('imageControls')}</h4><div className="contextual-action-group"><div><button type="button" onClick={() => updateActiveBlock({ width: Math.min(1200, (activeBlock.width || 240) + 16) })}>{t('enlargeImage')}</button><button type="button" onClick={() => updateActiveBlock({ width: Math.max(1, (activeBlock.width || 240) - 16) })}>{t('shrinkImage')}</button><button type="button" onClick={() => moveActiveImageVertical(-1)}>{t('moveUp')}</button><button type="button" onClick={() => moveActiveImageVertical(1)}>{t('moveDown')}</button></div><label>{t('imageWidth')} <input aria-label={t('imageWidth')} type="number" min="1" max="1200" value={activeBlock.width || 240} onChange={event => updateActiveBlock({ width: Math.min(1200, Math.max(1, Number(event.target.value) || 1)) })} /></label><label>{t('imageUpload')} <input type="file" accept="image/png,image/jpeg,image/gif,image/webp,image/svg+xml" onChange={event => { const file = event.target.files?.[0]; if (file) void uploadAsset(file, activeBlock.id).catch(() => undefined); event.currentTarget.value = '' }} /></label><small>{`${activeBlock.width || 240}px · ${activeBlock.offsetY || 0}px`}</small></div></aside>}
             <div className="editor-toolbar legacy-editor-toolbar" aria-label={t('editorToolbar')}>
              <button type="button" onClick={undoEditor} disabled={historyIndex <= 0} aria-label="Undo">↶ {t('undo')}</button><button type="button" onClick={redoEditor} disabled={historyIndex < 0 || historyIndex >= history.length - 1} aria-label="Redo">↷ {t('redo')}</button><button type="button" onClick={copyActiveBlock} aria-label="Copy block">{t('copy')}</button><button type="button" onClick={pasteBlock} disabled={!clipboardBlock} aria-label="Paste block">{t('paste')}</button><button type="button" onClick={() => setSnapEnabled(value => !value)} aria-pressed={snapEnabled}>{t('snap')}</button><button type="button" onClick={() => alignSelected('left')}>{t('alignLeft')}</button><button type="button" onClick={() => alignSelected('center')}>{t('alignCenter')}</button><button type="button" onClick={() => alignSelected('right')}>{t('alignRight')}</button>
              <button type="button" onClick={() => updateActiveBlock({ bold: !editorBlocks.find(block => block.id === activeBlockId)?.bold })} aria-pressed={Boolean(editorBlocks.find(block => block.id === activeBlockId)?.bold)}>{t('bold')}</button>
              <button type="button" onClick={() => updateActiveBlock({ italic: !editorBlocks.find(block => block.id === activeBlockId)?.italic })} aria-pressed={Boolean(editorBlocks.find(block => block.id === activeBlockId)?.italic)}>{t('italic')}</button>
              <label>{t('textColor')} <input type="color" value={editorBlocks.find(block => block.id === activeBlockId)?.color ?? '#203d37'} onChange={event => updateActiveBlock({ color: event.target.value })} /></label>
              <label>{t('font')} <select value={editorBlocks.find(block => block.id === activeBlockId)?.fontFamily ?? 'Noto Sans'} onChange={event => updateActiveBlock({ fontFamily: event.target.value })}><option>Noto Sans</option><option>Arial</option><option>Georgia</option></select></label>
              <label>{t('fontSize')} <input type="number" min="8" max="96" step="0.01" value={editorBlocks.find(block => block.id === activeBlockId)?.fontSize ?? 16} onChange={event => updateActiveBlock({ fontSize: Math.min(96, Math.max(8, Math.round((Number(event.target.value) || 16) * 100) / 100)) })} /></label>
              <label>{t('alignment')} <select value={editorBlocks.find(block => block.id === activeBlockId)?.align ?? 'left'} onChange={event => updateActiveBlock({ align: event.target.value as EditorBlock['align'] })}><option value="left">{t('left')}</option><option value="center">{t('center')}</option><option value="right">{t('right')}</option></select></label>
              <label><input type="checkbox" checked={Boolean(editorBlocks.find(block => block.id === activeBlockId)?.breakBefore)} onChange={event => updateActiveBlock({ breakBefore: event.target.checked })} /> {t('pageBreakBefore')}</label>
              <label><input type="checkbox" checked={editorBlocks.find(block => block.id === activeBlockId)?.keepTogether !== false} onChange={event => updateActiveBlock({ keepTogether: event.target.checked })} /> {t('keepTogether')}</label>
              <button type="button" onClick={addTextBlock}>{t('addTextBlock')}</button>
              <button type="button" onClick={addTableBlock}>{t('addTableBlock')}</button>
              <button type="button" onClick={addRepeatBlock}>{t('addRepeatBlock')}</button>
              <button type="button" onClick={addConditionalBlock}>{t('addConditionalBlock')}</button>
              <button type="button" onClick={addImageBlock}>{t('addImageBlock')}</button>
              <button type="button" onClick={addCodeBlock}>{t('addCodeBlock')}</button><button type="button" onClick={addShapeBlock}>{t('addShapeBlock')}</button><button type="button" onClick={() => addColumnMarker('columns')}>{t('addColumns')}</button><button type="button" onClick={() => addColumnMarker('column_break')}>{t('addColumnBreak')}</button><button type="button" onClick={() => addColumnMarker('columns_end')}>{t('addColumnsEnd')}</button>
              <button type="button" onClick={addChartBlock}>{t('addChartBlock')}</button>
              <button type="button" onClick={addTocBlock}>{t('addTocBlock')}</button>
              <button type="button" onClick={() => void generateSampleData()}>{t('generateSampleData')}</button>
              <button type="button" onClick={() => void saveEditorDraft()}>{t('saveDraft')}</button>
              <button type="button" onClick={() => void generatePdf()} disabled={pdfGenerating}>{pdfGenerating ? t('generatingPdf') : t('generatePdf')}</button>
            </div>
            <div className="page-settings-shell"><button type="button" className="page-settings-toggle" aria-expanded={pageSettingsOpen} aria-controls="page-settings-panel" onClick={() => setPageSettingsOpen(value => !value)}>{t('pageSettings')} <span aria-hidden="true">{pageSettingsOpen ? '−' : '+'}</span></button>{pageSettingsOpen && <div id="page-settings-panel" className="page-settings" aria-label={t('pageSettings')}><h4>{t('pageSettings')}</h4><div className="page-settings-grid"><label>{t('previewLocale')} <select value={previewLocale} onChange={event => setPreviewLocale(event.target.value)}><option value="en">English</option><option value="en-GB">English (UK)</option><option value="de-DE">Deutsch</option><option value="ar">العربية</option><option value="hi">हिन्दी</option><option value="th">ไทย</option><option value="zh-CN">中文</option><option value="ja-JP">日本語</option></select></label><label>{t('pageSize')} <select value={pageSettings.size} onChange={event => setPageSettings(current => ({ ...current, size: event.target.value as PageSettings['size'] }))}><option value="A3">A3</option><option value="A4">A4</option><option value="A5">A5</option><option value="Letter">Letter</option></select></label><label>{t('orientation')} <select value={pageSettings.orientation} onChange={event => setPageSettings(current => ({ ...current, orientation: event.target.value as PageSettings['orientation'] }))}><option value="portrait">{t('portrait')}</option><option value="landscape">{t('landscape')}</option></select></label><label>{t('topMargin')} <input type="number" min="0" max="100" value={pageSettings.marginTopMm} onChange={event => setPageSettings(current => ({ ...current, marginTopMm: Math.min(100, Math.max(0, Number(event.target.value) || 0)) }))} /> mm</label><label>{t('rightMargin')} <input type="number" min="0" max="100" value={pageSettings.marginRightMm} onChange={event => setPageSettings(current => ({ ...current, marginRightMm: Math.min(100, Math.max(0, Number(event.target.value) || 0)) }))} /> mm</label><label>{t('bottomMargin')} <input type="number" min="0" max="100" value={pageSettings.marginBottomMm} onChange={event => setPageSettings(current => ({ ...current, marginBottomMm: Math.min(100, Math.max(0, Number(event.target.value) || 0)) }))} /> mm</label><label>{t('leftMargin')} <input type="number" min="0" max="100" value={pageSettings.marginLeftMm} onChange={event => setPageSettings(current => ({ ...current, marginLeftMm: Math.min(100, Math.max(0, Number(event.target.value) || 0)) }))} /> mm</label><label>{t('headerComponent')} <select value={pageSettings.headerComponentId} onChange={event => setPageSettings(current => ({ ...current, headerComponentId: event.target.value }))}><option value="">{t('noComponent')}</option>{components.map(component => <option key={component.id} value={component.id}>{component.name}</option>)}</select></label><label>{t('footerComponent')} <select value={pageSettings.footerComponentId} onChange={event => setPageSettings(current => ({ ...current, footerComponentId: event.target.value }))}><option value="">{t('noComponent')}</option>{components.map(component => <option key={component.id} value={component.id}>{component.name}</option>)}</select></label><label><input type="checkbox" checked={pageSettings.showPageNumbers} onChange={event => setPageSettings(current => ({ ...current, showPageNumbers: event.target.checked }))} /> {t('pageNumbers')}</label><label>{t('headerAlign')} <select aria-label={t('headerAlign')} value={pageSettings.headerAlign} onChange={event => setPageSettings(current => ({ ...current, headerAlign: event.target.value as BoxAlign }))}>{BOX_ALIGNS.map(align => <option key={align} value={align}>{t(align)}</option>)}</select></label><label>{t('footerAlign')} <select aria-label={t('footerAlign')} value={pageSettings.footerAlign} onChange={event => setPageSettings(current => ({ ...current, footerAlign: event.target.value as BoxAlign }))}>{BOX_ALIGNS.map(align => <option key={align} value={align}>{t(align)}</option>)}</select></label><label>{t('pageNumberPosition')} <select aria-label={t('pageNumberPosition')} value={pageSettings.pageNumberPosition} onChange={event => setPageSettings(current => ({ ...current, pageNumberPosition: event.target.value as PageNumberPosition }))}>{PAGE_NUMBER_POSITIONS.map(position => <option key={position} value={position}>{position}</option>)}</select></label><label>{t('pageNumberFormat')} <input aria-label={t('pageNumberFormat')} maxLength={40} placeholder="Page {page} of {pages}" value={pageSettings.pageNumberFormat} onChange={event => setPageSettings(current => ({ ...current, pageNumberFormat: event.target.value }))} /></label><label>{t('headerFooterFontSize')} <input aria-label={t('headerFooterFontSize')} type="number" min="6" max="48" step="0.01" value={pageSettings.headerFooterFontSize} onChange={event => setPageSettings(current => ({ ...current, headerFooterFontSize: Math.min(48, Math.max(6, Math.round((Number(event.target.value) || 12) * 100) / 100)) }))} /></label><FurniturePanel value={pageSettings.furniture} onChange={furniture => setPageSettings(current => ({ ...current, furniture }))} /><label>{t('themeAccent')} <input type="color" value={themeAccent} onChange={event => setThemeAccent(event.target.value)} /></label><label>{t('pageBackground')} <input type="file" accept="image/png,image/jpeg,image/gif,image/webp" onChange={event => { const file = event.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = () => setPageBackground(String(reader.result || '')); reader.readAsDataURL(file) } event.currentTarget.value = '' }} /></label></div></div>}</div>
            <div className="pdf-background-control"><label>{t('pdfBackground')} <input id="locked-pdf-background-input" type="file" accept="application/pdf,.pdf" onChange={event => { const file = event.target.files?.[0]; if (file) { const reader = new FileReader(); reader.onload = () => { setPageBackgroundPdf(String(reader.result || '')); ensurePdfBackgroundBlock() }; reader.readAsDataURL(file) } event.currentTarget.value = '' }} /></label><span className="muted">{pageBackgroundPdf ? t('pdfBackgroundSet') : t('noPdfBackground')}</span></div>
            <div className="structure-controls" aria-label={t('structureControls')}><label>{t('anchorId')} <input value={editorBlocks.find(block => block.id === activeBlockId)?.anchorId || ''} onChange={event => updateActiveBlock({ anchorId: event.target.value })} placeholder="section-1" /></label><label>{t('tocLabel')} <input value={editorBlocks.find(block => block.id === activeBlockId)?.tocLabel || ''} onChange={event => updateActiveBlock({ tocLabel: event.target.value })} placeholder={t('tocLabelPlaceholder')} /></label><label>{t('tocLevel')} <input type="number" min="1" max="6" value={editorBlocks.find(block => block.id === activeBlockId)?.tocLevel || 1} onChange={event => updateActiveBlock({ tocLevel: Math.min(6, Math.max(1, Number(event.target.value) || 1)) })} /></label></div>
            <div className="theme-controls" aria-label={t('themeControls')}><label>{t('themeFont')} <select value={themeFontFamily} onChange={event => setThemeFontFamily(event.target.value)}><option>Noto Sans</option><option>Arial</option><option>Georgia</option></select></label><label>{t('themeSpacing')} <input type="number" min="0.8" max="2" step="0.05" value={themeSpacing} onChange={event => setThemeSpacing(event.target.value)} /></label></div>
            {editorBlocks.find(block => block.id === activeBlockId)?.kind === 'chart' && (() => { const chart = editorBlocks.find(block => block.id === activeBlockId)!; return <div className="chart-controls" aria-label={t('chartControls')}><label>{t('chartType')} <select value={chart.chartType || 'bar'} onChange={event => updateActiveBlock({ chartType: event.target.value as EditorBlock['chartType'] })}><option value="bar">Bar</option><option value="line">Line</option><option value="pie">Pie</option></select></label><label>{t('chartItems')} <input value={chart.items || 'chart_rows'} onChange={event => updateActiveBlock({ items: event.target.value })} /></label><label>{t('chartLabelPath')} <input value={chart.labelPath || 'label'} onChange={event => updateActiveBlock({ labelPath: event.target.value })} /></label><label>{t('chartValuePath')} <input value={chart.valuePath || 'value'} onChange={event => updateActiveBlock({ valuePath: event.target.value })} /></label><label>{t('chartTitle')} <input value={chart.chartTitle || ''} onChange={event => updateActiveBlock({ chartTitle: event.target.value })} /></label><label>{t('chartOrientation')} <select value={chart.chartOrientation || 'vertical'} onChange={event => updateActiveBlock({ chartOrientation: event.target.value as EditorBlock['chartOrientation'] })}><option value="vertical">{t('vertical')}</option><option value="horizontal">{t('horizontal')}</option></select></label>{chart.chartType === 'line' && <label><input type="checkbox" checked={chart.showPoints !== false} onChange={event => updateActiveBlock({ showPoints: event.target.checked })} /> {t('showPoints')}</label>}{chart.chartType === 'bar' && <label><input type="checkbox" checked={chart.showGrid !== false} onChange={event => updateActiveBlock({ showGrid: event.target.checked })} /> {t('showGrid')}</label>}{chart.chartType === 'pie' && <label><input type="checkbox" checked={chart.donut === true} onChange={event => updateActiveBlock({ donut: event.target.checked })} /> {t('donut')}</label>}<label><input type="checkbox" checked={chart.showLegend !== false} onChange={event => updateActiveBlock({ showLegend: event.target.checked })} /> {t('showLegend')}</label><label>{t('xAxisLabel')} <input value={chart.xAxisLabel || ''} onChange={event => updateActiveBlock({ xAxisLabel: event.target.value })} /></label><label>{t('yAxisLabel')} <input value={chart.yAxisLabel || ''} onChange={event => updateActiveBlock({ yAxisLabel: event.target.value })} /></label></div> })()}
            <div className="component-removal-toolbar" aria-label={t('reusableComponents')}><button type="button" disabled={!editorBlocks.some(block => block.id === activeBlockId && block.kind === 'component')} onClick={() => { const target = editorBlocks.find(block => block.id === activeBlockId && block.kind === 'component'); if (target) removeEditorBlock(target.id) }}>{t('removeComponent')}</button><button type="button" disabled={!activeBlockId} onClick={() => activeBlockId && removeEditorBlock(activeBlockId)}>{t('deleteBlock')}</button></div>
            {editorFeedback && <p className="editor-feedback" role="status">{editorFeedback}</p>}
            <div className="script-locale-controls" aria-label={t('additionalScriptLocales')}><span>{t('additionalScriptLocales')}</span><button type="button" onClick={() => setPreviewLocale('he')}>{t('hebrew')}</button><button type="button" onClick={() => setPreviewLocale('ta')}>{t('tamil')}</button><button type="button" onClick={() => setPreviewLocale('ko')}>{t('korean')}</button></div>
            <div className="component-controls" aria-label={t('reusableComponents')}><button type="button" onClick={() => void createComponentFromSelection()}>{t('saveAsComponent')}</button><button type="button" onClick={() => void updateComponentFromSelection()} disabled={!editorBlocks.some(block => block.id === activeBlockId && block.kind === 'component') || selectedBlockIds.length < 2}>{t('updateComponent')}</button>{components.map(component => <button type="button" key={component.id} onClick={() => addComponent(component)}>{t('addComponent')}: {component.name}</button>)}{editorBlocks.filter(block => block.kind === 'component').map(block => <button className="remove-component" type="button" key={`remove-${block.id}`} onClick={() => removeEditorBlock(block.id)}>{t('removeComponent')}: {block.text}</button>)}</div>
            <div className="editor-layout"><div className="editor-preview-column"><div className="editor-preview-heading"><div><strong>{t('localPreview')}</strong><span>{pageSettings.size} · {pageSettings.orientation}</span></div><small>Scroll to inspect the full page at its working size.</small></div><div className="editor-page-viewport" role="region" aria-label={`${t('preview')} — ${pageSettings.size} ${pageSettings.orientation}`} tabIndex={0}><div className="editor-page-stage"><div className="editor-page" style={{ '--preview-page-width': `${pageDimensions(pageSettings).width}mm`, '--preview-page-height': `${pageDimensions(pageSettings).height}mm` } as CSSProperties} aria-label={t('preview')} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); dropBlockOnPage(event.dataTransfer.getData('text/plain')) }}><span className="page-label">{t('localPreview')}</span>{snapEnabled && <span className={`alignment-guide alignment-guide-${editorBlocks.find(block => block.id === activeBlockId)?.align || 'left'}`} aria-hidden="true" />}{editorBlocks.map(block => block.kind === 'chart' ? <div key={block.id} data-block-id={block.id} className={`editor-chart-preview ${block.id === activeBlockId ? 'active' : ''}`}><strong>{block.chartTitle || block.text}</strong><span>{block.chartType || 'bar'} {t('chart')}</span>{chartPreviewGraphic(block)}</div> : block.kind === 'table' ? tablePreview(block) : block.kind === 'columns' || block.kind === 'column_break' || block.kind === 'columns_end' ? <div key={block.id} className="editor-column-marker" role="note">{block.kind === 'columns' ? `Columns (${block.columnsStyle?.count || 2}) start` : block.kind === 'column_break' ? 'Column break' : 'Columns end'}</div> : block.kind === 'shape' ? <div key={block.id} className="editor-shape-preview" aria-label="Shape preview" style={shapePreviewStyle(block.shapeStyle || {})} /> : block.kind === 'image' ? <figure key={block.id} className="editor-image-preview" style={{ textAlign: block.align, transform: `translate(${block.offsetX || 0}px, ${block.offsetY || 0}px)` }}><img src={block.source} alt={block.alt || 'Image preview'} style={{ width: `${Math.min(block.width || 240, 280)}px` }} /></figure> : <p key={block.id} dir="auto" style={{ fontWeight: block.bold ? 700 : 400, fontStyle: block.italic ? 'italic' : 'normal', color: block.color, fontFamily: block.fontFamily, fontSize: `${block.fontSize}px`, textAlign: block.align, transform: `translate(${block.offsetX || 0}px, ${block.offsetY || 0}px)` }}>{block.text}</p>)}</div></div></div></div></div>
            <div className="editor-generation-actions" aria-label="Document generation"><button type="button" onClick={() => void generateSampleData()}>{t('generateSampleData')}</button><button type="button" onClick={() => void generatePdf()} disabled={pdfGenerating}>{pdfGenerating ? t('generatingPdf') : t('generatePdf')}</button></div>
            {editorBlocks.some(block => block.kind === 'table' || block.kind === 'loop' || block.kind === 'if' || block.kind === 'image' || block.kind === 'code') && <div className="table-editor" aria-label={t('logicBlocks')}><h4>{t('logicBlocks')}</h4>{editorBlocks.filter(block => block.kind === 'table' || block.kind === 'loop' || block.kind === 'if' || block.kind === 'image' || block.kind === 'code').map(block => block.kind === 'code' ? <div className="table-editor-row" key={block.id}><label>{t('codeType')} <select value={block.codeType || 'qr'} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, codeType: event.target.value as EditorBlock['codeType'] } : item))}><option value="qr">QR</option><option value="code128">Code 128</option><option value="ean13">EAN-13</option></select></label><label>{t('codeValue')} <input value={block.codeValue || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, codeValue: event.target.value } : item))} /></label><label>{t('imageWidth')} <input type="number" min="40" max="1200" value={block.width || 220} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, width: Math.min(1200, Math.max(40, Number(event.target.value) || 220)) } : item))} /></label></div> : block.kind === 'image' ? <div className="table-editor-row" key={block.id}><label>{t('imageSource')} <input value={block.source || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, source: event.target.value } : item))} /></label><label>{t('imageUpload')} <input type="file" accept="image/png,image/jpeg,image/gif,image/webp,image/svg+xml" onChange={event => { const file = event.target.files?.[0]; if (file) void uploadAsset(file, block.id).catch(() => undefined); event.currentTarget.value = '' }} /></label><label>{t('imageAlt')} <input value={block.alt || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, alt: event.target.value } : item))} /></label><label>{t('imageWidth')} <input type="number" min="1" max="1200" value={block.width || 240} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, width: Math.min(1200, Math.max(1, Number(event.target.value) || 240)) } : item))} /></label><label>{t('alignment')} <select value={block.align} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, align: event.target.value as EditorBlock['align'] } : item))}><option value="left">{t('left')}</option><option value="center">{t('center')}</option><option value="right">{t('right')}</option></select></label></div> : block.kind === 'table' ? <div className="table-editor-row" key={block.id}><label>{t('tableItems')} <input value={block.items || 'rows'} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, items: event.target.value } : item))} /></label><label>{t('tableColumns')} <textarea value={JSON.stringify(block.columns || [], null, 2)} onChange={event => { try { const columns = JSON.parse(event.target.value) as TableColumn[]; setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, columns } : item)) } catch { /* keep the last valid table contract */ } }} /></label></div> : block.kind === 'loop' ? <div className="table-editor-row" key={block.id}><label>{t('repeatItems')} <input value={block.items || 'rows'} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, items: event.target.value } : item))} /></label><label>{t('repeatText')} <input value={block.repeatText || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, repeatText: event.target.value } : item))} /></label></div> : <div className="table-editor-row" key={block.id}><label>{t('conditionPath')} <input value={block.conditionPath || 'show_note'} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, conditionPath: event.target.value } : item))} /></label><label>{t('thenText')} <input value={block.thenText || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, thenText: event.target.value } : item))} /></label><label>{t('elseText')} <input value={block.elseText || ''} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, elseText: event.target.value } : item))} /></label><label><input type="checkbox" checked={block.conditionValue === true} onChange={event => setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, conditionValue: event.target.checked } : item))} /> {t('conditionEnabled')}</label></div>)}</div>}
            {editorArtifact && <details open className="editor-output"><summary>{t('serverPreview')}</summary><iframe title={t('serverPreview')} srcDoc={editorArtifact} sandbox="" />{editorDiagnostics && <section className="render-diagnostics" aria-label={t('renderDiagnostics')}><h4>{t('renderDiagnostics')}</h4><dl><div><dt>{t('renderEngine')}</dt><dd>{editorDiagnostics.engine || '—'}</dd></div><div><dt>{t('renderStatus')}</dt><dd>{editorDiagnostics.status || '—'}</dd></div><div><dt>{t('detectedScripts')}</dt><dd>{editorDiagnostics.scripts?.join(', ') || '—'}</dd></div><div><dt>{t('fontStacks')}</dt><dd>{editorDiagnostics.font_stacks?.join(' | ') || '—'}</dd></div></dl>{(editorDiagnostics.font_report || []).length > 0 && <table><thead><tr><th>{t('script')}</th><th>{t('requestedStack')}</th><th>{t('embeddedFonts')}</th><th>{t('missingGlyphs')}</th><th>{t('diagnosticStatus')}</th></tr></thead><tbody>{editorDiagnostics.font_report?.map(report => <tr key={report.script}><th scope="row">{report.script}</th><td>{report.requested_stack}</td><td>{report.embedded_fonts.join(', ') || '—'}</td><td>{report.missing_glyphs.join(', ') || '—'}</td><td>{report.status}</td></tr>)}</tbody></table>}</section>}</details>}
            {pdfFeedback && <p className="editor-feedback" role="status">{pdfFeedback}</p>}
            {pdfUrl && <section className="pdf-output" aria-label={t('pdfPreview')}><div className="pdf-output-heading"><h4>{t('pdfPreview')}</h4><a href={pdfUrl} download={`${(documentMetadata.title || selected.name || 'document').replace(/[^A-Za-z0-9_-]+/g, '-').toLowerCase()}.pdf`}>{t('downloadPdf')}</a></div><iframe title={t('pdfPreview')} src={pdfUrl} /><p className="muted">{pdfReport?.engine || '—'} · {pdfReport?.output_bytes ? `${pdfReport.output_bytes} bytes` : ''}</p></section>}
            {editorBlocks.find(block => block.id === activeBlockId)?.kind === 'chart' && (() => { const chart = editorBlocks.find(block => block.id === activeBlockId)!; const colors = chart.colors || ['#2f6f63', '#d97941', '#4d78a8']; return <div className="chart-data-advanced" aria-label="Chart data and style"><strong>Chart data and style</strong><label>Data source <select value={chart.chartDataMode || 'bound'} onChange={event => updateActiveBlock({ chartDataMode: event.target.value as EditorBlock['chartDataMode'] })}><option value="bound">Bound input data</option><option value="static">Static template data</option></select></label><small>{chart.chartDataMode === 'static' ? 'Static rows are stored in the template; bound data is supplied at render time.' : 'At render time, the server reads an array from this path.'}</small><label>Array path <input value={chart.items || 'chart_rows'} onChange={event => updateActiveBlock({ items: event.target.value })} /></label><label>Category field <input value={chart.labelPath || 'label'} onChange={event => updateActiveBlock({ labelPath: event.target.value })} /></label><label>Value field <input value={chart.valuePath || 'value'} onChange={event => updateActiveBlock({ valuePath: event.target.value })} /></label><label>Series field <input placeholder="Optional, e.g. series" value={chart.seriesPath || ''} onChange={event => updateActiveBlock({ seriesPath: event.target.value })} /></label><div className="chart-color-row"><label>Series 1 <input type="color" value={colors[0]} onChange={event => updateActiveBlock({ colors: [event.target.value, colors[1], colors[2]] })} /></label><label>Series 2 <input type="color" value={colors[1]} onChange={event => updateActiveBlock({ colors: [colors[0], event.target.value, colors[2]] })} /></label><label>Series 3 <input type="color" value={colors[2]} onChange={event => updateActiveBlock({ colors: [colors[0], colors[1], event.target.value] })} /></label></div><div className="chart-color-row"><label>Background <input type="color" value={chart.backgroundColor || '#ffffff'} onChange={event => updateActiveBlock({ backgroundColor: event.target.value })} /></label><label>Grid <input type="color" value={chart.gridColor || '#d9e2df'} onChange={event => updateActiveBlock({ gridColor: event.target.value })} /></label><label>Axes <input type="color" value={chart.axisColor || '#203d37'} onChange={event => updateActiveBlock({ axisColor: event.target.value })} /></label></div><label><input type="checkbox" checked={chart.showValues === true} onChange={event => updateActiveBlock({ showValues: event.target.checked })} /> Show values</label>{chart.chartType === 'bar' && <label><input type="checkbox" checked={chart.stacked === true} onChange={event => updateActiveBlock({ stacked: event.target.checked })} /> Stack series</label>}{chart.chartDataMode === 'static' && <label>Static rows (JSON) <textarea value={JSON.stringify(chart.staticData || [], null, 2)} onChange={event => { try { const parsed = JSON.parse(event.target.value); if (Array.isArray(parsed)) updateActiveBlock({ staticData: parsed }) } catch { /* keep last valid rows */ } }} /></label>}</div> })()}<h4>{t('data')}</h4><pre>{JSON.stringify(selected.sample_data, null, 2)}</pre><p className="muted">{t('future')}</p>
          </article> : templates.map(template => <article className="template-card" key={template.id}>
            <div className="paper-preview" aria-hidden="true"><div className="paper"><span className="paper-brand" /><span className="line short" /><span className="line" /><span className="line" /><span className="line medium" /><span className="paper-sign" /></div></div>
            <div className="card-body"><span className="tag">{t('sample')}</span><h3>{template.id === 'sample-welcome' ? t('letter') : template.name}</h3><p>{t('letterDescription')}</p><button onClick={() => void openTemplate(template.id)}>{t('open')}<span aria-hidden="true"> &rarr;</span></button></div>
          </article>)}
        </section>
      </div></>}
    </main>
    <footer>{t('footer')}</footer>
  </>
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
