import type { Job } from '../types'
import type { Grouping, SortDir, SortKey } from '../lib/filters'
import { groupValue } from '../lib/filters'
import { MON, ageDays, dateParts, relativeAge } from '../lib/format'

export type TableState = 'loading' | 'empty-nomatch' | 'empty-none' | 'rows'

interface Props {
  rows: Job[]
  grouping: Grouping
  sortKey: SortKey
  sortDir: SortDir
  onSort: (key: SortKey) => void
  state: TableState
  tracking: boolean
  lastSeen: string | null
  apps: Map<string, string>
  onSetStatus: (jobKey: string, status: string) => void
}

const STATUS_OPTIONS = ['applied', 'interviewing', 'rejected', 'offer']

export function jobKey(job: Job): string {
  return job.applyUrl || `${job.company}:${job.title}`
}

function Posted({ job }: { job: Job }) {
  const parts = dateParts(job.publishedAt)
  const label = parts.valid ? `${MON[parts.m - 1]} ${parts.d}, ${parts.y}` : '—'
  const age = parts.valid ? relativeAge(parts.ts) : ''
  const fresh = parts.valid && ageDays(parts.ts) >= 0 && ageDays(parts.ts) <= 7
  return (
    <>
      <span className="posted">{label}</span>
      {age && <span className={`age${fresh ? ' fresh' : ''}`}>{age}</span>}
    </>
  )
}

export function JobTable({
  rows,
  grouping,
  sortKey,
  sortDir,
  onSort,
  state,
  tracking,
  lastSeen,
  apps,
  onSetStatus,
}: Props) {
  const caret = (key: SortKey) => (sortKey === key ? (sortDir === 'asc' ? '↑' : '↓') : '↕')
  const ariaSort = (key: SortKey): 'ascending' | 'descending' | undefined =>
    sortKey === key ? (sortDir === 'asc' ? 'ascending' : 'descending') : undefined

  const seenTs = lastSeen ? new Date(lastSeen).getTime() : null
  const isNew = (job: Job) => {
    if (!seenTs) return false
    const time = new Date(job.publishedAt ?? '').getTime()
    return !isNaN(time) && time > seenTs
  }

  return (
    <div className={`table-card table-state-${state}`}>
      <table>
        <thead>
          <tr>
            <th style={{ width: 128 }} aria-sort={ariaSort('posted')}>
              <button type="button" className="sort-button" onClick={() => onSort('posted')}>
                Posted <span className="caret" aria-hidden="true">{caret('posted')}</span>
              </button>
            </th>
            <th aria-sort={ariaSort('title')}>
              <button type="button" className="sort-button" onClick={() => onSort('title')}>
                Role <span className="caret" aria-hidden="true">{caret('title')}</span>
              </button>
            </th>
            <th aria-sort={ariaSort('company')}>
              <button type="button" className="sort-button" onClick={() => onSort('company')}>
                Company <span className="caret" aria-hidden="true">{caret('company')}</span>
              </button>
            </th>
            <th>Location</th>
            {tracking && <th style={{ width: 154 }}>Status</th>}
            <th style={{ width: 92 }}>Apply</th>
          </tr>
        </thead>
        <tbody>
          {state === 'rows' &&
            rows.map((job, index) => {
              const key = jobKey(job)
              const status = apps.get(key) ?? ''
              return (
                <tr
                  key={`${job.company}-${index}`}
                  style={{ animationDelay: `${Math.min(index, 8) * 24}ms` }}
                >
                  <td className="td-posted" data-label="Posted">
                    <Posted job={job} />
                  </td>
                  <td className="td-role" data-label="Role">
                    <div className="role-line">
                      <a className="role-title" href={job.applyUrl || '#'} target="_blank" rel="noopener noreferrer">
                        {job.title}
                      </a>
                      {isNew(job) && <span className="new-badge">NEW</span>}
                    </div>
                    <span className="dept">{groupValue(job, grouping)}</span>
                  </td>
                  <td className="td-co" data-label="Company">
                    <span className="copill">{job.company}</span>
                  </td>
                  <td className="td-loc loc-cell" data-label="Location">
                    <span>{job.location || '—'}</span>
                    {job.secondaryCount > 0 && <span className="age">+{job.secondaryCount} more</span>}
                    {job.workplaceType && <span className="tag">{job.workplaceType}</span>}
                  </td>
                  {tracking && (
                    <td className="td-status" data-label="Status">
                      <div className="status-pill" data-status={status || 'untracked'}>
                        <span className="status-dot" aria-hidden="true" />
                        <select
                          className="status-select"
                          value={status}
                          aria-label={`Application status for ${job.title}`}
                          onChange={(event) => onSetStatus(key, event.target.value)}
                        >
                          <option value="">+ Track</option>
                          {STATUS_OPTIONS.map((option) => (
                            <option key={option} value={option}>
                              {option[0].toUpperCase() + option.slice(1)}
                            </option>
                          ))}
                        </select>
                      </div>
                    </td>
                  )}
                  <td className="td-apply" data-label="Apply">
                    <a className="apply" href={job.applyUrl || '#'} target="_blank" rel="noopener noreferrer">
                      Apply <span aria-hidden="true">↗</span>
                    </a>
                  </td>
                </tr>
              )
            })}
        </tbody>
      </table>

      {state === 'loading' && (
        <div className="empty" aria-live="polite">
          <span className="empty-loader" aria-hidden="true" />
          <h3>Loading company boards</h3>
          <p>Pulling live roles from Ashby.</p>
        </div>
      )}
      {state === 'empty-none' && (
        <div className="empty">
          <span className="empty-glyph" aria-hidden="true">∅</span>
          <h3>No roles found</h3>
          <p>These boards have no listed openings, or the fetches failed.</p>
        </div>
      )}
      {state === 'empty-nomatch' && (
        <div className="empty">
          <span className="empty-glyph" aria-hidden="true">⌁</span>
          <h3>No roles match</h3>
          <p>Widen the date range, or clear some filters.</p>
        </div>
      )}
    </div>
  )
}
