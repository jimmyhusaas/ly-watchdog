import { clsx, type ClassValue } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export const PARTY_COLORS: Record<string, string> = {
  民主進步黨: 'bg-green-100 text-green-800',
  中國國民黨: 'bg-blue-100 text-blue-800',
  台灣民眾黨: 'bg-cyan-100 text-cyan-800',
  時代力量: 'bg-yellow-100 text-yellow-800',
  無黨籍: 'bg-gray-100 text-gray-700',
}

export function partyColor(party: string | null): string {
  return PARTY_COLORS[party ?? ''] ?? 'bg-gray-100 text-gray-700'
}

export const BILL_STATUS_COLORS: Record<string, string> = {
  排入議程: 'bg-blue-100 text-blue-800',
  委員會審查: 'bg-yellow-100 text-yellow-800',
  完成三讀: 'bg-green-100 text-green-800',
  撤回: 'bg-red-100 text-red-800',
}

export function billStatusColor(status: string): string {
  for (const [key, cls] of Object.entries(BILL_STATUS_COLORS)) {
    if (status.includes(key)) return cls
  }
  return 'bg-gray-100 text-gray-700'
}
