import type { Job } from '../types'
import { dateParts } from './format'

export type Grouping = 'department' | 'team'
export type SortKey = 'posted' | 'title' | 'company'
export type SortDir = 'asc' | 'desc'

export interface FilterState {
  datePreset: string
  year: string
  month: string
  etype: string
  search: string
  exclude: string
  grouping: Grouping
  sortKey: SortKey
  sortDir: SortDir
  teams: string[]
  locs: string[]
  cos: string[]
}

export const DEFAULT_FILTERS: FilterState = {
  datePreset: 'any',
  year: 'any',
  month: 'any',
  etype: 'any',
  search: '',
  exclude: '',
  grouping: 'department',
  sortKey: 'posted',
  sortDir: 'desc',
  teams: [],
  locs: [],
  cos: [],
}

export function locTokens(j: Job): string[] {
  const tokens = [...j.countries]
  if (j.isRemote) tokens.push('Remote')
  if (tokens.length === 0) tokens.push('Unspecified')
  return tokens
}

export function groupValue(j: Job, grouping: Grouping): string {
  return (grouping === 'team' ? j.team : j.department) || '—'
}

function passDate(j: Job, f: FilterState): boolean {
  const p = dateParts(j.publishedAt)
  if (f.datePreset !== 'any') {
    if (!p.valid) return false
    const age = (Date.now() - p.ts) / 86400000
    return age >= 0 && age <= Number(f.datePreset)
  }
  if (f.year !== 'any' && (!p.valid || p.y !== Number(f.year))) return false
  if (f.month !== 'any' && (!p.valid || p.m !== Number(f.month))) return false
  return true
}

function passSearch(j: Job, f: FilterState): boolean {
  const q = f.search.trim().toLowerCase()
  if (!q) return true
  const hay = `${j.title} ${j.team} ${j.department} ${j.location} ${j.company} ${j.countries.join(' ')}`.toLowerCase()
  return hay.includes(q)
}

function passExclude(j: Job, f: FilterState): boolean {
  const raw = f.exclude.trim().toLowerCase()
  if (!raw) return true
  const terms = raw.split(',').map((s) => s.trim()).filter(Boolean)
  if (terms.length === 0) return true
  const hay = `${j.title} ${j.team} ${j.department}`.toLowerCase()
  return !terms.some((t) => hay.includes(t))
}

function passEmp(j: Job, f: FilterState): boolean {
  return f.etype === 'any' || j.employmentType === f.etype
}

function passTeam(j: Job, f: FilterState): boolean {
  return f.teams.length === 0 || f.teams.includes(groupValue(j, f.grouping))
}

function passLoc(j: Job, f: FilterState): boolean {
  if (f.locs.length === 0) return true
  return locTokens(j).some((t) => f.locs.includes(t))
}

function passCompany(j: Job, f: FilterState): boolean {
  return f.cos.length === 0 || f.cos.includes(j.company)
}

export type FacetKey = 'team' | 'loc' | 'company' | null

export function filterJobs(jobs: Job[], f: FilterState, exclude: FacetKey = null): Job[] {
  return jobs.filter((j) => {
    if (!passDate(j, f)) return false
    if (!passSearch(j, f)) return false
    if (!passExclude(j, f)) return false
    if (!passEmp(j, f)) return false
    if (exclude !== 'team' && !passTeam(j, f)) return false
    if (exclude !== 'loc' && !passLoc(j, f)) return false
    if (exclude !== 'company' && !passCompany(j, f)) return false
    return true
  })
}

export function sortJobs(rows: Job[], f: FilterState): Job[] {
  const dir = f.sortDir === 'asc' ? 1 : -1
  const copy = [...rows]
  copy.sort((a, b) => {
    if (f.sortKey === 'title') return a.title.localeCompare(b.title) * dir
    if (f.sortKey === 'company') {
      const c = a.company.localeCompare(b.company)
      return c !== 0 ? c * dir : dateParts(b.publishedAt).ts - dateParts(a.publishedAt).ts
    }
    const ta = dateParts(a.publishedAt)
    const tb = dateParts(b.publishedAt)
    if (!ta.valid && !tb.valid) return 0
    if (!ta.valid) return 1
    if (!tb.valid) return -1
    return (ta.ts - tb.ts) * dir
  })
  return copy
}

export type ChipEntry = [string, number]

function byCountThenName(a: ChipEntry, b: ChipEntry): number {
  return b[1] - a[1] || a[0].localeCompare(b[0])
}

export function teamChipCounts(jobs: Job[], f: FilterState): ChipEntry[] {
  const base = filterJobs(jobs, f, 'team')
  const counts = new Map<string, number>()
  for (const j of jobs) {
    const v = groupValue(j, f.grouping)
    if (!counts.has(v)) counts.set(v, 0)
  }
  for (const j of base) {
    const v = groupValue(j, f.grouping)
    counts.set(v, (counts.get(v) ?? 0) + 1)
  }
  return [...counts.entries()].sort(byCountThenName)
}

export function companyChipCounts(jobs: Job[], f: FilterState, allSlugs: string[]): ChipEntry[] {
  const base = filterJobs(jobs, f, 'company')
  const counts = new Map<string, number>()
  for (const s of allSlugs) counts.set(s, 0)
  for (const j of base) counts.set(j.company, (counts.get(j.company) ?? 0) + 1)
  return [...counts.entries()]
}

export function locChipCounts(jobs: Job[], f: FilterState): ChipEntry[] {
  const base = filterJobs(jobs, f, 'loc')
  const counts = new Map<string, number>()
  for (const j of jobs) for (const t of locTokens(j)) if (!counts.has(t)) counts.set(t, 0)
  for (const j of base) for (const t of locTokens(j)) counts.set(t, (counts.get(t) ?? 0) + 1)
  const rank = (t: string) => (t === 'Remote' ? 0 : t === 'Unspecified' ? 2 : 1)
  return [...counts.entries()].sort((a, b) => rank(a[0]) - rank(b[0]) || a[0].localeCompare(b[0]))
}
