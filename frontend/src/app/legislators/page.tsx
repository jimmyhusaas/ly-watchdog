import Link from 'next/link'
import { getLegislators } from '@/lib/api'
import { PartyBadge } from '@/components/PartyBadge'

export const revalidate = 300

interface Props {
  searchParams: Promise<{ term?: string; party?: string }>
}

export default async function LegislatorsPage({ searchParams }: Props) {
  const params = await searchParams
  const term = Number(params.term ?? 11)
  const party = params.party

  const legislators = await getLegislators({ term, party })

  const parties = Array.from(new Set(legislators.map(l => l.party).filter(Boolean)))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 className="text-2xl font-bold">立委列表</h1>
          <p className="text-slate-500 text-sm mt-1">共 {legislators.length} 位</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          {[11, 10].map(t => (
            <Link
              key={t}
              href={`/legislators?term=${t}${party ? `&party=${party}` : ''}`}
              className={`px-3 py-1.5 rounded-full text-sm border transition-colors ${term === t ? 'bg-slate-900 text-white border-slate-900' : 'bg-white hover:bg-slate-50 border-slate-200'}`}
            >
              第{t}屆
            </Link>
          ))}
        </div>
      </div>

      {/* Party filter */}
      <div className="flex gap-2 flex-wrap">
        <Link
          href={`/legislators?term=${term}`}
          className={`px-3 py-1 rounded-full text-sm border transition-colors ${!party ? 'bg-slate-800 text-white border-slate-800' : 'bg-white hover:bg-slate-50 border-slate-200'}`}
        >
          全部
        </Link>
        {parties.map(p => (
          <Link
            key={p}
            href={`/legislators?term=${term}&party=${encodeURIComponent(p!)}`}
            className={`px-3 py-1 rounded-full text-sm border transition-colors ${party === p ? 'bg-slate-800 text-white border-slate-800' : 'bg-white hover:bg-slate-50 border-slate-200'}`}
          >
            {p}
          </Link>
        ))}
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {legislators.map(leg => (
          <Link
            key={leg.id}
            href={`/legislators/${encodeURIComponent(leg.name)}?term=${leg.term}`}
            className="bg-white border rounded-xl p-4 hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="font-semibold text-slate-900">{leg.name}</span>
              <PartyBadge party={leg.party} />
            </div>
            <p className="text-sm text-slate-500">{leg.district ?? '不分區'}</p>
          </Link>
        ))}
      </div>
    </div>
  )
}
