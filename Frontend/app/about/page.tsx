'use client'

import Link from 'next/link'
import { UserButton } from '@clerk/nextjs'
import { Bot, Users, Target, Zap, Shield, Globe, ArrowRight } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function AboutPage() {
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
            About <span className="font-normal">BotSetu</span>
          </h1>
          <p className="text-xl text-white/60 max-w-3xl mx-auto mb-8">
            We're on a mission to make WhatsApp business automation accessible to everyone, 
            from small businesses to large enterprises.
          </p>
        </div>
      </section>

      {/* Mission Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-t border-white/10">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div>
              <h2 className="text-4xl font-light mb-6">Our Mission</h2>
              <p className="text-lg text-white/60 mb-4">
                BotSetu was founded with a simple belief: every business deserves powerful 
                automation tools without the complexity and high costs typically associated 
                with enterprise solutions.
              </p>
              <p className="text-lg text-white/60">
                We empower businesses to connect with their customers through WhatsApp, 
                automating conversations while maintaining the personal touch that makes 
                your brand unique.
              </p>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-xl p-12 flex items-center justify-center">
              <Bot className="w-32 h-32 text-white/20" />
            </div>
          </div>
        </div>
      </section>

      {/* Values Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-t border-white/10">
        <div className="max-w-7xl mx-auto">
          <h2 className="text-4xl font-light mb-12 text-center">Our Values</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="bg-white/5 border border-white/10 rounded-xl p-8 hover:bg-white/10 transition-colors">
              <Target className="w-12 h-12 text-blue-400 mb-4" />
              <h3 className="text-2xl font-light mb-3">Customer First</h3>
              <p className="text-white/60">
                Every decision we make is guided by what's best for our customers. 
                Your success is our success.
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-8 hover:bg-white/10 transition-colors">
              <Zap className="w-12 h-12 text-yellow-400 mb-4" />
              <h3 className="text-2xl font-light mb-3">Innovation</h3>
              <p className="text-white/60">
                We constantly evolve our platform with cutting-edge features to keep 
                you ahead of the competition.
              </p>
            </div>

            <div className="bg-white/5 border border-white/10 rounded-xl p-8 hover:bg-white/10 transition-colors">
              <Shield className="w-12 h-12 text-green-400 mb-4" />
              <h3 className="text-2xl font-light mb-3">Security</h3>
              <p className="text-white/60">
                Your data and your customers' privacy are paramount. We use 
                enterprise-grade security measures.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-t border-white/10">
        <div className="max-w-7xl mx-auto">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            <div className="text-center">
              <div className="text-5xl font-light mb-2">10K+</div>
              <div className="text-white/60">Active Bots</div>
            </div>
            <div className="text-center">
              <div className="text-5xl font-light mb-2">50M+</div>
              <div className="text-white/60">Messages Sent</div>
            </div>
            <div className="text-center">
              <div className="text-5xl font-light mb-2">150+</div>
              <div className="text-white/60">Countries</div>
            </div>
            <div className="text-center">
              <div className="text-5xl font-light mb-2">99.9%</div>
              <div className="text-white/60">Uptime</div>
            </div>
          </div>
        </div>
      </section>

      {/* Team Section */}
      <section className="py-16 px-4 sm:px-6 lg:px-8 border-t border-white/10">
        <div className="max-w-7xl mx-auto text-center">
          <h2 className="text-4xl font-light mb-6">Built by a Global Team</h2>
          <p className="text-xl text-white/60 max-w-3xl mx-auto mb-12">
            Our diverse team of engineers, designers, and support specialists work around 
            the clock to ensure BotSetu delivers the best WhatsApp automation experience.
          </p>
          <div className="flex justify-center gap-8 text-white/40">
            <div className="flex items-center gap-2">
              <Users className="w-5 h-5" />
              <span>50+ Team Members</span>
            </div>
            <div className="flex items-center gap-2">
              <Globe className="w-5 h-5" />
              <span>12 Countries</span>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8 border-t border-white/10">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-4xl font-light mb-6">Ready to Get Started?</h2>
          <p className="text-xl text-white/60 mb-8">
            Join thousands of businesses already automating their WhatsApp conversations.
          </p>
          <Link href="/create">
            <Button className="bg-white text-black hover:bg-white/90 text-lg px-8 py-6 h-auto">
              Create Your Bot
              <ArrowRight className="w-5 h-5 ml-2" />
            </Button>
          </Link>
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
