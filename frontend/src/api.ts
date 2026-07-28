import type { Application, BoardResponse, SavedSearch, User } from './types'
import type { FilterState } from './lib/filters'

// Same-origin by default (the backend can serve this app). For a split deploy,
// set VITE_API_BASE to the backend URL at build time.
const BASE = import.meta.env.VITE_API_BASE ?? ''

async function errText(res: Response): Promise<string> {
  let message = `HTTP ${res.status}`
  try {
    const body = await res.json()
    if (body && typeof body.detail === 'string') message = body.detail
  } catch {
    /* response had no JSON body */
  }
  return message
}

// ---- job feed (public) ----
export async function fetchBoard(slug: string): Promise<BoardResponse> {
  const res = await fetch(`${BASE}/api/board/${encodeURIComponent(slug)}`)
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as BoardResponse
}

// ---- auth ----
export async function register(email: string, password: string): Promise<User> {
  const res = await fetch(`${BASE}/api/auth/register`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as User
}

export async function login(email: string, password: string): Promise<User> {
  const res = await fetch(`${BASE}/api/auth/login`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as User
}

export async function logout(): Promise<void> {
  await fetch(`${BASE}/api/auth/logout`, { method: 'POST', credentials: 'include' })
}

export async function me(): Promise<User | null> {
  const res = await fetch(`${BASE}/api/auth/me`, { credentials: 'include' })
  if (res.status === 401) return null
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as User
}

// ---- saved searches (require login) ----
export async function listSearches(sort: 'recent' | 'popular', limit = 12): Promise<SavedSearch[]> {
  const res = await fetch(`${BASE}/api/searches?sort=${sort}&limit=${limit}`, { credentials: 'include' })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as SavedSearch[]
}

export async function saveSearch(input: {
  name: string
  companies: string[]
  filters: FilterState
}): Promise<SavedSearch> {
  const res = await fetch(`${BASE}/api/searches`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as SavedSearch
}

export async function useSearch(id: number): Promise<void> {
  await fetch(`${BASE}/api/searches/${id}/use`, { method: 'POST', credentials: 'include' })
}

export async function deleteSearch(id: number): Promise<void> {
  const res = await fetch(`${BASE}/api/searches/${id}`, { method: 'DELETE', credentials: 'include' })
  if (!res.ok) throw new Error(await errText(res))
}

// ---- last-seen watermark ----
export async function getSeen(): Promise<string | null> {
  const res = await fetch(`${BASE}/api/seen`, { credentials: 'include' })
  if (!res.ok) throw new Error(await errText(res))
  return ((await res.json()) as { lastSeenAt: string | null }).lastSeenAt ?? null
}

export async function markSeen(): Promise<string | null> {
  const res = await fetch(`${BASE}/api/seen`, { method: 'POST', credentials: 'include' })
  if (!res.ok) throw new Error(await errText(res))
  return ((await res.json()) as { lastSeenAt: string | null }).lastSeenAt ?? null
}

// ---- application tracking ----
export async function listApplications(): Promise<Application[]> {
  const res = await fetch(`${BASE}/api/applications`, { credentials: 'include' })
  if (!res.ok) throw new Error(await errText(res))
  return (await res.json()) as Application[]
}

export async function setApplication(jobKey: string, status: string): Promise<void> {
  const res = await fetch(`${BASE}/api/applications`, {
    method: 'PUT',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ jobKey, status }),
  })
  if (!res.ok) throw new Error(await errText(res))
}
