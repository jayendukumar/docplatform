export type ChartContextBlock = {
  chartType?: 'bar' | 'line' | 'pie'
  chartOrientation?: 'vertical' | 'horizontal'
  showLegend?: boolean
  showGrid?: boolean
  showPoints?: boolean
  donut?: boolean
  chartTitle?: string
  xAxisLabel?: string
  yAxisLabel?: string
  items?: string
  labelPath?: string
  valuePath?: string
  seriesPath?: string
  chartDataMode?: 'bound' | 'static'
  staticData?: Array<Record<string, unknown>>
  colors?: string[]
  backgroundColor?: string
  gridColor?: string
  axisColor?: string
  showValues?: boolean
  stacked?: boolean
}

type Props = {
  block: ChartContextBlock
  update: (change: Partial<ChartContextBlock>) => void
  align: (value: 'left' | 'center' | 'right') => void
  move: (value: number) => void
  remove: () => void
}

const fallbackColors = ['#2f6f63', '#d97941', '#4d78a8']

export function ChartContextualPanel({ block, update, align, move, remove }: Props) {
  const colors = block.colors || fallbackColors
  const colorAt = (index: number) => colors[index] || fallbackColors[index]
  const setColor = (index: number, value: string) => update({ colors: colors.map((color, current) => current === index ? value : color) })
  const field = (label: string, value: string, onChange: (value: string) => void, placeholder?: string) => <label>{label}<input value={value} placeholder={placeholder} onChange={event => onChange(event.target.value)} /></label>
  return <aside className="chart-contextual-panel" aria-label="Chart contextual actions">
    <h4>Chart contextual actions</h4>
    <div className="contextual-action-group"><span>Position</span><div><button type="button" onClick={() => align('left')}>Left</button><button type="button" onClick={() => align('center')}>Center</button><button type="button" onClick={() => align('right')}>Right</button><button type="button" onClick={() => move(-1)}>Move left</button><button type="button" onClick={() => move(1)}>Move right</button></div></div>
    <div className="contextual-action-group"><span>Chart type</span><select aria-label="Chart type" value={block.chartType || 'bar'} onChange={event => update({ chartType: event.target.value as ChartContextBlock['chartType'] })}><option value="bar">Bar</option><option value="line">Line</option><option value="pie">Pie</option></select>{block.chartType === 'bar' && <label>Orientation<select value={block.chartOrientation || 'vertical'} onChange={event => update({ chartOrientation: event.target.value as ChartContextBlock['chartOrientation'] })}><option value="vertical">Vertical</option><option value="horizontal">Horizontal</option></select></label>}{block.chartType === 'line' && <label><input type="checkbox" checked={block.showPoints !== false} onChange={event => update({ showPoints: event.target.checked })} /> Show points</label>}{block.chartType === 'pie' && <label><input type="checkbox" checked={block.donut === true} onChange={event => update({ donut: event.target.checked })} /> Donut</label>}</div>
    <div className="contextual-action-group"><span>Labels and axes</span>{field('Title', block.chartTitle || '', value => update({ chartTitle: value }))}{field('X-axis label', block.xAxisLabel || '', value => update({ xAxisLabel: value }))}{field('Y-axis label', block.yAxisLabel || '', value => update({ yAxisLabel: value }))}<label><input type="checkbox" checked={block.showLegend !== false} onChange={event => update({ showLegend: event.target.checked })} /> Show legend</label><label><input type="checkbox" checked={block.showGrid !== false} onChange={event => update({ showGrid: event.target.checked })} /> Show grid</label><label><input type="checkbox" checked={block.showValues === true} onChange={event => update({ showValues: event.target.checked })} /> Show values</label>{block.chartType === 'bar' && <label><input type="checkbox" checked={block.stacked === true} onChange={event => update({ stacked: event.target.checked })} /> Stack series</label>}</div>
    <div className="contextual-action-group"><span>Data binding</span><label>Data source<select value={block.chartDataMode || 'bound'} onChange={event => update({ chartDataMode: event.target.value as ChartContextBlock['chartDataMode'] })}><option value="bound">Bound input data</option><option value="static">Static template data</option></select></label>{field('Array path', block.items || 'chart_rows', value => update({ items: value }))}{field('Category field', block.labelPath || 'label', value => update({ labelPath: value }))}{field('Value field', block.valuePath || 'value', value => update({ valuePath: value }))}{field('Series field', block.seriesPath || '', value => update({ seriesPath: value }), 'Optional, e.g. series')}{block.chartDataMode === 'static' && <label>Static rows (JSON)<textarea value={JSON.stringify(block.staticData || [], null, 2)} onChange={event => { try { const parsed = JSON.parse(event.target.value); if (Array.isArray(parsed)) update({ staticData: parsed }) } catch { /* retain last valid JSON */ } }} /></label>}</div>
    <div className="contextual-action-group"><span>Colours</span><div className="chart-color-row">{[0, 1, 2].map(index => <label key={index}>Series {index + 1}<input aria-label={`Series ${index + 1} colour`} type="color" value={colorAt(index)} onChange={event => setColor(index, event.target.value)} /></label>)}</div><div className="chart-color-row"><label>Background<input aria-label="Background colour" type="color" value={block.backgroundColor || '#ffffff'} onChange={event => update({ backgroundColor: event.target.value })} /></label><label>Grid<input aria-label="Grid colour" type="color" value={block.gridColor || '#d9e2df'} onChange={event => update({ gridColor: event.target.value })} /></label><label>Axes<input aria-label="Axes colour" type="color" value={block.axisColor || '#203d37'} onChange={event => update({ axisColor: event.target.value })} /></label></div></div>
    <button type="button" className="danger-action" onClick={remove}>Delete chart</button>
  </aside>
}
