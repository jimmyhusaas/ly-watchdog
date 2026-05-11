import { notFound } from 'next/navigation'
import Link from 'next/link'
import {
  getLegislator,
  getLegislatorBills,
  getLegislatorSpeeches,
  getLegislatorCommittees,
} from '@/lib/api'
import { PartyBadge } from '@/components/PartyBadge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { billStatusColor } from '@/lib/utils'

export const revalidate = 300

interface Props {
  params: Promise<{ name: string }>
  searchParams: Promise<{ term?: string }>
}

export default async function LegislatorDetailPage({ params, searchParams }: Props) {
  const { name } = await params
  const sp = await searchParams
  const decodedName = decodeURIComponent(name)
  const term = Number(sp.term ?? 11)

  let legislator
  try {
    legislator = await getLegislator(decodedName, term)
  } catch {
    notFound()
  }

  const [bills, speeches, rawCommittees] = await Promise.all([
    getLegislatorBills(decodedName, { term, limit: 50 }).catch(() => []),
    getLegislatorSpeeches(decodedName, { term, limit: 20 }).catch(() => []),
    getLegislatorCommittees(decodedName, { term }).catch(() => []),
  ])

  // Deduplicate committee names — if any session made them convener, show convener badge
  const committeeMap = new Map<string, boolean>()
  for (const c of rawCommittees) {
    committeeMap.set(c.committee, (committeeMap.get(c.committee) ?? false) || c.is_convener)
  }
  const committees = Array.from(committeeMap.entries()).map(([committee, is_convener]) => ({
    committee,
    is_convener,
  }))

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="bg-white border rounded-xl p-6">
        <div className="flex items-start justify-between flex-wrap gap-4">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold">{legislator.name}</h1>
              <PartyBadge party={legislator.party} />
            </div>
            <p className="text-slate-500">
              {legislator.district ?? '不分區'} · 第{legislator.term}屆
            </p>
          </div>
          <div className="flex gap-6 text-center">
            <div>
              <p className="text-2xl font-bold text-slate-900">{legislator.bill_count}</p>
              <p className="text-xs text-slate-500 mt-1">提案數</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{legislator.speech_count}</p>
              <p className="text-xs text-slate-500 mt-1">院會發言</p>
            </div>
            <div>
              <p className="text-2xl font-bold text-slate-900">{committees.length}</p>
              <p className="text-xs text-slate-500 mt-1">委員會席次</p>
            </div>
          </div>
        </div>

        {committees.length > 0 && (
          <div className="flex gap-2 flex-wrap mt-4 pt-4 border-t">
            {committees.map(c => (
              <span
                key={c.committee}
                className={`text-xs px-2.5 py-1 rounded-full border ${c.is_convener ? 'bg-amber-50 border-amber-200 text-amber-800 font-medium' : 'bg-slate-50 border-slate-200 text-slate-600'}`}
              >
                {c.is_convener ? '★ ' : ''}{c.committee}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <Tabs defaultValue="bills">
        <TabsList>
          <TabsTrigger value="bills">提案 ({bills.length})</TabsTrigger>
          <TabsTrigger value="speeches">院會發言 ({speeches.length})</TabsTrigger>
        </TabsList>

        <TabsContent value="bills" className="mt-4 space-y-2">
          {bills.length === 0 && <p className="text-slate-500 text-sm">本屆無提案紀錄</p>}
          {bills.map(bill => (
            <div key={bill.id} className="bg-white border rounded-lg p-4">
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <p className="font-medium text-slate-900 leading-snug">{bill.bill_name}</p>
                  <p className="text-sm text-slate-500 mt-1">
                    {bill.bill_no} · 第{bill.session_period}會期
                  </p>
                </div>
                <span className={`text-xs rounded px-2 py-1 whitespace-nowrap shrink-0 ${billStatusColor(bill.bill_status)}`}>
                  {bill.bill_status}
                </span>
              </div>
            </div>
          ))}
          {bills.length === 50 && (
            <Link
              href={`/bills?term=${term}&proposer=${encodeURIComponent(decodedName)}`}
              className="block text-center text-sm text-blue-600 hover:underline py-2"
            >
              查看全部提案 →
            </Link>
          )}
        </TabsContent>

        <TabsContent value="speeches" className="mt-4 space-y-3">
          {speeches.length === 0 && <p className="text-slate-500 text-sm">本屆無院會發言紀錄</p>}
          {speeches.map(sp => (
            <div key={sp.id} className="bg-white border rounded-lg p-4">
              <p className="text-sm text-slate-500 mb-2">
                第{sp.session_period}會期 第{sp.meeting_times}次院會
              </p>
              <p className="text-sm text-slate-700 line-clamp-5 whitespace-pre-wrap">
                {sp.interp_content}
              </p>
            </div>
          ))}
          {speeches.length === 20 && (
            <Link
              href={`/speeches?term=${term}&legislator_name=${encodeURIComponent(decodedName)}`}
              className="block text-center text-sm text-blue-600 hover:underline py-2"
            >
              查看全部發言 →
            </Link>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}
