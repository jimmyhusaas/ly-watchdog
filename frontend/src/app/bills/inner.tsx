'use client'

import { useEffect, useState, useCallback } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { Search, ExternalLink } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { getBills } from '@/lib/api'
import { billStatusColor } from '@/lib/utils'
import type { Bill } from '@/types/api'

const PAGE_SIZE = 50

export default function BillsPage() {
  const sp = useSearchParams()
  const router = useRouter()

  const [keyword, setKeyword] = useState(sp.get('keyword') ?? '')
  const [bills, setBills] = useState<Bill[]>([])
  const [loading, setLoading] = useState(false)
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(false)

  const term = Number(sp.get('term') ?? 11)
  const proposer = sp.get('proposer') ?? undefined

  const fetchBills = useCallback(async (kw: string, off: number) => {
    setLoading(true)
    try {
      const data = await getBills({
        term,
        keyword: kw || undefined,
        proposer,
        limit: PAGE_SIZE + 1,
        offset: off,
      })
      if (off === 0) setBills(data.slice(0, PAGE_SIZE))
      else setBills(prev => [...prev, ...data.slice(0, PAGE_SIZE)])
      setHasMore(data.length > PAGE_SIZE)
    } finally {
      setLoading(false)
    }
  }, [term, proposer])

  useEffect(() => {
    setOffset(0)
    fetchBills(sp.get('keyword') ?? '', 0)
  }, [sp, fetchBills])

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    const params = new URLSearchParams({ term: String(term) })
    if (keyword.trim()) params.set('keyword', keyword.trim())
    if (proposer) params.set('proposer', proposer)
    router.replace(`/bills?${params}`)
  }

  function loadMore() {
    const next = offset + PAGE_SIZE
    setOffset(next)
    fetchBills(sp.get('keyword') ?? '', next)
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-2xl font-bold">法案查詢</h1>
        {proposer && <p className="text-slate-500 text-sm mt-1">提案人：{proposer}</p>}
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 max-w-2xl">
        <Input
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          placeholder="法案名稱關鍵字…"
          className="flex-1"
        />
        <Button type="submit" className="px-5">
          <Search className="w-4 h-4 mr-1" />搜尋
        </Button>
      </form>

      {loading && offset === 0 && (
        <div className="space-y-2">
          {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-16 w-full rounded-lg" />)}
        </div>
      )}

      {!loading && bills.length === 0 && (
        <p className="text-slate-500">找不到符合的法案</p>
      )}

      <div className="space-y-2">
        {bills.map(bill => (
          <div key={bill.id} className="bg-white border rounded-lg p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="min-w-0">
                <p className="font-medium leading-snug">{bill.bill_name}</p>
                <p className="text-sm text-slate-500 mt-1">
                  {bill.bill_no} · 第{bill.session_period}會期
                  {bill.bill_proposer && ` · ${bill.bill_proposer.slice(0, 40)}${(bill.bill_proposer?.length ?? 0) > 40 ? '…' : ''}`}
                </p>
                <a
                  href={`https://lis.ly.gov.tw/lislgmeetc/lgmeetkm?MEHF11^${bill.bill_no}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-blue-500 hover:underline mt-1"
                >
                  立院資料來源 <ExternalLink className="w-3 h-3" />
                </a>
              </div>
              <span className={`text-xs rounded px-2 py-1 shrink-0 whitespace-nowrap ${billStatusColor(bill.bill_status)}`}>
                {bill.bill_status}
              </span>
            </div>
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
