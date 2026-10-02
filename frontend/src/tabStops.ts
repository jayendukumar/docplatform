// Tab stops (DD-426): a bare number is a left stop; objects add right alignment and leaders.
// The editor's compact syntax is a comma-separated list such as "48, 500r." where the number is the
// position in px from the paragraph's left indent, "r" right-aligns the text after the tab, and a
// trailing ".", "_" or "-" draws a dot, underscore or hyphen leader up to the stop.
export type TabLeader = 'none' | 'dot' | 'underscore' | 'hyphen'
export type TabStop = number | { position: number; align?: 'left' | 'right'; leader?: TabLeader }

const LEADER_BY_SYMBOL: Record<string, TabLeader> = { '.': 'dot', _: 'underscore', '-': 'hyphen' }
const SYMBOL_BY_LEADER: Record<TabLeader, string> = { none: '', dot: '.', underscore: '_', hyphen: '-' }
export const MAX_TAB_STOPS = 16

export function tabStopPosition(stop: TabStop): number {
  return typeof stop === 'number' ? stop : stop.position
}

export function parseTabStops(text: string): TabStop[] {
  const stops: TabStop[] = []
  for (const token of text.split(',')) {
    const match = /^\s*(\d+(?:\.\d+)?)\s*([lr])?\s*([._-])?\s*$/i.exec(token)
    if (!match) continue
    const position = Math.round(Number(match[1]) * 100) / 100
    if (!(position >= 0 && position <= 2000)) continue
    const align = match[2]?.toLowerCase() === 'r' ? 'right' : 'left'
    const leader = match[3] ? LEADER_BY_SYMBOL[match[3]] : 'none'
    stops.push(align === 'left' && leader === 'none' ? position : { position, align, leader })
  }
  return stops.sort((a, b) => tabStopPosition(a) - tabStopPosition(b)).slice(0, MAX_TAB_STOPS)
}

export function formatTabStops(stops: TabStop[] | undefined): string {
  return (stops || []).map(stop => typeof stop === 'number' ? String(stop)
    : `${stop.position}${stop.align === 'right' ? 'r' : ''}${SYMBOL_BY_LEADER[stop.leader || 'none']}`).join(', ')
}
