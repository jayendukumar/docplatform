// Column section controls (DD-435). A "Start columns" block opens a section; "Column break" moves to the next
// column; "End columns" closes it. Keys use the template contract's snake_case names.
export type ColumnsStyle = { count?: number; gap_mm?: number; widths?: number[]; rule_color?: string; rule_width?: number }

export const COLUMN_KEYS: (keyof ColumnsStyle)[] = ['count', 'gap_mm', 'widths', 'rule_color', 'rule_width']

export function pickColumnsStyle(stored: Record<string, unknown>): ColumnsStyle {
  const style: Record<string, unknown> = {}
  for (const key of COLUMN_KEYS) if (stored[key] !== undefined) style[key] = stored[key]
  return style as ColumnsStyle
}

export function parseWidths(text: string, count: number): number[] | undefined {
  const widths = text.split(',').map(value => Math.round(Number(value.trim()) * 100) / 100)
    .filter(value => Number.isFinite(value) && value >= 5 && value <= 100)
  return widths.length === count ? widths : undefined
}

type Props = { value: ColumnsStyle; onChange: (value: ColumnsStyle) => void }

export function ColumnsPanel({ value, onChange }: Props) {
  const set = (patch: Partial<ColumnsStyle>) => {
    const next: Record<string, unknown> = { ...value, ...patch }
    for (const key of Object.keys(next)) if (next[key] === undefined) delete next[key]
    onChange(next as ColumnsStyle)
  }
  const count = value.count || 2
  return <aside className="contextual-palette columns-panel" aria-label="Columns">
    <h4>Columns</h4>
    <p className="muted">Blocks after this one are laid out in columns until "End columns". Insert "Column break" to move to the next column; without breaks the text flows across columns.</p>
    <label>Columns <select aria-label="Column count" value={count} onChange={event => set({ count: Number(event.target.value), widths: undefined })}>
      {[1, 2, 3, 4].map(option => <option key={option} value={option}>{option}</option>)}</select></label>
    <label>Gap mm <input aria-label="Column gap" type="number" min="0" max="50" step="0.01" value={value.gap_mm ?? 6}
      onChange={event => set({ gap_mm: Math.min(50, Math.max(0, Number(event.target.value) || 0)) })} /></label>
    <label>Widths % (comma separated, one per column) <input aria-label="Column widths" defaultValue={(value.widths || []).join(', ')} key={`${count}-${(value.widths || []).join()}`}
      placeholder="equal" onBlur={event => set({ widths: parseWidths(event.target.value, count) })} /></label>
    <label>Rule between columns <input aria-label="Column rule colour" type="color" value={value.rule_color || '#cccccc'} onChange={event => set({ rule_color: event.target.value })} /></label>
    <label>Rule width px <input aria-label="Column rule width" type="number" min="0" max="4" step="0.25" value={value.rule_width ?? 1}
      onChange={event => set({ rule_width: Math.min(4, Math.max(0, Number(event.target.value) || 0)) })} /></label>
    <button type="button" disabled={!value.rule_color} onClick={() => set({ rule_color: undefined })}>No rule</button>
  </aside>
}
