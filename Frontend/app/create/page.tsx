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
        return !!(formData.botName && formData.useCaseType)
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
          ownerUserId: user?.id,
          createdAt: new Date().toISOString(),
        }),
      })

      if (response.ok) {
        const data = await response.json()
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
    <div className="min-h-screen bg-black text-white py-12 px-4 sm:px-6 lg:px-8" style={{ fontFamily: 'var(--font-bitcount)' }}>
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
          <h1 className="text-4xl font-light mb-2">Create Your Bot</h1>
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
              <h2 className="text-2xl font-light border-b border-white/10 pb-2">🧾 Business Info</h2>
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
              <h2 className="text-2xl font-light border-b border-white/10 pb-2">🤖 Bot Config</h2>
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
                  </select>
                </div>
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
              </div>

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
              <h2 className="text-2xl font-light border-b border-white/10 pb-2">📞 WhatsApp Setup</h2>
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
              <h2 className="text-2xl font-light border-b border-white/10 pb-2">📝 Templates</h2>
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
              <h2 className="text-2xl font-light border-b border-white/10 pb-2">💬 Conversation</h2>
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
              <h2 className="text-2xl font-light border-b border-white/10 pb-2">💰 Billing</h2>
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
          <h2 className="text-2xl font-light text-white mb-2">Bot Created!</h2>
          <p className="text-white/50 text-sm mb-6">Your bot is saved. Follow the steps below to go live.</p>

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
