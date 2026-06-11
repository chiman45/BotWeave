'use client'

import { Skeleton } from 'boneyard-js/react'
import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useUser, UserButton } from '@clerk/nextjs'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Plus, Bot, TrendingUp, MessageSquare, Users, DollarSign, Settings, BarChart3, Home, CreditCard, Info, Tag, Menu, X, MessageCircle, BookOpen, Zap, Copy, CheckCircle, ExternalLink, Trash2, Phone } from 'lucide-react'

interface BotData {
  _id: string
  businessId: string
  businessName: string
  category: string
  botName: string
  useCaseType: string
  planType: string
  phoneNumber: string
  verificationStatus: string
  autoReply: boolean
  humanHandoff: boolean
  messageLimit: number
  messageBalance: number
  totalMessages?: number
  createdAt: string
  allocatedNumber?: string
  // Editable extended fields
  welcomeMessage?: string
  fallbackMessage?: string
  humanHandoffMessage?: string
  keywordResponses?: Record<string, string>
  mandis?: { name: string; location: string; address: string }[]
  slots?: string[]
  maxBookingsPerSlot?: number
  city?: string
  country?: string
  defaultLanguage?: string
  businessHours?: string
  // AI fields
  botType?: 'normal' | 'ai'
  aiModel?: string
  aiSystemPrompt?: string
  aiRagEnabled?: boolean
  // IVR fields
  ivrNodes?: { id: string; message: string; options: { label: string; nextNodeId: string }[]; isEndNode: boolean }[]
}

export default function DashboardPage() {
  const router = useRouter()
  const { user, isLoaded } = useUser()
  const [bots, setBots] = useState<BotData[]>([])
  const [loading, setLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activatingBotId, setActivatingBotId] = useState<string | null>(null)
  const [deactivatingBotId, setDeactivatingBotId] = useState<string | null>(null)
  const [deletingBotId, setDeletingBotId] = useState<string | null>(null)
  const [confirmDeleteBot, setConfirmDeleteBot] = useState<BotData | null>(null)

  // ── Edit Bot state ──────────────────────────────────────────
  const [editBot, setEditBot] = useState<BotData | null>(null)
  const [editDraft, setEditDraft] = useState<Record<string, unknown>>({})
  const [editKeywords, setEditKeywords] = useState<{ keyword: string; response: string }[]>([])
  const [editMandiList, setEditMandiList] = useState<{ name: string; location: string; address: string }[]>([])
  const [editSlotTimes, setEditSlotTimes] = useState<string[]>([])
  const [editMaxPerSlot, setEditMaxPerSlot] = useState(10)
  const [editSaving, setEditSaving] = useState(false)
  // IVR edit state
  type EditIvrNode = { id: string; message: string; options: { label: string; nextNodeId: string }[]; isEndNode: boolean }
  const [editIvrNodes, setEditIvrNodes] = useState<EditIvrNode[]>([])
  const [activationModal, setActivationModal] = useState<{
    botName: string
    allocatedNumber: string
    webhookUrl: string
  } | null>(null)
  const [ivrModal, setIvrModal] = useState<{
    botName: string
    phone: string
    voiceWebhookUrl: string
  } | null>(null)
  const [copiedField, setCopiedField] = useState<string | null>(null)
  const [stats, setStats] = useState({
    totalBots: 0,
    activeBots: 0,
    totalMessages: 0,
    totalRevenue: 0,
    totalConversations: 0,
    paymentDue: 0,
    paymentCompleted: 0
  })
  const [credits, setCredits] = useState<number | null>(null)
  const [sandboxInfo, setSandboxInfo] = useState<{ whatsappNumber: string; joinText: string } | null>(null)

  useEffect(() => {
    if (isLoaded && !user) {
      router.push('/')
      return
    }

    if (user) {
      fetchBots()
      // Fetch (and auto-init) credit balance
      fetch('/api/credits')
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setCredits(d.credits) })
        .catch(() => {})
      // Fetch sandbox info for WhatsApp test links
      const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:5000'
      fetch(`${BACKEND_URL}/api/bot/sandbox-info`)
        .then(r => r.ok ? r.json() : null)
        .then(d => { if (d) setSandboxInfo({ whatsappNumber: d.whatsappNumber, joinText: d.joinText }) })
        .catch(() => {})
    }
  }, [isLoaded, user, router])

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 2000)
  }

  const deleteBot = async (bot: BotData) => {
    setDeletingBotId(bot.businessId)
    setConfirmDeleteBot(null)
    try {
      const res = await fetch('/api/bot', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ businessId: bot.businessId })
      })
      if (res.ok) {
        setBots(prev => prev.filter(b => b.businessId !== bot.businessId))
        setStats(prev => ({
          ...prev,
          totalBots: prev.totalBots - 1,
          activeBots: bot.verificationStatus === 'verified' ? prev.activeBots - 1 : prev.activeBots
        }))
      } else {
        const data = await res.json()
        alert(data.message || 'Failed to delete bot')
      }
    } catch {
      alert('Failed to connect to server')
    } finally {
      setDeletingBotId(null)
    }
  }

  // ── AI KB state ──────────────────────────────────────────
  const [kbInfo, setKbInfo] = useState<{ exists: boolean; chunks: number } | null>(null)
  const [kbUploading, setKbUploading] = useState(false)
  const [kbUploadProgress, setKbUploadProgress] = useState<number | null>(null)
  const [kbStatusMsg, setKbStatusMsg] = useState('')
  const [ollamaModels] = useState<string[]>([])
  const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:5000'

  const fetchKbInfo = async (businessId: string) => {
    try {
      const res = await fetch(`${BACKEND}/api/ai/kb/${businessId}`)
      const data = await res.json()
      setKbInfo(data)
    } catch { setKbInfo(null) }
  }

  const uploadKbFile = (businessId: string, file: File) => {
    setKbUploading(true)
    setKbUploadProgress(0)
    setKbStatusMsg('Uploading file…')
    const fd = new FormData()
    fd.append('file', file)
    const xhr = new XMLHttpRequest()

    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100)
        setKbUploadProgress(pct)
        setKbStatusMsg(`Uploading… ${pct}%`)
      }
    }

    xhr.onload = () => {
      try {
        const data = JSON.parse(xhr.responseText)
        if (xhr.status >= 200 && xhr.status < 300 && data.jobId) {
          setKbStatusMsg('Chunking & embedding…')
          // Poll the progress endpoint
          const poll = setInterval(async () => {
            try {
              const res = await fetch(`${BACKEND}/api/ai/kb/progress/${data.jobId}`)
              const job = await res.json()
              const pct = job.progress ?? 0
              setKbUploadProgress(pct)
              setKbStatusMsg(
                job.status === 'done'  ? `Done — ${job.chunks} chunks indexed` :
                job.status === 'error' ? `Error: ${job.error}` :
                `Embedding chunks… ${pct}%`
              )
              if (job.status === 'done' || job.status === 'error') {
                clearInterval(poll)
                if (job.status === 'done') fetchKbInfo(businessId)
                setTimeout(() => { setKbUploadProgress(null); setKbUploading(false); setKbStatusMsg('') }, 1500)
              }
            } catch { /* retry next tick */ }
          }, 800)
        } else {
          alert(`❌ ${data.error || 'Upload failed'}`)
          setKbUploadProgress(null)
          setKbUploading(false)
          setKbStatusMsg('')
        }
      } catch {
        alert('Upload failed — unexpected response')
        setKbUploadProgress(null)
        setKbUploading(false)
        setKbStatusMsg('')
      }
    }

    xhr.onerror = () => {
      alert('Upload failed — is Flask running?')
      setKbUploadProgress(null)
      setKbUploading(false)
      setKbStatusMsg('')
    }

    xhr.open('POST', `${BACKEND}/api/ai/kb/${businessId}`)
    xhr.send(fd)
  }

  const deleteKb = async (businessId: string) => {
    if (!confirm('Delete the entire knowledge base for this bot?')) return
    await fetch(`${BACKEND}/api/ai/kb/${businessId}`, { method: 'DELETE' })
    setKbInfo({ exists: false, chunks: 0 })
  }
  // ─────────────────────────────────────────────────────────

  // ── Edit helpers ────────────────────────────────────────────
  const openEditModal = (bot: BotData) => {
    setEditBot(bot)
    setKbInfo(null)
    if (bot.botType === 'ai') {
      fetchKbInfo(bot.businessId)
    }
    setEditDraft({
      botName: bot.botName || '',
      businessName: bot.businessName || '',
      useCaseType: bot.useCaseType || '',
      category: bot.category || '',
      city: bot.city || '',
      country: bot.country || '',
      defaultLanguage: bot.defaultLanguage || '',
      businessHours: bot.businessHours || '',
      autoReply: bot.autoReply ?? false,
      humanHandoff: bot.humanHandoff ?? false,
      welcomeMessage: bot.welcomeMessage || '',
      fallbackMessage: bot.fallbackMessage || '',
      humanHandoffMessage: bot.humanHandoffMessage || '',
      maxBookingsPerSlot: bot.maxBookingsPerSlot ?? 10,
      // AI fields
      botType: bot.botType ?? 'normal',
      aiModel: bot.aiModel ?? 'llama3.2',
      aiSystemPrompt: bot.aiSystemPrompt ?? '',
      aiRagEnabled: bot.aiRagEnabled ?? false,
    })
    const kw = bot.keywordResponses ?? {}
    setEditKeywords(
      Object.keys(kw).length
        ? Object.entries(kw).map(([keyword, response]) => ({ keyword, response: response as string }))
        : [{ keyword: '', response: '' }]
    )
    setEditMandiList(bot.mandis?.length ? bot.mandis : [{ name: '', location: '', address: '' }])
    setEditSlotTimes(bot.slots?.length ? bot.slots : ['9:00 AM – 10:00 AM'])
    setEditMaxPerSlot(bot.maxBookingsPerSlot ?? 10)
    // IVR nodes
    setEditIvrNodes(
      bot.ivrNodes?.length
        ? bot.ivrNodes
        : [{ id: 'node_root', message: '', options: [], isEndNode: false }]
    )
  }

  const saveEdit = async () => {
    if (!editBot) return
    setEditSaving(true)
    try {
      const keywordResponses = editKeywords.reduce((acc: Record<string, string>, { keyword, response }) => {
        if (keyword.trim()) acc[keyword.trim().toLowerCase()] = response.trim()
        return acc
      }, {})
      const body: Record<string, unknown> = {
        businessId: editBot.businessId,
        ...editDraft,
        keywordResponses,
        ...(editDraft.useCaseType === 'mandi_booking' && {
          mandis: editMandiList.filter(m => m.name.trim()),
          slots: editSlotTimes.filter(s => s.trim()),
          maxBookingsPerSlot: editMaxPerSlot,
        }),
        ...(editDraft.useCaseType === 'ivr' && {
          ivrNodes: editIvrNodes.filter(n => n.message.trim()),
        }),
      }
      const res = await fetch('/api/bot', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })
      if (res.ok) {
        const data = await res.json()
        setBots(prev => prev.map(b => b.businessId === editBot.businessId ? { ...b, ...data.bot } : b))
        setEditBot(null)
      } else {
        const data = await res.json()
        alert(data.message || 'Failed to save changes')
      }
    } catch {
      alert('Failed to connect to server')
    } finally {
      setEditSaving(false)
    }
  }
  // ────────────────────────────────────────────────────────────

  const fetchBots = async () => {
    try {
      const response = await fetch('/api/bot')
      if (response.ok) {
        const data = await response.json()
        setBots(data.bots)
        
        // Calculate stats
        const totalBots = data.bots.length
        const activeBots = data.bots.filter((bot: BotData) => bot.verificationStatus === 'verified').length
        const totalMessages = data.bots.reduce(
          (sum: number, bot: BotData) => sum + (bot.totalMessages ?? bot.messageBalance ?? 0),
          0
        )
        
        // Show page immediately with bot data
        setLoading(false)
        setStats(prev => ({
          ...prev,
          totalBots,
          activeBots,
          totalMessages,
          totalRevenue: totalBots * 99,
        }))

        // Fetch conversations (all in parallel) + payments simultaneously
        const [convResults, paymentData] = await Promise.all([
          Promise.all(
            data.bots.map((bot: BotData) =>
              fetch(`/api/conversations?businessId=${bot.businessId}`)
                .then(r => r.ok ? r.json() : { count: 0 })
                .catch(() => ({ count: 0 }))
            )
          ),
          fetch('/api/payments')
            .then(r => r.ok ? r.json() : { totalDue: 0, totalCompleted: 0 })
            .catch(() => ({ totalDue: 0, totalCompleted: 0 }))
        ])

        const totalConversations = (convResults as { count?: number }[]).reduce(
          (sum, d) => sum + (d.count || 0), 0
        )

        setStats({
          totalBots,
          activeBots,
          totalMessages,
          totalRevenue: totalBots * 99,
          totalConversations,
          paymentDue: paymentData.totalDue || 0,
          paymentCompleted: paymentData.totalCompleted || 0,
        })
      }
    } catch (error) {
      console.error('Error fetching bots:', error)
    } finally {
      setLoading(false)
    }
  }

  const activateBot = async (bot: BotData) => {
    setActivatingBotId(bot.businessId)
    try {
      const res = await fetch('/api/bot/activate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ businessId: bot.businessId, userId: user?.id })
      })
      const data = await res.json()
      if (res.ok) {
        setBots(prev => prev.map(b =>
          b.businessId === bot.businessId
            ? { ...b, verificationStatus: 'verified', allocatedNumber: data.allocatedNumber }
            : b
        ))
        setStats(prev => ({ ...prev, activeBots: prev.activeBots + 1 }))
        setActivationModal({
          botName: bot.botName,
          allocatedNumber: data.allocatedNumber,
          webhookUrl: data.webhookUrl || ''
        })
      } else {
        alert(data.error || 'Failed to activate bot')
      }
    } catch {
      alert('Failed to connect to backend. Is the Python server running?')
    } finally {
      setActivatingBotId(null)
    }
  }

  const deactivateBot = async (bot: BotData) => {
    if (!confirm(`Deactivate "${bot.botName}"? It will stop receiving messages.`)) return
    setDeactivatingBotId(bot.businessId)
    try {
      const res = await fetch('/api/bot/deactivate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ businessId: bot.businessId, userId: user?.id })
      })
      const data = await res.json()
      if (res.ok) {
        setBots(prev => prev.map(b =>
          b.businessId === bot.businessId
            ? { ...b, verificationStatus: 'inactive', allocatedNumber: undefined }
            : b
        ))
        setStats(prev => ({ ...prev, activeBots: Math.max(0, prev.activeBots - 1) }))
      } else {
        alert(data.error || 'Failed to deactivate bot')
      }
    } catch {
      alert('Failed to connect to backend. Is the Python server running?')
    } finally {
      setDeactivatingBotId(null)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'verified':
        return 'bg-green-500/20 text-green-400 border-green-500/30'
      case 'pending':
        return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      case 'failed':
        return 'bg-red-500/20 text-red-400 border-red-500/30'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  const getPlanColor = (plan: string) => {
    switch (plan) {
      case 'enterprise':
        return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
      case 'pro':
        return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      case 'starter':
        return 'bg-green-500/20 text-green-400 border-green-500/30'
      default:
        return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  if (!isLoaded) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <>
    <div className="min-h-screen bg-black text-white flex overflow-x-hidden">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-black border-r border-white/10 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex flex-col h-full">
          {/* Logo */}
          <div className="flex items-center justify-between h-16 px-6 border-b border-white/10">
            <div className="flex items-center gap-2">
              <Bot className="w-6 h-6" />
              <span className="font-light text-lg">BotSetu</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-white/60 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Navigation */}
          <nav className="flex-1 px-4 py-6 space-y-2">
            <Link
              href="/"
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-white/60 hover:bg-white/5 hover:text-white transition-colors"
            >
              <Home className="w-5 h-5" />
              <span>Home</span>
            </Link>
            <Link
              href="/dashboard"
              className="flex items-center gap-3 px-4 py-3 rounded-lg bg-white/10 text-white transition-colors"
            >
              <Bot className="w-5 h-5" />
              <span>Dashboard</span>
            </Link>
            <Link
              href="/blog"
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-white/60 hover:bg-white/5 hover:text-white transition-colors"
            >
              <BookOpen className="w-5 h-5" />
              <span>How to Use</span>
            </Link>

            <Link
              href="/about"
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-white/60 hover:bg-white/5 hover:text-white transition-colors"
            >
              <Info className="w-5 h-5" />
              <span>About Us</span>
            </Link>
            <Link
              href="/payment"
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-white/60 hover:bg-white/5 hover:text-white transition-colors"
            >
              <CreditCard className="w-5 h-5" />
              <span>Payment</span>
            </Link>
          </nav>

          {/* User Profile */}
          <div className="p-4 border-t border-white/10">
            <div className="flex items-center gap-3 px-4 py-3">
              <UserButton />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{user?.firstName || 'User'}</p>
                <p className="text-xs text-white/60 truncate">{user?.primaryEmailAddress?.emailAddress}</p>
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-screen min-w-0 overflow-x-hidden">
        {/* Header */}
        <div className="border-b border-white/10 bg-black/50 backdrop-blur-sm sticky top-0 z-30">
          <div className="px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setSidebarOpen(true)}
                  className="lg:hidden text-white/60 hover:text-white"
                >
                  <Menu className="w-6 h-6" />
                </button>
                <h1 className="text-xl font-light">Dashboard</h1>
              </div>
              <div className="flex items-center gap-3">
                <Link href="/create">
                  <Button className="bg-white text-black hover:bg-white/90">
                    <Plus className="w-4 h-4 mr-2" />
                    Create New Bot
                  </Button>
                </Link>
                <div className="lg:hidden">
                  <UserButton />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 px-4 sm:px-6 lg:px-8 py-8">
          {/* Stats Grid */}
          <Skeleton name="stats-grid" loading={loading} fixture={
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8 animate-pulse">
              {[1,2,3,4].map(i => (
                <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="h-3 w-20 bg-white/10 rounded" />
                    <div className="h-5 w-5 bg-white/10 rounded" />
                  </div>
                  <div className="h-8 w-16 bg-white/10 rounded mb-3" />
                  <div className="h-3 w-24 bg-white/10 rounded" />
                </div>
              ))}
            </div>
          }>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div className="bg-white/5 border border-white/10 rounded-xl p-6 hover:bg-white/10 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <div className="text-white/60 text-sm">Total Bots</div>
                <Bot className="w-5 h-5 text-blue-400" />
              </div>
              <div className="text-3xl font-light">{stats.totalBots}</div>
              <div className="text-xs text-green-400 mt-2">+{stats.totalBots} this month</div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-6 hover:bg-white/10 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <div className="text-white/60 text-sm">Active Bots</div>
                <TrendingUp className="w-5 h-5 text-green-400" />
              </div>
              <div className="text-3xl font-light">{stats.activeBots}</div>
              <div className="text-xs text-white/60 mt-2">{((stats.activeBots / stats.totalBots) * 100 || 0).toFixed(0)}% verified</div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-6 hover:bg-white/10 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <div className="text-white/60 text-sm">Conversations</div>
                <MessageCircle className="w-5 h-5 text-purple-400" />
              </div>
              <div className="text-3xl font-light">{stats.totalConversations}</div>
              <div className="text-xs text-white/60 mt-2">Across all bots</div>
            </div>

            {/* Credits card */}
            <Link href="/payment">
              <div className={`rounded-xl p-6 transition-colors cursor-pointer h-full ${
                credits !== null && credits <= 20
                  ? 'bg-red-500/10 border border-red-500/30 hover:bg-red-500/20'
                  : 'bg-orange-500/10 border border-orange-500/20 hover:bg-orange-500/15'
              }`}>
                <div className="flex items-center justify-between mb-2">
                  <div className="text-white/60 text-sm">Message Credits</div>
                  <CreditCard className={`w-5 h-5 ${credits !== null && credits <= 20 ? 'text-red-400' : 'text-orange-400'}`} />
                </div>
                <div className={`text-3xl font-light tabular-nums ${credits !== null && credits <= 20 ? 'text-red-400' : 'text-orange-400'}`}>
                  {credits !== null ? credits.toLocaleString() : '—'}
                </div>
                <div className={`text-xs mt-2 ${credits !== null && credits <= 20 ? 'text-red-400' : 'text-orange-400/70'}`}>
                  {credits !== null && credits <= 20 ? '⚠ Low — click to buy more' : 'Click to buy more'}
                </div>
              </div>
            </Link>
          </div>
          </Skeleton>

          {/* Payment Stats Grid */}
          <Skeleton name="payment-stats" loading={loading} fixture={
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8 animate-pulse">
              {[1,2].map(i => (
                <div key={i} className="bg-white/5 border border-white/10 rounded-xl p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="h-3 w-24 bg-white/10 rounded" />
                    <div className="h-5 w-5 bg-white/10 rounded" />
                  </div>
                  <div className="h-8 w-20 bg-white/10 rounded mb-3" />
                  <div className="h-3 w-28 bg-white/10 rounded" />
                </div>
              ))}
            </div>
          }>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-8">
            <div className="bg-white/5 border border-white/10 rounded-xl p-6 hover:bg-white/10 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <div className="text-white/60 text-sm">Payment Due</div>
                <DollarSign className="w-5 h-5 text-red-400" />
              </div>
              <div className="text-3xl font-light">₹{stats.paymentDue.toLocaleString()}</div>
              <div className="text-xs text-red-400 mt-2">Pending payments</div>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-6 hover:bg-white/10 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <div className="text-white/60 text-sm">Payment Completed</div>
                <DollarSign className="w-5 h-5 text-green-400" />
              </div>
              <div className="text-3xl font-light">₹{stats.paymentCompleted.toLocaleString()}</div>
              <div className="text-xs text-green-400 mt-2">Total received</div>
            </div>
          </div>
          </Skeleton>

          {/* Bots List */}
          <Skeleton name="bot-list" loading={loading} fixture={
            <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden animate-pulse">
              <div className="px-6 py-4 border-b border-white/10">
                <div className="h-5 w-24 bg-white/10 rounded" />
              </div>
              <div className="divide-y divide-white/10">
                {[1,2,3].map(i => (
                  <div key={i} className="px-6 py-4 flex items-center gap-6">
                    <div className="h-4 w-28 bg-white/10 rounded" />
                    <div className="h-4 w-24 bg-white/10 rounded" />
                    <div className="h-4 w-16 bg-white/10 rounded" />
                    <div className="h-6 w-14 bg-white/10 rounded-md" />
                    <div className="h-6 w-16 bg-white/10 rounded-md" />
                    <div className="h-4 w-20 bg-white/10 rounded" />
                    <div className="h-4 w-12 bg-white/10 rounded ml-auto" />
                  </div>
                ))}
              </div>
            </div>
          }>
          <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-white/10">
            <h2 className="text-xl font-light">Your Bots</h2>
          </div>

          {bots.length === 0 ? (
            <div className="p-12 text-center">
              <Bot className="w-16 h-16 text-white/20 mx-auto mb-4" />
              <h3 className="text-xl font-light mb-2">No bots yet</h3>
              <p className="text-white/60 mb-6">Create your first bot to get started</p>
              <Link href="/create">
                <Button className="bg-white text-black hover:bg-white/90">
                  <Plus className="w-4 h-4 mr-2" />
                  Create Your First Bot
                </Button>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-white/5 border-b border-white/10">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Bot Name</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Business</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Plan</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Status</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Messages</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Features</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Created</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-white/60 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  {bots.map((bot) => (
                    <tr key={bot._id} className="hover:bg-white/5 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center gap-2">
                          <Bot className="w-4 h-4 text-blue-400" />
                          <span className="font-medium">{bot.botName}</span>
                          {bot.botType === 'ai' && (
                            <span className="text-xs font-medium bg-cyan-500/15 text-cyan-400 border border-cyan-500/30 px-1.5 py-0.5 rounded-full">AI</span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm">{bot.businessName}</div>
                        <div className="text-xs text-white/60">{bot.category}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm capitalize">{bot.useCaseType}</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`px-2 py-1 text-xs rounded-md border capitalize ${getPlanColor(bot.planType)}`}>
                          {bot.planType}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2 py-1 text-xs rounded-md border capitalize ${getStatusColor(bot.verificationStatus)}`}>
                          {bot.verificationStatus}
                        </span>
                        {bot.allocatedNumber && (
                          <div className="flex items-center gap-1.5 mt-1.5">
                            <span className="text-xs font-mono text-green-400">{bot.allocatedNumber}</span>
                            <button
                              onClick={() => copyToClipboard(bot.allocatedNumber!, `num-${bot._id}`)}
                              className="text-white/30 hover:text-white/70 transition-colors"
                              title="Copy number"
                            >
                              {copiedField === `num-${bot._id}` ? <CheckCircle className="w-3 h-3 text-green-400" /> : <Copy className="w-3 h-3" />}
                            </button>
                          </div>
                        )}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm">{bot.totalMessages ?? 0} sent</div>
                        <div className="text-xs text-white/60">Balance: {bot.messageBalance || 0} / {bot.messageLimit || 0}</div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex gap-2">
                          {bot.autoReply && (
                            <span className="px-2 py-1 text-xs rounded-md bg-green-500/20 text-green-400 border border-green-500/30">
                              Auto
                            </span>
                          )}
                          {bot.humanHandoff && (
                            <span className="px-2 py-1 text-xs rounded-md bg-blue-500/20 text-blue-400 border border-blue-500/30">
                              Human
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-white/60">
                        {new Date(bot.createdAt).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex gap-2">
                          {bot.verificationStatus === 'verified' ? (
                            <Button
                              size="sm"
                              onClick={() => deactivateBot(bot)}
                              disabled={deactivatingBotId === bot.businessId}
                              className="bg-yellow-600 hover:bg-yellow-500 text-white text-xs px-3 h-7"
                            >
                              <Zap className="w-3 h-3 mr-1" />
                              {deactivatingBotId === bot.businessId ? 'Deactivating…' : 'Deactivate'}
                            </Button>
                          ) : (
                            <Button
                              size="sm"
                              onClick={() => activateBot(bot)}
                              disabled={activatingBotId === bot.businessId}
                              className="bg-green-600 hover:bg-green-500 text-white text-xs px-3 h-7"
                            >
                              <Zap className="w-3 h-3 mr-1" />
                              {activatingBotId === bot.businessId ? 'Activating…' : 'Activate'}
                            </Button>
                          )}
                          <Link href={`/chats/${bot.businessId}`}>
                            <Button variant="ghost" size="sm" className="text-white/60 hover:text-white" title="View Chats">
                              <MessageCircle className="w-4 h-4" />
                            </Button>
                          </Link>
                          {bot.useCaseType === 'mandi_booking' && (
                            <Link href={`/dashboard/bookings?businessId=${bot.businessId}`}>
                              <Button variant="ghost" size="sm" className="text-yellow-400/60 hover:text-yellow-400" title="View Mandi Bookings">
                                <BookOpen className="w-4 h-4" />
                              </Button>
                            </Link>
                          )}
                          {bot.useCaseType === 'ivr' && (
                            <Button
                              variant="ghost"
                              size="sm"
                              title="IVR Call Info"
                              className="text-orange-400/60 hover:text-orange-400"
                              onClick={async () => {
                                const res = await fetch(`${BACKEND}/api/bot/ivr-number`).catch(() => null)
                                const data = res?.ok ? await res.json() : {}
                                setIvrModal({
                                  botName: bot.botName,
                                  phone: data.phoneNumber || 'N/A',
                                  voiceWebhookUrl: data.voiceWebhookUrl || '',
                                })
                              }}
                            >
                              <Phone className="w-4 h-4" />
                            </Button>
                          )}
                          {sandboxInfo?.joinText && (
                            <a
                              href={`https://wa.me/${sandboxInfo.whatsappNumber}?text=${encodeURIComponent(sandboxInfo.joinText)}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              title={`Open WhatsApp & send "${sandboxInfo.joinText}"`}
                            >
                              <Button variant="ghost" size="sm" className="text-green-400/60 hover:text-green-400">
                                <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current" xmlns="http://www.w3.org/2000/svg">
                                  <path d="M17.472 14.382c-.297-.149-1.758-.867-2.03-.967-.273-.099-.471-.148-.67.15-.197.297-.767.966-.94 1.164-.173.199-.347.223-.644.075-.297-.15-1.255-.463-2.39-1.475-.883-.788-1.48-1.761-1.653-2.059-.173-.297-.018-.458.13-.606.134-.133.298-.347.446-.52.149-.174.198-.298.298-.497.099-.198.05-.371-.025-.52-.075-.149-.669-1.612-.916-2.207-.242-.579-.487-.5-.669-.51-.173-.008-.371-.01-.57-.01-.198 0-.52.074-.792.372-.272.297-1.04 1.016-1.04 2.479 0 1.462 1.065 2.875 1.213 3.074.149.198 2.096 3.2 5.077 4.487.709.306 1.262.489 1.694.625.712.227 1.36.195 1.871.118.571-.085 1.758-.719 2.006-1.413.248-.694.248-1.289.173-1.413-.074-.124-.272-.198-.57-.347m-5.421 7.403h-.004a9.87 9.87 0 01-5.031-1.378l-.361-.214-3.741.982.998-3.648-.235-.374a9.86 9.86 0 01-1.51-5.26c.001-5.45 4.436-9.884 9.888-9.884 2.64 0 5.122 1.03 6.988 2.898a9.825 9.825 0 012.893 6.994c-.003 5.45-4.437 9.884-9.885 9.884m8.413-18.297A11.815 11.815 0 0012.05 0C5.495 0 .16 5.335.157 11.892c0 2.096.547 4.142 1.588 5.945L.057 24l6.305-1.654a11.882 11.882 0 005.683 1.448h.005c6.554 0 11.89-5.335 11.893-11.893a11.821 11.821 0 00-3.48-8.413z"/>
                                </svg>
                              </Button>
                            </a>
                          )}
                          <Button variant="ghost" size="sm" onClick={() => openEditModal(bot)} className="text-white/60 hover:text-white" title="Edit Bot">
                            <Settings className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white" title="Analytics">
                            <BarChart3 className="w-4 h-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => setConfirmDeleteBot(bot)}
                            disabled={deletingBotId === bot.businessId}
                            className="text-red-400/50 hover:text-red-400 hover:bg-red-500/10"
                            title="Delete Bot"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
        </Skeleton>
        </div>
      </div>
    </div>

    {/* ── Edit Bot Modal ── */}
    {editBot && (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
        <div className="bg-zinc-900 border border-white/20 rounded-2xl w-full max-w-2xl shadow-[0_0_60px_rgba(255,255,255,0.07)] my-4">
          {/* Header */}
          <div className="flex items-center justify-between px-8 py-5 border-b border-white/10">
            <div>
              <h2 className="text-xl font-light text-white">Edit Bot</h2>
              <p className="text-xs text-white/40 mt-0.5">{editBot.botName}</p>
            </div>
            <button onClick={() => setEditBot(null)} className="text-white/40 hover:text-white transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="px-8 py-6 space-y-6 max-h-[75vh] overflow-y-auto">

            {/* Basic Info */}
            <div>
              <h3 className="text-xs uppercase tracking-wider text-white/40 mb-3">Basic Info</h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {([
                  ['botName', 'Bot Name *'],
                  ['businessName', 'Business Name'],
                  ['city', 'City'],
                  ['country', 'Country'],
                  ['defaultLanguage', 'Language'],
                  ['businessHours', 'Business Hours'],
                ] as [string, string][]).map(([field, label]) => (
                  <div key={field}>
                    <label className="block text-xs text-white/50 mb-1.5">{label}</label>
                    <input
                      type="text"
                      value={String(editDraft[field] ?? '')}
                      onChange={e => setEditDraft(prev => ({ ...prev, [field]: e.target.value }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30"
                    />
                  </div>
                ))}
                <div>
                  <label className="block text-xs text-white/50 mb-1.5">Use-case Type</label>
                  <select
                    value={String(editDraft.useCaseType ?? '')}
                    onChange={e => setEditDraft(prev => ({ ...prev, useCaseType: e.target.value }))}
                    className="w-full bg-zinc-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30"
                  >
                    <option value="booking">Booking</option>
                    <option value="faq">FAQ</option>
                    <option value="orders">Orders</option>
                    <option value="leads">Leads</option>
                    <option value="mandi_booking">🌾 Mandi Booking</option>
                    <option value="ivr">📞 IVR Menu</option>
                  </select>
                </div>
              </div>
            </div>

            {/* Toggles */}
            <div>
              <h3 className="text-xs uppercase tracking-wider text-white/40 mb-3">Behaviour</h3>
              <div className="flex gap-4">
                {(['autoReply', 'humanHandoff'] as const).map(field => (
                  <label key={field} className="flex items-center gap-2 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={Boolean(editDraft[field])}
                      onChange={e => setEditDraft(prev => ({ ...prev, [field]: e.target.checked }))}
                      className="w-4 h-4 accent-white"
                    />
                    <span className="text-sm text-white/70">{field === 'autoReply' ? 'Auto Reply' : 'Human Handoff'}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Auto-reply messages */}
            {Boolean(editDraft.autoReply) && (
              <div className="space-y-3 p-4 bg-green-500/5 border border-green-500/20 rounded-xl">
                <h3 className="text-xs font-medium text-green-400">🤖 Auto-Reply Messages</h3>
                {([
                  ['welcomeMessage', 'Welcome Message', 'Sent on hi/hello'],
                  ['fallbackMessage', 'Fallback Message', 'Sent when no keyword matches'],
                ] as [string, string, string][]).map(([field, label, hint]) => (
                  <div key={field}>
                    <label className="block text-xs text-white/50 mb-1">{label}</label>
                    <textarea
                      rows={2}
                      value={String(editDraft[field] ?? '')}
                      onChange={e => setEditDraft(prev => ({ ...prev, [field]: e.target.value }))}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30 resize-none"
                    />
                    <p className="text-xs text-white/30 mt-0.5">{hint}</p>
                  </div>
                ))}
              </div>
            )}

            {Boolean(editDraft.humanHandoff) && (
              <div className="p-4 bg-blue-500/5 border border-blue-500/20 rounded-xl">
                <label className="block text-xs text-blue-400 mb-2">👤 Human Handoff Message</label>
                <textarea
                  rows={2}
                  value={String(editDraft.humanHandoffMessage ?? '')}
                  onChange={e => setEditDraft(prev => ({ ...prev, humanHandoffMessage: e.target.value }))}
                  className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30 resize-none"
                />
              </div>
            )}

            {/* Keyword Responses — Normal bots only */}
            {editDraft.useCaseType !== 'mandi_booking' && editDraft.botType !== 'ai' && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-xs uppercase tracking-wider text-white/40">🔑 Keyword Responses</h3>
                  <button
                    type="button"
                    onClick={() => setEditKeywords(prev => [...prev, { keyword: '', response: '' }])}
                    className="text-xs text-white/50 hover:text-white border border-white/20 px-2 py-0.5 rounded transition-colors"
                  >+ Add</button>
                </div>
                <div className="space-y-2">
                  {editKeywords.map((pair, i) => (
                    <div key={i} className="flex gap-2 items-center">
                      <input
                        type="text"
                        value={pair.keyword}
                        onChange={e => setEditKeywords(prev => prev.map((p, idx) => idx === i ? { ...p, keyword: e.target.value } : p))}
                        placeholder="Keyword"
                        className="w-1/3 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white text-xs focus:outline-none focus:border-white/30"
                      />
                      <input
                        type="text"
                        value={pair.response}
                        onChange={e => setEditKeywords(prev => prev.map((p, idx) => idx === i ? { ...p, response: e.target.value } : p))}
                        placeholder="Reply"
                        className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white text-xs focus:outline-none focus:border-white/30"
                      />
                      {editKeywords.length > 1 && (
                        <button
                          type="button"
                          onClick={() => setEditKeywords(prev => prev.filter((_, idx) => idx !== i))}
                          className="text-red-400/60 hover:text-red-400 px-1.5 text-base transition-colors">×</button>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* ── AI Bot Config ──────────────────────────────────── */}
            {editDraft.botType === 'ai' && (
              <div className="space-y-4 p-4 bg-cyan-500/5 border border-cyan-500/20 rounded-xl">
                <h3 className="text-xs font-medium text-cyan-400">🧠 AI Bot Configuration</h3>

                {/* Model */}
                <div>
                  <label className="block text-xs text-white/50 mb-1.5">AI Model</label>
                  <select
                    value={String(editDraft.aiModel ?? 'gemini-2.0-flash')}
                    onChange={e => setEditDraft(prev => ({ ...prev, aiModel: e.target.value }))}
                    className="w-full bg-zinc-800 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30"
                  >
                    <optgroup label="Gemini (Cloud)">
                      <option value="gemini-2.0-flash">gemini-2.0-flash (recommended)</option>
                      <option value="gemini-1.5-flash">gemini-1.5-flash</option>
                      <option value="gemini-1.5-pro">gemini-1.5-pro</option>
                    </optgroup>
                    {ollamaModels.length > 0 && (
                      <optgroup label="Local (Ollama)">
                        {ollamaModels.map(m => <option key={m} value={m}>{m}</option>)}
                      </optgroup>
                    )}
                  </select>
                </div>

                {/* System Prompt */}
                <div>
                  <label className="block text-xs text-white/50 mb-1.5">System Prompt</label>
                  <textarea
                    rows={4}
                    value={String(editDraft.aiSystemPrompt ?? '')}
                    onChange={e => setEditDraft(prev => ({ ...prev, aiSystemPrompt: e.target.value }))}
                    placeholder="Describe the AI's personality and role..."
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30 resize-none"
                  />
                </div>

                {/* RAG toggle */}
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={Boolean(editDraft.aiRagEnabled)}
                    onChange={e => {
                      setEditDraft(prev => ({ ...prev, aiRagEnabled: e.target.checked }))
                      if (e.target.checked && editBot) fetchKbInfo(editBot.businessId)
                    }}
                    className="w-4 h-4 accent-purple-400"
                  />
                  <span className="text-sm text-purple-300">Enable RAG (Knowledge Base)</span>
                </label>

                {/* Knowledge Base Manager */}
                {Boolean(editDraft.aiRagEnabled) && editBot && (
                  <div className="p-3 bg-purple-500/5 border border-purple-500/20 rounded-lg space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-purple-300 font-medium">📚 Knowledge Base</span>
                      {kbInfo && (
                        <span className="text-xs text-white/40">
                          {kbInfo.exists ? `${kbInfo.chunks} chunks indexed` : 'No documents yet'}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-white/40">Upload TXT, JSON, or CSV files. Each upload appends to the existing knowledge base.</p>

                    {/* Progress bar */}
                    {kbUploading && (
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs text-white/40">
                          <span>{kbStatusMsg || 'Processing…'}</span>
                          {kbUploadProgress !== null && <span>{kbUploadProgress}%</span>}
                        </div>
                        <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                          <div
                            className="h-full bg-purple-500 rounded-full transition-all duration-300"
                            style={{ width: `${kbUploadProgress ?? 0}%` }}
                          />
                        </div>
                      </div>
                    )}

                    <div className="flex gap-2">
                      <label className="flex-1 cursor-pointer">
                        <div className={`border rounded-lg px-3 py-2 text-xs text-center transition-colors ${
                          kbUploading
                            ? 'bg-white/5 border-purple-500/30 text-purple-400/50 cursor-wait'
                            : 'bg-white/5 border-white/10 hover:border-white/30 text-white/60 hover:text-white'
                        }`}>
                          {kbUploading ? (kbStatusMsg || 'Processing…') : '⬆ Upload File (.txt / .json / .csv)'}
                        </div>
                        <input
                          type="file"
                          accept=".txt,.json,.csv,.md"
                          className="hidden"
                          disabled={kbUploading}
                          onChange={e => {
                            const f = e.target.files?.[0]
                            if (f) uploadKbFile(editBot.businessId, f)
                            e.target.value = ''
                          }}
                        />
                      </label>
                      {kbInfo?.exists && (
                        <button
                          type="button"
                          onClick={() => deleteKb(editBot.businessId)}
                          className="text-xs text-red-400/60 hover:text-red-400 border border-red-500/20 px-3 py-2 rounded-lg transition-colors"
                        >
                          🗑 Clear KB
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}
            {/* ──────────────────────────────────────────────────── */}

            {/* Mandi Config — Normal bots only */}
            {editDraft.useCaseType === 'mandi_booking' && editDraft.botType !== 'ai' && (
              <div className="space-y-4 p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-xl">
                <h3 className="text-xs font-medium text-yellow-400">🌾 Mandi Booking Config</h3>

                {/* Mandis */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs text-white/50">Mandis</label>
                    <button type="button"
                      onClick={() => setEditMandiList(prev => [...prev, { name: '', location: '', address: '' }])}
                      className="text-xs text-yellow-400/70 hover:text-yellow-400 border border-yellow-500/20 px-2 py-0.5 rounded transition-colors">+ Add</button>
                  </div>
                  {editMandiList.map((m, i) => (
                    <div key={i} className="grid grid-cols-3 gap-2 mb-2 items-center">
                      <input type="text" value={m.name} placeholder="Name *"
                        onChange={e => setEditMandiList(prev => prev.map((x, idx) => idx === i ? { ...x, name: e.target.value } : x))}
                        className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-white text-xs focus:outline-none focus:border-white/30" />
                      <input type="text" value={m.location} placeholder="Location"
                        onChange={e => setEditMandiList(prev => prev.map((x, idx) => idx === i ? { ...x, location: e.target.value } : x))}
                        className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-white text-xs focus:outline-none focus:border-white/30" />
                      <div className="flex gap-1 items-center">
                        <input type="text" value={m.address} placeholder="Address"
                          onChange={e => setEditMandiList(prev => prev.map((x, idx) => idx === i ? { ...x, address: e.target.value } : x))}
                          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-white text-xs focus:outline-none focus:border-white/30" />
                        {editMandiList.length > 1 && (
                          <button type="button" onClick={() => setEditMandiList(prev => prev.filter((_, idx) => idx !== i))}
                            className="text-red-400/60 hover:text-red-400 text-base leading-none transition-colors">×</button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Slots */}
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="text-xs text-white/50">Time Slots</label>
                    <button type="button" onClick={() => setEditSlotTimes(prev => [...prev, ''])}
                      className="text-xs text-yellow-400/70 hover:text-yellow-400 border border-yellow-500/20 px-2 py-0.5 rounded transition-colors">+ Add</button>
                  </div>
                  <div className="grid grid-cols-2 gap-2">
                    {editSlotTimes.map((s, i) => (
                      <div key={i} className="flex gap-1 items-center">
                        <input type="text" value={s} placeholder="e.g. 9:00 AM – 10:00 AM"
                          onChange={e => setEditSlotTimes(prev => prev.map((x, idx) => idx === i ? e.target.value : x))}
                          className="flex-1 bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-white text-xs focus:outline-none focus:border-white/30" />
                        {editSlotTimes.length > 1 && (
                          <button type="button" onClick={() => setEditSlotTimes(prev => prev.filter((_, idx) => idx !== i))}
                            className="text-red-400/60 hover:text-red-400 text-base leading-none transition-colors">×</button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Max per slot */}
                <div>
                  <label className="block text-xs text-white/50 mb-1.5">Max Bookings per Slot</label>
                  <input type="number" min={1} max={500} value={editMaxPerSlot}
                    onChange={e => setEditMaxPerSlot(Number(e.target.value))}
                    className="w-24 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white text-sm focus:outline-none focus:border-white/30" />
                </div>
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="flex gap-3 px-8 py-5 border-t border-white/10">
            <button
              onClick={() => setEditBot(null)}
              className="flex-1 border border-white/20 hover:border-white/40 text-white/70 hover:text-white py-2.5 rounded-xl text-sm transition-colors"
            >Cancel</button>
            <button
              onClick={saveEdit}
              disabled={editSaving}
              className="flex-1 bg-white text-black hover:bg-white/90 disabled:opacity-50 py-2.5 rounded-xl text-sm font-medium transition-colors"
            >{editSaving ? 'Saving…' : 'Save Changes'}</button>
          </div>
        </div>
      </div>
    )}

    {/* ── Confirm Delete Modal ── */}
    {confirmDeleteBot && (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-100 flex items-center justify-center p-4">
        <div className="bg-zinc-900 border border-white/20 rounded-2xl p-8 max-w-sm w-full shadow-[0_0_60px_rgba(239,68,68,0.1)]">
          <div className="w-14 h-14 bg-red-500/10 rounded-full flex items-center justify-center mx-auto mb-4">
            <Trash2 className="w-6 h-6 text-red-400" />
          </div>
          <h2 className="text-xl font-light text-white text-center mb-2">Delete Bot?</h2>
          <p className="text-white/50 text-sm text-center mb-1">
            <span className="text-white font-medium">{confirmDeleteBot.botName}</span>
          </p>
          <p className="text-white/40 text-xs text-center mb-6">
            This will permanently delete the bot and all its conversations. This cannot be undone.
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => setConfirmDeleteBot(null)}
              className="flex-1 border border-white/20 hover:border-white/40 text-white/70 hover:text-white py-2.5 rounded-xl text-sm transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={() => deleteBot(confirmDeleteBot)}
              className="flex-1 bg-red-500 hover:bg-red-600 text-white py-2.5 rounded-xl text-sm font-medium transition-colors"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    )}

    {/* ── IVR Call Info Modal ── */}
    {ivrModal && (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-100 flex items-center justify-center p-4">
        <div className="bg-zinc-900 border border-white/20 rounded-2xl p-8 max-w-lg w-full shadow-[0_0_60px_rgba(249,115,22,0.15)]">
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-orange-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <Phone className="w-8 h-8 text-orange-400" />
            </div>
            <h2 className="text-2xl font-light text-white mb-1">IVR Call Bot Active</h2>
            <p className="text-white/50 text-sm">{ivrModal.botName}</p>
          </div>

          <div className="mb-4 p-4 bg-orange-500/5 border border-orange-500/20 rounded-xl">
            <p className="text-xs text-white/40 mb-2 uppercase tracking-wider">Twilio Phone Number</p>
            <div className="flex items-center justify-between gap-3">
              <p className="text-xl font-mono text-orange-400 font-semibold">{ivrModal.phone}</p>
              <button
                onClick={() => copyToClipboard(ivrModal.phone, 'ivr-phone')}
                className="flex items-center gap-1.5 text-xs text-white/60 hover:text-white border border-white/10 hover:border-white/30 px-3 py-1.5 rounded-lg transition-colors"
              >
                {copiedField === 'ivr-phone'
                  ? <><CheckCircle className="w-3.5 h-3.5 text-green-400" /> Copied!</>
                  : <><Copy className="w-3.5 h-3.5" /> Copy</>}
              </button>
            </div>
            <p className="text-xs text-white/40 mt-2">Call this number from any phone to interact with your IVR bot</p>
          </div>

          {ivrModal.voiceWebhookUrl && (
            <div className="mb-4 p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-xl">
              <p className="text-xs text-yellow-400/80 mb-2 uppercase tracking-wider">⚡ Twilio Voice Webhook URL</p>
              <div className="flex items-start justify-between gap-3 mb-2">
                <p className="text-xs font-mono text-white/80 break-all leading-relaxed">{ivrModal.voiceWebhookUrl}</p>
                <button
                  onClick={() => copyToClipboard(ivrModal.voiceWebhookUrl, 'ivr-webhook')}
                  className="shrink-0 flex items-center gap-1.5 text-xs text-white/60 hover:text-white border border-white/10 hover:border-white/30 px-3 py-1.5 rounded-lg transition-colors"
                >
                  {copiedField === 'ivr-webhook'
                    ? <><CheckCircle className="w-3.5 h-3.5 text-green-400" /> Copied!</>
                    : <><Copy className="w-3.5 h-3.5" /> Copy</>}
                </button>
              </div>
              <p className="text-xs text-white/40">Paste this in Twilio Console → Phone Numbers → Configure → &quot;A call comes in&quot;</p>
            </div>
          )}

          <div className="mb-6 p-4 bg-white/5 border border-white/10 rounded-xl">
            <p className="text-xs text-white/60 font-medium mb-2">📞 How to test:</p>
            <ol className="text-xs text-white/40 space-y-1 list-decimal list-inside">
              <li>Set the voice webhook URL in Twilio Console → Phone Numbers</li>
              <li>Call the Twilio number from any phone</li>
              <li>Navigate the menu using your keypad (DTMF tones)</li>
            </ol>
          </div>

          <button
            onClick={() => setIvrModal(null)}
            className="w-full bg-white text-black hover:bg-white/90 py-3 rounded-xl font-medium transition-colors"
          >
            Got it!
          </button>
        </div>
      </div>
    )}

    {/* ── Activation Success Modal ── */}
    {activationModal && (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-100 flex items-center justify-center p-4">
        <div className="bg-zinc-900 border border-white/20 rounded-2xl p-8 max-w-lg w-full shadow-[0_0_60px_rgba(34,197,94,0.15)]">
          {/* Header */}
          <div className="text-center mb-6">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <CheckCircle className="w-8 h-8 text-green-400" />
            </div>
            <h2 className="text-2xl font-light text-white mb-1">Bot Activated!</h2>
            <p className="text-white/50 text-sm">{activationModal.botName} is now live on WhatsApp</p>
          </div>

          {/* WhatsApp Number */}
          <div className="mb-4 p-4 bg-green-500/5 border border-green-500/20 rounded-xl">
            <p className="text-xs text-white/40 mb-2 uppercase tracking-wider">Your WhatsApp Bot Number</p>
            <div className="flex items-center justify-between gap-3">
              <p className="text-xl font-mono text-green-400 font-semibold">{activationModal.allocatedNumber}</p>
              <button
                onClick={() => copyToClipboard(activationModal.allocatedNumber, 'modal-number')}
                className="flex items-center gap-1.5 text-xs text-white/60 hover:text-white border border-white/10 hover:border-white/30 px-3 py-1.5 rounded-lg transition-colors"
              >
                {copiedField === 'modal-number'
                  ? <><CheckCircle className="w-3.5 h-3.5 text-green-400" /> Copied!</>
                  : <><Copy className="w-3.5 h-3.5" /> Copy</>}
              </button>
            </div>
            <p className="text-xs text-white/40 mt-2">Users send a WhatsApp message to this number to talk to your bot</p>
          </div>

          {/* Webhook URL */}
          {activationModal.webhookUrl ? (
            <div className="mb-4 p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-xl">
              <p className="text-xs text-yellow-400/80 mb-2 uppercase tracking-wider">⚡ Twilio Webhook URL</p>
              <div className="flex items-start justify-between gap-3 mb-2">
                <p className="text-xs font-mono text-white/80 break-all leading-relaxed">{activationModal.webhookUrl}</p>
                <button
                  onClick={() => copyToClipboard(activationModal.webhookUrl, 'modal-webhook')}
                  className="shrink-0 flex items-center gap-1.5 text-xs text-white/60 hover:text-white border border-white/10 hover:border-white/30 px-3 py-1.5 rounded-lg transition-colors"
                >
                  {copiedField === 'modal-webhook'
                    ? <><CheckCircle className="w-3.5 h-3.5 text-green-400" /> Copied!</>
                    : <><Copy className="w-3.5 h-3.5" /> Copy</>}
                </button>
              </div>
              <p className="text-xs text-white/40 mb-2">Paste this in Twilio Console → Messaging → Sandbox Settings → &quot;When a message comes in&quot;</p>
              <a
                href="https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                Open Twilio Console <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          ) : (
            <div className="mb-4 p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-xl">
              <p className="text-xs text-yellow-400/80 mb-1 uppercase tracking-wider">⚡ Set Twilio Webhook</p>
              <p className="text-xs text-white/50 mb-2">Run <code className="bg-white/10 px-1 rounded">python setup_webhook.py</code> in your Backend folder to auto-set the webhook, or manually set your ngrok URL in Twilio Console.</p>
              <a
                href="https://console.twilio.com/us1/develop/sms/try-it-out/whatsapp-learn"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                Open Twilio Console <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}

          {/* Test steps */}
          <div className="mb-6 p-4 bg-white/5 border border-white/10 rounded-xl">
            <p className="text-xs text-white/60 font-medium mb-2">📱 How to test:</p>
            <ol className="text-xs text-white/40 space-y-1 list-decimal list-inside">
              <li>Save the bot number in your phone contacts</li>
              <li>Open WhatsApp and send <span className="text-white/60 font-mono">join &lt;sandbox-code&gt;</span> (first time only)</li>
              <li>Send any message and your bot auto-replies instantly!</li>
            </ol>
          </div>

          <button
            onClick={() => setActivationModal(null)}
            className="w-full bg-white text-black hover:bg-white/90 py-3 rounded-xl font-medium transition-colors"
          >
            Got it!
          </button>
        </div>
      </div>
    )}
    </>
  )
}
