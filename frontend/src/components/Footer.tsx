import { ExternalLink } from 'lucide-react'

export function Footer() {
  return (
    <footer className="border-t bg-white mt-12">
      <div className="max-w-6xl mx-auto px-4 py-6 flex flex-col sm:flex-row items-center justify-between gap-3 text-sm text-slate-500">
        <p>立院監督平台 — 公民開源專案</p>
        <div className="flex flex-wrap gap-4 items-center justify-center">
          <span className="text-slate-400">資料來源：</span>
          <a
            href="https://data.ly.gov.tw"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-blue-600 hover:underline"
          >
            立法院開放資料平台
            <ExternalLink className="w-3 h-3" />
          </a>
          <a
            href="https://www.ly.gov.tw"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-blue-600 hover:underline"
          >
            立法院官網
            <ExternalLink className="w-3 h-3" />
          </a>
        </div>
      </div>
    </footer>
  )
}
