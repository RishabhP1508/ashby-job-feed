import type { ReactNode } from 'react'
import type { ChipEntry } from '../lib/filters'

interface Props {
  label: string
  entries: ChipEntry[]
  selected: string[]
  onToggle: (val: string) => void
  onSelectAll: () => void
  onClear: () => void
  extra?: ReactNode
}

export function Facet({ label, entries, selected, onToggle, onSelectAll, onClear, extra }: Props) {
  if (entries.length === 0) return null
  return (
    <div className="facet">
      <div className="facet-head">
        <span className="group-label">{label}</span>
        {extra}
        <div className="mini-actions">
          <button type="button" className="link-btn" onClick={onSelectAll}>
            Select all
          </button>
          <button type="button" className="link-btn" onClick={onClear}>
            Clear
          </button>
        </div>
      </div>
      <div className="chips">
        {entries.map(([val, n]) => {
          const on = selected.includes(val)
          return (
            <button
              type="button"
              key={val}
              className="chip"
              aria-pressed={on}
              disabled={n === 0 && !on}
              onClick={() => onToggle(val)}
            >
              {val} <span className="n">{n}</span>
            </button>
          )
        })}
      </div>
    </div>
  )
}
