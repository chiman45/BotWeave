'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useUser } from '@clerk/nextjs'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { MessageCircle, ArrowRight } from 'lucide-react'
import { SignInButton, SignUpButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs'

export default function LandingPage() {
  const router = useRouter()
  const { isSignedIn, isLoaded } = useUser()

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.push('/dashboard')
    }
  }, [isLoaded, isSignedIn, router])

  if (!isLoaded || isSignedIn) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="text-white text-xl">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-black text-white">
      {/* Navigation */}
      <nav className="fixed top-0 w-full z-50 border-b border-white/10 backdrop-blur-sm bg-black/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-3">
              <div className="bg-white/10 p-2 rounded-lg hover:bg-white/20 transition-colors">
                <MessageCircle className="w-5 h-5 text-white" />
              </div>
              <span className="font-light text-lg tracking-wide">BOTSETU</span>
            </Link>

            {/* Navigation Links */}
            <div className="hidden md:flex items-center gap-8 text-sm">
              <Link href="#features" className="text-white/60 hover:text-white transition-colors">
                Features
              </Link>
              <Link href="#pricing" className="text-white/60 hover:text-white transition-colors">
                Pricing
              </Link>
              <Link href="#faq" className="text-white/60 hover:text-white transition-colors">
                FAQ
              </Link>
            </div>

            {/* Auth Buttons */}
            <div className="flex items-center gap-2">
              <SignedOut>
                <SignInButton mode="modal">
                  <Button 
                    variant="ghost" 
                    className="text-white hover:bg-white/10 text-sm"
                  >
                    Login
                  </Button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <Button 
                    className="bg-white text-black hover:bg-white/90 text-sm font-medium"
                  >
                    Join
                  </Button>
                </SignUpButton>
              </SignedOut>
              <SignedIn>
                <Link href="/dashboard">
                  <Button variant="ghost" className="text-white hover:bg-white/10 text-sm">
                    Dashboard
                  </Button>
                </Link>
                <UserButton />
              </SignedIn>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="pt-32 pb-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto text-center space-y-12">
          {/* Main Headline */}
          <div className="space-y-6">
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-light tracking-tight leading-tight">
              Automate Your<br />
              <span className="font-semibold">Business</span>
            </h1>
            
            <p className="text-lg sm:text-xl text-white/60 font-light max-w-2xl mx-auto leading-relaxed">
              Create intelligent WhatsApp bots without coding. Automate customer support, sales, and engagement for your small business.
            </p>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/create">
              <Button 
                size="lg"
                className="bg-white text-black hover:bg-white/90 font-medium text-base px-8 h-12"
              >
                Create Your Bot Now
              </Button>
            </Link>
            <Link href="/demo">
              <Button 
                variant="ghost"
                size="lg"
                className="text-white border border-white/20 hover:border-white/40 hover:bg-white/5 font-medium text-base px-8 h-12"
              >
                Watch Demo <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="border-t border-white/10" />

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-light text-center mb-16">Core Features</h2>
          
          <div className="grid md:grid-cols-3 gap-12">
            {/* Feature 1 */}
            <div className="space-y-4">
              <div className="w-12 h-12 bg-white/10 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium">Fast Setup</h3>
              <p className="text-white/60 font-light leading-relaxed">
                Get your bot running in minutes. No coding required, just fill in your details and you're good to go.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="space-y-4">
              <div className="w-12 h-12 bg-white/10 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
              </div>
              <h3 className="text-lg font-medium">AI-Powered</h3>
              <p className="text-white/60 font-light leading-relaxed">
                Intelligent responses that learn from conversations. Provide exceptional customer support automatically.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="space-y-4">
              <div className="w-12 h-12 bg-white/10 rounded-lg flex items-center justify-center">
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium">Analytics</h3>
              <p className="text-white/60 font-light leading-relaxed">
                Track conversations, response rates, and customer satisfaction. Data-driven insights for growth.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="border-t border-white/10" />

      {/* Showcase Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <h2 className="text-4xl font-light">
                Build in <span className="font-semibold">Minutes</span>
              </h2>
              <p className="text-lg text-white/60 font-light leading-relaxed">
                No complex workflows or technical knowledge needed. Our visual bot builder makes it easy for anyone to create powerful automations.
              </p>
              <ul className="space-y-3">
                {['Template library', 'Drag and drop builder', 'Pre-built integrations'].map((item) => (
                  <li key={item} className="flex items-center gap-3 text-white/80">
                    <div className="w-2 h-2 bg-white rounded-full" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className="bg-white/5 border border-white/10 rounded-lg p-8 h-80 flex items-center justify-center">
              <div className="text-center text-white/40">
                <p className="font-light">Bot Builder Preview</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="border-t border-white/10" />

      {/* Stats Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-3 gap-8 text-center">
            <div className="space-y-2">
              <p className="text-4xl font-light">500+</p>
              <p className="text-white/60 font-light text-sm">Businesses</p>
            </div>
            <div className="space-y-2">
              <p className="text-4xl font-light">10M+</p>
              <p className="text-white/60 font-light text-sm">Messages</p>
            </div>
            <div className="space-y-2">
              <p className="text-4xl font-light">99%</p>
              <p className="text-white/60 font-light text-sm">Uptime</p>
            </div>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="border-t border-white/10" />

      {/* Pricing Section */}
      <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-light mb-4">Simple Pricing</h2>
            <p className="text-lg text-white/60 font-light">
              Choose the plan that fits your business needs
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {/* Starter Plan */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-8 space-y-6 hover:border-white/20 transition-colors">
              <div>
                <h3 className="text-xl font-medium mb-2">Starter</h3>
                <p className="text-white/60 text-sm font-light">Perfect for small businesses</p>
              </div>
              <div className="space-y-1">
                <p className="text-4xl font-light">$29</p>
                <p className="text-white/60 text-sm">per month</p>
              </div>
              <ul className="space-y-3">
                {['1 WhatsApp Bot', '1,000 messages/month', 'Basic analytics', 'Email support'].map((feature) => (
                  <li key={feature} className="flex items-start gap-3 text-white/80 text-sm">
                    <div className="w-1.5 h-1.5 bg-white rounded-full mt-2" />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button className="w-full bg-white/10 hover:bg-white/20 text-white border border-white/20">
                Get Started
              </Button>
            </div>

            {/* Professional Plan */}
            <div className="bg-white/5 border-2 border-white/30 rounded-lg p-8 space-y-6 relative">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-white text-black px-4 py-1 rounded-full text-xs font-medium">
                POPULAR
              </div>
              <div>
                <h3 className="text-xl font-medium mb-2">Professional</h3>
                <p className="text-white/60 text-sm font-light">For growing businesses</p>
              </div>
              <div className="space-y-1">
                <p className="text-4xl font-light">$79</p>
                <p className="text-white/60 text-sm">per month</p>
              </div>
              <ul className="space-y-3">
                {['5 WhatsApp Bots', '10,000 messages/month', 'Advanced analytics', 'Priority support', 'Custom integrations'].map((feature) => (
                  <li key={feature} className="flex items-start gap-3 text-white/80 text-sm">
                    <div className="w-1.5 h-1.5 bg-white rounded-full mt-2" />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button className="w-full bg-white text-black hover:bg-white/90">
                Get Started
              </Button>
            </div>

            {/* Enterprise Plan */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-8 space-y-6 hover:border-white/20 transition-colors">
              <div>
                <h3 className="text-xl font-medium mb-2">Enterprise</h3>
                <p className="text-white/60 text-sm font-light">For large organizations</p>
              </div>
              <div className="space-y-1">
                <p className="text-4xl font-light">Custom</p>
                <p className="text-white/60 text-sm">contact sales</p>
              </div>
              <ul className="space-y-3">
                {['Unlimited bots', 'Unlimited messages', 'Custom analytics', '24/7 dedicated support', 'SLA guarantee', 'On-premise option'].map((feature) => (
                  <li key={feature} className="flex items-start gap-3 text-white/80 text-sm">
                    <div className="w-1.5 h-1.5 bg-white rounded-full mt-2" />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button className="w-full bg-white/10 hover:bg-white/20 text-white border border-white/20">
                Contact Sales
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="border-t border-white/10" />

      {/* FAQ Section */}
      <section id="faq" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-light mb-4">Frequently Asked Questions</h2>
            <p className="text-lg text-white/60 font-light">
              Everything you need to know about BotSetu
            </p>
          </div>
          
          <div className="space-y-6">
            {/* FAQ Item 1 */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-6 space-y-3">
              <h3 className="text-lg font-medium">How quickly can I set up a bot?</h3>
              <p className="text-white/60 font-light leading-relaxed">
                You can have your WhatsApp bot up and running in less than 5 minutes. Our intuitive builder guides you through the process step by step.
              </p>
            </div>

            {/* FAQ Item 2 */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-6 space-y-3">
              <h3 className="text-lg font-medium">Do I need coding knowledge?</h3>
              <p className="text-white/60 font-light leading-relaxed">
                Not at all! BotSetu is designed for everyone. Our visual builder requires zero coding knowledge. Just fill in your details and customize your bot's behavior.
              </p>
            </div>

            {/* FAQ Item 3 */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-6 space-y-3">
              <h3 className="text-lg font-medium">Can I upgrade or downgrade my plan?</h3>
              <p className="text-white/60 font-light leading-relaxed">
                Yes! You can change your plan at any time. Upgrades take effect immediately, and downgrades will be applied at the start of your next billing cycle.
              </p>
            </div>

            {/* FAQ Item 4 */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-6 space-y-3">
              <h3 className="text-lg font-medium">What kind of support do you offer?</h3>
              <p className="text-white/60 font-light leading-relaxed">
                We offer email support for all plans, priority support for Professional plans, and dedicated 24/7 support for Enterprise customers. We also have extensive documentation and video tutorials.
              </p>
            </div>

            {/* FAQ Item 5 */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-6 space-y-3">
              <h3 className="text-lg font-medium">Is my data secure?</h3>
              <p className="text-white/60 font-light leading-relaxed">
                Absolutely. We use industry-standard encryption and security practices. All data is encrypted in transit and at rest. We're GDPR compliant and take data privacy seriously.
              </p>
            </div>

            {/* FAQ Item 6 */}
            <div className="bg-white/5 border border-white/10 rounded-lg p-6 space-y-3">
              <h3 className="text-lg font-medium">Can I integrate with my existing tools?</h3>
              <p className="text-white/60 font-light leading-relaxed">
                Yes! We offer integrations with popular CRM, e-commerce, and business tools. Professional and Enterprise plans also support custom integrations via our API.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className="border-t border-white/10" />

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center space-y-8">
          <h2 className="text-4xl font-light">
            Ready to automate?
          </h2>
          <p className="text-lg text-white/60 font-light">
            Join hundreds of small businesses that are already saving time and increasing revenue with BotFlow.
          </p>
          <Link href="/signup">
            <Button 
              size="lg"
              className="bg-white text-black hover:bg-white/90 font-medium text-base px-8 h-12"
            >
              Get Started Free
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10 py-12 px-4 sm:px-6 lg:px-8">
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div>
              <h3 className="font-medium mb-4">Product</h3>
              <ul className="space-y-2 text-sm text-white/60">
                <li><Link href="#" className="hover:text-white transition-colors">Features</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Pricing</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">API</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium mb-4">Company</h3>
              <ul className="space-y-2 text-sm text-white/60">
                <li><Link href="#" className="hover:text-white transition-colors">About</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Blog</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Status</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium mb-4">Resources</h3>
              <ul className="space-y-2 text-sm text-white/60">
                <li><Link href="#" className="hover:text-white transition-colors">Docs</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Guides</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Support</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium mb-4">Legal</h3>
              <ul className="space-y-2 text-sm text-white/60">
                <li><Link href="#" className="hover:text-white transition-colors">Privacy</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Terms</Link></li>
                <li><Link href="#" className="hover:text-white transition-colors">Contact</Link></li>
              </ul>
            </div>
          </div>
          
          <div className="border-t border-white/10 pt-8 flex justify-between items-center text-sm text-white/60">
            <p>&copy; 2024 BotFlow. All rights reserved.</p>
            <div className="flex gap-6">
              <Link href="#" className="hover:text-white transition-colors">Twitter</Link>
              <Link href="#" className="hover:text-white transition-colors">LinkedIn</Link>
              <Link href="#" className="hover:text-white transition-colors">GitHub</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
