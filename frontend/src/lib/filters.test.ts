import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Job } from '../types'
import {
  DEFAULT_FILTERS,
  type FilterState,
  companyChipCounts,
  filterJobs,
  groupValue,
  locChipCounts,
  locTokens,
  sortJobs,
  teamChipCounts,
} from './filters'

const NOW = Date.UTC(2026, 6, 28, 12, 0, 0) // 2026-07-28T12:00:00Z
const DAY = 86400000
const iso = (daysAgo: number) => new Date(NOW - daysAgo * DAY).toISOString()

const job = (over: Partial<Job> = {}): Job => ({
  company: 'openai',
  title: 'Engineer',
  team: 'Infra',
  department: 'Engineering',
  location: 'San Francisco, CA',
  secondaryCount: 0,
  workplaceType: 'Onsite',
  employmentType: 'FullTime',
  isRemote: false,
  countries: ['United States'],
  applyUrl: 'https://x/1',
  publishedAt: iso(3),
  ...over,
})

const f = (over: Partial<FilterState> = {}): FilterState => ({ ...DEFAULT_FILTERS, ...over })
const titles = (rows: Job[]) => rows.map((r) => r.title)

beforeEach(() => {
  vi.useFakeTimers()
  vi.setSystemTime(NOW)
})
afterEach(() => vi.useRealTimers())

describe('locTokens', () => {
  it('lists countries and adds Remote when the job is remote', () => {
    expect(locTokens(job({ countries: ['United States'], isRemote: true }))).toEqual([
      'United States',
      'Remote',
    ])
  })

  it('falls back to Unspecified when there is nothing to show', () => {
    expect(locTokens(job({ countries: [], isRemote: false }))).toEqual(['Unspecified'])
  })
})

describe('groupValue', () => {
  it('reads the chosen field and falls back when it is empty', () => {
    const j = job({ team: 'Inference', department: 'Applied' })
    expect(groupValue(j, 'team')).toBe('Inference')
    expect(groupValue(j, 'department')).toBe('Applied')
    expect(groupValue(job({ team: '' }), 'team')).toBe('—')
  })
})

describe('filterJobs', () => {
  it('keeps only jobs inside the posted-within window', () => {
    const rows = filterJobs(
      [job({ title: 'fresh', publishedAt: iso(3) }), job({ title: 'stale', publishedAt: iso(10) })],
      f({ datePreset: '7' }),
    )
    expect(titles(rows)).toEqual(['fresh'])
  })

  it('drops undated jobs when a window is set', () => {
    expect(filterJobs([job({ publishedAt: null })], f({ datePreset: '7' }))).toEqual([])
  })

  it('matches an exact year and month when no preset is active', () => {
    const jobs = [
      job({ title: 'march', publishedAt: '2026-03-15T00:00:00Z' }),
      job({ title: 'april', publishedAt: '2026-04-15T00:00:00Z' }),
    ]
    expect(titles(filterJobs(jobs, f({ year: '2026', month: '3' })))).toEqual(['march'])
  })

  it('searches the title, the department, and country names', () => {
    const jobs = [
      job({ title: 'Engineer', department: 'Engineering' }),
      job({ title: 'Designer', department: 'Design' }),
    ]
    expect(titles(filterJobs(jobs, f({ search: 'designer' })))).toEqual(['Designer'])
    // the department is searched too, not just the title
    expect(titles(filterJobs(jobs, f({ search: 'engineering' })))).toEqual(['Engineer'])
    // so are country names, which both jobs share
    expect(filterJobs(jobs, f({ search: 'united' })).length).toBe(2)
  })

  it('excludes on a comma-separated list and ignores the location', () => {
    const jobs = [job({ title: 'Senior Engineer' }), job({ title: 'Engineer' })]
    expect(titles(filterJobs(jobs, f({ exclude: 'senior, staff' })))).toEqual(['Engineer'])
    // "francisco" appears only in location, which exclude does not read
    expect(filterJobs(jobs, f({ exclude: 'francisco' })).length).toBe(2)
  })

  it('filters by employment type, team, location token, and company', () => {
    const jobs = [
      job({ title: 'a', employmentType: 'FullTime', department: 'Eng', company: 'openai' }),
      job({ title: 'b', employmentType: 'Intern', department: 'Ops', company: 'ramp' }),
    ]
    expect(titles(filterJobs(jobs, f({ etype: 'Intern' })))).toEqual(['b'])
    expect(titles(filterJobs(jobs, f({ teams: ['Eng'] })))).toEqual(['a'])
    expect(titles(filterJobs(jobs, f({ cos: ['ramp'] })))).toEqual(['b'])
    expect(titles(filterJobs([job({ isRemote: true })], f({ locs: ['Remote'] })))).toEqual([
      'Engineer',
    ])
  })

  it('skips the named facet so that facet can count its own options', () => {
    const jobs = [job({ department: 'Eng' })]
    const state = f({ teams: ['Ops'] }) // would normally exclude the job
    expect(filterJobs(jobs, state)).toEqual([])
    expect(filterJobs(jobs, state, 'team').length).toBe(1)
  })
})

describe('sortJobs', () => {
  it('puts the newest first by default and undated jobs last', () => {
    const jobs = [
      job({ title: 'old', publishedAt: iso(10) }),
      job({ title: 'none', publishedAt: null }),
      job({ title: 'new', publishedAt: iso(1) }),
    ]
    expect(titles(sortJobs(jobs, f()))).toEqual(['new', 'old', 'none'])
  })

  it('sorts by title in the requested direction', () => {
    const jobs = [job({ title: 'B' }), job({ title: 'A' })]
    expect(titles(sortJobs(jobs, f({ sortKey: 'title', sortDir: 'asc' })))).toEqual(['A', 'B'])
    expect(titles(sortJobs(jobs, f({ sortKey: 'title', sortDir: 'desc' })))).toEqual(['B', 'A'])
  })

  it('breaks a company tie with the newer role first', () => {
    const jobs = [
      job({ title: 'older', company: 'openai', publishedAt: iso(9) }),
      job({ title: 'newer', company: 'openai', publishedAt: iso(2) }),
    ]
    expect(titles(sortJobs(jobs, f({ sortKey: 'company', sortDir: 'asc' })))).toEqual([
      'newer',
      'older',
    ])
  })
})

describe('chip counts', () => {
  it('keeps every option visible at zero when another facet filters it out', () => {
    const jobs = [
      job({ department: 'Eng', company: 'openai' }),
      job({ department: 'Ops', company: 'ramp' }),
    ]
    const counts = new Map(teamChipCounts(jobs, f({ cos: ['openai'] })))
    expect(counts.get('Eng')).toBe(1)
    expect(counts.get('Ops')).toBe(0)
  })

  it('orders team chips by count then name', () => {
    const jobs = [job({ department: 'B' }), job({ department: 'B' }), job({ department: 'A' })]
    expect(teamChipCounts(jobs, f()).map(([name]) => name)).toEqual(['B', 'A'])
  })

  it('seeds every tracked company, even one with no matching roles', () => {
    const counts = new Map(companyChipCounts([job({ company: 'openai' })], f(), ['openai', 'ramp']))
    expect(counts.get('openai')).toBe(1)
    expect(counts.get('ramp')).toBe(0)
  })

  it('puts Remote first and Unspecified last', () => {
    const jobs = [
      job({ countries: ['United States'] }),
      job({ countries: [], isRemote: false }),
      job({ countries: [], isRemote: true }),
    ]
    expect(locChipCounts(jobs, f()).map(([name]) => name)).toEqual([
      'Remote',
      'United States',
      'Unspecified',
    ])
  })
})
