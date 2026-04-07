'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useUser, UserButton } from '@clerk/nextjs'
import { Button } from '@/components/ui/button'
import { ArrowLeft, ArrowRight, Check, CheckCircle } from 'lucide-react'
import Link from 'next/link'

const steps = [
  { id: 1, name: 'Business Info', icon: '🧾' },
  { id: 2, name: 'Bot Config', icon: '🤖' },
  { id: 3, name: 'WhatsApp Setup', icon: '📞' },
  { id: 4, name: 'Templates', icon: '📝' },
  { id: 5, name: 'Conversation', icon: '💬' },
  { id: 6, name: 'Billing', icon: '💰' },
]

export default function CreateBotPage() {
  const router = useRouter()
  const { user } = useUser()
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(1)
  const [showSuccess, setShowSuccess] = useState(false)
  const [createdBusinessId, setCreatedBusinessId] = useState<string | null>(null)
  const [kbUploading, setKbUploading] = useState(false)
  const [kbUploadProgress, setKbUploadProgress] = useState<number | null>(null)
  const [kbUploadedFiles, setKbUploadedFiles] = useState<{ name: string; chunks: number }[]>([])

  const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000'

  const [formData, setFormData] = useState({
    // Business Info
    businessName: '',
    category: '',
    city: '',
    country: '',
    defaultLanguage: '',
    businessHours: '',
    
    // Bot Config
    botName: '',
    botType: 'normal' as 'normal' | 'ai',
    useCaseType: '',
    autoReply: false,
    humanHandoff: false,
    
    // WhatsApp Setup
    phoneNumber: '',
    bspName: '',
    wabaId: '',
    phoneNumberId: '',
    verificationStatus: 'pending',
    
    // Templates
    templateName: '',
    templateText: '',
    templateCategory: '',
    approvalStatus: 'pending',
    
    // Conversation
    conversationState: 'active',
    lastUserMessageTime: '',
    assignedFlow: '',
    
    // Billing
    planType: '',
    messageBalance: 0,
    messageLimit: 0,
    // Auto-reply
    welcomeMessage: '',
    fallbackMessage: '',
    humanHandoffMessage: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }))
  }

  // ── AI Bot config state ──────────────────────────────────────────
  const [aiModel, setAiModel] = useState('gemini-2.0-flash')
  const [aiSystemPrompt, setAiSystemPrompt] = useState('')
  const [aiRagEnabled, setAiRagEnabled] = useState(false)
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [ollamaOnline, setOllamaOnline] = useState<boolean | null>(null)

  const fetchOllamaModels = async () => {
    try {
      const res = await fetch('/api/ai/models')
      const data = await res.json()
      setOllamaOnline(data.ollamaRunning)
      if (data.models?.length) setOllamaModels(data.models)
    } catch {
      setOllamaOnline(false)
    }
  }
  // ────────────────────────────────────────────────────────────

  // ── IVR Flow config state ──────────────────────────────────
  interface IvrOption { label: string; nextNodeId: string }
  interface IvrNode { id: string; message: string; options: IvrOption[]; isEndNode: boolean }

  const makeNodeId = () => `node_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`

  const [ivrNodes, setIvrNodes] = useState<IvrNode[]>([
    { id: 'node_root', message: '', options: [], isEndNode: false },
  ])

  const addIvrChildNode = (parentId: string) => {
    const newId = makeNodeId()
    const newNode: IvrNode = { id: newId, message: '', options: [], isEndNode: true }
    setIvrNodes(prev => [
      ...prev.map(n =>
        n.id === parentId
          ? { ...n, isEndNode: false, options: [...n.options, { label: '', nextNodeId: newId }] }
          : n
      ),
      newNode,
    ])
  }

  const removeIvrNode = (nodeId: string) => {
    if (nodeId === 'node_root') return
    setIvrNodes(prev => {
      const updated = prev
        .filter(n => n.id !== nodeId)
        .map(n => ({
          ...n,
          options: n.options.filter(o => o.nextNodeId !== nodeId),
        }))
      // Mark parent as isEndNode if it now has 0 options
      return updated.map(n => ({ ...n, isEndNode: n.options.length === 0 && n.id !== 'node_root' }))
    })
  }

  const updateIvrNode = (nodeId: string, field: 'message' | 'isEndNode', value: string | boolean) =>
    setIvrNodes(prev => prev.map(n => n.id === nodeId ? { ...n, [field]: value } : n))

  const updateIvrOption = (nodeId: string, optIdx: number, field: 'label', value: string) =>
    setIvrNodes(prev => prev.map(n =>
      n.id === nodeId
        ? { ...n, options: n.options.map((o, i) => i === optIdx ? { ...o, [field]: value } : o) }
        : n
    ))

  const addIvrOption = (nodeId: string) => {
    const newId = makeNodeId()
    setIvrNodes(prev => [
      ...prev.map(n =>
        n.id === nodeId
          ? { ...n, isEndNode: false, options: [...n.options, { label: '', nextNodeId: newId }] }
          : n
      ),
      { id: newId, message: '', options: [], isEndNode: true },
    ])
  }

  const removeIvrOption = (nodeId: string, optIdx: number) => {
    setIvrNodes(prev => {
      const parent = prev.find(n => n.id === nodeId)
      const targetNodeId = parent?.options[optIdx]?.nextNodeId
      const filtered = prev
        .filter(n => n.id !== targetNodeId)
        .map(n => {
          if (n.id !== nodeId) return n
          const nextOptions = n.options.filter((_, idx) => idx !== optIdx)
          return { ...n, options: nextOptions, isEndNode: nextOptions.length === 0 && n.id !== 'node_root' }
        })

      return filtered.map(n => ({
        ...n,
        options: n.options.filter(o => o.nextNodeId !== targetNodeId),
      }))
    })
  }

  const nodeById = (id: string) => ivrNodes.find(n => n.id === id)
  // ─────────────────────────────────────────────────────────

  // ── Mandi Booking config state ────────────────────────────
  const [mandiList, setMandiList] = useState([{ name: '', location: '', address: '' }])
  const [slotTimes, setSlotTimes] = useState([
    '9:00 AM – 10:00 AM',
    '10:00 AM – 11:00 AM',
    '11:00 AM – 12:00 PM',
    '2:00 PM – 3:00 PM',
  ])
  const [maxPerSlot, setMaxPerSlot] = useState(10)

  const addMandi = () => setMandiList(prev => [...prev, { name: '', location: '', address: '' }])
  const removeMandi = (i: number) => setMandiList(prev => prev.filter((_, idx) => idx !== i))
  const updateMandi = (i: number, field: 'name' | 'location' | 'address', value: string) =>
    setMandiList(prev => prev.map((m, idx) => idx === i ? { ...m, [field]: value } : m))

  const addSlot = () => setSlotTimes(prev => [...prev, ''])
  const removeSlot = (i: number) => setSlotTimes(prev => prev.filter((_, idx) => idx !== i))
  const updateSlot = (i: number, value: string) =>
    setSlotTimes(prev => prev.map((s, idx) => idx === i ? value : s))
  // ─────────────────────────────────────────────────────────

  // (IVR state defined above)

  const [keywordPairs, setKeywordPairs] = useState<{ keyword: string; response: string }[]>([
    { keyword: '', response: '' }
  ])
  const addKeywordPair = () => setKeywordPairs(prev => [...prev, { keyword: '', response: '' }])
  const removeKeywordPair = (index: number) => setKeywordPairs(prev => prev.filter((_, i) => i !== index))
  const updateKeywordPair = (index: number, field: 'keyword' | 'response', value: string) => {
    setKeywordPairs(prev => prev.map((pair, i) => i === index ? { ...pair, [field]: value } : pair))
  }

  const validateStep = (step: number): boolean => {
    switch (step) {
      case 1:
        return !!(formData.businessName && formData.category && formData.city && 
                 formData.country && formData.defaultLanguage && formData.businessHours)
      case 2:
        return !!(formData.botName && (formData.botType === 'ai' || formData.useCaseType))
      case 3:
        return true // WhatsApp number is assigned automatically on activation
      case 4:
        return true // Optional step
      case 5:
        return true // Optional step
      case 6:
        return !!(formData.planType)
      default:
        return false
    }
  }

  const handleNext = () => {
    if (validateStep(currentStep)) {
      setCurrentStep(prev => Math.min(prev + 1, steps.length))
    } else {
      alert('Please fill in all required fields before continuing.')
    }
  }

  const handlePrevious = () => {
    setCurrentStep(prev => Math.max(prev - 1, 1))
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!validateStep(currentStep)) {
      alert('Please fill in all required fields.')
      return
    }

    setLoading(true)

    try {
      const response = await fetch('/api/bot', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          ...formData,
          keywordResponses: keywordPairs.reduce((acc: Record<string, string>, { keyword, response }) => {
            if (keyword.trim()) acc[keyword.trim().toLowerCase()] = response.trim()
            return acc
          }, {}),
          ...(formData.useCaseType === 'mandi_booking' && {
            mandis: mandiList.filter(m => m.name.trim()),
            slots: slotTimes.filter(s => s.trim()),
            maxBookingsPerSlot: maxPerSlot,
            autoReply: true,
          }),
          ...(formData.useCaseType === 'ivr' && {
            ivrNodes: ivrNodes.filter(n => n.message.trim()),
            autoReply: true,
          }),
          ...(formData.botType === 'ai' && {
            aiModel,
            aiSystemPrompt,
            aiRagEnabled,
            autoReply: true,
          }),
          ownerUserId: user?.id,
          createdAt: new Date().toISOString(),
        }),
      })

      if (response.ok) {
        const data = await response.json()
        setCreatedBusinessId(data.businessId || null)
        setShowSuccess(true)
      } else {
        const error = await response.json()
        alert(`Error: ${error.message}`)
      }
    } catch (error) {
      console.error('Error creating bot:', error)
      alert('Failed to create bot. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <>
    <div className="min-h-screen bg-black text-white py-12 px-4 sm:px-6 lg:px-8">
      <div className="max-w-4xl mx-auto border border-white/20 rounded-2xl p-8 shadow-[0_0_50px_rgba(255,255,255,0.15)] bg-black/50 backdrop-blur-sm">
        {/* Header */}
        <div className="mb-8">
          <div className="flex justify-between items-center mb-4">
            <Link href="/" className="inline-flex items-center text-white/60 hover:text-white">
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Home
            </Link>
            <UserButton />
          </div>
          <h1 className="text-4xl font-bitcount mb-2">Create Your Bot</h1>
          <p className="text-white/60">Complete the steps to set up your WhatsApp bot</p>
        </div>

        {/* Progress Timeline */}
        <div className="mb-12">
          <div className="flex items-center justify-between">
            {steps.map((step, index) => (
              <div key={step.id} className="flex-1 flex items-center">
                {/* Step Circle */}
                <div className="flex flex-col items-center relative">
                  <div
                    className={`w-12 h-12 rounded-full flex items-center justify-center border-2 transition-all ${
                      currentStep > step.id
                        ? 'bg-green-500 border-green-500'
                        : currentStep === step.id
                        ? 'bg-white border-white'
                        : 'bg-white/5 border-white/20'
                    }`}
                  >
                    {currentStep > step.id ? (
                      <Check className="w-6 h-6 text-white" />
                    ) : (
                      <span className={`text-xl ${currentStep === step.id ? 'text-black' : 'text-white/60'}`}>
                        {step.icon}
                      </span>
                    )}
                  </div>
                  <div className="mt-2 text-center">
                    <p
                      className={`text-xs font-medium ${
                        currentStep >= step.id ? 'text-white' : 'text-white/40'
                      }`}
                    >
                      {step.name}
                    </p>
                  </div>
                </div>

                {/* Connector Line */}
                {index < steps.length - 1 && (
                  <div
                    className={`flex-1 h-0.5 mx-2 transition-all ${
                      currentStep > step.id ? 'bg-green-500' : 'bg-white/20'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-8 border border-white/20 rounded-2xl p-8 shadow-[0_0_30px_rgba(255,255,255,0.1)]">
          {/* Step 1: Business Info */}
          {currentStep === 1 && (
            <div className="space-y-6 animate-fadeIn">
              <h2 className="text-2xl font-bitcount border-b border-white/10 pb-2">🧾 Business Info</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-white/60 mb-2">Business Name *</label>
                  <input
                    type="text"
                    name="businessName"
                    value={formData.businessName}
                    onChange={handleChange}
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">Category *</label>
                  <select
                    name="category"
                    value={formData.category}
                    onChange={handleChange}
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  >
                    <option value="">Select Category</option>
                    <option value="shop">Shop</option>
                    <option value="clinic">Clinic</option>
                    <option value="tour">Tour</option>
                    <option value="restaurant">Restaurant</option>
                    <option value="salon">Salon</option>
                    <option value="other">Other</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">City *</label>
                  <input
                    type="text"
                    name="city"
                    value={formData.city}
                    onChange={handleChange}
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">Country *</label>
                  <input
                    type="text"
                    name="country"
                    value={formData.country}
                    onChange={handleChange}
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">Default Language *</label>
                  <input
                    type="text"
                    name="defaultLanguage"
                    value={formData.defaultLanguage}
                    onChange={handleChange}
                    required
                    placeholder="e.g., English, Hindi"
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">Business Hours *</label>
                  <input
                    type="text"
                    name="businessHours"
                    value={formData.businessHours}
                    onChange={handleChange}
                    required
                    placeholder="e.g., 9 AM - 6 PM"
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 2: Bot Config */}
          {currentStep === 2 && (
            <div className="space-y-6 animate-fadeIn">
              <h2 className="text-2xl font-bitcount border-b border-white/10 pb-2">🤖 Bot Config</h2>

              {/* ── Bot Type Toggle ─────────────────────────────── */}
              <div>
                <p className="text-sm text-white/50 mb-3">Bot Type *</p>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => setFormData(prev => ({ ...prev, botType: 'normal' }))}
                    className={`p-4 rounded-xl border-2 transition-all text-left ${
                      formData.botType !== 'ai'
                        ? 'border-white bg-white/10'
                        : 'border-white/20 bg-white/5 hover:border-white/40'
                    }`}
                  >
                    <div className="text-base font-medium mb-1">⚡ Normal Bot</div>
                    <div className="text-xs text-white/50">Keyword rules, FAQ, mandi booking flow</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => { setFormData(prev => ({ ...prev, botType: 'ai' })); fetchOllamaModels() }}
                    className={`p-4 rounded-xl border-2 transition-all text-left ${
                      formData.botType === 'ai'
                        ? 'border-cyan-400 bg-cyan-500/10'
                        : 'border-white/20 bg-white/5 hover:border-white/40'
                    }`}
                  >
                    <div className="text-base font-medium mb-1">🧠 AI Bot</div>
                    <div className="text-xs text-white/50">Local Ollama LLM · RAG knowledge base</div>
                  </button>
                </div>
              </div>

              {/* ── Bot Name (always visible) ───────────────────── */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-white/60 mb-2">Bot Name *</label>
                  <input
                    type="text"
                    name="botName"
                    value={formData.botName}
                    onChange={handleChange}
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                </div>
                {formData.botType !== 'ai' && (
                <div>
                  <label className="block text-sm text-white/60 mb-2">Use-case Type *</label>
                  <select
                    name="useCaseType"
                    value={formData.useCaseType}
                    onChange={handleChange}
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  >
                    <option value="">Select Type</option>
                    <option value="booking">Booking</option>
                    <option value="faq">FAQ</option>
                    <option value="orders">Orders</option>
                    <option value="leads">Leads</option>
                    <option value="mandi_booking">🌾 Mandi Booking (Farmer Flow)</option>
                    <option value="ivr">📞 IVR Call Bot (Phone Menu)</option>
                  </select>
                </div>
                )}
                {formData.botType !== 'ai' && (
                <div className="flex items-center gap-3 p-4 bg-white/5 rounded-lg border border-white/10">
                  <input
                    type="checkbox"
                    name="autoReply"
                    checked={formData.autoReply}
                    onChange={handleChange}
                    className="w-5 h-5 accent-white"
                  />
                  <label className="text-sm text-white/80">Enable Auto-reply</label>
                </div>
                )}
                {formData.botType !== 'ai' && (
                <div className="flex items-center gap-3 p-4 bg-white/5 rounded-lg border border-white/10">
                  <input
                    type="checkbox"
                    name="humanHandoff"
                    checked={formData.humanHandoff}
                    onChange={handleChange}
                    className="w-5 h-5 accent-white"
                  />
                  <label className="text-sm text-white/80">Enable Human Handoff</label>
                </div>
                )}
              </div>

              {/* ══ AI BOT CONFIG ═══════════════════════════════════ */}
              {formData.botType === 'ai' && (
                <div className="space-y-5 p-5 bg-cyan-500/5 border border-cyan-500/20 rounded-xl">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🧠</span>
                    <h3 className="text-sm font-medium text-cyan-400">AI Bot Configuration</h3>
                    {ollamaOnline === true && <span className="ml-auto text-xs text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">● Ollama online</span>}
                  </div>

                  {/* Model */}
                  <div>
                    <label className="block text-sm text-white/60 mb-2">AI Model *</label>
                    <select
                      value={aiModel}
                      onChange={e => setAiModel(e.target.value)}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30"
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
                    <p className="text-xs text-white/40 mt-1">Gemini models use the cloud API. Local models require Ollama running.</p>
                  </div>

                  {/* System Prompt */}
                  <div>
                    <label className="block text-sm text-white/60 mb-2">System Prompt</label>
                    <textarea
                      rows={4}
                      value={aiSystemPrompt}
                      onChange={e => setAiSystemPrompt(e.target.value)}
                      placeholder={`You are a helpful assistant for ${formData.businessName || 'this business'}. Answer clearly and concisely. Reply in the same language the user writes in.`}
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-white/30 resize-none"
                    />
                    <p className="text-xs text-white/40 mt-1">Defines how the AI behaves. Leave blank for a sensible default.</p>
                  </div>

                  {/* RAG */}
                  <div className="p-4 bg-purple-500/5 border border-purple-500/20 rounded-lg space-y-3">
                    <div className="flex items-center gap-3">
                      <input
                        type="checkbox"
                        id="ragEnabled"
                        checked={aiRagEnabled}
                        onChange={e => setAiRagEnabled(e.target.checked)}
                        className="w-4 h-4 accent-purple-400"
                      />
                      <label htmlFor="ragEnabled" className="text-sm text-purple-300 font-medium cursor-pointer">
                        Enable RAG (Knowledge Base)
                      </label>
                    </div>
                    <p className="text-xs text-white/40">
                      The bot will search your uploaded documents before answering.
                    </p>
                    {aiRagEnabled && (
                      <p className="text-xs text-purple-300/60 bg-purple-500/10 px-3 py-2 rounded-lg">
                        📁 You&apos;ll be able to upload your knowledge base documents immediately after the bot is created.
                      </p>
                    )}
                  </div>
                </div>
              )}
              {/* ═══════════════════════════════════════════════════ */}

              {formData.autoReply && (
                <div className="space-y-4 p-4 bg-green-500/5 border border-green-500/20 rounded-lg">
                  <h3 className="text-sm font-medium text-green-400">🤖 Auto-Reply Messages</h3>
                  <div>
                    <label className="block text-sm text-white/60 mb-2">Welcome Message</label>
                    <textarea
                      name="welcomeMessage"
                      value={formData.welcomeMessage}
                      onChange={handleChange}
                      rows={3}
                      placeholder="Hi! 👋 Welcome to [Your Business]. How can I help you today?"
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors resize-none"
                    />
                    <p className="text-xs text-white/40 mt-1">Sent when user says "hi", "hello", "hey"</p>
                  </div>
                  <div>
                    <label className="block text-sm text-white/60 mb-2">Fallback Message</label>
                    <textarea
                      name="fallbackMessage"
                      value={formData.fallbackMessage}
                      onChange={handleChange}
                      rows={3}
                      placeholder="Sorry, I didn't understand that. Type 'help' for assistance."
                      className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors resize-none"
                    />
                    <p className="text-xs text-white/40 mt-1">Sent when no keyword matches</p>
                  </div>
                </div>
              )}

              {formData.humanHandoff && (
                <div className="p-4 bg-blue-500/5 border border-blue-500/20 rounded-lg">
                  <h3 className="text-sm font-medium text-blue-400 mb-3">👤 Human Handoff Message</h3>
                  <textarea
                    name="humanHandoffMessage"
                    value={formData.humanHandoffMessage}
                    onChange={handleChange}
                    rows={2}
                    placeholder="Connecting you to a human agent. Please hold on..."
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors resize-none"
                  />
                  <p className="text-xs text-white/40 mt-1">Sent when user says "human", "agent", "help me"</p>
                </div>
              )}

              {/* ══ IVR FLOW BUILDER ═══════════════════════════════════ */}
              {formData.useCaseType === 'ivr' && (
                <div className="space-y-4 p-5 bg-orange-500/5 border border-orange-500/20 rounded-xl">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">📞</span>
                    <h3 className="text-sm font-medium text-orange-400">IVR Menu Builder</h3>
                    <span className="ml-auto text-xs text-white/30">{ivrNodes.length} node{ivrNodes.length !== 1 ? 's' : ''}</span>
                  </div>
                  <p className="text-xs text-white/40">Build a multi-level WhatsApp menu. Customers navigate by replying with numbers.</p>

                  <div className="space-y-3">
                    {ivrNodes.map((node) => {
                      const parentNode = ivrNodes.find(n => n.options.some(o => o.nextNodeId === node.id))
                      const optionIndex = parentNode?.options.findIndex(o => o.nextNodeId === node.id)

                      return (
                        <div
                          key={node.id}
                          className={`rounded-xl border p-4 space-y-3 ${
                            node.id === 'node_root'
                              ? 'border-orange-500/40 bg-orange-500/10'
                              : 'border-white/10 bg-white/5'
                          }`}
                        >
                          {/* Node header */}
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-orange-400/70">
                              {node.id === 'node_root' ? '🌳 Root' : `↳ Option ${(optionIndex ?? 0) + 1} of ${parentNode?.id === 'node_root' ? 'Root' : parentNode?.id.slice(-8)}`}
                            </span>
                            <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${
                              node.isEndNode
                                ? 'bg-orange-500/15 text-orange-300 border border-orange-500/30'
                                : 'bg-green-500/15 text-green-300 border border-green-500/30'
                            }`}>
                              {node.isEndNode ? 'Leaf (no sub-options)' : `${node.options.length} sub-option${node.options.length !== 1 ? 's' : ''}`}
                            </span>
                            {node.id !== 'node_root' && (
                              <button
                                type="button"
                                onClick={() => removeIvrNode(node.id)}
                                className="text-red-400/50 hover:text-red-400 transition-colors text-lg leading-none ml-1"
                                title="Remove this node"
                              >
                                ×
                              </button>
                            )}
                          </div>

                          {/* Option label (shown only for non-root) */}
                          {node.id !== 'node_root' && parentNode && (
                            <div>
                              <label className="block text-xs text-white/40 mb-1">Menu option label (what the parent shows)</label>
                              <input
                                type="text"
                                value={parentNode.options[optionIndex!]?.label ?? ''}
                                onChange={e => updateIvrOption(parentNode.id, optionIndex!, 'label', e.target.value)}
                                placeholder={`e.g. Sales, Support, Hours…`}
                                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-orange-500/40"
                              />
                            </div>
                          )}

                          {/* Node message */}
                          <div>
                            <label className="block text-xs text-white/40 mb-1">
                              {node.id === 'node_root' ? 'Root menu message (shown first)' : 'Response message'}
                            </label>
                            <textarea
                              rows={3}
                              value={node.message}
                              onChange={e => updateIvrNode(node.id, 'message', e.target.value)}
                              placeholder={
                                node.id === 'node_root'
                                  ? 'Welcome! Please choose:\n1️⃣ Sales\n2️⃣ Support\n3️⃣ Hours'
                                  : 'Our sales team will call you back. Email: sales@example.com'
                              }
                              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-orange-500/40 resize-none"
                            />
                            <p className="text-xs text-white/30 mt-1">The numbered list is <em>auto-appended</em> by the bot — just write the intro line here.</p>
                          </div>

                          {/* Options listed */}
                          {node.options.length > 0 && (
                            <div className="space-y-1">
                              {node.options.map((opt, oi) => (
                                <div key={oi} className="flex items-center gap-2 text-xs text-white/40">
                                  <span className="w-5 h-5 flex items-center justify-center rounded-full bg-orange-500/20 text-orange-300 shrink-0">{oi + 1}</span>
                                  <span className="truncate">{opt.label || <em className="opacity-50">unlabelled</em>}</span>
                                  <span className="font-mono text-white/20 ml-auto shrink-0">{nodeById(opt.nextNodeId)?.isEndNode ? '🔚' : '▶'}</span>
                                </div>
                              ))}
                            </div>
                          )}

                          {/* Add sub-option button */}
                          {!node.isEndNode || node.id === 'node_root' ? (
                            <button
                              type="button"
                              onClick={() => addIvrChildNode(node.id)}
                              className="text-xs text-orange-400/70 hover:text-orange-400 border border-orange-500/20 hover:border-orange-500/40 px-3 py-1.5 rounded-md transition-colors w-full"
                            >
                              + Add Sub-option to this node
                            </button>
                          ) : null}
                        </div>
                      )
                    })}
                  </div>
                  <p className="text-xs text-white/30">💡 Tip: keep each level to ≤ 9 options so customers can reply with a single digit.</p>
                </div>
              )}
              {/* ═══════════════════════════════════════════════════ */}

              {/* ── Mandi Booking Configuration ──────────────────────── */}
              {formData.useCaseType === 'mandi_booking' && (
                <div className="space-y-6 p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-lg">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🌾</span>
                    <h3 className="text-sm font-medium text-yellow-400">Mandi Booking Configuration</h3>
                  </div>
                  <p className="text-xs text-white/40">The bot will guide farmers step-by-step: name → village → crop → quantity → mandi → slot → confirmation token.</p>

                  {/* Mandis */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-sm text-white/70">Mandis / Markets</label>
                      <button type="button" onClick={addMandi}
                        className="text-xs text-yellow-400/70 hover:text-yellow-400 border border-yellow-500/20 hover:border-yellow-500/40 px-3 py-1 rounded-md transition-colors">
                        + Add Mandi
                      </button>
                    </div>
                    {mandiList.map((m, i) => (
                      <div key={i} className="grid grid-cols-3 gap-2 items-center">
                        <input type="text" value={m.name} onChange={e => updateMandi(i, 'name', e.target.value)}
                          placeholder="Mandi Name *"
                          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                        <input type="text" value={m.location} onChange={e => updateMandi(i, 'location', e.target.value)}
                          placeholder="Location / Area"
                          className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                        <div className="flex gap-2 items-center">
                          <input type="text" value={m.address} onChange={e => updateMandi(i, 'address', e.target.value)}
                            placeholder="Full Address"
                            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                          {mandiList.length > 1 && (
                            <button type="button" onClick={() => removeMandi(i)}
                              className="text-red-400/60 hover:text-red-400 px-2 text-lg leading-none transition-colors">×</button>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Slots */}
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <label className="text-sm text-white/70">Daily Time Slots</label>
                      <button type="button" onClick={addSlot}
                        className="text-xs text-yellow-400/70 hover:text-yellow-400 border border-yellow-500/20 hover:border-yellow-500/40 px-3 py-1 rounded-md transition-colors">
                        + Add Slot
                      </button>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      {slotTimes.map((s, i) => (
                        <div key={i} className="flex gap-2 items-center">
                          <input type="text" value={s} onChange={e => updateSlot(i, e.target.value)}
                            placeholder="e.g. 9:00 AM – 10:00 AM"
                            className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                          {slotTimes.length > 1 && (
                            <button type="button" onClick={() => removeSlot(i)}
                              className="text-red-400/60 hover:text-red-400 px-2 text-lg leading-none transition-colors">×</button>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Max per slot */}
                  <div>
                    <label className="block text-sm text-white/70 mb-2">Max Bookings per Slot</label>
                    <input type="number" min={1} max={100} value={maxPerSlot}
                      onChange={e => setMaxPerSlot(Number(e.target.value))}
                      className="w-32 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                    <p className="text-xs text-white/40 mt-1">Once a slot is full, it won't be shown to new farmers</p>
                  </div>
                </div>
              )}
              {/* ─────────────────────────────────────────────────────── */}

              {/* ══ IVR BUILDER ═══════════════════════════════════════ */}
              {formData.useCaseType === 'ivr' && (
                <div className="space-y-4 p-5 bg-orange-500/5 border border-orange-500/20 rounded-xl">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="text-lg">📞</span>
                      <h3 className="text-sm font-medium text-orange-400">IVR Flow Builder</h3>
                    </div>
                  </div>
                  <p className="text-xs text-white/40">Build a multi-level menu tree. Each node is a message the bot sends. Add numbered options to navigate between nodes.</p>

                  <div className="space-y-3">
                    {ivrNodes.map((node) => (
                      <div key={node.id} className={`p-4 rounded-xl border ${
                        node.id === 'node_root'
                          ? 'bg-orange-500/10 border-orange-500/30'
                          : 'bg-white/5 border-white/10'
                      }`}>
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs font-mono text-orange-300/70">
                            {node.id === 'node_root' ? '🌳 Root Node' : `📄 ${node.id}`}
                          </span>
                          <div className="flex items-center gap-2">
                            <label className="flex items-center gap-1.5 text-xs text-white/50 cursor-pointer">
                              <input
                                type="checkbox"
                                checked={node.isEndNode}
                                onChange={e => updateIvrNode(node.id, 'isEndNode', e.target.checked)}
                                className="w-3 h-3 accent-orange-400"
                                disabled={node.id === 'node_root'}
                              />
                              End node
                            </label>
                            {node.id !== 'node_root' && (
                              <button
                                type="button"
                                onClick={() => removeIvrNode(node.id)}
                                className="text-red-400/50 hover:text-red-400 text-xs px-1.5 py-0.5 border border-red-500/20 rounded transition-colors"
                              >✕ Remove</button>
                            )}
                          </div>
                        </div>
                        <textarea
                          rows={3}
                          value={node.message}
                          onChange={e => updateIvrNode(node.id, 'message', e.target.value)}
                          placeholder={node.id === 'node_root'
                            ? 'Welcome! Press 1 for Sales, 2 for Support, 3 for Hours'
                            : 'Enter the message for this node…'}
                          className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-orange-400/40 resize-none mb-3"
                        />
                        {!node.isEndNode && (
                          <div className="space-y-2">
                            {node.options.map((opt, optIdx) => (
                              <div key={optIdx} className="flex gap-2 items-center">
                                <span className="text-xs text-orange-300/60 w-5 shrink-0">{optIdx + 1}.</span>
                                <input
                                  type="text"
                                  value={opt.label}
                                  onChange={e => updateIvrOption(node.id, optIdx, 'label', e.target.value)}
                                  placeholder="Option label (e.g. Sales)"
                                  className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-white text-xs focus:outline-none focus:border-orange-400/40"
                                />
                                <span className="text-xs text-white/30">→</span>
                                <span className="text-xs font-mono text-orange-300/50 shrink-0">
                                  {opt.nextNodeId}
                                </span>
                                <button
                                  type="button"
                                  onClick={() => removeIvrOption(node.id, optIdx)}
                                  className="text-red-400/50 hover:text-red-400 text-base leading-none transition-colors"
                                >×</button>
                              </div>
                            ))}
                            <button
                              type="button"
                              onClick={() => addIvrOption(node.id)}
                              className="text-xs text-orange-400/70 hover:text-orange-400 border border-orange-500/20 hover:border-orange-500/40 px-3 py-1 rounded-md transition-colors"
                            >
                              + Add Option
                            </button>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {/* ═══════════════════════════════════════════════════════ */}

              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-medium text-white/80">🔑 Keyword Responses</h3>
                  <button
                    type="button"
                    onClick={addKeywordPair}
                    className="text-xs text-white/60 hover:text-white border border-white/20 hover:border-white/40 px-3 py-1 rounded-md transition-colors"
                  >
                    + Add Keyword
                  </button>
                </div>
                <p className="text-xs text-white/40">Define automatic replies for specific keywords (optional)</p>
                {keywordPairs.map((pair, index) => (
                  <div key={index} className="flex gap-2 items-center">
                    <input
                      type="text"
                      value={pair.keyword}
                      onChange={e => updateKeywordPair(index, 'keyword', e.target.value)}
                      placeholder="Keyword (e.g. price)"
                      className="w-1/3 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30"
                    />
                    <input
                      type="text"
                      value={pair.response}
                      onChange={e => updateKeywordPair(index, 'response', e.target.value)}
                      placeholder="Reply for this keyword"
                      className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30"
                    />
                    {keywordPairs.length > 1 && (
                      <button
                        type="button"
                        onClick={() => removeKeywordPair(index)}
                        className="text-red-400/60 hover:text-red-400 px-2 transition-colors text-lg leading-none"
                      >
                        ×
                      </button>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step 3: WhatsApp Setup */}
          {currentStep === 3 && (
            <div className="space-y-6 animate-fadeIn">
              <h2 className="text-2xl font-bitcount border-b border-white/10 pb-2">📞 WhatsApp Setup</h2>
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <p className="text-sm text-blue-300">
                  <strong>💡 How it works:</strong> BotSetu uses a shared Twilio WhatsApp number.
                  You don&apos;t need a WABA ID or Phone Number ID. Simply complete the wizard,
                  then click <strong>Activate</strong> in the Dashboard — your WhatsApp bot number is assigned instantly.
                </p>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-white/60 mb-2">Business Contact Number</label>
                  <input
                    type="tel"
                    name="phoneNumber"
                    value={formData.phoneNumber}
                    onChange={handleChange}
                    placeholder="+1234567890 (optional)"
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                  <p className="text-xs text-white/40 mt-1">Your business contact number for reference only</p>
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">BSP Provider</label>
                  <select
                    name="bspName"
                    value={formData.bspName}
                    onChange={handleChange}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  >
                    <option value="twilio">Twilio (Default)</option>
                    <option value="infobip">Infobip</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Step 4: Templates */}
          {currentStep === 4 && (
            <div className="space-y-6 animate-fadeIn">
              <h2 className="text-2xl font-bitcount border-b border-white/10 pb-2">📝 Templates</h2>
              <p className="text-white/60 text-sm">Configure message templates for your bot (optional)</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-white/60 mb-2">Template Name</label>
                  <input
                    type="text"
                    name="templateName"
                    value={formData.templateName}
                    onChange={handleChange}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">Template Category</label>
                  <select
                    name="templateCategory"
                    value={formData.templateCategory}
                    onChange={handleChange}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  >
                    <option value="">Select Category</option>
                    <option value="utility">Utility</option>
                    <option value="marketing">Marketing</option>
                  </select>
                </div>
                <div className="md:col-span-2">
                  <label className="block text-sm text-white/60 mb-2">Template Text</label>
                  <textarea
                    name="templateText"
                    value={formData.templateText}
                    onChange={handleChange}
                    rows={4}
                    placeholder="Use {{1}}, {{2}} for placeholders"
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 5: Conversation */}
          {currentStep === 5 && (
            <div className="space-y-6 animate-fadeIn">
              <h2 className="text-2xl font-bitcount border-b border-white/10 pb-2">💬 Conversation</h2>
              <p className="text-white/60 text-sm">Configure conversation flow settings (optional)</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-white/60 mb-2">Assigned Flow</label>
                  <input
                    type="text"
                    name="assignedFlow"
                    value={formData.assignedFlow}
                    onChange={handleChange}
                    placeholder="e.g., booking_flow"
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 6: Billing */}
          {currentStep === 6 && (
            <div className="space-y-6 animate-fadeIn">
              <h2 className="text-2xl font-bitcount border-b border-white/10 pb-2">💰 Billing</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm text-white/60 mb-2">Plan Type *</label>
                  <select
                    name="planType"
                    value={formData.planType}
                    onChange={handleChange}
                    required
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  >
                    <option value="">Select Plan</option>
                    <option value="free">Free</option>
                    <option value="starter">Starter</option>
                    <option value="pro">Pro</option>
                    <option value="enterprise">Enterprise</option>
                  </select>
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">Message Limit</label>
                  <input
                    type="number"
                    name="messageLimit"
                    value={formData.messageLimit}
                    onChange={handleChange}
                    placeholder="1000"
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between items-center pt-6 border-t border-white/10">
            <div>
              {currentStep > 1 && (
                <Button
                  type="button"
                  onClick={handlePrevious}
                  variant="ghost"
                  className="text-white border border-white/20 hover:border-white/40 hover:bg-white/5"
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Previous
                </Button>
              )}
            </div>
            
            <div className="flex gap-3">
              <Link href="/">
                <Button
                  type="button"
                  variant="ghost"
                  className="text-white/60 hover:text-white hover:bg-white/5"
                >
                  Cancel
                </Button>
              </Link>
              
              {currentStep < steps.length ? (
                <Button
                  type="button"
                  onClick={handleNext}
                  className="bg-white text-black hover:bg-white/90 font-medium"
                >
                  Next
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  disabled={loading}
                  className="bg-green-500 text-white hover:bg-green-600 font-medium"
                >
                  {loading ? 'Creating...' : 'Create Bot'}
                  <Check className="w-4 h-4 ml-2" />
                </Button>
              )}
            </div>
          </div>
        </form>
      </div>
    </div>

    {/* ── Success Modal ── */}
    {showSuccess && (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-100 flex items-center justify-center p-4">
        <div className="bg-zinc-900 border border-white/20 rounded-2xl p-8 max-w-md w-full shadow-[0_0_60px_rgba(34,197,94,0.15)] text-center">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <h2 className="text-2xl font-bitcount text-white mb-2">Bot Created!</h2>
          <p className="text-white/50 text-sm mb-4">Your bot is saved. Follow the steps below to go live.</p>

          {/* ── RAG Knowledge Base Upload (shown right after creation when RAG enabled) ── */}
          {aiRagEnabled && createdBusinessId && (
            <div className="text-left mb-6 p-4 bg-purple-500/5 border border-purple-500/20 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-purple-300 font-medium">📚 Upload Knowledge Base</span>
                {kbUploadedFiles.length > 0 && (
                  <span className="text-xs text-green-400">{kbUploadedFiles.length} file(s) uploaded</span>
                )}
              </div>
              <p className="text-xs text-white/40">
                Upload your business documents so the bot answers from them. Supports TXT, JSON, CSV, MD.
                You can also add more files later from the dashboard.
              </p>

              {kbUploadedFiles.length > 0 && (
                <div className="space-y-1">
                  {kbUploadedFiles.map((f, i) => (
                    <div key={i} className="flex items-center justify-between bg-white/5 rounded-lg px-3 py-1.5">
                      <span className="text-xs text-white/70 truncate">{f.name}</span>
                      <span className="text-xs text-purple-300 shrink-0 ml-2">{f.chunks} chunks</span>
                    </div>
                  ))}
                </div>
              )}

              <label className="block cursor-pointer">
                <div className={`border border-dashed rounded-lg px-4 py-3 text-center text-sm transition-colors ${
                  kbUploading
                    ? 'border-purple-500/30 text-purple-400/50 cursor-wait'
                    : 'border-purple-500/30 text-purple-300 hover:border-purple-400 hover:text-purple-200'
                }`}>
                  {kbUploading
                    ? (kbUploadProgress !== null && kbUploadProgress < 100
                        ? `⬆ Uploading… ${kbUploadProgress}%`
                        : '⏳ Embedding chunks…')
                    : '⬆ Click to upload a file (.txt / .json / .csv / .md)'}
                </div>

                {/* Progress bar */}
                {kbUploading && (
                  <div className="mt-2 space-y-1">
                    <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                      {kbUploadProgress !== null && kbUploadProgress < 100 ? (
                        <div className="h-full bg-purple-500 rounded-full transition-all duration-150" style={{ width: `${kbUploadProgress}%` }} />
                      ) : (
                        <div className="h-full w-full bg-purple-500/60 rounded-full animate-pulse" />
                      )}
                    </div>
                    <p className="text-xs text-purple-300/60 text-center">
                      {kbUploadProgress !== null && kbUploadProgress < 100
                        ? `Uploading file… ${kbUploadProgress}%`
                        : 'File uploaded — embedding chunks into vector store…'}
                    </p>
                  </div>
                )}

                <input
                  type="file"
                  accept=".txt,.json,.csv,.md"
                  className="hidden"
                  disabled={kbUploading}
                  onChange={e => {
                    const file = e.target.files?.[0]
                    if (!file || !createdBusinessId) return
                    e.target.value = ''
                    setKbUploading(true)
                    setKbUploadProgress(0)
                    const fd = new FormData()
                    fd.append('file', file)
                    const xhr = new XMLHttpRequest()
                    xhr.upload.onprogress = (ev) => {
                      if (ev.lengthComputable) setKbUploadProgress(Math.round((ev.loaded / ev.total) * 100))
                    }
                    xhr.upload.onload = () => setKbUploadProgress(100)
                    xhr.onload = () => {
                      try {
                        const data = JSON.parse(xhr.responseText)
                        if (xhr.status >= 200 && xhr.status < 300) {
                          setKbUploadedFiles(prev => [...prev, { name: file.name, chunks: data.chunks ?? 0 }])
                        } else {
                          alert(`❌ ${data.error || 'Upload failed'}`)
                        }
                      } catch { alert('Upload failed — unexpected response') }
                      setKbUploadProgress(null)
                      setKbUploading(false)
                    }
                    xhr.onerror = () => {
                      alert('Upload failed — is the Flask server running?')
                      setKbUploadProgress(null)
                      setKbUploading(false)
                    }
                    xhr.open('POST', `${BACKEND}/api/ai/kb/${createdBusinessId}`)
                    xhr.send(fd)
                  }}
                />
              </label>
            </div>
          )}

          <div className="text-left space-y-3 mb-7">
            {[
              { step: '1', label: 'Go to Dashboard', desc: 'Your new bot will appear in the list' },
              { step: '2', label: 'Click Activate', desc: 'Get your shared WhatsApp number instantly' },
              { step: '3', label: 'Set Webhook in Twilio', desc: 'Paste the webhook URL shown in the activation popup' },
              { step: '4', label: 'Test Your Bot', desc: 'Send a WhatsApp message and watch it auto-reply!' },
            ].map(({ step, label, desc }) => (
              <div key={step} className="flex gap-3 items-start">
                <div className="w-6 h-6 bg-green-500/20 border border-green-500/30 rounded-full flex items-center justify-center text-xs font-semibold text-green-400 shrink-0 mt-0.5">{step}</div>
                <div>
                  <p className="text-sm text-white font-medium">{label}</p>
                  <p className="text-xs text-white/40">{desc}</p>
                </div>
              </div>
            ))}
          </div>

          <button
            onClick={() => router.push('/dashboard')}
            className="w-full bg-white text-black hover:bg-white/90 py-3 rounded-xl font-medium transition-colors"
          >
            Go to Dashboard →
          </button>
        </div>
      </div>
    )}
    </>
  )
}
