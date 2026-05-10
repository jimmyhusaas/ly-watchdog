import { Suspense } from 'react'
import SpeechesInner from './inner'
import { Skeleton } from '@/components/ui/skeleton'

export default function SpeechesPage() {
  return (
    <Suspense fallback={<div className="space-y-3">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-32 w-full rounded-lg" />)}</div>}>
      <SpeechesInner />
    </Suspense>
  )
}
