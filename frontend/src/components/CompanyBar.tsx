import type { CompanyState } from '../types'

interface Props {
  companies: CompanyState[]
  counts: Map<string, number>
  selected: string[]
  onToggle: (slug: string) => void
  onRemove: (slug: string) => void
  onRetry: (slug: string) => void
}

export function CompanyBar({ companies, counts, selected, onToggle, onRemove, onRetry }: Props) {
  if (companies.length === 0) return null
  return (
    <div className="cbar" aria-label="Tracked companies">
      {companies.map((company) => {
        const selectedCompany = selected.includes(company.slug)
        const clickable = company.status === 'ok'
        const className = `cchip${selectedCompany ? ' on' : ''}${company.status !== 'ok' ? ' pending' : ''}`
        return (
          <div
            key={company.slug}
            className={className}
            title={company.status === 'error' ? company.error : undefined}
          >
            <button
              type="button"
              className="cchip-main"
              disabled={!clickable}
              aria-pressed={clickable ? selectedCompany : undefined}
              onClick={clickable ? () => onToggle(company.slug) : undefined}
            >
              {company.status === 'loading' && <span className="cspin" aria-hidden="true" />}
              {company.status === 'ok' && <span className="cdot ok" aria-hidden="true" />}
              {company.status === 'error' && <span className="cdot err" aria-hidden="true" />}
              <span className="cname">{company.slug}</span>
              {company.status === 'ok' && <span className="n">{counts.get(company.slug) ?? 0}</span>}
              {company.status === 'loading' && <span className="n">loading</span>}
              {company.status === 'error' && <span className="n">failed</span>}
            </button>
            {company.status === 'error' && (
              <button
                type="button"
                className="cx retry"
                aria-label={`Retry ${company.slug}`}
                onClick={() => onRetry(company.slug)}
              >
                ↻
              </button>
            )}
            <button
              type="button"
              className="cx"
              aria-label={`Remove ${company.slug}`}
              onClick={() => onRemove(company.slug)}
            >
              ×
            </button>
          </div>
        )
      })}
    </div>
  )
}
