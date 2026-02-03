'use client'

import Link from 'next/link'
import { UserButton } from '@clerk/nextjs'
import { Bot, Clock, Wrench, ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function PaymentPage() {
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
      <main className="flex-1 flex items-center justify-center px-4 sm:px-6 lg:px-8">
        <div className="max-w-2xl w-full text-center">
          {/* Icon */}
          <div className="mb-8 flex justify-center">
            <div className="bg-white/5 border border-white/10 rounded-full p-8">
              <Wrench className="w-16 h-16 text-white/40" />
            </div>
          </div>

          {/* Title */}
          <h1 className="text-5xl md:text-6xl font-light mb-6">
            Payment Gateway <span className="font-normal">Coming Soon</span>
          </h1>

          {/* Description */}
          <p className="text-xl text-white/60 mb-8 max-w-xl mx-auto">
            We're currently working on integrating a secure payment gateway to provide you with 
            a seamless checkout experience.
          </p>

          {/* Status Box */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-8 mb-8 max-w-lg mx-auto">
            <div className="flex items-center justify-center gap-3 mb-4">
              <Clock className="w-6 h-6 text-yellow-400" />
              <span className="text-lg font-light">Under Development</span>
            </div>
            <p className="text-sm text-white/60">
              Our team is working hard to add multiple payment options including credit cards, 
              PayPal, and cryptocurrency. This page will be updated soon with full payment functionality.
            </p>
          </div>

          {/* Features List */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-6 mb-8 max-w-lg mx-auto">
            <h3 className="text-lg font-light mb-4">What to Expect:</h3>
            <ul className="text-left space-y-3 text-white/60">
              <li className="flex items-start gap-2">
                <span className="text-green-400 mt-1">✓</span>
                <span>Multiple payment methods (Credit/Debit cards, PayPal, UPI)</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-400 mt-1">✓</span>
                <span>Secure PCI-compliant payment processing</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-400 mt-1">✓</span>
                <span>Automatic billing and invoicing</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-400 mt-1">✓</span>
                <span>Subscription management</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-green-400 mt-1">✓</span>
                <span>Instant payment confirmations</span>
              </li>
            </ul>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Link href="/pricing">
              <Button className="bg-white text-black hover:bg-white/90">
                View Pricing Plans
              </Button>
            </Link>
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
