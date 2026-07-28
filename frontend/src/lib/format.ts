import type { Job } from '../types'

export const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
export const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
]

const EMP_LABELS: Record<string, string> = {
  FullTime: 'Full-time',
  PartTime: 'Part-time',
  Contract: 'Contract',
  Contractor: 'Contractor',
  Intern: 'Internship',
  Temporary: 'Temporary',
  Seasonal: 'Seasonal',
}

export function prettyEmp(e: string): string {
  if (!e) return 'Other'
  return EMP_LABELS[e] ?? e.replace(/([a-z])([A-Z])/g, '$1 $2')
}

export interface DateParts {
  valid: boolean
  ts: number
  y: number
  m: number
  d: number
}

export function dateParts(iso: string | null): DateParts {
  if (!iso) return { valid: false, ts: 0, y: 0, m: 0, d: 0 }
  const dt = new Date(iso)
  if (isNaN(dt.getTime())) return { valid: false, ts: 0, y: 0, m: 0, d: 0 }
  return {
    valid: true,
    ts: dt.getTime(),
    y: dt.getUTCFullYear(),
    m: dt.getUTCMonth() + 1,
    d: dt.getUTCDate(),
  }
}

export function ageDays(ts: number): number {
  return Math.floor((Date.now() - ts) / 86400000)
}

export function relativeAge(ts: number): string {
  const d = ageDays(ts)
  if (d < 0) return ''
  if (d === 0) return 'today'
  if (d === 1) return '1 day ago'
  if (d < 30) return `${d} days ago`
  const mo = Math.floor(d / 30)
  if (mo < 12) return `${mo} mo ago`
  return `${Math.floor(d / 365)} yr ago`
}

export function normSlug(raw: string): string {
  let s = (raw || '').trim()
  const m = s.match(/ashbyhq\.com\/([^/?#]+)/i)
  if (m) s = m[1]
  s = s.split(/[/?#]/)[0]
  return s.replace(/\s+/g, '').toLowerCase()
}

function csvCell(v: string): string {
  return /[",\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v
}

export function toCsv(rows: Job[]): string {
  const head = [
    'company', 'publishedAt', 'title', 'team', 'department',
    'location', 'countries', 'workplaceType', 'employmentType', 'applyUrl',
  ]
  const lines = [head.join(',')]
  for (const j of rows) {
    const p = dateParts(j.publishedAt)
    const posted = p.valid
      ? `${p.y}-${String(p.m).padStart(2, '0')}-${String(p.d).padStart(2, '0')}`
      : ''
    const cells = [
      j.company, posted, j.title, j.team, j.department,
      j.location, j.countries.join('; '), j.workplaceType, j.employmentType, j.applyUrl,
    ]
    lines.push(cells.map((x) => csvCell(String(x ?? ''))).join(','))
  }
  return lines.join('\n')
}
