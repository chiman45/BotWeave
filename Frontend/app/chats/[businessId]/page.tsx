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
  Check,
  Circle,
  Trash2,
  RefreshCw,
  Menu,
  X,
  Home,
  Tag,
  Info,
  CreditCard,
  MoreVertical,
  Video
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
      <div className="min-h-screen bg-[#111b21] flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 rounded-full bg-[#25d366] flex items-center justify-center mx-auto mb-4">
            <MessageSquare className="w-8 h-8 text-white animate-pulse" />
          </div>
          <div className="text-white text-xl">Loading chats...</div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#111b21] text-white flex">
      {/* Sidebar */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-[#111b21] border-r border-white/10 transform transition-transform duration-300 ease-in-out lg:translate-x-0 lg:static ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}>
        <div className="flex flex-col h-full">
          <div className="flex items-center justify-between h-16 px-6 border-b border-white/10 bg-[#202c33]">
            <div className="flex items-center gap-2">
              <BotIcon className="w-6 h-6 text-[#25d366]" />
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
        <div className="border-b border-[#2a3942] bg-[#202c33] backdrop-blur-sm sticky top-0 z-30">
          <div className="px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <div className="flex items-center gap-3">
                <button onClick={() => setSidebarOpen(true)} className="lg:hidden text-white/60 hover:text-white">
                  <Menu className="w-6 h-6" />
                </button>
                <Link href="/dashboard">
                  <Button variant="ghost" size="sm" className="text-white/60 hover:text-white hover:bg-white/10">
                    <ArrowLeft className="w-4 h-4 mr-2" />
                    Back to Dashboard
                  </Button>
                </Link>
              </div>
              <div className="flex items-center gap-3">
                <Button variant="ghost" size="sm" onClick={fetchConversations} className="text-white/60 hover:text-white hover:bg-white/10">
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
          <div className="w-full md:w-80 lg:w-96 border-r border-[#2a3942] flex flex-col bg-[#111b21]">
            <div className="p-4 border-b border-[#2a3942] bg-[#202c33]">
              <h2 className="text-xl font-light mb-4">Chats</h2>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-white/40" />
                <input
                  type="text"
                  placeholder="Search or start new chat"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-[#202c33] border border-[#2a3942] rounded-lg pl-10 pr-4 py-2.5 text-sm focus:outline-none focus:ring-1 focus:ring-[#25d366]"
                />
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              {filteredConversations.length === 0 ? (
                <div className="p-8 text-center">
                  <MessageSquare className="w-12 h-12 text-white/20 mx-auto mb-3" />
                  <p className="text-white/60">No conversations yet</p>
                </div>
              ) : (
                <div>
                  {filteredConversations.map((conv) => (
                    <div
                      key={conv.phoneNumber}
                      onClick={() => handleConversationClick(conv.phoneNumber)}
                      className={`p-3 cursor-pointer hover:bg-[#202c33] transition-colors border-b border-[#2a3942]/50 ${
                        selectedPhone === conv.phoneNumber ? 'bg-[#2a3942]' : ''
                      }`}
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 rounded-full bg-[#6b7c85] flex items-center justify-center shrink-0">
                          <User className="w-6 h-6 text-[#202c33]" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between mb-1">
                            <div className="font-medium truncate">{conv.phoneNumber}</div>
                            <div className="text-xs text-[#8696a0]">{formatTime(conv.lastMessageTime)}</div>
                          </div>
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-1 flex-1 min-w-0">
                              {conv.lastSender === 'bot' ? (
                                <BotIcon className="w-3.5 h-3.5 text-[#25d366] shrink-0" />
                              ) : (
                                <CheckCheck className="w-3.5 h-3.5 text-[#53bdeb] shrink-0" />
                              )}
                              <p className="text-sm text-[#8696a0] truncate">{conv.lastMessage}</p>
                            </div>
                            {conv.unreadCount > 0 && (
                              <div className="ml-2 bg-[#25d366] text-[#111b21] text-xs font-medium rounded-full min-w-[20px] h-5 flex items-center justify-center px-1.5 shrink-0">
                                {conv.unreadCount}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Messages View */}
          <div className="flex-1 flex flex-col bg-[#0b141a]">
            {selectedPhone ? (
              <>
                {/* Chat Header */}
                <div className="px-4 py-2 border-b border-[#2a3942] flex items-center justify-between bg-[#202c33]">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-[#6b7c85] flex items-center justify-center">
                      <User className="w-5 h-5 text-[#202c33]" />
                    </div>
                    <div>
                      <div className="font-medium">{selectedPhone}</div>
                      <div className="text-xs text-[#8696a0]">
                        {messages.length} message{messages.length !== 1 ? 's' : ''}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-[#8696a0] hover:text-white hover:bg-white/10 h-10 w-10 p-0"
                    >
                      <Video className="w-5 h-5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-[#8696a0] hover:text-white hover:bg-white/10 h-10 w-10 p-0"
                    >
                      <Phone className="w-5 h-5" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteConversation(selectedPhone)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/10 h-10 w-10 p-0"
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="text-[#8696a0] hover:text-white hover:bg-white/10 h-10 w-10 p-0"
                    >
                      <MoreVertical className="w-5 h-5" />
                    </Button>
                  </div>
                </div>

                {/* Messages */}
                <div 
                  className="flex-1 overflow-y-auto p-4 space-y-2" 
                  style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.02'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
                    backgroundColor: '#0b141a'
                  }}
                >
                  {messagesLoading ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-[#8696a0]">Loading messages...</div>
                    </div>
                  ) : messages.length === 0 ? (
                    <div className="flex items-center justify-center h-full">
                      <div className="text-center">
                        <MessageSquare className="w-12 h-12 text-white/20 mx-auto mb-3" />
                        <p className="text-[#8696a0]">No messages</p>
                      </div>
                    </div>
                  ) : (
                    messages.slice().reverse().map((msg, idx) => (
                      <div key={idx} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                        <div 
                          className={`relative max-w-[65%] rounded-lg px-3 py-2 shadow-md ${
                            msg.sender === 'user' 
                              ? 'bg-[#005c4b] text-white' 
                              : 'bg-[#202c33] text-white'
                          }`}
                        >
                          {msg.messageType === 'text' ? (
                            <p className="text-[14.2px] leading-[19px] break-words whitespace-pre-wrap">{msg.messageContent}</p>
                          ) : (
                            <div>
                              <p className="text-xs text-[#8696a0] mb-2 capitalize">{msg.messageType}</p>
                              <a
                                href={msg.messageContent}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="text-xs text-[#53bdeb] hover:underline"
                              >
                                View {msg.messageType}
                              </a>
                            </div>
                          )}
                          <div className="flex items-center justify-end gap-1 mt-1 ml-4">
                            <span className={`text-[11px] ${msg.sender === 'user' ? 'text-[#99d6c5]' : 'text-[#8696a0]'}`}>
                              {formatTime(msg.timestamp)}
                            </span>
                            {msg.sender === 'user' && (
                              msg.read ? (
                                <CheckCheck className="w-4 h-4 text-[#53bdeb]" />
                              ) : (
                                <Check className="w-4 h-4 text-[#8696a0]" />
                              )
                            )}
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center" style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23ffffff' fill-opacity='0.02'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")`,
                backgroundColor: '#0b141a'
              }}>
                <div className="text-center">
                  <div className="w-20 h-20 rounded-full bg-[#202c33] flex items-center justify-center mx-auto mb-4">
                    <MessageSquare className="w-10 h-10 text-[#8696a0]" />
                  </div>
                  <h3 className="text-2xl font-light mb-2 text-[#e9edef]">BotSetu Chat</h3>
                  <p className="text-[#8696a0] text-sm max-w-md">
                    Select a conversation from the list to view chat history and messages
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
