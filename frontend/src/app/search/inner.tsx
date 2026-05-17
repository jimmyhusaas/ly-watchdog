'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import { Search, FileText, Mic, User, ExternalLink } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { PartyBadge } from '@/components/PartyBadge'
import { searchAll } from '@/lib/api'
import type { SearchResult } from '@/types/api'

export default function SearchPage() {
  const sp = useSearchParams()
  const router = useRouter()
  const [q, setQ] = useState(sp.get('q') ?? '')
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)

  const doSearch = useCallback(async (query: string) => {
    if (!query.trim()) return
    setLoading(true)
    try {
      const data = await searchAll({ q: query, limit: 30 })
      setResults(data)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const initial = sp.get('q')
    if (initial) doSearch(initial)
  }, [sp, doSearch])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (q.trim()) {
      router.replace(`/search?q=${encodeURIComponent(q.trim())}`)
      doSearch(q.trim())
    }
  }

  const legislators = results.filter(r => r.type === 'legislator')
  const bills = results.filter(r => r.type === 'bill')
  const speeches = results.filter(r => r.type === 'speech')

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="flex gap-2 max-w-2xl">
        <Input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="搜尋關鍵字…"
          className="flex-1 h-10"
        />
        <Button type="submit" className="h-10 px-5">
          <Search className="w-4 h-4 mr-1" />搜尋
        </Button>
      </form>

      {loading && (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
        </div>
      )}

      {!loading && results.length === 0 && sp.get('q') && (
        <p className="text-slate-500">找不到「{sp.get('q')}」相關結果</p>
      )}

      {legislators.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-1">
            <User className="w-4 h-4" /> 立委 ({legislators.length})
          </h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {legislators.map((r, i) => (
              <Link
                key={i}
                href={`/legislators/${encodeURIComponent(r.name ?? '')}?term=${r.term}`}
                className="bg-white rounded-lg border p-4 hover:shadow-md transition-shadow"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold">{r.name}</span>
                  <PartyBadge party={r.party ?? null} />
                </div>
                <p className="text-sm text-slate-500">{r.district ?? '不分區'} · 第{r.term}屆</p>
              </Link>
            ))}
          </div>
        </section>
      )}

      {bills.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-1">
            <FileText className="w-4 h-4" /> 法案 ({bills.length})
          </h2>
          <div className="space-y-2">
            {bills.map((r, i) => (
              <div key={i} className="bg-white rounded-lg border p-4">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="font-medium">{r.bill_name}</p>
                    <p className="text-sm text-slate-500 mt-1">
                      {r.bill_proposer && <span>提案：{r.bill_proposer.slice(0, 30)}{(r.bill_proposer?.length ?? 0) > 30 ? '…' : ''} · </span>}
                      第{r.term}屆第{r.session_period}會期
                    </p>
                    {r.highlight && r.highlight !== r.bill_name && (
                      <p className="text-xs text-slate-400 mt-1 line-clamp-2">{r.highlight}</p>
                    )}
                    <a
                      href="https://data.ly.gov.tw/getds.action?id=20"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-xs text-blue-500 hover:underline mt-1"
                    >
                      立院資料來源 <ExternalLink className="w-3 h-3" />
                    </a>
                  </div>
                  <span className="text-xs bg-slate-100 text-slate-600 rounded px-2 py-1 whitespace-nowrap shrink-0">
                    {r.bill_status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </section>
      )}

      {speeches.length > 0 && (
        <section>
          <h2 className="text-sm font-semibold text-slate-500 uppercase tracking-wide mb-3 flex items-center gap-1">
            <Mic className="w-4 h-4" /> 院會發言 ({speeches.length})
          </h2>
          <div className="space-y-2">
            {speeches.map((r, i) => (
              <div key={i} className="bg-white rounded-lg border p-4">
                <Link
                  href={`/legislators/${encodeURIComponent(r.legislator_name ?? '')}?term=${r.term}`}
                  className="font-medium hover:underline"
                >
                  {r.legislator_name}
                </Link>
                <span className="text-sm text-slate-500 ml-2">
                  第{r.term}屆第{r.session_period}會期
                </span>
                <p className="text-sm text-slate-600 mt-2 line-clamp-3">{r.highlight}</p>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
