'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { getInterpellations } from '@/lib/api'
import type { Interpellation } from '@/types/api'

const PAGE_SIZE = 20

export default function SpeechesPage() {
  const sp = useSearchParams()
  const router = useRouter()

  const [keyword, setKeyword] = useState(sp.get('keyword') ?? '')
  const [speeches, setSpeeches] = useState<Interpellation[]>([])
  const [loading, setLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  const term = Number(sp.get('term') ?? 11)
  const legislatorName = sp.get('legislator_name') ?? undefined

  const fetchSpeeches = useCallback(async (kw: string, off: number) => {
    setLoading(true)
    try {
      const data = await getInterpellations({
        term,
        legislator_name: legislatorName,
        keyword: kw || undefined,
        limit: PAGE_SIZE + 1,
        offset: off,
      })
      if (off === 0) setSpeeches(data.slice(0, PAGE_SIZE))
      else setSpeeches(prev => [...prev, ...data.slice(0, PAGE_SIZE)])
      setHasMore(data.length > PAGE_SIZE)
    } finally {
      setLoading(false)
    }
  }, [term, legislatorName])

  useEffect(() => {
    setOffset(0)
    fetchSpeeches(sp.get('keyword') ?? '', 0)
  }, [sp, fetchSpeeches])

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const params = new URLSearchParams({ term: String(term) })
    if (keyword.trim()) params.set('keyword', keyword.trim())
    if (legislatorName) params.set('legislator_name', legislatorName)
    router.replace(`/speeches?${params}`)
  }

  function loadMore() {
    const next = offset + PAGE_SIZE
    setOffset(next)
    fetchSpeeches(sp.get('keyword') ?? '', next)
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">院會發言紀錄</h1>
        {legislatorName && (
          <p className="text-slate-500 text-sm mt-1">
            立委：
            <Link href={`/legislators/${encodeURIComponent(legislatorName)}?term=${term}`} className="text-blue-600 hover:underline">
              {legislatorName}
            </Link>
          </p>
        )}
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 max-w-2xl">
        <Input
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          placeholder="發言內容關鍵字…"
          className="flex-1"
        />
        <Button type="submit" className="px-5">
          <Search className="w-4 h-4 mr-1" />搜尋
        </Button>
      </form>

      {loading && offset === 0 && (
        <div className="space-y-3">
          {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-32 w-full rounded-lg" />)}
        </div>
      )}

      {!loading && speeches.length === 0 && (
        <p className="text-slate-500">找不到符合的發言紀錄</p>
      )}

      <div className="space-y-3">
        {speeches.map(sp => (
          <div key={sp.id} className="bg-white border rounded-lg p-4">
            <div className="flex items-center gap-3 mb-2">
              <Link
                href={`/legislators/${encodeURIComponent(sp.legislator_name)}?term=${sp.term}`}
                className="font-semibold hover:underline text-slate-900"
              >
                {sp.legislator_name}
              </Link>
              <span className="text-sm text-slate-400">
                第{sp.session_period}會期 第{sp.meeting_times}次院會
              </span>
            </div>
            <p className="text-sm text-slate-700 line-clamp-6 whitespace-pre-wrap leading-relaxed">
              {sp.interp_content}
            </p>
          </div>
        ))}
      </div>

      {hasMore && (
        <button
          onClick={loadMore}
          disabled={loading}
          className="w-full py-2 text-sm text-slate-500 hover:text-slate-800 border border-dashed rounded-lg hover:bg-white transition-colors"
        >
          {loading ? '載入中…' : '載入更多'}
        </button>
      )}
    </div>
  )
}
