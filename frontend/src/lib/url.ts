import { DEFAULT_FILTERS, type FilterState } from './filters'
import { normSlug } from './format'

function joinSet(a: string[]): string {
  return a.join('\n')
}

function splitSet(v: string | null): string[] {
  return (v ?? '').split('\n').map((s) => s.trim()).filter(Boolean)
}

export function parseUrl(): { companies: string[]; filters: FilterState } {
  let h = window.location.hash || ''
  if (h.startsWith('#')) h = h.slice(1)
  if (h.startsWith('?')) h = h.slice(1)
  const p = new URLSearchParams(h)

  const f: FilterState = { ...DEFAULT_FILTERS, teams: [], locs: [], cos: [] }
  const d = p.get('d'); if (d) f.datePreset = d
  const y = p.get('y'); if (y) f.year = y
  const m = p.get('m'); if (m) f.month = m
  const e = p.get('e'); if (e) f.etype = e
  const q = p.get('q'); if (q) f.search = q
  const x = p.get('x'); if (x) f.exclude = x

  const g = p.get('g')
  if (g === 'team' || g === 'department') f.grouping = g

  const s = p.get('s')
  if (s) {
    const [k, dir] = s.split('.')
    if (k === 'posted' || k === 'title' || k === 'company') f.sortKey = k
    if (dir === 'asc' || dir === 'desc') f.sortDir = dir
  }

  f.teams = splitSet(p.get('t'))
  f.locs = splitSet(p.get('l'))
  f.cos = splitSet(p.get('co'))

  const companies = (p.get('c') ?? '').split(/[\s,]+/).map(normSlug).filter(Boolean)
  return { companies, filters: f }
}

export function writeUrl(companies: string[], f: FilterState): void {
  try {
    const p = new URLSearchParams()
    if (companies.length) p.set('c', companies.join(','))
    if (f.cos.length) p.set('co', joinSet(f.cos))
    if (f.datePreset !== 'any') {
      p.set('d', f.datePreset)
    } else {
      if (f.year !== 'any') p.set('y', f.year)
      if (f.month !== 'any') p.set('m', f.month)
    }
    if (f.etype !== 'any') p.set('e', f.etype)
    if (f.search.trim()) p.set('q', f.search.trim())
    if (f.exclude.trim()) p.set('x', f.exclude.trim())
    if (f.grouping !== 'department') p.set('g', f.grouping)
    if (f.teams.length) p.set('t', joinSet(f.teams))
    if (f.locs.length) p.set('l', joinSet(f.locs))
    if (!(f.sortKey === 'posted' && f.sortDir === 'desc')) p.set('s', `${f.sortKey}.${f.sortDir}`)

    const hash = p.toString()
    const target = hash ? `#${hash}` : window.location.pathname + window.location.search
    window.history.replaceState(null, '', target)
  } catch {
    /* history API may be unavailable in some sandboxes; filtering still works */
  }
}
