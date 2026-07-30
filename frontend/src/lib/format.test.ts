import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { Job } from '../types'
import { ageDays, dateParts, normSlug, prettyEmp, relativeAge, toCsv } from './format'

const NOW = Date.UTC(2026, 6, 28, 12, 0, 0) // 2026-07-28T12:00:00Z
const DAY = 86400000

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
  applyUrl: 'https://jobs.ashbyhq.com/openai/1',
  publishedAt: '2026-07-20T00:00:00Z',
  ...over,
})

describe('dateParts', () => {
  it('reports invalid for null and unparseable input', () => {
    expect(dateParts(null).valid).toBe(false)
    expect(dateParts('not a date').valid).toBe(false)
    expect(dateParts(null).ts).toBe(0)
  })

  it('splits the date in UTC, not local time', () => {
    // 00:30Z lands on the previous day in any western timezone.
    const p = dateParts('2026-01-01T00:30:00Z')
    expect([p.valid, p.y, p.m, p.d]).toEqual([true, 2026, 1, 1])
  })
})

describe('age helpers', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.setSystemTime(NOW)
  })
  afterEach(() => vi.useRealTimers())

  it('counts whole days elapsed', () => {
    expect(ageDays(NOW)).toBe(0)
    expect(ageDays(NOW - 7 * DAY)).toBe(7)
  })

  it('describes each age band', () => {
    expect(relativeAge(NOW)).toBe('today')
    expect(relativeAge(NOW - DAY)).toBe('1 day ago')
    expect(relativeAge(NOW - 29 * DAY)).toBe('29 days ago')
    expect(relativeAge(NOW - 30 * DAY)).toBe('1 mo ago')
    expect(relativeAge(NOW - 400 * DAY)).toBe('1 yr ago')
  })

  it('returns nothing for a future date', () => {
    expect(relativeAge(NOW + 5 * DAY)).toBe('')
  })
})

describe('normSlug', () => {
  it('pulls the handle out of a full board URL', () => {
    expect(normSlug('https://jobs.ashbyhq.com/OpenAI')).toBe('openai')
    expect(normSlug('https://jobs.ashbyhq.com/Notion/jobs?x=1')).toBe('notion')
  })

  it('trims, lowercases, and drops trailing path or spaces', () => {
    expect(normSlug('  Ramp  ')).toBe('ramp')
    expect(normSlug('openai/jobs')).toBe('openai')
    expect(normSlug('my company')).toBe('mycompany')
    expect(normSlug('')).toBe('')
  })
})

describe('toCsv', () => {
  it('writes the header and formats the posted date as YYYY-MM-DD', () => {
    const [head, row] = toCsv([job()]).split('\n')
    expect(head).toBe(
      'company,publishedAt,title,team,department,location,countries,workplaceType,employmentType,applyUrl',
    )
    expect(row.startsWith('openai,2026-07-20,')).toBe(true)
  })

  it('quotes cells containing a comma, a quote, or a newline', () => {
    const csv = toCsv([job({ title: 'Engineer, Senior', team: 'A"B', location: 'X\nY' })])
    expect(csv).toContain('"Engineer, Senior"')
    expect(csv).toContain('"A""B"')
    expect(csv).toContain('"X\nY"')
  })

  it('joins countries with a semicolon so the cell needs no quoting', () => {
    expect(toCsv([job({ countries: ['US', 'CA'] })])).toContain('US; CA')
  })

  it('leaves the date empty when the job has none', () => {
    const row = toCsv([job({ publishedAt: null })]).split('\n')[1]
    expect(row.startsWith('openai,,')).toBe(true)
  })
})

describe('prettyEmp', () => {
  it('uses the label map, splits camelCase, and names the empty case', () => {
    expect(prettyEmp('FullTime')).toBe('Full-time')
    expect(prettyEmp('ContractToHire')).toBe('Contract To Hire')
    expect(prettyEmp('')).toBe('Other')
  })
})
