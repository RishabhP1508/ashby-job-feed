import { beforeEach, describe, expect, it } from 'vitest'
import { DEFAULT_FILTERS, type FilterState } from './filters'
import { parseUrl, writeUrl } from './url'

beforeEach(() => {
  window.history.replaceState(null, '', '/')
})

describe('parseUrl', () => {
  it('returns the defaults when there is no hash', () => {
    const { companies, filters } = parseUrl()
    expect(companies).toEqual([])
    expect(filters).toEqual(DEFAULT_FILTERS)
  })

  it('normalizes company handles from the hash', () => {
    window.location.hash = '#c=OpenAI, https://jobs.ashbyhq.com/Ramp'
    expect(parseUrl().companies).toEqual(['openai', 'ramp'])
  })

  it('ignores an unknown grouping or sort key', () => {
    window.location.hash = '#g=nonsense&s=bogus.sideways'
    const { filters } = parseUrl()
    expect(filters.grouping).toBe(DEFAULT_FILTERS.grouping)
    expect(filters.sortKey).toBe(DEFAULT_FILTERS.sortKey)
    expect(filters.sortDir).toBe(DEFAULT_FILTERS.sortDir)
  })
})

describe('writeUrl', () => {
  it('writes no hash when nothing differs from the defaults', () => {
    writeUrl([], DEFAULT_FILTERS)
    expect(window.location.hash).toBe('')
  })

  it('round-trips companies and every non-default filter', () => {
    const filters: FilterState = {
      ...DEFAULT_FILTERS,
      datePreset: '7',
      etype: 'FullTime',
      search: 'engineer',
      exclude: 'senior, staff',
      grouping: 'team',
      sortKey: 'title',
      sortDir: 'asc',
      teams: ['Research', 'Applied Eng'],
      locs: ['United States', 'Remote'],
      cos: ['openai'],
    }
    writeUrl(['openai', 'ramp'], filters)

    const back = parseUrl()
    expect(back.companies).toEqual(['openai', 'ramp'])
    expect(back.filters).toEqual(filters)
  })

  it('drops year and month while a posted-within preset is active', () => {
    writeUrl([], { ...DEFAULT_FILTERS, datePreset: '30', year: '2025', month: '3' })
    expect(window.location.hash).not.toContain('y=')
    expect(window.location.hash).not.toContain('m=')

    const { filters } = parseUrl()
    expect(filters.datePreset).toBe('30')
    expect(filters.year).toBe('any')
    expect(filters.month).toBe('any')
  })

  it('keeps year and month when no preset is active', () => {
    writeUrl([], { ...DEFAULT_FILTERS, year: '2025', month: '3' })
    const { filters } = parseUrl()
    expect([filters.year, filters.month]).toEqual(['2025', '3'])
  })
})
