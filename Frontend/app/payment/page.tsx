'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { UserButton } from '@clerk/nextjs'
import { Bot, Check, ArrowLeft, CreditCard, Shield, Zap, Building2, Rocket } from 'lucide-react'
import { Button } from '@/components/ui/button'

declare global {
  interface Window {
    Razorpay: any
  }
}

export default function PaymentPage() {
  const [loading, setLoading] = useState<string | null>(null)
  const [scriptLoaded, setScriptLoaded] = useState(false)

  const plans = [
    {
      name: 'Starter',
      icon: Zap,
      price: 49,
      description: 'Perfect for small businesses',
      features: [
        '1,000 messages/month',
        '2 WhatsApp bots',
        'Basic templates',
        'Auto-reply',
        'Email support'
      ]
    },
    {
      name: 'Pro',
      icon: Building2,
      price: 149,
      description: 'For growing businesses',
      features: [
        '10,000 messages/month',
        '10 WhatsApp bots',
        'AI responses',
        'Priority support',
        'Advanced analytics'
      ],
      popular: true
    },
    {
      name: 'Enterprise',
      icon: Rocket,
      price: 499,
      description: 'For large organizations',
      features: [
        'Unlimited messages',
        'Unlimited bots',
        'Full AI capabilities',
        'Dedicated support',
        'Custom integrations'
      ]
    }
  ]

  useEffect(() => {
    // Load Razorpay script
    const script = document.createElement('script')
    script.src = 'https://checkout.razorpay.com/v1/checkout.js'
    script.async = true
    script.onload = () => setScriptLoaded(true)
    document.body.appendChild(script)

    return () => {
      document.body.removeChild(script)
    }
  }, [])

  const handlePayment = async (plan: typeof plans[0]) => {
    setLoading(plan.name)
    
    try {
      // Create order on backend
      const orderResponse = await fetch('/api/razorpay/create-order', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: plan.price,
          planName: plan.name,
          planType: 'subscription'
        })
      })

      if (!orderResponse.ok) {
        throw new Error('Failed to create order')
      }

      const orderData = await orderResponse.json()

      // Configure Razorpay options
      const options = {
        key: orderData.keyId,
        amount: orderData.amount,
        currency: orderData.currency,
        name: 'BotSetu',
        description: `${plan.name} Plan Subscription`,
        order_id: orderData.orderId,
        handler: async function (response: any) {
          // Verify payment on backend
          try {
            const verifyResponse = await fetch('/api/razorpay/verify-payment', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                amount: orderData.amount,
                planName: plan.name,
                planType: 'subscription'
              })
            })

            const verifyData = await verifyResponse.json()

            if (verifyData.success) {
              alert('Payment successful! Thank you for subscribing to ' + plan.name)
              window.location.href = '/dashboard'
            } else {
              alert('Payment verification failed. Please contact support.')
            }
          } catch (error) {
            console.error('Verification error:', error)
            alert('Payment verification failed. Please contact support.')
          }
        },
        prefill: {
          name: '',
          email: '',
          contact: ''
        },
        theme: {
          color: '#000000'
        },
        modal: {
          ondismiss: function() {
            setLoading(null)
          }
        }
      }

      // Open Razorpay checkout
      if (scriptLoaded && window.Razorpay) {
        const razorpay = new window.Razorpay(options)
        razorpay.open()
      } else {
        alert('Payment gateway is loading. Please try again in a moment.')
      }
    } catch (error) {
      console.error('Payment error:', error)
      alert('Failed to initiate payment. Please try again.')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="min-h-screen bg-black text-white flex flex-col">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/50 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center gap-2">
              <Bot className="w-6 h-6" />
              <span className="font-light text-lg">BotSetu</span>
            </Link>
            <div className="flex items-center gap-4">
              <Link href="/dashboard">
                <Button variant="ghost" className="text-white/60 hover:text-white">
                  Dashboard
                </Button>
              </Link>
              <UserButton />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 px-4 sm:px-6 lg:px-8 py-16">
        <div className="max-w-7xl mx-auto">
          {/* Title */}
          <div className="text-center mb-16">
            <h1 className="text-5xl md:text-6xl font-light mb-6">
              Choose Your <span className="font-normal">Plan</span>
            </h1>
            <p className="text-xl text-white/60 mb-8 max-w-2xl mx-auto">
              Secure payment powered by Razorpay. Start your subscription today.
            </p>
            
            {/* Trust Badges */}
            <div className="flex items-center justify-center gap-8 text-white/40 text-sm">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4" />
                <span>Secure Payment</span>
              </div>
              <div className="flex items-center gap-2">
                <CreditCard className="w-4 h-4" />
                <span>UPI, Cards & More</span>
              </div>
            </div>
          </div>

          {/* Pricing Cards */}
          <div className="grid md:grid-cols-3 gap-8 mb-16">
            {plans.map((plan) => {
              const Icon = plan.icon
              return (
                <div
                  key={plan.name}
                  className={`relative bg-white/5 border rounded-xl p-8 hover:bg-white/10 transition-all ${
                    plan.popular 
                      ? 'border-blue-500 shadow-lg shadow-blue-500/20 scale-105' 
                      : 'border-white/10'
                  }`}
                >
                  {plan.popular && (
                    <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-blue-500 text-white text-xs font-medium px-4 py-1 rounded-full">
                      Most Popular
                    </div>
                  )}
                  
                  <div className="mb-6">
                    <Icon className="w-12 h-12 text-white/60 mb-4" />
                    <h3 className="text-2xl font-light mb-2">{plan.name}</h3>
                    <p className="text-sm text-white/60 mb-6">{plan.description}</p>
                    
                    <div className="flex items-baseline mb-2">
                      <span className="text-white/60 text-2xl mr-1">$</span>
                      <span className="text-5xl font-light">{plan.price}</span>
                      <span className="text-white/60 ml-2">/month</span>
                    </div>
                  </div>

                  <Button 
                    onClick={() => handlePayment(plan)}
                    disabled={loading !== null}
                    className={`w-full mb-6 ${
                      plan.popular 
                        ? 'bg-blue-500 hover:bg-blue-600 text-white' 
                        : 'bg-white text-black hover:bg-white/90'
                    }`}
                  >
                    {loading === plan.name ? 'Processing...' : 'Subscribe Now'}
                  </Button>

                  <div className="space-y-3">
                    {plan.features.map((feature, idx) => (
                      <div key={idx} className="flex items-start gap-3">
                        <Check className="w-5 h-5 text-green-400 shrink-0 mt-0.5" />
                        <span className="text-sm text-white/80">{feature}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>

          {/* Back Button */}
          <div className="text-center">
            <Link href="/dashboard">
              <Button variant="outline" className="border-white/20 text-white hover:bg-white/5">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back to Dashboard
              </Button>
            </Link>
          </div>

          {/* Footer Note */}
          <div className="mt-12 text-sm text-white/40">
            <p>Have questions? Contact us at <span className="text-white/60">support@botsetu.com</span></p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center text-white/40 text-sm">
          <p>&copy; 2026 BotSetu. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
