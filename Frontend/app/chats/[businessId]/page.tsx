'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useUser, UserButton } from '@clerk/nextjs'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { 
  ArrowLeft, 
  MessageSquare, 
  Search, 
  Phone, 
  User, 
  Bot as BotIcon, 
  CheckCheck, 
  Circle,
  Trash2,
  RefreshCw,
  Menu,
  X,
  Home,
  Tag,
  Info,
  CreditCard
} from 'lucide-react'

interface Message {
  phoneNumber: string
  messageType: string
  messageContent: string
  sender: 'user' | 'bot'
  timestamp: string
  read: boolean
  metadata?: any
}

interface Conversation {
  phoneNumber: string
  lastMessage: string
  lastMessageTime: string
  lastSender: string
  messageCount: number
  unreadCount: number
}

export default function ChatLogsPage() {
  const params = useParams()
  const router = useRouter()
  const { user, isLoaded } = useUser()
  const businessId = params.businessId as string

  const [conversations, setConversations] = useState<Conversation[]>([])
  const [selectedPhone, setSelectedPhone] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(true)
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    if (isLoaded && !user) {
      router.push('/')
      return
    }

    if (user && businessId) {
      fetchConversations()
    }
  }, [isLoaded, user, router, businessId])

  const fetchConversations = async () => {
    try {
      setLoading(true)
      const response = await fetch(`/api/conversations?businessId=${businessId}`)
      if (response.ok) {
        const data = await response.json()
        setConversations(data.conversations || [])
      }
    } catch (error) {
      console.error('Error fetching conversations:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchMessages = async (phoneNumber: string) => {
    try {
      setMessagesLoading(true)
      const encodedPhone = encodeURIComponent(phoneNumber)
      const response = await fetch(`/api/conversations?businessId=${businessId}&phoneNumber=${encodedPhone}`)
      if (response.ok) {
        const data = await response.json()
        setMessages(data.messages || [])
        
        // Mark as read
        await fetch('/api/conversations', {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            businessId,
            phoneNumber,
            action: 'mark_read'
          })
        })
        
        // Refresh conversations to update unread count
        fetchConversations()
      }
    } catch (error) {
      console.error('Error fetching messages:', error)
    } finally {
      setMessagesLoading(false)
    }
  }

  const handleConversationClick = (phoneNumber: string) => {
    setSelectedPhone(phoneNumber)
    fetchMessages(phoneNumber)
  }

  const handleDeleteConversation = async (phoneNumber: string) => {
    if (!confirm(`Delete conversation with ${phoneNumber}?`)) return

    try {
      const encodedPhone = encodeURIComponent(phoneNumber)
      const response = await fetch(`/api/conversations?businessId=${businessId}&phoneNumber=${encodedPhone}`, {
        method: 'DELETE'
      })
      
      if (response.ok) {
        setConversations(conversations.filter(c => c.phoneNumber !== phoneNumber))
        if (selectedPhone === phoneNumber) {
          setSelectedPhone(null)
          setMessages([])
        }
      }
    } catch (error) {
      console.error('Error deleting conversation:', error)
    }
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    const now = new Date()
    const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)

    if (diffInHours < 24) {
      return date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    } else if (diffInHours < 168) {
      return date.toLocaleDateString('en-US', { weekday: 'short' })
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
  }

  const filteredConversations = conversations.filter(conv =>
    conv.phoneNumber.toLowerCase().includes(searchQuery.toLowerCase())
  )

  if (!isLoaded || loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading chat logs...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-black text-white flex">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-black border-r border-white/10 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between h-16 px-6 border-b border-white/10">
            <div className="flex items-center gap-2">
              <BotIcon className="w-6 h-6" />
              <span className="font-light text-lg">BotSetu</span>
            </div>
            <button
              onClick={() => setSidebarOpen(false)}
              className="lg:hidden text-white/60 hover:text-white"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <nav className="flex-1 px-4 py-6 space-y-2">
            <Link href="/" className="flex items-center gap-3 px-4 py-3 rounded-lg text-white/60 hover:bg-white/5 hover:text-white transition-colors">
              <Home className="w-5 h-5" />
              <span>Home</span>
            </Link>
            <Link href="/dashboard" className="flex items-center gap-3 px-4 py-3 rounded-lg text-white/60 hover:bg-white/5 hover:text-white transition-colors">
              <BotIcon className="w-5 h-5" />
              <span>Dashboard</span>
            </Link>
            <Link href="/pricing" className="flex items-center gap-3 px-4 py-3 rounded-lg text-white/60 hover:bg-white/5 hover:text-white transition-colors">
              <Tag className="w-5 h-5" />
              <span>Pricing</span>
            </Link>
            <Link href="/about" className="flex items-center gap-3 px-4 py-3 rounded-lg text-white/60 hover:bg-white/5 hover:text-white transition-colors">
              <Info className="w-5 h-5" />
              <span>About Us</span>
            </Link>
            <Link href="/payment" className="flex items-center gap-3 px-4 py-3 rounded-lg text-white/60 hover:bg-white/5 hover:text-white transition-colors">
              <CreditCard className="w-5 h-5" />
              <span>Payment</span>
            </Link>
          </nav>

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

      {sidebarOpen && (
        <div className="fixed inset-0 bg-black/50 z-40 lg:hidden" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Header */}
        <div className="border-b border-white/10 bg-black/50 backdrop-blur-sm sticky top-0 z-30">
          <div className="px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center gap-3">
                <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-white/60 hover:text-white">
                  <Menu className="w-6 h-6" />
                </button>
                <Link href="/dashboard">
                  <Button variant="ghost" size="sm" className="text-white/60 hover:text-white">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Dashboard
                  </Button>
                </Link>
              </div>
              <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" onClick={fetchConversations} className="text-white/60 hover:text-white">
                  <RefreshCw className="w-4 h-4" />
                </Button>
                <div className="lg:hidden">
                  <UserButton />
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="flex-1 flex overflow-hidden">
          {/* Conversations List */}
          <div className="w-full md:w-80 lg:w-96 border-r border-white/10 flex flex-col bg-black">
            <div className="p-4 border-b border-white/10">
              <h2 className="text-xl font-light mb-4">Chat Logs</h2>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-white/40" />
                <input
                  type="text"
                  placeholder="Search conversations..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-white/20"
                />
              </div>
              <div className="mt-4 text-sm text-white/60">
                {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              {filteredConversations.length === 0 ? (
                <div className="p-8 text-center">
                  <MessageSquare className="w-12 h-12 text-white/20 mx-auto mb-3" />
                  <p className="text-white/60">No conversations yet</p>
                </div>
              ) : (
                <div className="divide-y divide-white/10">
                  {filteredConversations.map((conv) => (
                    <div
                      key={conv.phoneNumber}
                      onClick={() => handleConversationClick(conv.phoneNumber)}
                      className={`p-4 cursor-pointer hover:bg-white/5 transition-colors ${
                        selectedPhone === conv.phoneNumber ? 'bg-white/10' : ''
                      }`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                            <Phone className="w-5 h-5 text-blue-400" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium truncate">{conv.phoneNumber}</div>
                            <div className="text-xs text-white/60">{conv.messageCount} messages</div>
                          </div>
                        </div>
                        <div className="text-xs text-white/60">{formatTime(conv.lastMessageTime)}</div>
                      </div>
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 flex-1 min-w-0">
                          {conv.lastSender === 'bot' ? (
                            <BotIcon className="w-3 h-3 text-white/40 shrink-0" />
                          ) : (
                            <User className="w-3 h-3 text-white/40 shrink-0" />
                          )}
                          <p className="text-sm text-white/60 truncate">{conv.lastMessage}</p>
                        </div>
                        {conv.unreadCount > 0 && (
                          <div className="ml-2 bg-blue-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center shrink-0">
                            {conv.unreadCount}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Messages View */}
          <div className="flex-1 flex flex-col bg-black">
            {selectedPhone ? (
              <>
                {/* Chat Header */}
                <div className="p-4 border-b border-white/10 flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                      <Phone className="w-5 h-5 text-blue-400" />
                    </div>
                    <div>
                      <div className="font-medium">{selectedPhone}</div>
                      <div className="text-xs text-white/60">
                        {messages.length} message{messages.length !== 1 ? 's' : ''}
                      </div>
                    </div>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => handleDeleteConversation(selectedPhone)}
                    className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                  >
                    <Trash2 className="w-4 h-4" />
                  </Button>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4">
                  {messagesLoading ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-white/60">Loading messages...</div>
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <MessageSquare className="w-12 h-12 text-white/20 mx-auto mb-3" />
                        <p className="text-white/60">No messages</p>
                      </div>
                    </div>
                  ) : (
                    messages.slice().reverse().map((msg, idx) => (
                      <div key={idx} className={`flex ${msg.sender === 'bot' ? 'justify-start' : 'justify-end'}`}>
                        <div className={`max-w-[70%] ${msg.sender === 'bot' ? 'bg-white/10' : 'bg-blue-500/20'} rounded-lg p-3`}>
                          <div className="flex items-center gap-2 mb-1">
                            {msg.sender === 'bot' ? (
                              <BotIcon className="w-3 h-3 text-blue-400" />
                            ) : (
                              <User className="w-3 h-3 text-white/60" />
                            )}
                            <span className="text-xs text-white/60 capitalize">{msg.sender}</span>
                          </div>
                          {msg.messageType === 'text' ? (
                            <p className="text-sm">{msg.messageContent}</p>
                          ) : (
                            <div>
                              <p className="text-xs text-white/60 mb-2 capitalize">{msg.messageType}</p>
                              <a
                                href={msg.messageContent}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-blue-400 hover:underline"
                              >
                                View {msg.messageType}
                              </a>
                            </div>
                          )}
                          <div className="flex items-center justify-end gap-1 mt-2">
                            <span className="text-xs text-white/40">{formatTime(msg.timestamp)}</span>
                            {msg.read && <CheckCheck className="w-3 h-3 text-blue-400" />}
                            {!msg.read && <Circle className="w-3 h-3 text-white/20" />}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center">
                  <MessageSquare className="w-16 h-16 text-white/20 mx-auto mb-4" />
                  <h3 className="text-xl font-light mb-2">Select a conversation</h3>
                  <p className="text-white/60">Choose a conversation to view chat history</p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
