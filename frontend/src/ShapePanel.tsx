// Line and rectangle shape controls (DD-433). Shape keys use the template contract's snake_case names;
// placement reuses the editor's shared position fields, which the draft serializer saves for every block.
export type ShapeStyle = {
  shape?: 'line' | 'rectangle'
  orientation?: 'horizontal' | 'vertical'
  width_mm?: number
  height_mm?: number
  stroke_color?: string
  stroke_width?: number
  stroke_style?: 'solid' | 'dashed' | 'dotted'
  fill_color?: string
  layer?: 'front' | 'behind'
}

export const SHAPE_KEYS: (keyof ShapeStyle)[] = ['shape', 'orientation', 'width_mm', 'height_mm', 'stroke_color',
  'stroke_width', 'stroke_style', 'fill_color', 'layer']

export function pickShapeStyle(stored: Record<string, unknown>): ShapeStyle {
  const style: Record<string, unknown> = {}
  for (const key of SHAPE_KEYS) if (stored[key] !== undefined) style[key] = stored[key]
  return style as ShapeStyle
}

export type ShapePlacement = { positionMode?: 'flow' | 'absolute'; positionUnit?: 'px' | 'mm'; positionX?: number; positionY?: number; paragraphSpacingBefore?: number }

type Props = { value: ShapeStyle; placement: ShapePlacement; onChange: (value: ShapeStyle) => void; onPlacement: (patch: ShapePlacement) => void }

function bounded(value: string, low: number, high: number): number | undefined {
  if (value.trim() === '') return undefined
  const number = Math.round(Number(value) * 100) / 100
  return Number.isFinite(number) ? Math.min(high, Math.max(low, number)) : undefined
}

export function shapePreviewStyle(style: ShapeStyle): Record<string, string> {
  const stroke = `${style.stroke_width ?? 1}px ${style.stroke_style || 'solid'} ${style.stroke_color || '#000000'}`
  const mmToPx = 96 / 25.4
  if (style.shape === 'rectangle') {
    return { width: `${(style.width_mm || 40) * mmToPx}px`, height: `${(style.height_mm || 10) * mmToPx}px`,
      border: (style.stroke_width ?? 1) > 0 ? stroke : 'none', background: style.fill_color || 'transparent', boxSizing: 'border-box' }
  }
  return style.orientation === 'vertical'
    ? { width: '0', height: `${(style.height_mm || 10) * mmToPx}px`, borderLeft: stroke }
    : { width: style.width_mm ? `${style.width_mm * mmToPx}px` : '100%', height: '0', borderTop: stroke }
}

export function ShapePanel({ value, placement, onChange, onPlacement }: Props) {
  const set = (patch: Partial<ShapeStyle>) => {
    const next: Record<string, unknown> = { ...value, ...patch }
    for (const key of Object.keys(next)) if (next[key] === undefined) delete next[key]
    onChange(next as ShapeStyle)
  }
  const number = (key: keyof ShapeStyle, label: string, low: number, high: number) =>
    <label>{label} <input aria-label={`Shape ${label.toLowerCase()}`} type="number" min={low} max={high} step="0.01"
      value={(value[key] as number | undefined) ?? ''} onChange={event => set({ [key]: bounded(event.target.value, low, high) })} /></label>
  const absolute = placement.positionMode === 'absolute'
  return <aside className="contextual-palette shape-panel" aria-label="Shape">
    <h4>Shape</h4>
    <label>Shape <select aria-label="Shape kind" value={value.shape || 'line'} onChange={event => set({ shape: event.target.value as ShapeStyle['shape'] })}>
      <option value="line">Line</option><option value="rectangle">Rectangle</option></select></label>
    {value.shape !== 'rectangle' && <label>Direction <select aria-label="Shape orientation" value={value.orientation || 'horizontal'}
      onChange={event => set({ orientation: event.target.value as ShapeStyle['orientation'] })}>
      <option value="horizontal">Horizontal</option><option value="vertical">Vertical</option></select></label>}
    {number('width_mm', 'Width mm', 0.1, 500)}
    {number('height_mm', 'Height mm', 0.1, 500)}
    <label>Line colour <input aria-label="Shape stroke colour" type="color" value={value.stroke_color || '#000000'} onChange={event => set({ stroke_color: event.target.value })} /></label>
    {number('stroke_width', 'Line width', 0, 10)}
    <label>Line style <select aria-label="Shape stroke style" value={value.stroke_style || 'solid'} onChange={event => set({ stroke_style: event.target.value as ShapeStyle['stroke_style'] })}>
      <option value="solid">Solid</option><option value="dashed">Dashed</option><option value="dotted">Dotted</option></select></label>
    {value.shape === 'rectangle' && <><label>Fill <input aria-label="Shape fill colour" type="color" value={value.fill_color || '#ffffff'} onChange={event => set({ fill_color: event.target.value })} /></label>
      <button type="button" disabled={!value.fill_color} onClick={() => set({ fill_color: undefined })}>No fill</button></>}
    <label>Layer <select aria-label="Shape layer" value={value.layer || 'front'} onChange={event => set({ layer: event.target.value as ShapeStyle['layer'] })}>
      <option value="front">In front of text</option><option value="behind">Behind text</option></select></label>
    <label><input aria-label="Shape fixed position" type="checkbox" checked={absolute}
      onChange={event => onPlacement({ positionMode: event.target.checked ? 'absolute' : 'flow', positionUnit: 'mm' })} /> Place at fixed page coordinates (mm)</label>
    {absolute && <>
      <label>X mm <input aria-label="Shape position X" type="number" min="0" max="500" step="0.01" value={placement.positionX ?? 0}
        onChange={event => onPlacement({ positionX: bounded(event.target.value, 0, 500) ?? 0, positionUnit: 'mm' })} /></label>
      <label>Y mm <input aria-label="Shape position Y" type="number" min="0" max="500" step="0.01" value={placement.positionY ?? 0}
        onChange={event => onPlacement({ positionY: bounded(event.target.value, 0, 500) ?? 0, positionUnit: 'mm' })} /></label></>}
    {!absolute && <label>Spacing before px <input aria-label="Shape spacing before" type="number" min="0" max="240" value={placement.paragraphSpacingBefore ?? 0}
      onChange={event => onPlacement({ paragraphSpacingBefore: bounded(event.target.value, 0, 240) ?? 0 })} /></label>}
  </aside>
}
