// Table data source, header and appearance controls (DD-431). Values use the template contract's
// snake_case keys so the panel edits exactly what the renderer and capability manifest describe.
export type TableStyle = {
  data_mode?: 'bound' | 'static'
  static_rows?: string[][]
  show_header?: boolean
  header_bold?: boolean
  header_background?: string
  font_family?: string
  font_size?: number
  borders?: 'grid' | 'horizontal' | 'none'
  border_color?: string
  border_width?: number
  cell_padding_x?: number
  cell_padding_y?: number
  row_height?: number
  header_row_height?: number
  header_spacing_after?: number
  row_styles?: RowStyle[]
  paragraph_spacing_before?: number
  paragraph_spacing_after?: number
}

// One body row's style (DD-447): row is 0-based; a negative row counts from the end (-1 = last row).
export type RowStyle = { row: number; bold?: boolean; italic?: boolean; background?: string; color?: string }

export const TABLE_STYLE_KEYS: (keyof TableStyle)[] = ['data_mode', 'static_rows', 'show_header', 'header_bold',
  'header_background', 'font_family', 'font_size', 'borders', 'border_color', 'border_width', 'cell_padding_x', 'cell_padding_y',
  'row_height', 'header_row_height', 'header_spacing_after', 'row_styles', 'paragraph_spacing_before', 'paragraph_spacing_after']

export function pickTableStyle(stored: Record<string, unknown>): TableStyle {
  const style: Record<string, unknown> = {}
  for (const key of TABLE_STYLE_KEYS) if (stored[key] !== undefined) style[key] = stored[key]
  return style as TableStyle
}

// Static rows are edited as one row per line with cells separated by " | ".
export function formatStaticRows(rows: string[][] | undefined): string {
  return (rows || []).map(row => row.join(' | ')).join('\n')
}

export function parseStaticRows(text: string, columns: number): string[][] {
  return text.split('\n').filter(line => line.trim()).slice(0, 1000)
    .map(line => line.split('|').map(cell => cell.trim()).slice(0, Math.max(1, columns)))
}

type Props = { value: TableStyle; columns: number; onChange: (value: TableStyle) => void }

function bounded(value: string, low: number, high: number): number | undefined {
  if (value.trim() === '') return undefined
  const number = Math.round(Number(value) * 100) / 100
  return Number.isFinite(number) ? Math.min(high, Math.max(low, number)) : undefined
}

export function TableStylePanel({ value, columns, onChange }: Props) {
  const set = (patch: Partial<TableStyle>) => {
    const next: Record<string, unknown> = { ...value, ...patch }
    for (const key of Object.keys(next)) if (next[key] === undefined) delete next[key]
    onChange(next as TableStyle)
  }
  const number = (key: keyof TableStyle, label: string, low: number, high: number) =>
    <label>{label} <input aria-label={`Table ${label.toLowerCase()}`} type="number" min={low} max={high} step="0.01"
      value={(value[key] as number | undefined) ?? ''} onChange={event => set({ [key]: bounded(event.target.value, low, high) })} /></label>
  return <div className="table-style-panel">
    <h4>Table data and style</h4>
    <label>Rows <select aria-label="Table rows source" value={value.data_mode || 'bound'}
      onChange={event => set({ data_mode: event.target.value as TableStyle['data_mode'] })}>
      <option value="bound">Repeat from data</option><option value="static">Fixed rows</option></select></label>
    {value.data_mode === 'static' && <label className="table-style-wide">Fixed rows (one per line, cells separated by |)
      <textarea aria-label="Table fixed rows" defaultValue={formatStaticRows(value.static_rows)} key={formatStaticRows(value.static_rows)}
        onBlur={event => set({ static_rows: parseStaticRows(event.target.value, columns) })} /></label>}
    <label><input aria-label="Table show header" type="checkbox" checked={value.show_header !== false}
      onChange={event => set({ show_header: event.target.checked })} /> Show header row</label>
    <label><input aria-label="Table header bold" type="checkbox" checked={value.header_bold !== false}
      onChange={event => set({ header_bold: event.target.checked })} /> Bold header</label>
    <label>Header shading <input aria-label="Table header background" type="color" value={value.header_background || '#ffffff'}
      onChange={event => set({ header_background: event.target.value })} /></label>
    <button type="button" disabled={!value.header_background} onClick={() => set({ header_background: undefined })}>No header shading</button>
    <label>Font family <input aria-label="Table font family" placeholder="Arial, sans-serif" value={value.font_family || ''}
      onChange={event => set({ font_family: /^[A-Za-z0-9 ,_-]{1,80}$/.test(event.target.value) ? event.target.value : undefined })} /></label>
    {number('font_size', 'Font size', 8, 96)}
    <label>Borders <select aria-label="Table borders" value={value.borders || 'grid'}
      onChange={event => set({ borders: event.target.value as TableStyle['borders'] })}>
      <option value="grid">Grid</option><option value="horizontal">Horizontal rules</option><option value="none">None</option></select></label>
    <label>Border colour <input aria-label="Table border colour" type="color" value={value.border_color || '#cfd9cc'}
      onChange={event => set({ border_color: event.target.value })} /></label>
    {number('border_width', 'Border width', 0, 4)}
    {number('cell_padding_x', 'Cell padding horizontal', 0, 48)}
    {number('cell_padding_y', 'Cell padding vertical', 0, 48)}
    {number('row_height', 'Row height', 1, 400)}
    {number('header_row_height', 'Header row height', 1, 400)}
    {number('header_spacing_after', 'Space after header', 0, 240)}
    {number('paragraph_spacing_before', 'Spacing before', 0, 240)}
    {number('paragraph_spacing_after', 'Spacing after', 0, 240)}
    <RowStylesEditor value={value.row_styles || []} onChange={rows => set({ row_styles: rows.length ? rows : undefined })} />
  </div>
}

// Per-row styles (DD-447): each entry styles one body row; -1 is the last row, so a bound table's totals row works.
function RowStylesEditor({ value, onChange }: { value: RowStyle[]; onChange: (value: RowStyle[]) => void }) {
  const update = (index: number, patch: Partial<RowStyle>) => onChange(value.map((entry, i) => {
    if (i !== index) return entry
    const next: Record<string, unknown> = { ...entry, ...patch }
    for (const key of Object.keys(next)) if (next[key] === undefined) delete next[key]
    return next as RowStyle
  }))
  return <fieldset className="table-style-wide table-row-styles">
    <legend>Row styles (row 0 is the first body row; -1 is the last)</legend>
    {value.map((entry, index) => <div key={index} className="table-row-style">
      <label>Row <input aria-label={`Row style ${index + 1} row`} type="number" min={-1000} max={999} step="1" value={entry.row}
        onChange={event => { const row = Math.trunc(Number(event.target.value)); if (Number.isFinite(row)) update(index, { row }) }} /></label>
      <label><input aria-label={`Row style ${index + 1} bold`} type="checkbox" checked={entry.bold === true}
        onChange={event => update(index, { bold: event.target.checked || undefined })} /> Bold</label>
      <label><input aria-label={`Row style ${index + 1} italic`} type="checkbox" checked={entry.italic === true}
        onChange={event => update(index, { italic: event.target.checked || undefined })} /> Italic</label>
      <label>Shading <input aria-label={`Row style ${index + 1} background`} type="color" value={entry.background || '#ffffff'}
        onChange={event => update(index, { background: event.target.value })} /></label>
      <button type="button" disabled={!entry.background} onClick={() => update(index, { background: undefined })}>No shading</button>
      <label>Text colour <input aria-label={`Row style ${index + 1} color`} type="color" value={entry.color || '#000000'}
        onChange={event => update(index, { color: event.target.value })} /></label>
      <button type="button" disabled={!entry.color} onClick={() => update(index, { color: undefined })}>Default colour</button>
      <button type="button" onClick={() => onChange(value.filter((_, i) => i !== index))}>Remove</button>
    </div>)}
    <button type="button" disabled={value.length >= 50} onClick={() => onChange([...value, { row: -1, bold: true }])}>Add row style</button>
  </fieldset>
}
