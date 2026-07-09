'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useUser, UserButton } from '@clerk/nextjs'
import { Button } from '@/components/ui/button'
import { ArrowLeft, ArrowRight, Check, CheckCircle, Bot, Phone, Zap, Brain, FileText, Layers, Sparkles, Loader2 } from 'lucide-react'
import Link from 'next/link'

interface DbTemplate {
  id: string
  name: string
  icon: string
  category: string
  useCases: string[]
  intelligenceMode: string
  useCaseType: string
  aiModel: string
  aiSystemPrompt: string
  aiRagEnabled: boolean
  welcomeMessage: string
  fallbackMessage: string
  keywords: { keyword: string; response: string }[]
  flow: { label: string; type: string; branches?: { label: string; next: string | null }[] }[]
}

const steps = [
  { id: 1, name: 'Create Bot' },
  { id: 2, name: 'Intelligence' },
  { id: 3, name: 'Connect' },
]

type IntelligenceMode = 'workflow' | 'ai' | 'kb' | 'template'
type Channel = 'whatsapp' | 'ivr'

export default function CreateBotPage() {
  const router = useRouter()
  const { user } = useUser()
  const [loading, setLoading] = useState(false)
  const [currentStep, setCurrentStep] = useState(1)
  const [showSuccess, setShowSuccess] = useState(false)
  const [createdBusinessId, setCreatedBusinessId] = useState<string | null>(null)

  // ── New flow state ────────────────────────────────────────────
  const [channel, setChannel] = useState<Channel>('whatsapp')
  const [intelligenceMode, setIntelligenceMode] = useState<IntelligenceMode>('workflow')
  const [selectedTemplate, setSelectedTemplate] = useState<string | null>(null)

  const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:5000'

  // ── Form data ─────────────────────────────────────────────────
  const [formData, setFormData] = useState({
    botName: '',
    useCaseType: '',
    welcomeMessage: '',
    fallbackMessage: '',
    humanHandoffMessage: '',
    humanHandoff: false,
    phoneNumber: '',
  })

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target
    setFormData(prev => ({
      ...prev,
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value
    }))
  }

  // ── AI config ─────────────────────────────────────────────────
  const [aiModel, setAiModel] = useState('gemini-2.0-flash')
  const [aiSystemPrompt, setAiSystemPrompt] = useState('')
  const [ollamaModels, setOllamaModels] = useState<string[]>([])
  const [ollamaOnline, setOllamaOnline] = useState<boolean | null>(null)

  const fetchOllamaModels = async () => {
    try {
      const res = await fetch('/api/ai/models')
      const data = await res.json()
      setOllamaOnline(data.ollamaRunning)
      if (data.models?.length) setOllamaModels(data.models)
    } catch { setOllamaOnline(false) }
  }

  // ── KB upload ─────────────────────────────────────────────────
  const [kbUploading, setKbUploading] = useState(false)
  const [kbUploadProgress, setKbUploadProgress] = useState<number | null>(null)
  const [kbUploadedFiles, setKbUploadedFiles] = useState<{ name: string; chunks: number }[]>([])

  // ── IVR state ─────────────────────────────────────────────────
  interface IvrOption { label: string; nextNodeId: string }
  interface IvrNode { id: string; message: string; options: IvrOption[]; isEndNode: boolean }

  const makeNodeId = () => `node_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`
  const [ivrNodes, setIvrNodes] = useState<IvrNode[]>([
    { id: 'node_root', message: '', options: [], isEndNode: false },
  ])

  const addIvrChildNode = (parentId: string) => {
    const newId = makeNodeId()
    setIvrNodes(prev => [
      ...prev.map(n => n.id === parentId ? { ...n, isEndNode: false, options: [...n.options, { label: '', nextNodeId: newId }] } : n),
      { id: newId, message: '', options: [], isEndNode: true },
    ])
  }
  const removeIvrNode = (nodeId: string) => {
    if (nodeId === 'node_root') return
    setIvrNodes(prev => {
      const updated = prev.filter(n => n.id !== nodeId).map(n => ({ ...n, options: n.options.filter(o => o.nextNodeId !== nodeId) }))
      return updated.map(n => ({ ...n, isEndNode: n.options.length === 0 && n.id !== 'node_root' }))
    })
  }
  const updateIvrNode = (nodeId: string, field: 'message' | 'isEndNode', value: string | boolean) =>
    setIvrNodes(prev => prev.map(n => n.id === nodeId ? { ...n, [field]: value } : n))
  const updateIvrOption = (nodeId: string, optIdx: number, value: string) =>
    setIvrNodes(prev => prev.map(n => n.id === nodeId ? { ...n, options: n.options.map((o, i) => i === optIdx ? { ...o, label: value } : o) } : n))
  const nodeById = (id: string) => ivrNodes.find(n => n.id === id)

  // ── Mandi booking ─────────────────────────────────────────────
  const [mandiList, setMandiList] = useState([{ name: '', location: '', address: '' }])
  const [slotTimes, setSlotTimes] = useState(['9:00 AM – 10:00 AM', '10:00 AM – 11:00 AM', '11:00 AM – 12:00 PM', '2:00 PM – 3:00 PM'])
  const [maxPerSlot, setMaxPerSlot] = useState(10)
  const addMandi = () => setMandiList(p => [...p, { name: '', location: '', address: '' }])
  const removeMandi = (i: number) => setMandiList(p => p.filter((_, idx) => idx !== i))
  const updateMandi = (i: number, f: 'name' | 'location' | 'address', v: string) => setMandiList(p => p.map((m, idx) => idx === i ? { ...m, [f]: v } : m))
  const addSlot = () => setSlotTimes(p => [...p, ''])
  const removeSlot = (i: number) => setSlotTimes(p => p.filter((_, idx) => idx !== i))
  const updateSlot = (i: number, v: string) => setSlotTimes(p => p.map((s, idx) => idx === i ? v : s))

  // ── Keyword pairs ─────────────────────────────────────────────
  const [keywordPairs, setKeywordPairs] = useState<{ keyword: string; response: string }[]>([{ keyword: '', response: '' }])
  const addKeyword = () => setKeywordPairs(p => [...p, { keyword: '', response: '' }])
  const removeKeyword = (i: number) => setKeywordPairs(p => p.filter((_, idx) => idx !== i))
  const updateKeyword = (i: number, f: 'keyword' | 'response', v: string) => setKeywordPairs(p => p.map((k, idx) => idx === i ? { ...k, [f]: v } : k))

  // ── DB templates + AI generation ──────────────────────────────
  const [dbTemplates, setDbTemplates] = useState<DbTemplate[]>([])
  const [templatesLoading, setTemplatesLoading] = useState(false)
  const [aiPrompt, setAiPrompt] = useState('')
  const [aiGenerating, setAiGenerating] = useState(false)
  const [aiGenError, setAiGenError] = useState('')

  useEffect(() => {
    if (intelligenceMode !== 'template') return
    setTemplatesLoading(true)
    fetch('/api/templates')
      .then(r => r.json())
      .then(d => setDbTemplates(d.templates ?? []))
      .catch(() => {})
      .finally(() => setTemplatesLoading(false))
  }, [intelligenceMode])

  // ── Apply template ─────────────────────────────────────────────
  const applyTemplate = (tpl: DbTemplate) => {
    setSelectedTemplate(tpl.id)
    setIntelligenceMode(tpl.intelligenceMode as 'workflow' | 'ai' | 'kb' | 'template')
    setFormData(prev => ({
      ...prev,
      useCaseType: tpl.useCaseType,
      welcomeMessage: tpl.welcomeMessage,
      fallbackMessage: tpl.fallbackMessage,
    }))
    if (tpl.aiModel) setAiModel(tpl.aiModel)
    if (tpl.aiSystemPrompt) setAiSystemPrompt(tpl.aiSystemPrompt)
    setKeywordPairs(tpl.keywords.length ? tpl.keywords : [{ keyword: '', response: '' }])
  }

  const handleGenerateTemplate = async () => {
    if (!aiPrompt.trim()) return
    setAiGenerating(true)
    setAiGenError('')
    try {
      const res = await fetch('/api/ai/generate-template', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: aiPrompt }),
      })
      const data = await res.json()
      if (!res.ok) { setAiGenError(data.error || 'Generation failed'); return }
      applyTemplate({ ...data, id: `generated_${Date.now()}`, category: 'generated' } as DbTemplate)
    } catch {
      setAiGenError('Could not reach backend. Is Flask running?')
    } finally {
      setAiGenerating(false)
    }
  }

  // ── Validation ────────────────────────────────────────────────
  const validateStep = (step: number) => {
    if (step === 1) return !!(formData.botName.trim() && (channel === 'ivr' || formData.useCaseType))
    return true
  }

  const handleNext = () => {
    if (!validateStep(currentStep)) {
      alert('Please fill in all required fields.')
      return
    }
    // When switching to AI/KB, fetch models
    if (currentStep === 1 && (intelligenceMode === 'ai' || intelligenceMode === 'kb')) fetchOllamaModels()
    setCurrentStep(p => Math.min(p + 1, 3))
  }

  // ── Submit ────────────────────────────────────────────────────
  const handleSubmit = async () => {
    setLoading(true)
    const derivedBotType = (intelligenceMode === 'ai' || intelligenceMode === 'kb') ? 'ai' : 'normal'
    const derivedUseCaseType = channel === 'ivr' ? 'ivr' : formData.useCaseType

    try {
      const res = await fetch('/api/bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          botName: formData.botName,
          businessName: formData.botName,
          category: 'other',
          city: '',
          country: '',
          defaultLanguage: 'en',
          businessHours: '9 AM – 6 PM',
          botType: derivedBotType,
          useCaseType: derivedUseCaseType,
          autoReply: true,
          humanHandoff: formData.humanHandoff,
          humanHandoffMessage: formData.humanHandoffMessage,
          welcomeMessage: formData.welcomeMessage,
          fallbackMessage: formData.fallbackMessage,
          phoneNumber: formData.phoneNumber,
          planType: 'starter',
          messageLimit: 500,
          messageBalance: 500,
          keywordResponses: keywordPairs.reduce((acc: Record<string, string>, { keyword, response }) => {
            if (keyword.trim()) acc[keyword.trim().toLowerCase()] = response.trim()
            return acc
          }, {}),
          ...(derivedUseCaseType === 'mandi_booking' && {
            mandis: mandiList.filter(m => m.name.trim()),
            slots: slotTimes.filter(s => s.trim()),
            maxBookingsPerSlot: maxPerSlot,
          }),
          ...(derivedUseCaseType === 'ivr' && {
            ivrNodes: ivrNodes.filter(n => n.message.trim()),
          }),
          ...(derivedBotType === 'ai' && {
            aiModel,
            aiSystemPrompt,
            aiRagEnabled: intelligenceMode === 'kb',
          }),
          ownerUserId: user?.id,
          createdAt: new Date().toISOString(),
        }),
      })
      if (res.ok) {
        const data = await res.json()
        setCreatedBusinessId(data.businessId || null)
        setShowSuccess(true)
      } else {
        const err = await res.json()
        alert(`Error: ${err.message}`)
      }
    } catch {
      alert('Failed to create bot. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  // ── Shared input/textarea classes ─────────────────────────────
  const inputCls = 'w-full bg-white/5 border border-white/10 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors'
  const textareaCls = `${inputCls} resize-none`

  return (
    <>
    <div className="min-h-screen bg-transparent text-white py-10 px-4 sm:px-6 lg:px-8">
      <div className="max-w-3xl mx-auto">

        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <Link href="/dashboard" className="inline-flex items-center text-white/50 hover:text-white text-sm gap-1.5 transition-colors">
            <ArrowLeft className="w-4 h-4" /> Dashboard
          </Link>
          <UserButton />
        </div>

        {/* Title */}
        <div className="mb-8">
          <h1 className="text-3xl font-light mb-1">Create a Bot</h1>
          <p className="text-white/40 text-sm">Bot live in under 60 seconds</p>
        </div>

        {/* Step Progress */}
        <div className="flex items-center gap-2 mb-10">
          {steps.map((step, i) => (
            <div key={step.id} className="flex items-center gap-2 flex-1">
              <div className="flex items-center gap-2">
                <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-medium border transition-all ${
                  currentStep > step.id ? 'bg-green-500 border-green-500 text-white' :
                  currentStep === step.id ? 'bg-white border-white text-black' :
                  'bg-white/5 border-white/20 text-white/40'
                }`}>
                  {currentStep > step.id ? <Check className="w-3.5 h-3.5" /> : step.id}
                </div>
                <span className={`text-sm hidden sm:block ${currentStep >= step.id ? 'text-white' : 'text-white/30'}`}>{step.name}</span>
              </div>
              {i < steps.length - 1 && (
                <div className={`flex-1 h-px transition-all ${currentStep > step.id ? 'bg-green-500' : 'bg-white/10'}`} />
              )}
            </div>
          ))}
        </div>

        {/* ── STEP 1: Create Bot ────────────────────────────── */}
        {currentStep === 1 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-xl font-light mb-1">Name your bot</h2>
              <p className="text-white/40 text-sm">This is what customers will interact with</p>
            </div>

            {/* Bot Name */}
            <div>
              <label className="block text-sm text-white/60 mb-2">Bot Name *</label>
              <input
                type="text"
                name="botName"
                value={formData.botName}
                onChange={handleChange}
                placeholder="e.g. BPCL Support, Shop Assistant"
                className={inputCls}
                autoFocus
              />
            </div>

            {/* Channel */}
            <div>
              <label className="block text-sm text-white/60 mb-3">Channel *</label>
              <div className="grid grid-cols-2 gap-3">
                {([
                  { id: 'whatsapp', label: 'WhatsApp', icon: <Bot className="w-5 h-5" />, desc: 'Chat-based messaging bot' },
                  { id: 'ivr', label: 'IVR', icon: <Phone className="w-5 h-5" />, desc: 'Phone call menu system' },
                ] as const).map(ch => (
                  <button
                    key={ch.id}
                    type="button"
                    onClick={() => {
                      setChannel(ch.id)
                      if (ch.id === 'ivr') setFormData(p => ({ ...p, useCaseType: 'ivr' }))
                    }}
                    className={`p-4 rounded-xl border-2 text-left transition-all ${
                      channel === ch.id
                        ? 'border-white bg-white/10'
                        : 'border-white/15 bg-white/3 hover:border-white/30'
                    }`}
                  >
                    <div className={`mb-2 ${channel === ch.id ? 'text-white' : 'text-white/50'}`}>{ch.icon}</div>
                    <div className="font-medium text-sm">{ch.label}</div>
                    <div className="text-xs text-white/40 mt-0.5">{ch.desc}</div>
                  </button>
                ))}
              </div>
            </div>

            {/* Use Case (WhatsApp only) */}
            {channel === 'whatsapp' && (
              <div>
                <label className="block text-sm text-white/60 mb-3">What should this bot do? *</label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {[
                    { id: 'faq', label: 'Customer Support', icon: '🎧' },
                    { id: 'leads', label: 'Lead Generation', icon: '🎯' },
                    { id: 'booking', label: 'Appointment Booking', icon: '📅' },
                    { id: 'orders', label: 'Order Tracking', icon: '📦' },
                    { id: 'mandi_booking', label: 'Mandi Booking', icon: '🌾' },
                    { id: 'custom', label: 'Custom', icon: '⚙️' },
                  ].map(uc => (
                    <button
                      key={uc.id}
                      type="button"
                      onClick={() => setFormData(p => ({ ...p, useCaseType: uc.id }))}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        formData.useCaseType === uc.id
                          ? 'border-white/50 bg-white/10 text-white'
                          : 'border-white/10 bg-white/3 text-white/60 hover:border-white/25 hover:text-white'
                      }`}
                    >
                      <div className="text-base mb-1">{uc.icon}</div>
                      <div className="text-xs font-medium">{uc.label}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {channel === 'ivr' && (
              <div className="p-4 bg-orange-500/5 border border-orange-500/20 rounded-xl text-sm text-orange-300/80">
                📞 IVR creates a phone menu system. You&apos;ll build the call tree in the next step.
              </div>
            )}
          </div>
        )}

        {/* ── STEP 2: Intelligence ─────────────────────────── */}
        {currentStep === 2 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-xl font-light mb-1">How should your bot answer?</h2>
              <p className="text-white/40 text-sm">Choose the intelligence behind your bot</p>
            </div>

            {/* Intelligence mode selector */}
            {channel === 'whatsapp' ? (
              <div className="grid grid-cols-2 gap-3">
                {([
                  { id: 'workflow', label: 'Workflow Builder', icon: <Layers className="w-5 h-5" />, desc: 'Keywords, rules, auto-replies', color: 'green' },
                  { id: 'ai', label: 'AI Assistant', icon: <Brain className="w-5 h-5" />, desc: 'LLM-powered free responses', color: 'cyan' },
                  { id: 'kb', label: 'Knowledge Base', icon: <FileText className="w-5 h-5" />, desc: 'Answers from your documents', color: 'purple' },
                  { id: 'template', label: 'Prebuilt Template', icon: <Zap className="w-5 h-5" />, desc: 'Start from a ready-made bot', color: 'yellow' },
                ] as const).map(mode => {
                  const active = intelligenceMode === mode.id
                  const colorMap = { green: 'border-green-500/50 bg-green-500/10 text-green-400', cyan: 'border-cyan-500/50 bg-cyan-500/10 text-cyan-400', purple: 'border-purple-500/50 bg-purple-500/10 text-purple-400', yellow: 'border-yellow-500/50 bg-yellow-500/10 text-yellow-400' }
                  return (
                    <button
                      key={mode.id}
                      type="button"
                      onClick={() => {
                        setIntelligenceMode(mode.id)
                        if (mode.id === 'ai' || mode.id === 'kb') fetchOllamaModels()
                      }}
                      className={`p-4 rounded-xl border-2 text-left transition-all ${
                        active ? colorMap[mode.color] : 'border-white/15 bg-white/3 hover:border-white/25'
                      }`}
                    >
                      <div className={`mb-2 ${active ? '' : 'text-white/40'}`}>{mode.icon}</div>
                      <div className="font-medium text-sm">{mode.label}</div>
                      <div className="text-xs text-white/40 mt-0.5">{mode.desc}</div>
                    </button>
                  )
                })}
              </div>
            ) : (
              <div className="p-4 bg-orange-500/5 border border-orange-500/20 rounded-xl">
                <div className="flex items-center gap-2 mb-1">
                  <Phone className="w-4 h-4 text-orange-400" />
                  <span className="text-sm font-medium text-orange-400">IVR Menu Builder</span>
                </div>
                <p className="text-xs text-white/40">Build a multi-level phone menu. Callers press number keys to navigate.</p>
              </div>
            )}

            {/* ── Workflow config ───────────────────────────── */}
            {(intelligenceMode === 'workflow' || channel === 'ivr') && (
              <div className="space-y-4">

                {/* IVR Builder (IVR channel only) */}
                {channel === 'ivr' && (
                  <div className="space-y-3 p-5 bg-orange-500/5 border border-orange-500/20 rounded-xl">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-orange-400">IVR Call Tree</span>
                      <span className="text-xs text-white/30">{ivrNodes.length} node{ivrNodes.length !== 1 ? 's' : ''}</span>
                    </div>
                    <div className="space-y-3">
                      {ivrNodes.map(node => {
                        const parent = ivrNodes.find(n => n.options.some(o => o.nextNodeId === node.id))
                        const optIdx = parent?.options.findIndex(o => o.nextNodeId === node.id)
                        return (
                          <div key={node.id} className={`rounded-xl border p-4 space-y-3 ${node.id === 'node_root' ? 'border-orange-500/40 bg-orange-500/10' : 'border-white/10 bg-white/5'}`}>
                            <div className="flex items-center gap-2">
                              <span className="text-xs text-orange-400/70 font-mono">
                                {node.id === 'node_root' ? '🌳 Root menu' : `↳ Option ${(optIdx ?? 0) + 1}`}
                              </span>
                              <span className={`ml-auto text-xs px-2 py-0.5 rounded-full border ${node.isEndNode ? 'bg-orange-500/15 text-orange-300 border-orange-500/30' : 'bg-green-500/15 text-green-300 border-green-500/30'}`}>
                                {node.isEndNode ? 'End' : `${node.options.length} sub-options`}
                              </span>
                              {node.id !== 'node_root' && (
                                <button type="button" onClick={() => removeIvrNode(node.id)} className="text-red-400/50 hover:text-red-400 text-lg leading-none">×</button>
                              )}
                            </div>
                            {node.id !== 'node_root' && parent && (
                              <input
                                type="text"
                                value={parent.options[optIdx!]?.label ?? ''}
                                onChange={e => updateIvrOption(parent.id, optIdx!, e.target.value)}
                                placeholder="Option label (e.g. Sales, Support)"
                                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-orange-500/40"
                              />
                            )}
                            <textarea
                              rows={3}
                              value={node.message}
                              onChange={e => updateIvrNode(node.id, 'message', e.target.value)}
                              placeholder={node.id === 'node_root' ? 'Welcome! Please choose:\n1️⃣ Sales\n2️⃣ Support\n3️⃣ Hours' : 'Our sales team will call you back shortly.'}
                              className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-orange-400/40 resize-none"
                            />
                            {node.options.length > 0 && (
                              <div className="space-y-1">
                                {node.options.map((opt, oi) => (
                                  <div key={oi} className="flex items-center gap-2 text-xs text-white/40">
                                    <span className="w-5 h-5 flex items-center justify-center rounded-full bg-orange-500/20 text-orange-300 shrink-0">{oi + 1}</span>
                                    <span className="truncate">{opt.label || <em className="opacity-50">unlabelled</em>}</span>
                                    <span className="font-mono text-white/20 ml-auto">{nodeById(opt.nextNodeId)?.isEndNode ? '🔚' : '▶'}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                            <button type="button" onClick={() => addIvrChildNode(node.id)} className="text-xs text-orange-400/70 hover:text-orange-400 border border-orange-500/20 hover:border-orange-500/40 px-3 py-1.5 rounded-md w-full transition-colors">
                              + Add Sub-option
                            </button>
                          </div>
                        )
                      })}
                    </div>
                    <p className="text-xs text-white/30">💡 Keep each level to ≤9 options so callers can press a single key.</p>
                  </div>
                )}

                {/* Mandi Booking config */}
                {formData.useCaseType === 'mandi_booking' && channel === 'whatsapp' && (
                  <div className="space-y-4 p-4 bg-yellow-500/5 border border-yellow-500/20 rounded-xl">
                    <div className="flex items-center gap-2">
                      <span>🌾</span>
                      <h3 className="text-sm font-medium text-yellow-400">Mandi Booking Configuration</h3>
                    </div>
                    <p className="text-xs text-white/40">The bot guides farmers: name → village → crop → quantity → mandi → slot → token.</p>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-white/70">Mandis / Markets</label>
                        <button type="button" onClick={addMandi} className="text-xs text-yellow-400/70 hover:text-yellow-400 border border-yellow-500/20 px-3 py-1 rounded-md transition-colors">+ Add Mandi</button>
                      </div>
                      {mandiList.map((m, i) => (
                        <div key={i} className="grid grid-cols-3 gap-2 items-center">
                          <input type="text" value={m.name} onChange={e => updateMandi(i, 'name', e.target.value)} placeholder="Mandi Name *" className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                          <input type="text" value={m.location} onChange={e => updateMandi(i, 'location', e.target.value)} placeholder="Location" className="bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                          <div className="flex gap-2">
                            <input type="text" value={m.address} onChange={e => updateMandi(i, 'address', e.target.value)} placeholder="Address" className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                            {mandiList.length > 1 && <button type="button" onClick={() => removeMandi(i)} className="text-red-400/60 hover:text-red-400 text-lg px-1 transition-colors">×</button>}
                          </div>
                        </div>
                      ))}
                    </div>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <label className="text-sm text-white/70">Daily Time Slots</label>
                        <button type="button" onClick={addSlot} className="text-xs text-yellow-400/70 hover:text-yellow-400 border border-yellow-500/20 px-3 py-1 rounded-md transition-colors">+ Add Slot</button>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        {slotTimes.map((s, i) => (
                          <div key={i} className="flex gap-2">
                            <input type="text" value={s} onChange={e => updateSlot(i, e.target.value)} placeholder="9:00 AM – 10:00 AM" className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                            {slotTimes.length > 1 && <button type="button" onClick={() => removeSlot(i)} className="text-red-400/60 hover:text-red-400 text-lg px-1 transition-colors">×</button>}
                          </div>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="text-sm text-white/70 block mb-2">Max Bookings per Slot</label>
                      <input type="number" min={1} max={100} value={maxPerSlot} onChange={e => setMaxPerSlot(Number(e.target.value))} className="w-28 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none" />
                    </div>
                  </div>
                )}

                {/* Keyword pairs (WhatsApp workflow) */}
                {channel === 'whatsapp' && (
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="text-sm font-medium text-white/80">Keyword Responses</h3>
                        <p className="text-xs text-white/40">Auto-reply when a message contains these words</p>
                      </div>
                      <button type="button" onClick={addKeyword} className="text-xs text-white/60 hover:text-white border border-white/20 hover:border-white/40 px-3 py-1 rounded-md transition-colors">+ Add</button>
                    </div>
                    {keywordPairs.map((pair, i) => (
                      <div key={i} className="flex gap-2 items-center">
                        <input type="text" value={pair.keyword} onChange={e => updateKeyword(i, 'keyword', e.target.value)} placeholder="Keyword" className="w-1/3 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                        <input type="text" value={pair.response} onChange={e => updateKeyword(i, 'response', e.target.value)} placeholder="Reply" className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-white/30" />
                        {keywordPairs.length > 1 && <button type="button" onClick={() => removeKeyword(i)} className="text-red-400/60 hover:text-red-400 text-lg px-1 transition-colors">×</button>}
                      </div>
                    ))}
                  </div>
                )}

                {/* Welcome / Fallback */}
                {channel === 'whatsapp' && (
                  <div className="space-y-4 pt-2">
                    <div>
                      <label className="block text-sm text-white/60 mb-2">Welcome Message</label>
                      <textarea name="welcomeMessage" value={formData.welcomeMessage} onChange={handleChange} rows={3} placeholder={`Hi! 👋 Welcome to ${formData.botName || 'our business'}. How can I help you?`} className={textareaCls} />
                    </div>
                    <div>
                      <label className="block text-sm text-white/60 mb-2">Fallback Message</label>
                      <textarea name="fallbackMessage" value={formData.fallbackMessage} onChange={handleChange} rows={2} placeholder="Sorry, I didn't understand. Type 'help' for assistance." className={textareaCls} />
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* ── AI config ─────────────────────────────────── */}
            {(intelligenceMode === 'ai' || intelligenceMode === 'kb') && channel === 'whatsapp' && (
              <div className="space-y-4 p-5 bg-cyan-500/5 border border-cyan-500/20 rounded-xl">
                <div className="flex items-center gap-2">
                  <Brain className="w-4 h-4 text-cyan-400" />
                  <h3 className="text-sm font-medium text-cyan-400">
                    {intelligenceMode === 'kb' ? 'Knowledge Base + AI' : 'AI Configuration'}
                  </h3>
                  {ollamaOnline === true && <span className="ml-auto text-xs text-green-400 bg-green-500/10 px-2 py-0.5 rounded-full">● Ollama online</span>}
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">AI Model</label>
                  <select value={aiModel} onChange={e => setAiModel(e.target.value)} className={inputCls}>
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
                <div>
                  <label className="block text-sm text-white/60 mb-2">System Prompt <span className="text-white/30">(optional)</span></label>
                  <textarea
                    rows={4}
                    value={aiSystemPrompt}
                    onChange={e => setAiSystemPrompt(e.target.value)}
                    placeholder={`You are a helpful assistant for ${formData.botName || 'this business'}. Reply clearly and in the same language the user writes in.`}
                    className={textareaCls}
                  />
                </div>
                {intelligenceMode === 'kb' && (
                  <div className="p-3 bg-purple-500/10 border border-purple-500/20 rounded-lg text-xs text-purple-300">
                    📁 You&apos;ll upload your documents right after the bot is created — PDFs, TXT, CSV, JSON all supported.
                  </div>
                )}
              </div>
            )}

            {/* ── Template picker ───────────────────────────── */}
            {intelligenceMode === 'template' && channel === 'whatsapp' && (
              <div className="space-y-4">

                {/* DB templates */}
                {templatesLoading ? (
                  <div className="flex items-center gap-2 text-white/40 text-sm py-4">
                    <Loader2 className="w-4 h-4 animate-spin" /> Loading templates…
                  </div>
                ) : (
                  <div className="space-y-2">
                    {dbTemplates.map(tpl => (
                      <button
                        key={tpl.id}
                        type="button"
                        onClick={() => applyTemplate(tpl)}
                        className={`w-full p-4 rounded-xl border text-left transition-all ${
                          selectedTemplate === tpl.id
                            ? 'border-yellow-500/50 bg-yellow-500/10'
                            : 'border-white/10 bg-white/5 hover:border-white/25'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <span className="text-2xl shrink-0">{tpl.icon}</span>
                          <div className="min-w-0 flex-1">
                            <div className="font-medium text-sm">{tpl.name}</div>
                            <div className="text-xs text-white/40 mt-0.5 truncate">{tpl.useCases.join(', ')}</div>
                            <div className="flex gap-2 mt-1.5 flex-wrap">
                              {tpl.keywords.length > 0 && (
                                <span className="text-xs text-white/25 bg-white/5 px-2 py-0.5 rounded-full">{tpl.keywords.length} keywords</span>
                              )}
                              <span className="text-xs text-white/25 bg-white/5 px-2 py-0.5 rounded-full capitalize">{tpl.intelligenceMode}</span>
                            </div>
                            {/* Mini flow preview */}
                            {tpl.flow.length > 0 && (
                              <div className="flex items-center gap-1 mt-2 flex-wrap">
                                {tpl.flow.slice(0, 5).map((step, si) => (
                                  <span key={si} className="flex items-center gap-1 text-white/20 text-xs">
                                    {si > 0 && <span>→</span>}
                                    <span className="bg-white/5 px-1.5 py-0.5 rounded">{step.label}</span>
                                  </span>
                                ))}
                                {tpl.flow.length > 5 && <span className="text-white/20 text-xs">+{tpl.flow.length - 5} more</span>}
                              </div>
                            )}
                          </div>
                          {selectedTemplate === tpl.id && <Check className="w-4 h-4 text-yellow-400 shrink-0 mt-0.5" />}
                        </div>
                      </button>
                    ))}
                  </div>
                )}

                {selectedTemplate && !selectedTemplate.startsWith('generated_') && (
                  <div className="p-3 bg-green-500/5 border border-green-500/20 rounded-lg text-xs text-green-400">
                    ✓ Template applied — intelligence mode, keywords and messages pre-filled.
                  </div>
                )}

                {/* Build with AI */}
                <div className="border border-dashed border-white/20 rounded-xl p-5 space-y-3 mt-2">
                  <div className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-purple-400" />
                    <span className="text-sm font-medium text-purple-400">Build with AI</span>
                    <span className="text-xs text-white/30 bg-white/5 px-2 py-0.5 rounded-full ml-auto">Needs Ollama</span>
                  </div>
                  <p className="text-xs text-white/40">Describe the bot you want and the local LLM will generate a complete template — greeting, workflow, keywords and flow.</p>
                  <div className="space-y-2">
                    <div className="grid grid-cols-2 gap-2 text-xs text-white/30">
                      {[
                        '"I need a hospital appointment bot."',
                        '"I need a GST support bot."',
                        '"I need a scholarship inquiry bot."',
                        '"I need an AI HR assistant."',
                      ].map(ex => (
                        <button
                          key={ex}
                          type="button"
                          onClick={() => setAiPrompt(ex.replace(/"/g, ''))}
                          className="text-left p-2 bg-white/3 hover:bg-white/8 border border-white/8 rounded-lg transition-colors truncate"
                        >
                          {ex}
                        </button>
                      ))}
                    </div>
                    <textarea
                      rows={2}
                      value={aiPrompt}
                      onChange={e => setAiPrompt(e.target.value)}
                      placeholder="Describe the bot you want…"
                      className="w-full bg-white/5 border border-white/15 rounded-lg px-3 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500/40 resize-none"
                    />
                    {aiGenError && <p className="text-xs text-red-400">{aiGenError}</p>}
                    <button
                      type="button"
                      disabled={!aiPrompt.trim() || aiGenerating}
                      onClick={handleGenerateTemplate}
                      className="w-full flex items-center justify-center gap-2 bg-purple-600 hover:bg-purple-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-medium py-2.5 rounded-lg transition-colors"
                    >
                      {aiGenerating ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating…</> : <><Sparkles className="w-4 h-4" /> Generate Bot</>}
                    </button>
                    {selectedTemplate?.startsWith('generated_') && (
                      <div className="p-3 bg-purple-500/5 border border-purple-500/20 rounded-lg text-xs text-purple-300">
                        ✓ AI-generated template applied! Review the settings below before continuing.
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── STEP 3: Connect ──────────────────────────────── */}
        {currentStep === 3 && (
          <div className="space-y-6 animate-fadeIn">
            <div>
              <h2 className="text-xl font-light mb-1">
                {channel === 'whatsapp' ? 'Connect WhatsApp' : 'Connect IVR'}
              </h2>
              <p className="text-white/40 text-sm">You can do this now or skip and connect later from the dashboard</p>
            </div>

            {channel === 'whatsapp' && (
              <div className="space-y-3">
                {[
                  { id: 'twilio', label: 'Connect via Twilio', desc: 'Use a shared sandbox number instantly — best for testing', badge: 'Recommended', badgeColor: 'text-green-400 bg-green-500/10' },
                  { id: 'meta', label: 'Connect Meta Account', desc: 'Use your own WhatsApp Business number via Meta Cloud API', badge: 'Coming soon', badgeColor: 'text-white/30 bg-white/5' },
                  { id: 'later', label: "I'll do this later", desc: 'Create the bot now, connect WhatsApp from the dashboard', badge: null, badgeColor: '' },
                ].map(opt => (
                  <button
                    key={opt.id}
                    type="button"
                    disabled={opt.id === 'meta'}
                    onClick={() => setChannel(opt.id === 'later' ? channel : channel)}
                    className={`w-full p-4 rounded-xl border text-left transition-all ${
                      opt.id === 'meta' ? 'border-white/5 bg-white/3 opacity-40 cursor-not-allowed' :
                      'border-white/15 bg-white/5 hover:border-white/30'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-medium text-sm">{opt.label}</div>
                        <div className="text-xs text-white/40 mt-0.5">{opt.desc}</div>
                      </div>
                      {opt.badge && <span className={`text-xs px-2 py-0.5 rounded-full ${opt.badgeColor}`}>{opt.badge}</span>}
                    </div>
                  </button>
                ))}

                <div className="p-4 bg-blue-500/5 border border-blue-500/15 rounded-xl text-sm">
                  <p className="text-blue-300 font-medium mb-1">💡 How Twilio Sandbox works</p>
                  <p className="text-white/40 text-xs">After creating the bot, click <strong className="text-white/70">Activate</strong> in the dashboard — you&apos;ll get a shared WhatsApp number + webhook URL instantly. Paste the webhook URL in Twilio Console and you&apos;re live.</p>
                </div>
              </div>
            )}

            {channel === 'ivr' && (
              <div className="space-y-4">
                <div className="p-4 bg-orange-500/5 border border-orange-500/20 rounded-xl space-y-3">
                  <p className="text-sm font-medium text-orange-400">📞 Voice Webhook Setup</p>
                  <div className="text-xs text-white/50 space-y-1.5">
                    <p>1. After bot creation, go to Dashboard → your bot → click the orange phone button</p>
                    <p>2. Copy the voice webhook URL shown in the popup</p>
                    <p>3. In Twilio Console → Phone Numbers → your IVR number → set <em>"A call comes in"</em> to that URL</p>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-white/60 mb-2">Your Twilio Phone Number <span className="text-white/30">(optional, for reference)</span></label>
                  <input type="tel" name="phoneNumber" value={formData.phoneNumber} onChange={handleChange} placeholder="+1234567890" className={inputCls} />
                </div>
              </div>
            )}

            {/* Summary */}
            <div className="p-4 bg-white/3 border border-white/10 rounded-xl space-y-2">
              <p className="text-sm font-medium text-white/70 mb-3">Summary</p>
              <div className="grid grid-cols-2 gap-y-2 text-xs">
                <span className="text-white/40">Bot Name</span><span className="text-white">{formData.botName}</span>
                <span className="text-white/40">Channel</span><span className="text-white capitalize">{channel}</span>
                {channel === 'whatsapp' && <><span className="text-white/40">Use Case</span><span className="text-white capitalize">{formData.useCaseType}</span></>}
                <span className="text-white/40">Intelligence</span>
                <span className="text-white capitalize">
                  {channel === 'ivr' ? 'IVR Workflow' : intelligenceMode === 'kb' ? 'Knowledge Base' : intelligenceMode === 'ai' ? 'AI Assistant' : intelligenceMode === 'template' ? 'Prebuilt Template' : 'Workflow Builder'}
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ── Navigation ───────────────────────────────────── */}
        <div className="flex justify-between items-center mt-10 pt-6 border-t border-white/10">
          <div>
            {currentStep > 1 && (
              <Button type="button" onClick={() => setCurrentStep(p => p - 1)} variant="ghost" className="text-white border border-white/20 hover:border-white/40 hover:bg-white/5">
                <ArrowLeft className="w-4 h-4 mr-2" /> Back
              </Button>
            )}
          </div>
          <div className="flex gap-3">
            <Link href="/dashboard">
              <Button type="button" variant="ghost" className="text-white/50 hover:text-white hover:bg-white/5">Cancel</Button>
            </Link>
            {currentStep < 3 ? (
              <Button type="button" onClick={handleNext} className="bg-white text-black hover:bg-white/90 font-medium">
                Next <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            ) : (
              <Button type="button" onClick={handleSubmit} disabled={loading} className="bg-green-500 text-white hover:bg-green-600 font-medium px-6">
                {loading ? 'Creating...' : 'Create Bot'} {!loading && <Check className="w-4 h-4 ml-2" />}
              </Button>
            )}
          </div>
        </div>

      </div>
    </div>

    {/* ── Success Modal ────────────────────────────────────── */}
    {showSuccess && (
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div className="bg-zinc-900 border border-white/20 rounded-2xl p-8 max-w-md w-full shadow-[0_0_60px_rgba(34,197,94,0.15)] text-center">
          <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
          <h2 className="text-2xl font-light text-white mb-2">Bot Created!</h2>
          <p className="text-white/50 text-sm mb-6">Your bot is saved. Follow the steps below to go live.</p>

          {/* KB upload */}
          {intelligenceMode === 'kb' && createdBusinessId && (
            <div className="text-left mb-6 p-4 bg-purple-500/5 border border-purple-500/20 rounded-xl space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-purple-300 font-medium">📚 Upload Knowledge Base</span>
                {kbUploadedFiles.length > 0 && <span className="text-xs text-green-400">{kbUploadedFiles.length} file(s) uploaded</span>}
              </div>
              <p className="text-xs text-white/40">Upload your documents (TXT, JSON, CSV, MD). You can add more later from the dashboard.</p>
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
                <div className={`border border-dashed rounded-lg px-4 py-3 text-center text-sm transition-colors ${kbUploading ? 'border-purple-500/30 text-purple-400/50 cursor-wait' : 'border-purple-500/30 text-purple-300 hover:border-purple-400 hover:text-purple-200'}`}>
                  {kbUploading
                    ? (kbUploadProgress !== null && kbUploadProgress < 100 ? `⬆ Uploading… ${kbUploadProgress}%` : '⏳ Embedding chunks…')
                    : '⬆ Click to upload a file (.txt / .json / .csv / .md)'}
                </div>
                {kbUploading && (
                  <div className="mt-2 space-y-1">
                    <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                      {kbUploadProgress !== null && kbUploadProgress < 100
                        ? <div className="h-full bg-purple-500 rounded-full transition-all" style={{ width: `${kbUploadProgress}%` }} />
                        : <div className="h-full w-full bg-purple-500/60 rounded-full animate-pulse" />}
                    </div>
                  </div>
                )}
                <input type="file" accept=".txt,.json,.csv,.md" className="hidden" disabled={kbUploading} onChange={e => {
                  const file = e.target.files?.[0]
                  if (!file || !createdBusinessId) return
                  e.target.value = ''
                  setKbUploading(true)
                  setKbUploadProgress(0)
                  const fd = new FormData()
                  fd.append('file', file)
                  const xhr = new XMLHttpRequest()
                  xhr.upload.onprogress = ev => { if (ev.lengthComputable) setKbUploadProgress(Math.round((ev.loaded / ev.total) * 100)) }
                  xhr.upload.onload = () => setKbUploadProgress(100)
                  xhr.onload = () => {
                    try {
                      const data = JSON.parse(xhr.responseText)
                      if (xhr.status >= 200 && xhr.status < 300) setKbUploadedFiles(p => [...p, { name: file.name, chunks: data.chunks ?? 0 }])
                      else alert(`❌ ${data.error || 'Upload failed'}`)
                    } catch { alert('Upload failed — unexpected response') }
                    setKbUploadProgress(null)
                    setKbUploading(false)
                  }
                  xhr.onerror = () => { alert('Upload failed — is Flask running?'); setKbUploadProgress(null); setKbUploading(false) }
                  xhr.open('POST', `${BACKEND}/api/ai/kb/${createdBusinessId}`)
                  xhr.send(fd)
                }} />
              </label>
            </div>
          )}

          <div className="text-left space-y-3 mb-7">
            {[
              { step: '1', label: 'Go to Dashboard', desc: 'Your new bot appears in the list' },
              { step: '2', label: 'Click Activate', desc: 'Get your shared WhatsApp number instantly' },
              { step: '3', label: 'Set Webhook in Twilio', desc: 'Paste the webhook URL shown in the popup' },
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

          <button onClick={() => router.push('/dashboard')} className="w-full bg-white text-black hover:bg-white/90 py-3 rounded-xl font-medium transition-colors">
            Go to Dashboard →
          </button>
        </div>
      </div>
    )}
    </>
  )
}
