import { Suspense } from 'react'
import BillsInner from './inner'
import { Skeleton } from '@/components/ui/skeleton'

export default function BillsPage() {
  return (
    <Suspense fallback={<div className="space-y-2">{[...Array(6)].map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}</div>}>
      <BillsInner />
    </Suspense>
  )
}
