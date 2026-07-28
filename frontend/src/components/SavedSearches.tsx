import type { SavedSearch } from '../types'

interface Props {
  searches: SavedSearch[]
  sort: 'recent' | 'popular'
  onSort: (sort: 'recent' | 'popular') => void
  onApply: (search: SavedSearch) => void
  onDelete: (id: number) => void
}

export function SavedSearches({ searches, sort, onSort, onApply, onDelete }: Props) {
  return (
    <div className="saved">
      <div className="saved-head">
        <span className="group-label">Saved searches</span>
        <div className="toggle" role="group" aria-label="Saved search order">
          <button type="button" aria-pressed={sort === 'recent'} onClick={() => onSort('recent')}>
            Recent
          </button>
          <button type="button" aria-pressed={sort === 'popular'} onClick={() => onSort('popular')}>
            Popular
          </button>
        </div>
      </div>
      {searches.length === 0 ? (
        <div className="saved-empty">
          No saved searches yet. Add companies, set your filters, then choose Save search.
        </div>
      ) : (
        <div className="chips">
          {searches.map((search) => {
            const countLabel = `reopened ${search.useCount} ${search.useCount === 1 ? 'time' : 'times'}`
            return (
              <span key={search.id} className="schip">
                <button
                  type="button"
                  className="schip-main"
                  title={`${search.companies.join(', ')}. Reopened ${search.useCount} ${search.useCount === 1 ? 'time' : 'times'}.`}
                  onClick={() => onApply(search)}
                >
                  <span>{search.name}</span>
                  <span className="n">{countLabel}</span>
                </button>
                <button
                  type="button"
                  className="cx"
                  aria-label={`Delete ${search.name}`}
                  onClick={() => onDelete(search.id)}
                >
                  ×
                </button>
              </span>
            )
          })}
        </div>
      )}
    </div>
  )
}
