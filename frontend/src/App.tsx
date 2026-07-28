import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { CompanyState, Job, SavedSearch, User } from './types'
import {
  deleteSearch,
  fetchBoard,
  getSeen,
  listApplications,
  listSearches,
  logout,
  markSeen,
  me,
  saveSearch,
  setApplication,
  useSearch,
} from './api'
import { normSlug, toCsv } from './lib/format'
import {
  DEFAULT_FILTERS,
  type FilterState,
  type SortKey,
  companyChipCounts,
  filterJobs,
  groupValue,
  locChipCounts,
  locTokens,
  sortJobs,
  teamChipCounts,
} from './lib/filters'
import { parseUrl, writeUrl } from './lib/url'
import { CompanyBar } from './components/CompanyBar'
import { SavedSearches } from './components/SavedSearches'
import { AuthPopover } from './components/AuthPopover'
import { Filters } from './components/Filters'
import { Facet } from './components/Facet'
import { JobTable, type TableState } from './components/JobTable'

export default function App() {
  const [companies, setCompanies] = useState<CompanyState[]>([])
  const [filters, setFilters] = useState<FilterState>(() => parseUrl().filters)
  const [handle, setHandle] = useState('')
  const [status, setStatus] = useState('')
  const [copied, setCopied] = useState(false)
  const [notice, setNotice] = useState<{ id: number; message: string } | null>(null)

  const [user, setUser] = useState<User | null>(null)
  const [authChecked, setAuthChecked] = useState(false)

  const [saved, setSaved] = useState<SavedSearch[]>([])
  const [savedSort, setSavedSort] = useState<'recent' | 'popular'>('recent')
  const [saveName, setSaveName] = useState('')
  const [savedBusy, setSavedBusy] = useState(false)

  const [lastSeen, setLastSeen] = useState<string | null>(null)
  const [apps, setApps] = useState<Map<string, string>>(new Map())

  const started = useRef<Set<string>>(new Set())
  const groupingTouched = useRef(false)
  const firstWrite = useRef(true)
  const handleInputRef = useRef<HTMLInputElement>(null)
  const noticeId = useRef(0)

  const patch = useCallback((p: Partial<FilterState>) => setFilters((f) => ({ ...f, ...p })), [])
  const showFailure = useCallback((message: string) => {
    noticeId.current += 1
    setNotice({ id: noticeId.current, message })
  }, [])

  useEffect(() => {
    if (!notice) return
    const timer = window.setTimeout(() => setNotice(null), 5000)
    return () => window.clearTimeout(timer)
  }, [notice])

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        handleInputRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [])

  const addCompany = useCallback((raw: string) => {
    const slug = normSlug(raw)
    if (!slug) return
    setCompanies((prev) =>
      prev.some((c) => c.slug === slug) ? prev : [...prev, { slug, status: 'loading', jobs: [] }],
    )
  }, [])

  const removeCompany = useCallback((slug: string) => {
    started.current.delete(slug)
    setCompanies((prev) => prev.filter((c) => c.slug !== slug))
    setFilters((f) => (f.cos.includes(slug) ? { ...f, cos: f.cos.filter((s) => s !== slug) } : f))
  }, [])

  const retryCompany = useCallback((slug: string) => {
    started.current.delete(slug)
    setCompanies((prev) => prev.map((c) => (c.slug === slug ? { slug, status: 'loading', jobs: [] } : c)))
  }, [])

  // Fetch every company that is 'loading' and not yet started.
  useEffect(() => {
    companies.forEach((c) => {
      if (c.status !== 'loading' || started.current.has(c.slug)) return
      started.current.add(c.slug)
      fetchBoard(c.slug)
        .then((res) =>
          setCompanies((prev) =>
            prev.map((x) => (x.slug === c.slug ? { slug: c.slug, status: 'ok' as const, jobs: res.jobs } : x)),
          ),
        )
        .catch((err) =>
          setCompanies((prev) =>
            prev.map((x) =>
              x.slug === c.slug
                ? { slug: c.slug, status: 'error' as const, jobs: [], error: String(err?.message ?? err) }
                : x,
            ),
          ),
        )
    })
  }, [companies])

  // Seed companies from the URL once on mount (filters are seeded lazily above).
  useEffect(() => {
    const p = new URLSearchParams((window.location.hash || '').replace(/^#\??/, ''))
    if (p.has('g')) groupingTouched.current = true
    parseUrl().companies.forEach(addCompany)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Check for an existing session once on mount.
  useEffect(() => {
    me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setAuthChecked(true))
  }, [])

  // Load saved searches when logged in; clear them when logged out.
  useEffect(() => {
    if (!user) {
      setSaved([])
      return
    }
    let alive = true
    listSearches(savedSort)
      .then((s) => {
        if (alive) setSaved(s)
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [user, savedSort])

  const reloadSaved = useCallback(() => {
    listSearches(savedSort).then(setSaved).catch(() => {})
  }, [savedSort])

  // Load the last-seen time and tracked applications when logged in.
  useEffect(() => {
    if (!user) {
      setLastSeen(null)
      setApps(new Map())
      return
    }
    let alive = true
    getSeen()
      .then((v) => {
        if (alive) setLastSeen(v)
      })
      .catch(() => {})
    listApplications()
      .then((list) => {
        if (alive) setApps(new Map(list.map((a) => [a.jobKey, a.status])))
      })
      .catch(() => {})
    return () => {
      alive = false
    }
  }, [user])

  const allJobs = useMemo<Job[]>(
    () => companies.filter((c) => c.status === 'ok').flatMap((c) => c.jobs),
    [companies],
  )

  // Pick the more informative grouping by default, until the user overrides it.
  useEffect(() => {
    if (groupingTouched.current || allJobs.length === 0) return
    const deps = new Set(allJobs.map((j) => j.department).filter(Boolean)).size
    const teams = new Set(allJobs.map((j) => j.team).filter(Boolean)).size
    const g: FilterState['grouping'] = teams > deps ? 'team' : 'department'
    setFilters((f) => (f.grouping === g ? f : { ...f, grouping: g }))
  }, [allJobs])

  const slugOrder = useMemo(() => companies.map((c) => c.slug), [companies])

  // Reflect state into the URL (skip the first run so an incoming URL isn't clobbered).
  useEffect(() => {
    if (firstWrite.current) {
      firstWrite.current = false
      return
    }
    writeUrl(slugOrder, filters)
  }, [slugOrder, filters])

  const years = useMemo(() => {
    const set = new Set<number>()
    for (const j of allJobs) {
      const d = new Date(j.publishedAt ?? '')
      if (!isNaN(d.getTime())) set.add(d.getUTCFullYear())
    }
    return [...set].sort((a, b) => b - a).map(String)
  }, [allJobs])

  const etypes = useMemo(
    () => [...new Set(allJobs.map((j) => j.employmentType).filter(Boolean))].sort(),
    [allJobs],
  )

  const rows = useMemo(() => sortJobs(filterJobs(allJobs, filters, null), filters), [allJobs, filters])

  const seenTs = lastSeen ? new Date(lastSeen).getTime() : null
  const newCount = useMemo(() => {
    if (!seenTs) return 0
    return rows.reduce((n, j) => {
      const t = new Date(j.publishedAt ?? '').getTime()
      return n + (!isNaN(t) && t > seenTs ? 1 : 0)
    }, 0)
  }, [rows, seenTs])
  const teamEntries = useMemo(() => teamChipCounts(allJobs, filters), [allJobs, filters])
  const locEntries = useMemo(() => locChipCounts(allJobs, filters), [allJobs, filters])
  const companyCountsArr = useMemo(
    () => companyChipCounts(allJobs, filters, slugOrder),
    [allJobs, filters, slugOrder],
  )
  const companyCounts = useMemo(() => new Map(companyCountsArr), [companyCountsArr])

  const toggle = (key: 'teams' | 'locs' | 'cos', val: string) =>
    setFilters((f) => ({
      ...f,
      [key]: f[key].includes(val) ? f[key].filter((x) => x !== val) : [...f[key], val],
    }))

  const onAdd = () => {
    const slugs = handle.split(/[\s,]+/).map(normSlug).filter(Boolean)
    if (slugs.length === 0) {
      setStatus('Type at least one Ashby handle.')
      return
    }
    setStatus('')
    setHandle('')
    slugs.forEach(addCompany)
  }

  const onSort = (key: SortKey) =>
    setFilters((f) =>
      f.sortKey === key
        ? { ...f, sortDir: f.sortDir === 'asc' ? 'desc' : 'asc' }
        : { ...f, sortKey: key, sortDir: key === 'posted' ? 'desc' : 'asc' },
    )

  const onCsv = () => {
    const blob = new Blob([toCsv(rows)], { type: 'text/csv;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = (companies.length === 1 ? companies[0].slug : 'ashby_jobs') + '.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  const onCopyLink = async () => {
    writeUrl(slugOrder, filters)
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    } catch {
      setStatus('Copy this link to save your search: ' + window.location.href)
    }
  }

  const setGrouping = (g: FilterState['grouping']) => {
    groupingTouched.current = true
    setFilters((f) => ({ ...f, grouping: g, teams: [] }))
  }

  const selectAllTeams = () => {
    const vals = new Set<string>()
    for (const j of allJobs) vals.add(groupValue(j, filters.grouping))
    setFilters((f) => ({ ...f, teams: [...vals] }))
  }

  const selectAllLocs = () => {
    const vals = new Set<string>()
    for (const j of allJobs) for (const t of locTokens(j)) vals.add(t)
    setFilters((f) => ({ ...f, locs: [...vals] }))
  }

  // ---- auth ----
  const onAuth = (u: User) => setUser(u)
  const onLogout = () => {
    logout().finally(() => {
      setUser(null)
      setSaved([])
    })
  }

  // ---- saved searches ----
  const onSaveSearch = async () => {
    const list = companies.map((c) => c.slug)
    if (list.length === 0) {
      setStatus('Add at least one company before saving a search.')
      return
    }
    setSavedBusy(true)
    try {
      await saveSearch({ name: saveName.trim() || list.join(', '), companies: list, filters })
      setSaveName('')
      reloadSaved()
    } catch (e) {
      showFailure('Search was not saved. ' + String((e as Error).message))
    } finally {
      setSavedBusy(false)
    }
  }

  const applySearch = (s: SavedSearch) => {
    started.current = new Set()
    groupingTouched.current = true
    setCompanies(s.companies.map((slug) => ({ slug, status: 'loading' as const, jobs: [] })))
    setFilters({ ...DEFAULT_FILTERS, ...s.filters })
    useSearch(s.id).then(reloadSaved).catch(() => {})
  }

  const onDeleteSaved = (id: number) => {
    deleteSearch(id).then(reloadSaved).catch(() => {})
  }

  // ---- watermark and application tracking ----
  const markAllSeen = () => {
    markSeen()
      .then((v) => setLastSeen(v))
      .catch((error) => {
        showFailure('Seen state was not updated. ' + String((error as Error).message))
      })
  }

  const onSetStatus = (key: string, status: string) => {
    setApps((prev) => {
      const next = new Map(prev)
      if (status) next.set(key, status)
      else next.delete(key)
      return next
    })
    setApplication(key, status).catch((error) => {
      showFailure('Application status was not saved. ' + String((error as Error).message))
      // On failure, resync from the server.
      listApplications()
        .then((list) => setApps(new Map(list.map((a) => [a.jobKey, a.status]))))
        .catch(() => {})
    })
  }

  const okCount = companies.filter((c) => c.status === 'ok').length
  const loadingCount = companies.filter((c) => c.status === 'loading').length

  const tableState: TableState =
    rows.length > 0
      ? 'rows'
      : loadingCount > 0 && okCount === 0
        ? 'loading'
        : allJobs.length === 0 && companies.length > 0
          ? 'empty-none'
          : 'empty-nomatch'

  const now = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })

  const metaBits: string[] = []
  if (filters.cos.length) metaBits.push(`${filters.cos.length} ${filters.cos.length > 1 ? 'companies' : 'company'}`)
  if (filters.locs.length) metaBits.push(`${filters.locs.length} ${filters.locs.length > 1 ? 'locations' : 'location'}`)
  if (filters.teams.length) metaBits.push(`${filters.teams.length} ${filters.grouping}${filters.teams.length > 1 ? 's' : ''}`)

  return (
    <div className="wrap">
      <header className="page-header">
        <div className="authbar">
          {user ? (
            <>
              <span className="who">{user.email}</span>
              <button type="button" className="btn btn-quiet" onClick={onLogout}>
                Log out
              </button>
            </>
          ) : authChecked ? (
            <AuthPopover onAuth={onAuth} />
          ) : null}
        </div>
        <div className="hero-copy">
          <p className="eyebrow"><span className="eyebrow-dot" aria-hidden="true" />Live roles from Ashby</p>
          <h1>One focused feed for every company you track.</h1>
          <p className="lede">
            Add company boards, narrow the signal, and move from discovery to application without tab sprawl.
            Feeds stay live, shareable, and cached for speed.
          </p>
        </div>
      </header>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <span className="group-label">Company boards</span>
            <h2>Build your feed</h2>
          </div>
          <span className="panel-meta">PUBLIC DATA</span>
        </div>
        <div className="search-row">
          <div className="command-input">
            <svg viewBox="0 0 20 20" aria-hidden="true">
              <path d="m17 17-3.65-3.65m1.65-4.1A5.75 5.75 0 1 1 3.5 9.25a5.75 5.75 0 0 1 11.5 0Z" />
            </svg>
            <label className="sr-only" htmlFor="handle">Companies</label>
            <input
              ref={handleInputRef}
              id="handle"
              type="text"
              placeholder="Add Ashby handles, for example openai, ramp, notion"
              autoComplete="off"
              spellCheck={false}
              value={handle}
              onChange={(e) => setHandle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') onAdd()
              }}
            />
            <kbd aria-hidden="true">⌘ K</kbd>
          </div>
          <button type="button" className="btn btn-primary add-company" onClick={onAdd}>
            Add company
          </button>
        </div>
        <div className="hint">
          Use commas or spaces for multiple boards. Find each handle at jobs.ashbyhq.com/NAME.
        </div>

        <CompanyBar
          companies={companies}
          counts={companyCounts}
          selected={filters.cos}
          onToggle={(s) => toggle('cos', s)}
          onRemove={removeCompany}
          onRetry={retryCompany}
        />

        {user && (
          <>
            <SavedSearches
              searches={saved}
              sort={savedSort}
              onSort={setSavedSort}
              onApply={applySearch}
              onDelete={onDeleteSaved}
            />
            {companies.length > 0 && (
              <div className="save-row">
                <input
                  className="save-name"
                  type="text"
                  placeholder="Name this search (optional)"
                  value={saveName}
                  onChange={(e) => setSaveName(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') onSaveSearch()
                  }}
                />
                <button type="button" className="btn btn-ghost btn-sm" disabled={savedBusy} onClick={onSaveSearch}>
                  {savedBusy ? 'Saving…' : 'Save search'}
                </button>
              </div>
            )}
          </>
        )}

        {status && <div className="note">{status}</div>}
      </section>

      {companies.length > 0 && (
        <section className="results">
          <div className="readout">
            <span className="cell">
              <span className="dot" />
              <span className="v">LIVE</span>
            </span>
            <span className="cell">
              <span className="k">companies</span>
              <span className="v">{okCount === companies.length ? companies.length : `${okCount}/${companies.length}`}</span>
            </span>
            <span className="cell">
              <span className="k">roles</span>
              <span className="v">{allJobs.length}</span>
            </span>
            <span className="cell">
              <span className="k">showing</span>
              <span className="v">{rows.length}</span>
            </span>
            <span className="cell">
              <span className="k">as of</span>
              <span className="v">{now}</span>
            </span>
          </div>

          {user && (
            <div className="seen-row">
              {lastSeen === null ? (
                <span className="new-count muted">Mark as seen to start flagging new roles</span>
              ) : newCount > 0 ? (
                <span className="new-count">{newCount} new since you last marked as seen</span>
              ) : (
                <span className="new-count muted">Nothing new since you last marked as seen</span>
              )}
              <button className="btn btn-ghost btn-sm" onClick={markAllSeen}>
                Mark all as seen
              </button>
            </div>
          )}

          <Filters
            filters={filters}
            years={years}
            etypes={etypes}
            onChange={patch}
            onCsv={onCsv}
            onCopyLink={onCopyLink}
          />

          <Facet
            label="Location"
            entries={locEntries}
            selected={filters.locs}
            onToggle={(v) => toggle('locs', v)}
            onSelectAll={selectAllLocs}
            onClear={() => patch({ locs: [] })}
          />

          <Facet
            label="Team"
            entries={teamEntries}
            selected={filters.teams}
            onToggle={(v) => toggle('teams', v)}
            onSelectAll={selectAllTeams}
            onClear={() => patch({ teams: [] })}
            extra={
              <div className="toggle" role="group" aria-label="Group by">
                <button aria-pressed={filters.grouping === 'department'} onClick={() => setGrouping('department')}>
                  Department
                </button>
                <button aria-pressed={filters.grouping === 'team'} onClick={() => setGrouping('team')}>
                  Team
                </button>
              </div>
            }
          />

          <div className="result-meta">
            Showing <b>{rows.length}</b> of <b>{allJobs.length}</b> roles
            {metaBits.length ? ` · ${metaBits.join(', ')}` : ''}
          </div>

          <JobTable
            rows={rows}
            grouping={filters.grouping}
            sortKey={filters.sortKey}
            sortDir={filters.sortDir}
            onSort={onSort}
            state={tableState}
            tracking={!!user}
            lastSeen={lastSeen}
            apps={apps}
            onSetStatus={onSetStatus}
          />
        </section>
      )}

      <footer>Fetched live from Ashby and cached briefly on the server. Saved searches are private to your account.</footer>

      {copied && (
        <div className="copied-toast" role="status" aria-live="polite">
          Link copied
        </div>
      )}
      {notice && (
        <div className="toast" role="alert">
          {notice.message}
        </div>
      )}
    </div>
  )
}
