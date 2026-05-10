import { Suspense } from 'react'
import SearchInner from './inner'
import { Skeleton } from '@/components/ui/skeleton'

export default function SearchPage() {
  return (
    <Suspense fallback={<div className="space-y-3">{[...Array(6)].map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}</div>}>
      <SearchInner />
    </Suspense>
  )
}
