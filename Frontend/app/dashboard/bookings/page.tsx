'use client'

import { Suspense, useState, useEffect, useCallback } from 'react'
import { useUser, UserButton } from '@clerk/nextjs'
import { useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, RefreshCw, Calendar, Search, Download } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Booking {
  _id: string
  tokenNumber: string
  farmerName: string
  village: string
  cropType: string
  quantity: string
  mandiName: string
  mandiLocation: string
  timeSlot: string
  date: string
  phoneNumber: string
  status: string
  businessId: string
  createdAt: string
}

function BookingsPageContent() {
  const { user } = useUser()
  const searchParams = useSearchParams()
  const businessId = searchParams.get('businessId') ?? ''

  const [bookings, setBookings] = useState<Booking[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [dateFilter, setDateFilter] = useState(() => new Date().toISOString().slice(0, 10))
  const [search, setSearch] = useState('')

  const fetchBookings = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const params = new URLSearchParams()
      if (businessId) params.set('businessId', businessId)
      if (dateFilter) params.set('date', dateFilter)
      const res = await fetch(`/api/bookings?${params.toString()}`)
      if (!res.ok) throw new Error((await res.json()).message || 'Failed to load bookings')
      const data = await res.json()
      setBookings(data.bookings || [])
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load bookings')
    } finally {
      setLoading(false)
    }
  }, [businessId, dateFilter])

  useEffect(() => { fetchBookings() }, [fetchBookings])

  const filtered = bookings.filter(b =>
    !search ||
    b.farmerName.toLowerCase().includes(search.toLowerCase()) ||
    b.tokenNumber.toLowerCase().includes(search.toLowerCase()) ||
    b.village.toLowerCase().includes(search.toLowerCase()) ||
    b.phoneNumber.includes(search)
  )

  const exportCSV = () => {
    const headers = ['Token', 'Farmer Name', 'Village', 'Crop', 'Quantity', 'Mandi', 'Location', 'Time Slot', 'Date', 'Phone', 'Status']
    const rows = filtered.map(b => [
      b.tokenNumber, b.farmerName, b.village, b.cropType, b.quantity,
      b.mandiName, b.mandiLocation, b.timeSlot, b.date, b.phoneNumber, b.status,
    ])
    const csv = [headers, ...rows].map(r => r.map(v => `"${String(v ?? '').replace(/"/g, '""')}"`).join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `bookings-${dateFilter || 'all'}.csv`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="min-h-screen bg-transparent text-white" style={{ fontFamily: 'var(--font-bitcount)' }}>
      {/* Header */}
      <div className="border-b border-white/10 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/dashboard">
            <Button variant="ghost" size="sm" className="text-white/60 hover:text-white">
              <ArrowLeft className="w-4 h-4 mr-2" /> Dashboard
            </Button>
          </Link>
          <h1 className="text-2xl font-light">🌾 Mandi Bookings</h1>
        </div>
        <UserButton />
      </div>

      <div className="max-w-7xl mx-auto px-6 py-8 space-y-6">
        {/* Controls row */}
        <div className="flex flex-wrap gap-3 items-center">
          {/* Date filter */}
          <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2">
            <Calendar className="w-4 h-4 text-white/40" />
            <input
              type="date"
              value={dateFilter}
              onChange={e => setDateFilter(e.target.value)}
              className="bg-transparent text-white text-sm focus:outline-none"
            />
            {dateFilter && (
              <button onClick={() => setDateFilter('')} className="text-white/40 hover:text-white text-sm ml-1">×</button>
            )}
          </div>

          {/* Search */}
          <div className="flex items-center gap-2 bg-white/5 border border-white/10 rounded-lg px-3 py-2 flex-1 min-w-50">
            <Search className="w-4 h-4 text-white/40" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search by name, token, village, phone…"
              className="bg-transparent text-white text-sm focus:outline-none flex-1"
            />
          </div>

          {/* Refresh */}
          <Button variant="ghost" size="sm" onClick={fetchBookings} className="text-white/60 hover:text-white border border-white/10">
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
            Refresh
          </Button>

          {/* Export */}
          {filtered.length > 0 && (
            <Button variant="ghost" size="sm" onClick={exportCSV} className="text-green-400/70 hover:text-green-400 border border-green-500/20">
              <Download className="w-4 h-4 mr-2" />
              Export CSV
            </Button>
          )}
        </div>

        {/* Summary cards */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {[
            { label: 'Total Bookings', value: filtered.length },
            { label: 'Confirmed', value: filtered.filter(b => b.status === 'confirmed').length },
            { label: 'Unique Farmers', value: new Set(filtered.map(b => b.phoneNumber)).size },
            { label: 'Mandis', value: new Set(filtered.map(b => b.mandiName)).size },
          ].map(card => (
            <div key={card.label} className="bg-white/5 border border-white/10 rounded-xl p-4 text-center">
              <p className="text-2xl font-light text-white">{card.value}</p>
              <p className="text-xs text-white/40 mt-1">{card.label}</p>
            </div>
          ))}
        </div>

        {/* Table */}
        {loading ? (
          <div className="text-center py-20 text-white/40">Loading bookings…</div>
        ) : error ? (
          <div className="text-center py-20 text-red-400">{error}</div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20 text-white/40">
            {bookings.length === 0
              ? 'No bookings found. Farmers will appear here once they book via WhatsApp.'
              : 'No bookings match your search.'}
          </div>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-white/10">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-white/10 bg-white/5 text-white/50 text-xs uppercase tracking-wide">
                  {['Token', 'Farmer', 'Village', 'Crop', 'Qty (qtl)', 'Mandi', 'Time Slot', 'Date', 'Phone', 'Status'].map(h => (
                    <th key={h} className="px-4 py-3 text-left whitespace-nowrap">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {filtered.map((b, i) => (
                  <tr key={b._id} className={`border-b border-white/5 hover:bg-white/5 transition-colors ${i % 2 === 0 ? '' : 'bg-white/2'}`}>
                    <td className="px-4 py-3 font-mono text-yellow-400 whitespace-nowrap">{b.tokenNumber}</td>
                    <td className="px-4 py-3 text-white font-medium">{b.farmerName}</td>
                    <td className="px-4 py-3 text-white/70">{b.village}</td>
                    <td className="px-4 py-3 text-white/70">{b.cropType}</td>
                    <td className="px-4 py-3 text-white/70">{b.quantity}</td>
                    <td className="px-4 py-3 text-white/70">{b.mandiName}</td>
                    <td className="px-4 py-3 text-white/70 whitespace-nowrap">{b.timeSlot}</td>
                    <td className="px-4 py-3 text-white/70 whitespace-nowrap">{b.date}</td>
                    <td className="px-4 py-3 text-white/50 font-mono text-xs">{b.phoneNumber.replace('whatsapp:', '')}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                        b.status === 'confirmed'
                          ? 'bg-green-500/20 text-green-400'
                          : 'bg-white/10 text-white/50'
                      }`}>
                        {b.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="text-xs text-white/30 text-center">
          Showing {filtered.length} of {bookings.length} bookings
          {dateFilter ? ` for ${dateFilter}` : ' (all dates)'}
          {user?.firstName ? ` — ${user.firstName}'s account` : ''}
        </p>
      </div>
    </div>
  )
}

export default function BookingsPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-transparent text-white flex items-center justify-center">Loading bookings...</div>}>
      <BookingsPageContent />
    </Suspense>
  )
}
