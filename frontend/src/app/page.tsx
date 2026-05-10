'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Search } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

export default function HomePage() {
  const [q, setQ] = useState('')
  const router = useRouter()

  function handleSearch(e: React.FormEvent) {
    e.preventDefault()
    if (q.trim()) router.push(`/search?q=${encodeURIComponent(q.trim())}`)
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] gap-10 text-center">
      <div>
        <h1 className="text-4xl font-bold text-slate-900 mb-3">🏛 立院監督平台</h1>
        <p className="text-slate-500 text-lg">查詢立委的提案、院會發言與委員會職務</p>
      </div>

      <form onSubmit={handleSearch} className="flex gap-2 w-full max-w-xl">
        <Input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="搜尋立委姓名、法案名稱、發言關鍵字…"
          className="flex-1 h-12 text-base"
          autoFocus
        />
        <Button type="submit" size="lg" className="h-12 px-6">
          <Search className="w-4 h-4 mr-2" />
          搜尋
        </Button>
      </form>

      <div className="flex gap-6 text-sm text-slate-500">
        <Link href="/legislators?term=11" className="hover:text-slate-800 transition-colors underline underline-offset-4">
          第11屆立委列表
        </Link>
        <Link href="/bills?term=11" className="hover:text-slate-800 transition-colors underline underline-offset-4">
          第11屆法案
        </Link>
        <Link href="/speeches?term=11" className="hover:text-slate-800 transition-colors underline underline-offset-4">
          院會發言紀錄
        </Link>
      </div>
    </div>
  )
}
