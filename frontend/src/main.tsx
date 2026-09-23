import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { useTranslation } from 'react-i18next'
import './i18n'
import './style.css'
import './editor.css'
import { epicStories } from './epicStories'

type Template = { id: string; name: string; schema_version: number }
type Definition = { name: string; blocks: { type: string; text: string }[]; sample_data: unknown }
type EditorBlock = { id: string; text: string; bold: boolean; italic: boolean; color: string; align: 'left' | 'center' | 'right' }
type Health = { status: string; dependencies: Record<string, string> }

type Epic = {
  id: string
  name: string
  weight: number
  progress: number
  status: 'verified' | 'in-progress' | 'planned'
  achievement: string
}

const epics: Epic[] = [
  { id: 'E1', name: 'Platform foundation and deployment', weight: 5.5, progress: 1.4, status: 'in-progress', achievement: 'The Compose foundation, PostgreSQL migrations, readiness checks and sample workspace are running. Storage contract verification and CPU rendering/extraction evidence remain.' },
  { id: 'E2', name: 'Template editor', weight: 7.3, progress: 0, status: 'in-progress', achievement: 'Initial local editor slice added: text blocks can be edited, reordered and formatted with an immediate preview. Persistence and final output remain pending.' },
  { id: 'E3', name: 'Template management and governance', weight: 6.9, progress: 0, status: 'planned', achievement: 'Versioning, folders, publishing and portable template governance are not implemented yet.' },
  { id: 'E4', name: 'Rendering engine and multi-language support', weight: 8.3, progress: 0, status: 'planned', achievement: 'The multilingual rendering spike is still a prerequisite; no script coverage or renderer selection is claimed.' },
  { id: 'E5', name: 'Data binding and template logic', weight: 6.9, progress: 0, status: 'planned', achievement: 'Bounded expressions, validation and approved extraction binding are queued behind the template contracts.' },
  { id: 'E6', name: 'Output formats', weight: 6.9, progress: 0, status: 'planned', achievement: 'PDF generation, Word merging and conversion are not available in the current foundation.' },
  { id: 'E7', name: 'API, SDKs and integrations', weight: 7.3, progress: 0, status: 'in-progress', achievement: 'A small read-only API and OpenAPI explorer are available; authentication, jobs, SDKs and webhooks remain future work.' },
  { id: 'E8', name: 'Digitization: ingestion and OCR pipeline', weight: 9.2, progress: 0, status: 'planned', achievement: 'Upload routing, layout analysis and OCR have not started.' },
  { id: 'E9', name: 'Schema and extraction', weight: 7.3, progress: 0, status: 'planned', achievement: 'Schema extraction, normalization and confidence calibration have not started.' },
  { id: 'E10', name: 'Review and correction', weight: 6.4, progress: 0, status: 'planned', achievement: 'Source overlays, correction history and approval workflows have not started.' },
  { id: 'E11', name: 'Identity, security and compliance', weight: 7.3, progress: 0, status: 'planned', achievement: 'The local foundation is loopback-only and unauthenticated; identity and broader security controls remain future work.' },
  { id: 'E12', name: 'Operations, observability and scale', weight: 5.5, progress: 0, status: 'planned', achievement: 'Basic health checks exist; durable job operations, observability and scale testing have not started.' },
  { id: 'E13', name: 'AI assistance and agent integration', weight: 4.6, progress: 0, status: 'planned', achievement: 'Optional AI assistance and agent integrations are intentionally not part of the current foundation.' },
  { id: 'E14', name: 'Ecosystem, documentation and community', weight: 6.0, progress: 0, status: 'in-progress', achievement: 'Foundation documentation, implementation planning and decision traceability are in place; launch examples and contributor workflows remain.' },
  { id: 'E15', name: 'Hosted cloud and billing', weight: 4.6, progress: 0, status: 'planned', achievement: 'Hosted tenancy, metering and billing are outside the current self-hosted foundation.' },
]

const totalWeight = epics.reduce((sum, epic) => sum + epic.weight, 0)
const completedPoints = epics.reduce((sum, epic) => sum + epic.progress, 0)

function App() {
  const { t } = useTranslation()
  const [templates, setTemplates] = useState<Template[]>([])
  const [health, setHealth] = useState<Health | null>(null)
  const [selected, setSelected] = useState<Definition | null>(null)
  const [editorBlocks, setEditorBlocks] = useState<EditorBlock[]>([])
  const [activeBlockId, setActiveBlockId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const [attempt, setAttempt] = useState(0)
  const [showProjectStatus, setShowProjectStatus] = useState(false)
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
    return () => controller.abort()
  }, [attempt])
  async function openTemplate(id: string) {
    setFailed(false)
    try {
      const response = await fetch(`/api/templates/${encodeURIComponent(id)}`)
      if (!response.ok) throw new Error('unavailable')
      const definition = await response.json() as Definition
      const blocks = definition.blocks.map((block, index) => ({ id: `block-${index}`, text: block.text, bold: false, italic: false, color: '#203d37', align: 'left' as const }))
      setSelected(definition); setEditorBlocks(blocks); setActiveBlockId(blocks[0]?.id ?? null)
    } catch { setFailed(true) }
  }
  function updateActiveBlock(change: Partial<EditorBlock>) {
    if (!activeBlockId) return
    setEditorBlocks(blocks => blocks.map(block => block.id === activeBlockId ? { ...block, ...change } : block))
  }
  function addTextBlock() {
    const block = { id: `block-${Date.now()}`, text: 'New text block', bold: false, italic: false, color: '#203d37', align: 'left' as const }
    setEditorBlocks(blocks => [...blocks, block]); setActiveBlockId(block.id)
  }
  function moveBlock(sourceId: string, targetId: string) {
    if (sourceId === targetId) return
    setEditorBlocks(blocks => { const source = blocks.find(block => block.id === sourceId); if (!source) return blocks; const remaining = blocks.filter(block => block.id !== sourceId); const targetIndex = remaining.findIndex(block => block.id === targetId); remaining.splice(targetIndex, 0, source); return remaining })
  }
  return <>
    <header><a className="brand" href="/"><span className="mark" aria-hidden="true">D</span>{t('brand')}</a><span className="workspace">{t('workspace')}</span></header>
    <main>
      <section className="intro"><p className="eyebrow">{t('eyebrow')}</p><h1>{t('heading')}</h1><p>{t('description')}</p></section>
      {showProjectStatus ? <section className="project-status-view" aria-labelledby="project-status-title">
        <a className="back-link" href="/" onClick={event => { event.preventDefault(); setShowProjectStatus(false) }}>{t('backToWorkspace')}</a>
        <div className="project-status-heading"><div><p className="eyebrow">{t('projectEyebrow')}</p><h2 id="project-status-title">{t('projectStatus')}</h2></div><span className="status-date">{t('statusSnapshot')}</span></div>
        <div className="overall-status"><span>{t('overallStatus')}</span><strong>{completedPoints.toFixed(1)}%</strong><div className="progress-track" role="progressbar" aria-label={t('overallProgress')} aria-valuemin={0} aria-valuemax={100} aria-valuenow={completedPoints}><span style={{ width: `${completedPoints}%` }} /></div></div>
        <div className="table-wrap"><table className="story-table"><caption>{t('epicTableCaption')}</caption><thead><tr><th scope="col">{t('storyId')}</th><th scope="col">{t('story')}</th><th scope="col">{t('priority')}</th><th scope="col">{t('size')}</th></tr></thead><tbody>{epics.map(epic => <><tr className="epic-group" key={`${epic.id}-group`}><th colSpan={4} scope="colgroup"><span className="epic-group-id">{epic.id}</span><span className="epic-group-name">{epic.name}</span><span className={`epic-status ${epic.status}`}>{t(epic.status)}</span><span className="epic-group-meta">{t('weight')}: {epic.weight.toFixed(1)} · {epic.progress.toFixed(1)} {t('of')} {epic.weight.toFixed(1)}</span></th></tr>{(epicStories[epic.id] ?? []).map(item => <tr key={item.id}><th scope="row" className="story-id">{item.id}</th><td className="story-title">{item.story}</td><td><span className={`priority priority-${item.priority.toLowerCase()}`}>{item.priority}</span></td><td className="story-size">{item.size}</td></tr>)}</>)}</tbody></table></div>
      </section> : <>
      <section className="project-status-banner" aria-labelledby="project-status-link-title"><div><p className="eyebrow">{t('projectEyebrow')}</p><h2 id="project-status-link-title">{t('projectStatus')}</h2><p>{t('projectNote')}</p></div><a href="#project-status" onClick={event => { event.preventDefault(); setShowProjectStatus(true) }}>{t('viewProjectStatus')} <span aria-hidden="true">&rarr;</span></a></section>
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
              <button type="button" onClick={() => updateActiveBlock({ bold: !editorBlocks.find(block => block.id === activeBlockId)?.bold })} aria-pressed={Boolean(editorBlocks.find(block => block.id === activeBlockId)?.bold)}>{t('bold')}</button>
              <button type="button" onClick={() => updateActiveBlock({ italic: !editorBlocks.find(block => block.id === activeBlockId)?.italic })} aria-pressed={Boolean(editorBlocks.find(block => block.id === activeBlockId)?.italic)}>{t('italic')}</button>
              <label>{t('textColor')} <input type="color" value={editorBlocks.find(block => block.id === activeBlockId)?.color ?? '#203d37'} onChange={event => updateActiveBlock({ color: event.target.value })} /></label>
              <label>{t('alignment')} <select value={editorBlocks.find(block => block.id === activeBlockId)?.align ?? 'left'} onChange={event => updateActiveBlock({ align: event.target.value as EditorBlock['align'] })}><option value="left">{t('left')}</option><option value="center">{t('center')}</option><option value="right">{t('right')}</option></select></label>
              <button type="button" onClick={addTextBlock}>{t('addTextBlock')}</button>
            </div>
            <div className="editor-layout"><div className="editor-block-list" aria-label={t('textBlocks')}>{editorBlocks.map(block => <div className={`editor-block-row ${block.id === activeBlockId ? 'active' : ''}`} key={block.id} draggable onDragStart={event => event.dataTransfer.setData('text/plain', block.id)} onDragOver={event => event.preventDefault()} onDrop={event => { event.preventDefault(); moveBlock(event.dataTransfer.getData('text/plain'), block.id) }}><button className="block-grip" type="button" onClick={() => setActiveBlockId(block.id)} aria-label={`${t('selectBlock')} ${block.text}`}>⠿</button><textarea value={block.text} onFocus={() => setActiveBlockId(block.id)} onChange={event => { setActiveBlockId(block.id); setEditorBlocks(blocks => blocks.map(item => item.id === block.id ? { ...item, text: event.target.value } : item)) }} /></div>)}</div><div className="editor-page" aria-label={t('preview')}><span className="page-label">{t('localPreview')}</span>{editorBlocks.map(block => <p key={block.id} dir="auto" style={{ fontWeight: block.bold ? 700 : 400, fontStyle: block.italic ? 'italic' : 'normal', color: block.color, textAlign: block.align }}>{block.text}</p>)}</div></div>
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
