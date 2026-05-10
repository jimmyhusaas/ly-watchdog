import type {
  Bill,
  CommitteeMembership,
  Interpellation,
  Legislator,
  LegislatorDetail,
  SearchResult,
} from '@/types/api'

const BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function get<T>(path: string, params?: Record<string, string | number | boolean | undefined>): Promise<T> {
  const url = new URL(`${BASE}${path}`)
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== null && v !== '') {
        url.searchParams.set(k, String(v))
      }
    }
  }
  const res = await fetch(url.toString(), { next: { revalidate: 60 } })
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`)
  return res.json() as Promise<T>
}

// Legislators
export const getLegislators = (params?: {
  term?: number
  party?: string
  district?: string
}) => get<Legislator[]>('/v1/legislators', params)

export const getLegislator = (name: string, term?: number) =>
  get<LegislatorDetail>(`/v1/legislators/${encodeURIComponent(name)}`, { term })

export const getLegislatorBills = (
  name: string,
  params: { term: number; session_period?: number; limit?: number; offset?: number }
) => get<Bill[]>(`/v1/legislators/${encodeURIComponent(name)}/bills`, params)

export const getLegislatorSpeeches = (
  name: string,
  params: { term: number; session_period?: number; keyword?: string; limit?: number; offset?: number }
) => get<Interpellation[]>(`/v1/legislators/${encodeURIComponent(name)}/speeches`, params)

export const getLegislatorCommittees = (
  name: string,
  params: { term: number; session_period?: number }
) => get<CommitteeMembership[]>(`/v1/legislators/${encodeURIComponent(name)}/committees`, params)

// Bills
export const getBills = (params: {
  term: number
  session_period?: number
  proposer?: string
  keyword?: string
  status?: string
  limit?: number
  offset?: number
}) => get<Bill[]>('/v1/bills', params)

// Interpellations
export const getInterpellations = (params: {
  term: number
  session_period?: number
  legislator_name?: string
  keyword?: string
  limit?: number
  offset?: number
}) => get<Interpellation[]>('/v1/interpellations', params)

// Search
export const searchAll = (params: { q: string; term?: number; limit?: number }) =>
  get<SearchResult[]>('/v1/search', params)
