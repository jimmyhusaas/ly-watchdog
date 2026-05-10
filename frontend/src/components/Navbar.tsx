import Link from 'next/link'

export function Navbar() {
  return (
    <header className="border-b bg-white sticky top-0 z-50">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center gap-6">
        <Link href="/" className="font-bold text-slate-900 text-lg">
          🏛 立院監督
        </Link>
        <nav className="flex gap-4 text-sm text-slate-600">
          <Link href="/legislators" className="hover:text-slate-900 transition-colors">立委</Link>
          <Link href="/bills" className="hover:text-slate-900 transition-colors">法案</Link>
          <Link href="/speeches" className="hover:text-slate-900 transition-colors">院會發言</Link>
        </nav>
      </div>
    </header>
  )
}
