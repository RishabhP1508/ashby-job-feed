import type { FilterState } from '../lib/filters'
import { MONTHS, prettyEmp } from '../lib/format'

interface Props {
  filters: FilterState
  years: string[]
  etypes: string[]
  onChange: (patch: Partial<FilterState>) => void
  onCsv: () => void
  onCopyLink: () => void
}

const PRESETS: Array<[string, string]> = [
  ['any', 'Any time'],
  ['1', '24 hours'],
  ['7', '7 days'],
  ['30', '30 days'],
  ['90', '90 days'],
]

export function Filters({ filters, years, etypes, onChange, onCsv, onCopyLink }: Props) {
  const presetActive = filters.datePreset !== 'any'
  return (
    <div className="filters">
      <div className="field full">
        <label>Posted within</label>
        <div className="toggle" role="group" aria-label="Posted within">
          {PRESETS.map(([value, label]) => (
            <button
              type="button"
              key={value}
              aria-pressed={filters.datePreset === value}
              onClick={() => onChange({ datePreset: value })}
            >
              {label}
            </button>
          ))}
        </div>
      </div>

      <div className="field compact">
        <label htmlFor="year">Year</label>
        <select
          id="year"
          value={filters.year}
          disabled={presetActive}
          onChange={(event) => onChange({ year: event.target.value })}
        >
          <option value="any">Any year</option>
          {years.map((year) => (
            <option key={year} value={year}>
              {year}
            </option>
          ))}
        </select>
      </div>

      <div className="field compact">
        <label htmlFor="month">Month</label>
        <select
          id="month"
          value={filters.month}
          disabled={presetActive}
          onChange={(event) => onChange({ month: event.target.value })}
        >
          <option value="any">Any month</option>
          {MONTHS.map((month, index) => (
            <option key={month} value={String(index + 1)}>
              {month}
            </option>
          ))}
        </select>
      </div>

      <div className="field compact">
        <label htmlFor="etype">Job type</label>
        <select
          id="etype"
          value={filters.etype}
          onChange={(event) => onChange({ etype: event.target.value })}
        >
          <option value="any">All types</option>
          {etypes.map((type) => (
            <option key={type} value={type}>
              {prettyEmp(type)}
            </option>
          ))}
        </select>
      </div>

      <div className="field search">
        <label htmlFor="search">Search roles</label>
        <div className="input-with-icon">
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path d="m17 17-3.65-3.65m1.65-4.1A5.75 5.75 0 1 1 3.5 9.25a5.75 5.75 0 0 1 11.5 0Z" />
          </svg>
          <input
            id="search"
            type="text"
            placeholder="Engineer, backend"
            value={filters.search}
            onChange={(event) => onChange({ search: event.target.value })}
          />
        </div>
      </div>

      <div className="field search">
        <label htmlFor="exclude">Exclude words</label>
        <div className="input-with-icon">
          <svg viewBox="0 0 20 20" aria-hidden="true">
            <path d="M5 10h10M10 18a8 8 0 1 0 0-16 8 8 0 0 0 0 16Z" />
          </svg>
          <input
            id="exclude"
            type="text"
            placeholder="Senior, manager, staff"
            value={filters.exclude}
            onChange={(event) => onChange({ exclude: event.target.value })}
          />
        </div>
      </div>

      <div className="actions">
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCsv}>
          Download CSV
        </button>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onCopyLink}>
          Copy link
        </button>
      </div>
    </div>
  )
}
