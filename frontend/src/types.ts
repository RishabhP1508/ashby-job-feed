import type { FilterState } from './lib/filters'

export interface Job {
  company: string
  title: string
  team: string
  department: string
  location: string
  secondaryCount: number
  workplaceType: string
  employmentType: string
  isRemote: boolean
  countries: string[]
  applyUrl: string
  publishedAt: string | null
}

export interface BoardResponse {
  slug: string
  fetchedAt: string
  cached: boolean
  count: number
  jobs: Job[]
}

/** One entry in the validated company directory (frontend/src/data/companies.json).
 *  jobCount is a validation-time snapshot used only to order the grid. It goes
 *  stale within days, so it is never displayed. */
export interface DirectoryCompany {
  name: string
  slug: string
  industries: string[]
  jobCount: number
}

export type CompanyStatus = 'loading' | 'ok' | 'error'

export interface CompanyState {
  slug: string
  status: CompanyStatus
  jobs: Job[]
  error?: string
}

export interface SavedSearch {
  id: number
  name: string
  companies: string[]
  filters: FilterState
  useCount: number
  createdAt: string
  lastUsedAt: string
}

export interface User {
  id: number
  email: string
}

export type ApplicationStatus = 'applied' | 'interviewing' | 'rejected' | 'offer'

export interface Application {
  jobKey: string
  status: string
  updatedAt: string
}
