'use client'

import Link from 'next/link'
import { UserButton } from '@clerk/nextjs'
import { Bot, Check, ArrowRight, Zap, Building2, Rocket } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function PricingPage() {
  const plans = [
    {
      name: 'Starter',
      icon: Zap,
      price: '49',
      description: 'Perfect for small businesses getting started with WhatsApp automation',
      features: [
        '1,000 messages/month',
        '2 WhatsApp bots',
        'Basic templates',
        'Auto-reply',
        'Email support',
        'Basic analytics',
        '7-day message history'
      ],
      cta: 'Pay Now',
      popular: false
    },
    {
      name: 'Pro',
      icon: Building2,
      price: '149',
      description: 'For growing businesses that need more power and flexibility',
      features: [
        '10,000 messages/month',
        '10 WhatsApp bots',
        'Advanced templates',
        'Auto-reply + AI responses',
        'Human handoff',
        'Priority support',
        'Advanced analytics',
        '30-day message history',
        'Custom integrations',
        'Team collaboration'
      ],
      cta: 'Pay Now',
      popular: true
    },
    {
      name: 'Enterprise',
      icon: Rocket,
      price: 'Custom',
      description: 'For large organizations with custom needs and high volume',
      features: [
        'Unlimited messages',
        'Unlimited bots',
        'Custom templates',
        'Full AI capabilities',
        'Advanced routing',
        'Dedicated support',
        'Custom analytics',
        'Unlimited history',
        'API access',
        'Custom integrations',
        'SLA guarantee',
        'White-label option'
      ],
      cta: 'Contact Sales',
      popular: false
    }
  ]

  return (
    <div className="min-h-screen bg-black text-white">
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

      {/* Hero Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-light mb-6">
            Simple, <span className="font-normal">transparent pricing</span>
          </h1>
          <p className="text-xl text-white/60 max-w-3xl mx-auto mb-4">
            Choose the plan that's right for your business. Secure payment powered by Razorpay.
          </p>
          <p className="text-sm text-white/40">
            Instant activation • Cancel anytime
          </p>
        </div>
      </section>

      {/* Pricing Cards */}
      <section className="py-16 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8">
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
                      {plan.price === 'Custom' ? (
                        <span className="text-4xl font-light">Custom</span>
                      ) : (
                        <>
                          <span className="text-white/60 text-2xl mr-1">$</span>
                          <span className="text-5xl font-light">{plan.price}</span>
                          <span className="text-white/60 ml-2">/month</span>
                        </>
                      )}
                    </div>
                    <p className="text-xs text-white/40">Billed monthly</p>
                  </div>

                  <Link href="/payment" className="block mb-6">
                    <Button 
                      className={`w-full ${
                        plan.popular 
                          ? 'bg-blue-500 hover:bg-blue-600 text-white' 
                          : 'bg-white text-black hover:bg-white/90'
                      }`}
                    >
                      {plan.cta}
                      <ArrowRight className="w-4 h-4 ml-2" />
                    </Button>
                  </Link>

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
        </div>
      </section>

      {/* Comparison Table */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-t border-white/10">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-4xl font-light mb-12 text-center">Compare Plans</h2>
          
          <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-white/5 border-b border-white/10">
                  <tr>
                    <th className="px-6 py-4 text-left text-sm font-medium text-white/60">Feature</th>
                    <th className="px-6 py-4 text-center text-sm font-medium text-white/60">Starter</th>
                    <th className="px-6 py-4 text-center text-sm font-medium text-white/60">Pro</th>
                    <th className="px-6 py-4 text-center text-sm font-medium text-white/60">Enterprise</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/10">
                  <tr>
                    <td className="px-6 py-4 text-white/80">Messages per month</td>
                    <td className="px-6 py-4 text-center text-white/60">1,000</td>
                    <td className="px-6 py-4 text-center text-white/60">10,000</td>
                    <td className="px-6 py-4 text-center text-white/60">Unlimited</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-white/80">WhatsApp bots</td>
                    <td className="px-6 py-4 text-center text-white/60">2</td>
                    <td className="px-6 py-4 text-center text-white/60">10</td>
                    <td className="px-6 py-4 text-center text-white/60">Unlimited</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-white/80">AI-powered responses</td>
                    <td className="px-6 py-4 text-center"><span className="text-white/30">—</span></td>
                    <td className="px-6 py-4 text-center"><Check className="w-5 h-5 text-green-400 mx-auto" /></td>
                    <td className="px-6 py-4 text-center"><Check className="w-5 h-5 text-green-400 mx-auto" /></td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-white/80">Human handoff</td>
                    <td className="px-6 py-4 text-center"><span className="text-white/30">—</span></td>
                    <td className="px-6 py-4 text-center"><Check className="w-5 h-5 text-green-400 mx-auto" /></td>
                    <td className="px-6 py-4 text-center"><Check className="w-5 h-5 text-green-400 mx-auto" /></td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-white/80">API access</td>
                    <td className="px-6 py-4 text-center"><span className="text-white/30">—</span></td>
                    <td className="px-6 py-4 text-center"><span className="text-white/30">—</span></td>
                    <td className="px-6 py-4 text-center"><Check className="w-5 h-5 text-green-400 mx-auto" /></td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-white/80">Support</td>
                    <td className="px-6 py-4 text-center text-white/60">Email</td>
                    <td className="px-6 py-4 text-center text-white/60">Priority</td>
                    <td className="px-6 py-4 text-center text-white/60">Dedicated</td>
                  </tr>
                  <tr>
                    <td className="px-6 py-4 text-white/80">SLA</td>
                    <td className="px-6 py-4 text-center"><span className="text-white/30">—</span></td>
                    <td className="px-6 py-4 text-center"><span className="text-white/30">—</span></td>
                    <td className="px-6 py-4 text-center"><Check className="w-5 h-5 text-green-400 mx-auto" /></td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-t border-white/10">
        <div className="max-w-4xl mx-auto">
          <h2 className="text-4xl font-light mb-12 text-center">Frequently Asked Questions</h2>
          
          <div className="space-y-6">
            <div className="bg-white/5 border border-white/10 rounded-xl p-6">
              <h3 className="text-xl font-light mb-2">Can I change plans later?</h3>
              <p className="text-white/60">
                Yes! You can upgrade or downgrade your plan at any time. Changes take effect immediately, 
                and we'll prorate the difference.
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-6">
              <h3 className="text-xl font-light mb-2">What happens if I exceed my message limit?</h3>
              <p className="text-white/60">
                We'll notify you when you reach 80% of your limit. If you exceed it, you can either upgrade 
                your plan or purchase additional message credits.
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-6">
              <h3 className="text-xl font-light mb-2">Is there a setup fee?</h3>
              <p className="text-white/60">
                No setup fees for Starter and Pro plans. Enterprise plans may include a one-time onboarding 
                fee depending on customization requirements.
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-6">
              <h3 className="text-xl font-light mb-2">Do you offer refunds?</h3>
              <p className="text-white/60">
                Yes, we offer a 30-day money-back guarantee. If you're not satisfied, contact our support 
                team for a full refund.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 border-t border-white/10">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-light mb-6">Still have questions?</h2>
          <p className="text-xl text-white/60 mb-8">
            Our team is here to help you find the perfect plan for your business.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/payment">
              <Button className="bg-white text-black hover:bg-white/90">
                View Plans
              </Button>
            </Link>
            <Button variant="outline" className="border-white/20 text-white hover:bg-white/5">
              Contact Sales
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-8 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto text-center text-white/40 text-sm">
          <p>&copy; 2026 BotSetu. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}
