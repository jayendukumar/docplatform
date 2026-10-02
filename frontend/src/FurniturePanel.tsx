// Header/footer zones, distances from the page edge and rules (DD-437). Keys use the template contract's
// snake_case page properties and are saved directly into the page definition.
export type FurnitureSettings = {
  header_left?: string; header_center?: string; header_right?: string
  footer_left?: string; footer_center?: string; footer_right?: string
  header_distance_mm?: number; footer_distance_mm?: number
  header_rule?: boolean; footer_rule?: boolean
  header_rule_offset_mm?: number; footer_rule_offset_mm?: number
  furniture_rule_color?: string; furniture_rule_width?: number
  zone_styles?: Record<string, ZoneStyle>
}

export type ZoneStyle = { font_size?: number; bold?: boolean; italic?: boolean }

export const FURNITURE_KEYS: (keyof FurnitureSettings)[] = ['header_left', 'header_center', 'header_right',
  'footer_left', 'footer_center', 'footer_right', 'header_distance_mm', 'footer_distance_mm', 'header_rule',
  'footer_rule', 'header_rule_offset_mm', 'footer_rule_offset_mm', 'furniture_rule_color', 'furniture_rule_width', 'zone_styles']

export function pickFurniture(page: Record<string, unknown>): FurnitureSettings {
  const settings: Record<string, unknown> = {}
  for (const key of FURNITURE_KEYS) if (page[key] !== undefined) settings[key] = page[key]
  return settings as FurnitureSettings
}

type Props = { value: FurnitureSettings; onChange: (value: FurnitureSettings) => void }

function bounded(value: string, low: number, high: number): number | undefined {
  if (value.trim() === '') return undefined
  const number = Math.round(Number(value) * 100) / 100
  return Number.isFinite(number) ? Math.min(high, Math.max(low, number)) : undefined
}

export function FurniturePanel({ value, onChange }: Props) {
  const set = (patch: Partial<FurnitureSettings>) => {
    const next: Record<string, unknown> = { ...value, ...patch }
    for (const key of Object.keys(next)) if (next[key] === undefined || next[key] === '') delete next[key]
    onChange(next as FurnitureSettings)
  }
  const styleOf = (key: string): ZoneStyle => value.zone_styles?.[key] || {}
  const setStyle = (key: string, patch: ZoneStyle) => {
    const merged: Record<string, unknown> = { ...styleOf(key), ...patch }
    for (const name of Object.keys(merged)) if (merged[name] === undefined || merged[name] === false) delete merged[name]
    const styles: Record<string, ZoneStyle> = { ...(value.zone_styles || {}) }
    if (Object.keys(merged).length) styles[key] = merged as ZoneStyle
    else delete styles[key]
    set({ zone_styles: Object.keys(styles).length ? styles : undefined })
  }
  // Each zone: its text plus an optional size, bold and italic that override the shared header/footer size (DD-439).
  const zone = (key: keyof FurnitureSettings, label: string) => <div className="furniture-zone">
    <label>{label} <input aria-label={label} maxLength={500} value={(value[key] as string | undefined) || ''}
      onChange={event => set({ [key]: event.target.value })} /></label>
    <label>Size <input aria-label={`${label} size`} type="number" min="6" max="48" step="0.01" value={styleOf(key).font_size ?? ''}
      onChange={event => setStyle(key, { font_size: bounded(event.target.value, 6, 48) })} /></label>
    <label><input aria-label={`${label} bold`} type="checkbox" checked={styleOf(key).bold === true}
      onChange={event => setStyle(key, { bold: event.target.checked })} /> B</label>
    <label><input aria-label={`${label} italic`} type="checkbox" checked={styleOf(key).italic === true}
      onChange={event => setStyle(key, { italic: event.target.checked })} /> I</label>
  </div>
  const number = (key: keyof FurnitureSettings, label: string, low: number, high: number) =>
    <label>{label} <input aria-label={label} type="number" min={low} max={high} step="0.01" value={(value[key] as number | undefined) ?? ''}
      onChange={event => set({ [key]: bounded(event.target.value, low, high) })} /></label>
  return <fieldset className="furniture-panel">
    <legend>Header and footer zones</legend>
    {zone('header_left', 'Header left')}{zone('header_center', 'Header centre')}{zone('header_right', 'Header right')}
    {zone('footer_left', 'Footer left')}{zone('footer_center', 'Footer centre')}{zone('footer_right', 'Footer right')}
    {number('header_distance_mm', 'Header distance from top edge (mm)', 0, 100)}
    {number('footer_distance_mm', 'Footer distance from bottom edge (mm)', 0, 100)}
    <label><input aria-label="Header rule" type="checkbox" checked={value.header_rule === true} onChange={event => set({ header_rule: event.target.checked || undefined })} /> Rule under header</label>
    {value.header_rule && number('header_rule_offset_mm', 'Header rule gap above content (mm)', 0, 100)}
    <label><input aria-label="Footer rule" type="checkbox" checked={value.footer_rule === true} onChange={event => set({ footer_rule: event.target.checked || undefined })} /> Rule above footer</label>
    {value.footer_rule && number('footer_rule_offset_mm', 'Footer rule gap below content (mm)', 0, 100)}
    {(value.header_rule || value.footer_rule) && <>
      <label>Rule colour <input aria-label="Header and footer rule colour" type="color" value={value.furniture_rule_color || '#000000'} onChange={event => set({ furniture_rule_color: event.target.value })} /></label>
      {number('furniture_rule_width', 'Rule width (px)', 0, 4)}</>}
  </fieldset>
}
