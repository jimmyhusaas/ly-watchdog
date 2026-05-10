import { partyColor } from '@/lib/utils'

export function PartyBadge({ party }: { party: string | null }) {
  return (
    <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${partyColor(party)}`}>
      {party ?? '無黨籍'}
    </span>
  )
}
