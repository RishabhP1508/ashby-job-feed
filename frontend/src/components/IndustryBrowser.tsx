import { useMemo, useState } from 'react'
import type { DirectoryCompany } from '../types'

interface Props {
  companies: DirectoryCompany[]
  /** Slugs already in the company bar, so their cards read as added. */
  added: string[]
  onAdd: (slug: string) => void
  open: boolean
  onToggle: () => void
}

const PANEL_ID = 'industry-browser'

export function IndustryBrowser({ companies, added, onAdd, open, onToggle }: Props) {
  const [picked, setPicked] = useState<string[]>([])
  const [query, setQuery] = useState('')

  const addedSet = useMemo(() => new Set(added), [added])
  const searching = query.trim().length > 0

  // Industries with live counts, biggest first. Counts come from the data, never
  // from the design preview, whose numbers are illustrative.
  const industries = useMemo(() => {
    const counts = new Map<string, number>()
    for (const c of companies) {
      for (const i of c.industries) counts.set(i, (counts.get(i) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
  }, [companies])

  // Open roles first, then name so the order is stable. jobCount orders the grid
  // and is never rendered: it is a validation-time snapshot that goes stale.
  const ordered = useMemo(
    () => [...companies].sort((a, b) => b.jobCount - a.jobCount || a.name.localeCompare(b.name)),
    [companies],
  )

  // A search reaches every company, so it takes precedence over the chips. The
  // chips render inactive while that is true, so nothing claims to be applied.
  const shown = useMemo(() => {
    if (searching) {
      const q = query.trim().toLowerCase()
      return ordered.filter((c) => c.name.toLowerCase().includes(q))
    }
    if (picked.length === 0) return ordered
    return ordered.filter((c) => c.industries.some((i) => picked.includes(i)))
  }, [ordered, picked, query, searching])

  const toggleIndustry = (name: string) =>
    setPicked((prev) => (prev.includes(name) ? prev.filter((x) => x !== name) : [...prev, name]))

  if (!open) {
    return (
      <button
        type="button"
        className="browse-btn"
        aria-expanded={false}
        aria-controls={PANEL_ID}
        onClick={onToggle}
      >
        Browse by industry
      </button>
    )
  }

  const noun = shown.length === 1 ? 'company' : 'companies'
  const countLabel = searching
    ? `${shown.length} ${noun} matching "${query.trim()}"`
    : picked.length > 0
      ? `${shown.length} ${noun} in ${picked.join(', ')}`
      : `${shown.length} ${noun}`

  return (
    <div className="browser" id={PANEL_ID}>
      <div className="browser-head">
        <span className="browser-title">Browse by industry</span>
        <span className="browser-sub">{companies.length} companies · curated starter list</span>
        <button
          type="button"
          className="collapse"
          aria-expanded={true}
          aria-controls={PANEL_ID}
          onClick={onToggle}
        >
          Hide
        </button>
      </div>

      <div className="bsearch">
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" aria-hidden="true">
          <circle cx="11" cy="11" r="7" />
          <path d="m21 21-4.3-4.3" />
        </svg>
        <label className="sr-only" htmlFor="browser-search">Filter companies by name</label>
        <input
          id="browser-search"
          type="text"
          placeholder="Filter companies by name"
          autoComplete="off"
          spellCheck={false}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>

      <div className="ind-chips" role="group" aria-label="Filter by industry">
        {industries.map(([name, count]) => {
          // While searching, the chips are ignored, so they must not look or
          // report as active. The selection itself survives in state.
          const on = !searching && picked.includes(name)
          return (
            <button
              type="button"
              key={name}
              className={`ind${searching ? ' dimmed' : ''}`}
              aria-pressed={on}
              onClick={() => toggleIndustry(name)}
            >
              {name}
              <span className="n">{count}</span>
            </button>
          )
        })}
      </div>

      <div className="bmeta">
        <span>{countLabel}</span>
        {(picked.length > 0 || searching) && (
          <button
            type="button"
            className="clear"
            onClick={() => {
              setPicked([])
              setQuery('')
            }}
          >
            Clear filters
          </button>
        )}
      </div>

      {shown.length === 0 ? (
        <p className="bempty">No companies match. Try a different name, or clear the filters.</p>
      ) : (
        <div className="cgrid">
          {shown.map((c) => {
            const isAdded = addedSet.has(c.slug)
            return (
              <button
                type="button"
                key={c.slug}
                className={`ccard${isAdded ? ' is-added' : ''}`}
                aria-label={isAdded ? `${c.name}, already added` : `Add ${c.name}`}
                aria-disabled={isAdded}
                onClick={isAdded ? undefined : () => onAdd(c.slug)}
              >
                <span className="cn">
                  <span className="nm">{c.name}</span>
                  <span className="plus" aria-hidden="true">{isAdded ? '✓' : '+'}</span>
                </span>
                <span className="tags">
                  {c.industries.map((i) => (
                    <span className="tag2" key={i}>{i}</span>
                  ))}
                </span>
              </button>
            )
          })}
        </div>
      )}

      <p className="bfoot">
        Companies with open roles appear first. A curated starter list, not every Ashby company.
      </p>
    </div>
  )
}
