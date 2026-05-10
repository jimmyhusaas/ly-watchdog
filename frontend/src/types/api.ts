export interface Legislator {
  id: string
  legislator_uid: string
  term: number
  name: string
  party: string | null
  district: string | null
  valid_from: string
  valid_to: string | null
  recorded_at: string
  superseded_at: string | null
}

export interface LegislatorDetail extends Legislator {
  bill_count: number
  speech_count: number
}

export interface Bill {
  id: string
  bill_uid: string
  term: number
  session_period: number
  bill_no: string
  bill_name: string
  bill_org: string | null
  bill_proposer: string | null
  bill_cosignatory: string | null
  bill_status: string
  valid_from: string
  valid_to: string | null
  recorded_at: string
  superseded_at: string | null
}

export interface Interpellation {
  id: string
  interp_uid: string
  term: number
  session_period: number
  meeting_times: number
  legislator_name: string
  interp_content: string
  valid_from: string
  valid_to: string | null
  recorded_at: string
  superseded_at: string | null
}

export interface CommitteeMembership {
  id: string
  committee_uid: string
  term: number
  session_period: number
  legislator_name: string
  committee: string
  is_convener: boolean
  valid_from: string
  valid_to: string | null
  recorded_at: string
  superseded_at: string | null
}

export interface SearchResult {
  type: 'legislator' | 'bill' | 'speech'
  term: number
  // legislator
  name?: string
  party?: string
  district?: string
  // bill
  bill_no?: string
  bill_name?: string
  bill_status?: string
  bill_proposer?: string
  session_period?: number
  // speech
  legislator_name?: string
  // shared
  highlight?: string
}
