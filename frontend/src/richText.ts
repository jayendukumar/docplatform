export type RichTextFormat = 'text' | 'number' | 'currency' | 'date' | 'percent'

export type RichTextStyle = {
  fontFamily?: string
  fontSize?: number
  color?: string
  bold?: boolean
  italic?: boolean
  underline?: boolean
}

export type RichTextCondition = {
  path: string
  operator: 'equals' | 'not_equals' | 'in' | 'truthy' | 'greater_than' | 'greater_or_equal' | 'less_than' | 'less_or_equal'
  value?: string | number | boolean | Array<string | number | boolean>
  then: RichTextRun[]
  else?: RichTextRun[]
}

export type RichTextRun = {
  type: 'text' | 'binding' | 'condition'
  text?: string
  path?: string
  format?: RichTextFormat
  currency?: string
  style?: RichTextStyle
  condition?: RichTextCondition
}

export type RichTextParagraph = {
  align: 'left' | 'center' | 'right' | 'justify'
  runs: RichTextRun[]
}

export type RichTextDocument = {
  version: 1
  paragraphs: RichTextParagraph[]
}

export function defaultRichText(): RichTextDocument {
  return { version: 1, paragraphs: [{ align: 'left', runs: [{ type: 'text', text: 'New text block', style: {} }] }] }
}

export function richTextPlainText(document: RichTextDocument): string {
  return document.paragraphs.map(paragraph => paragraph.runs.map(run => run.type === 'text' ? run.text || '' : run.type === 'binding' ? `{{${run.path || 'field'}}}` : '[condition]').join('')).join('\n')
}
