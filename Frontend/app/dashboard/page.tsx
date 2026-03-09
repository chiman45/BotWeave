'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useUser, UserButton } from '@clerk/nextjs'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Plus, Bot, TrendingUp, MessageSquare, Users, DollarSign, Settings, BarChart3, Home, CreditCard, Info, Tag, Menu, X, MessageCircle, BookOpen, Zap, Copy, CheckCircle, ExternalLink } from 'lucide-react'

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
  createdAt: string
  allocatedNumber?: string
}

export default function DashboardPage() {
  const router = useRouter()
  const { user, isLoaded } = useUser()
  const [bots, setBots] = useState<BotData[]>([])
  const [loading, setLoading] = useState(true)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [activatingBotId, setActivatingBotId] = useState<string | null>(null)
  const [activationModal, setActivationModal] = useState<{
    botName: string
    allocatedNumber: string
    webhookUrl: string
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

  useEffect(() => {
    if (isLoaded && !user) {
      router.push('/')
      return
    }

    if (user) {
      fetchBots()
    }
  }, [isLoaded, user, router])

  const copyToClipboard = (text: string, field: string) => {
    navigator.clipboard.writeText(text)
    setCopiedField(field)
    setTimeout(() => setCopiedField(null), 2000)
  }

  const fetchBots = async () => {
    try {
      const response = await fetch('/api/bot')
      if (response.ok) {
        const data = await response.json()
        setBots(data.bots)
        
        // Calculate stats
        const totalBots = data.bots.length
        const activeBots = data.bots.filter((bot: BotData) => bot.verificationStatus === 'verified').length
        const totalMessages = data.bots.reduce((sum: number, bot: BotData) => sum + (bot.messageBalance || 0), 0)
        
        // Fetch total conversations across all bots
        let totalConversations = 0
        for (const bot of data.bots) {
          try {
            const convResponse = await fetch(`/api/conversations?businessId=${bot.businessId}`)
            if (convResponse.ok) {
              const convData = await convResponse.json()
              totalConversations += convData.count || 0
            }
          } catch (err) {
            // Skip if conversations not available
          }
        }
        
        // Fetch payment stats
        let paymentDue = 0
        let paymentCompleted = 0
        try {
          const paymentResponse = await fetch('/api/payments')
          if (paymentResponse.ok) {
            const paymentData = await paymentResponse.json()
            paymentDue = paymentData.totalDue || 0
            paymentCompleted = paymentData.totalCompleted || 0
          }
        } catch (err) {
          // Use default values if payment API not available
        }
        
        setStats({
          totalBots,
          activeBots,
          totalMessages,
          totalRevenue: totalBots * 99, // Mock calculation
          totalConversations,
          paymentDue,
          paymentCompleted
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

  if (!isLoaded || loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <>
    <div className="min-h-screen bg-black text-white flex">
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
              href="/pricing"
              className="flex items-center gap-3 px-4 py-3 rounded-lg text-white/60 hover:bg-white/5 hover:text-white transition-colors"
            >
              <Tag className="w-5 h-5" />
              <span>Pricing</span>
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
      <div className="flex-1 flex flex-col min-h-screen">
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
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
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

            <div className="bg-white/5 border border-white/10 rounded-xl p-6 hover:bg-white/10 transition-colors">
              <div className="flex items-center justify-between mb-2">
                <div className="text-white/60 text-sm">Total Messages</div>
                <MessageSquare className="w-5 h-5 text-cyan-400" />
              </div>
              <div className="text-3xl font-light">{stats.totalMessages.toLocaleString()}</div>
              <div className="text-xs text-white/60 mt-2">Message balance</div>
            </div>
          </div>

          {/* Payment Stats Grid */}
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

          {/* Bots List */}
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
                        <div className="text-sm">{bot.messageBalance || 0} / {bot.messageLimit || 0}</div>
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
                          <Button
                            size="sm"
                            onClick={() => activateBot(bot)}
                            disabled={activatingBotId === bot.businessId}
                            className="bg-green-600 hover:bg-green-500 text-white text-xs px-3 h-7"
                          >
                            <Zap className="w-3 h-3 mr-1" />
                            {activatingBotId === bot.businessId ? 'Activating…' : 'Activate'}
                          </Button>
                          <Link href={`/chats/${bot.businessId}`}>
                            <Button variant="ghost" size="sm" className="text-white/60 hover:text-white" title="View Chats">
                              <MessageCircle className="w-4 h-4" />
                            </Button>
                          </Link>
                          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white" title="Settings">
                            <Settings className="w-4 h-4" />
                          </Button>
                          <Button variant="ghost" size="sm" className="text-white/60 hover:text-white" title="Analytics">
                            <BarChart3 className="w-4 h-4" />
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
        </div>
      </div>
    </div>

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
