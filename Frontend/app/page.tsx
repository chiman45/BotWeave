'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useUser } from '@clerk/nextjs'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { MessageCircle, ArrowRight, Sun, Moon } from 'lucide-react'
import { SignInButton, SignUpButton, SignedIn, SignedOut, UserButton } from '@clerk/nextjs'

export default function LandingPage() {
  const router = useRouter()
  const { isSignedIn, isLoaded } = useUser()
  const [isDarkMode, setIsDarkMode] = useState(true)

  useEffect(() => {
    // Load theme preference from localStorage
    const savedTheme = localStorage.getItem('theme')
    if (savedTheme === 'light') {
      setIsDarkMode(false)
    }
  }, [])

  useEffect(() => {
    if (isLoaded && isSignedIn) {
      router.push('/dashboard')
    }
  }, [isLoaded, isSignedIn, router])

  const toggleTheme = () => {
    const newTheme = !isDarkMode
    setIsDarkMode(newTheme)
    localStorage.setItem('theme', newTheme ? 'dark' : 'light')
  }

  if (!isLoaded || isSignedIn) {
    return (
      <div className={`min-h-screen flex items-center justify-center ${isDarkMode ? 'bg-black' : 'bg-white'}`}>
        <div className={`text-xl ${isDarkMode ? 'text-white' : 'text-black'}`}>Loading...</div>
      </div>
    )
  }

  const dividerClass = isDarkMode ? 'border-white/10' : 'border-black/10'
  const textMutedClass = isDarkMode ? 'text-white/60' : 'text-black/60'
  const bgMutedClass = isDarkMode ? 'bg-white/5' : 'bg-black/5'
  const borderClass = isDarkMode ? 'border-white/10' : 'border-black/10'

  return (
    <div className={`min-h-screen transition-colors duration-300 ${isDarkMode ? 'bg-black text-white' : 'bg-white text-black'}`}>
      {/* Navigation */}
      <nav className={`fixed top-0 w-full z-50 border-b backdrop-blur-sm transition-colors duration-300 ${
        isDarkMode ? 'border-white/10 bg-black/50' : 'border-black/10 bg-white/50'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            {/* Logo */}
            <Link href="/" className="flex items-center gap-3">
              <div className={`p-2 rounded-lg transition-colors ${
                isDarkMode ? 'bg-white/10 hover:bg-white/20' : 'bg-black/10 hover:bg-black/20'
              }`}>
                <MessageCircle className={`w-5 h-5 ${isDarkMode ? 'text-white' : 'text-black'}`} />
              </div>
              <span className="font-light text-lg tracking-wide">BOTSETU</span>
            </Link>

            {/* Navigation Links */}
            <div className="hidden md:flex items-center gap-8 text-sm">
              <Link href="#features" className={`transition-colors ${
                isDarkMode ? 'text-white/60 hover:text-white' : 'text-black/60 hover:text-black'
              }`}>
                Features
              </Link>
              <Link href="#pricing" className={`transition-colors ${
                isDarkMode ? 'text-white/60 hover:text-white' : 'text-black/60 hover:text-black'
              }`}>
                Pricing
              </Link>
              <Link href="#faq" className={`transition-colors ${
                isDarkMode ? 'text-white/60 hover:text-white' : 'text-black/60 hover:text-black'
              }`}>
                FAQ
              </Link>
            </div>

            {/* Auth Buttons & Theme Toggle */}
            <div className="flex items-center gap-2">
              <SignedOut>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleTheme}
                  className={`transition-colors ${
                    isDarkMode ? 'text-white hover:bg-white/10' : 'text-black hover:bg-black/10'
                  }`}
                  aria-label="Toggle theme"
                >
                  {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                </Button>
                <SignInButton mode="modal">
                  <Button 
                    variant="ghost" 
                    className={`text-sm ${
                      isDarkMode ? 'text-white hover:bg-white/10' : 'text-black hover:bg-black/10'
                    }`}
                  >
                    Login
                  </Button>
                </SignInButton>
                <SignUpButton mode="modal">
                  <Button 
                    className={`text-sm font-medium ${
                      isDarkMode ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-black/90'
                    }`}
                  >
                    Join
                  </Button>
                </SignUpButton>
              </SignedOut>
              <SignedIn>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleTheme}
                  className={`transition-colors ${
                    isDarkMode ? 'text-white hover:bg-white/10' : 'text-black hover:bg-black/10'
                  }`}
                  aria-label="Toggle theme"
                >
                  {isDarkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
                </Button>
                <Link href="/dashboard">
                  <Button variant="ghost" className={`text-sm ${
                    isDarkMode ? 'text-white hover:bg-white/10' : 'text-black hover:bg-black/10'
                  }`}>
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
            
            <p className={`text-lg sm:text-xl font-light max-w-2xl mx-auto leading-relaxed ${textMutedClass}`}>
              Create intelligent WhatsApp bots without coding. Automate customer support, sales, and engagement for your small business.
            </p>
          </div>

          {/* CTA Buttons */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
            <Link href="/create">
              <Button 
                size="lg"
                className={`font-medium text-base px-8 h-12 ${
                  isDarkMode ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-black/90'
                }`}
              >
                Create Your Bot Now
              </Button>
            </Link>
            <Link href="/demo">
              <Button 
                variant="ghost"
                size="lg"
                className={`border font-medium text-base px-8 h-12 ${
                  isDarkMode
                    ? 'text-white border-white/20 hover:border-white/40 hover:bg-white/5'
                    : 'text-black border-black/20 hover:border-black/40 hover:bg-black/5'
                }`}
              >
                Watch Demo <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className={`border-t ${dividerClass}`} />

      {/* Features Section */}
      <section id="features" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-4xl font-light text-center mb-16">Core Features</h2>
          
          <div className="grid md:grid-cols-3 gap-12">
            {/* Feature 1 */}
            <div className="space-y-4">
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${bgMutedClass}`}>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium">Fast Setup</h3>
              <p className={`${textMutedClass} font-light leading-relaxed`}>
                Get your bot running in minutes. No coding required, just fill in your details and you're good to go.
              </p>
            </div>

            {/* Feature 2 */}
            <div className="space-y-4">
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${bgMutedClass}`}>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
                </svg>
              </div>
              <h3 className="text-lg font-medium">AI-Powered</h3>
              <p className={`${textMutedClass} font-light leading-relaxed`}>
                Intelligent responses that learn from conversations. Provide exceptional customer support automatically.
              </p>
            </div>

            {/* Feature 3 */}
            <div className="space-y-4">
              <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${bgMutedClass}`}>
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </div>
              <h3 className="text-lg font-medium">Analytics</h3>
              <p className={`${textMutedClass} font-light leading-relaxed`}>
                Track conversations, response rates, and customer satisfaction. Data-driven insights for growth.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className={`border-t ${dividerClass}`} />

      {/* Showcase Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-5xl mx-auto">
          <div className="grid md:grid-cols-2 gap-12 items-center">
            <div className="space-y-6">
              <h2 className="text-4xl font-light">
                Build in <span className="font-semibold">Minutes</span>
              </h2>
              <p className={`text-lg font-light leading-relaxed ${textMutedClass}`}>
                No complex workflows or technical knowledge needed. Our visual bot builder makes it easy for anyone to create powerful automations.
              </p>
              <ul className="space-y-3">
                {['Template library', 'Drag and drop builder', 'Pre-built integrations'].map((item) => (
                  <li key={item} className={`flex items-center gap-3 ${isDarkMode ? 'text-white/80' : 'text-black/80'}`}>
                    <div className={`w-2 h-2 rounded-full ${isDarkMode ? 'bg-white' : 'bg-black'}`} />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
            <div className={`border rounded-lg p-8 h-80 flex items-center justify-center ${bgMutedClass} ${borderClass}`}>
              <div className={`text-center ${isDarkMode ? 'text-white/40' : 'text-black/40'}`}>
                <p className="font-light">Bot Builder Preview</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className={`border-t ${dividerClass}`} />

      {/* Stats Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-4xl mx-auto">
          <div className="grid grid-cols-3 gap-8 text-center">
            <div className="space-y-2">
              <p className="text-4xl font-light">500+</p>
              <p className={`${textMutedClass} font-light text-sm`}>Businesses</p>
            </div>
            <div className="space-y-2">
              <p className="text-4xl font-light">10M+</p>
              <p className={`${textMutedClass} font-light text-sm`}>Messages</p>
            </div>
            <div className="space-y-2">
              <p className="text-4xl font-light">99%</p>
              <p className={`${textMutedClass} font-light text-sm`}>Uptime</p>
            </div>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className={`border-t ${dividerClass}`} />

      {/* Pricing Section */}
      <section id="pricing" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-light mb-4">Simple Pricing</h2>
            <p className={`text-lg font-light ${textMutedClass}`}>
              Choose the plan that fits your business needs
            </p>
          </div>
          
          <div className="grid md:grid-cols-3 gap-8">
            {/* Starter Plan */}
            <div className={`border rounded-lg p-8 space-y-6 transition-colors ${bgMutedClass} ${borderClass} ${
              isDarkMode ? 'hover:border-white/20' : 'hover:border-black/20'
            }`}>
              <div>
                <h3 className="text-xl font-medium mb-2">Starter</h3>
                <p className={`text-sm font-light ${textMutedClass}`}>Perfect for small businesses</p>
              </div>
              <div className="space-y-1">
                <p className="text-4xl font-light">$29</p>
                <p className={`text-sm ${textMutedClass}`}>per month</p>
              </div>
              <ul className="space-y-3">
                {['1 WhatsApp Bot', '1,000 messages/month', 'Basic analytics', 'Email support'].map((feature) => (
                  <li key={feature} className={`flex items-start gap-3 text-sm ${isDarkMode ? 'text-white/80' : 'text-black/80'}`}>
                    <div className={`w-1.5 h-1.5 rounded-full mt-2 ${isDarkMode ? 'bg-white' : 'bg-black'}`} />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button className={`w-full border ${
                isDarkMode ? 'bg-white/10 hover:bg-white/20 text-white border-white/20' : 'bg-black/10 hover:bg-black/20 text-black border-black/20'
              }`}>
                Get Started
              </Button>
            </div>

            {/* Professional Plan */}
            <div className={`border-2 rounded-lg p-8 space-y-6 relative ${bgMutedClass} ${
              isDarkMode ? 'border-white/30' : 'border-black/30'
            }`}>
              <div className={`absolute -top-4 left-1/2 -translate-x-1/2 px-4 py-1 rounded-full text-xs font-medium ${
                isDarkMode ? 'bg-white text-black' : 'bg-black text-white'
              }`}>
                POPULAR
              </div>
              <div>
                <h3 className="text-xl font-medium mb-2">Professional</h3>
                <p className={`text-sm font-light ${textMutedClass}`}>For growing businesses</p>
              </div>
              <div className="space-y-1">
                <p className="text-4xl font-light">$79</p>
                <p className={`text-sm ${textMutedClass}`}>per month</p>
              </div>
              <ul className="space-y-3">
                {['5 WhatsApp Bots', '10,000 messages/month', 'Advanced analytics', 'Priority support', 'Custom integrations'].map((feature) => (
                  <li key={feature} className={`flex items-start gap-3 text-sm ${isDarkMode ? 'text-white/80' : 'text-black/80'}`}>
                    <div className={`w-1.5 h-1.5 rounded-full mt-2 ${isDarkMode ? 'bg-white' : 'bg-black'}`} />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button className={`w-full ${
                isDarkMode ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-black/90'
              }`}>
                Get Started
              </Button>
            </div>

            {/* Enterprise Plan */}
            <div className={`border rounded-lg p-8 space-y-6 transition-colors ${bgMutedClass} ${borderClass} ${
              isDarkMode ? 'hover:border-white/20' : 'hover:border-black/20'
            }`}>
              <div>
                <h3 className="text-xl font-medium mb-2">Enterprise</h3>
                <p className={`text-sm font-light ${textMutedClass}`}>For large organizations</p>
              </div>
              <div className="space-y-1">
                <p className="text-4xl font-light">Custom</p>
                <p className={`text-sm ${textMutedClass}`}>contact sales</p>
              </div>
              <ul className="space-y-3">
                {['Unlimited bots', 'Unlimited messages', 'Custom analytics', '24/7 dedicated support', 'SLA guarantee', 'On-premise option'].map((feature) => (
                  <li key={feature} className={`flex items-start gap-3 text-sm ${isDarkMode ? 'text-white/80' : 'text-black/80'}`}>
                    <div className={`w-1.5 h-1.5 rounded-full mt-2 ${isDarkMode ? 'bg-white' : 'bg-black'}`} />
                    {feature}
                  </li>
                ))}
              </ul>
              <Button className={`w-full border ${
                isDarkMode ? 'bg-white/10 hover:bg-white/20 text-white border-white/20' : 'bg-black/10 hover:bg-black/20 text-black border-black/20'
              }`}>
                Contact Sales
              </Button>
            </div>
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className={`border-t ${dividerClass}`} />

      {/* FAQ Section */}
      <section id="faq" className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-light mb-4">Frequently Asked Questions</h2>
            <p className={`text-lg font-light ${textMutedClass}`}>
              Everything you need to know about BotSetu
            </p>
          </div>
          
          <div className="space-y-6">
            {[
              {
                q: "How quickly can I set up a bot?",
                a: "You can have your WhatsApp bot up and running in less than 5 minutes. Our intuitive builder guides you through the process step by step."
              },
              {
                q: "Do I need coding knowledge?",
                a: "Not at all! BotSetu is designed for everyone. Our visual builder requires zero coding knowledge. Just fill in your details and customize your bot's behavior."
              },
              {
                q: "Can I upgrade or downgrade my plan?",
                a: "Yes! You can change your plan at any time. Upgrades take effect immediately, and downgrades will be applied at the start of your next billing cycle."
              },
              {
                q: "What kind of support do you offer?",
                a: "We offer email support for all plans, priority support for Professional plans, and dedicated 24/7 support for Enterprise customers. We also have extensive documentation and video tutorials."
              },
              {
                q: "Is my data secure?",
                a: "Absolutely. We use industry-standard encryption and security practices. All data is encrypted in transit and at rest. We're GDPR compliant and take data privacy seriously."
              },
              {
                q: "Can I integrate with my existing tools?",
                a: "Yes! We offer integrations with popular CRM, e-commerce, and business tools. Professional and Enterprise plans also support custom integrations via our API."
              }
            ].map((faq, index) => (
              <div key={index} className={`border rounded-lg p-6 space-y-3 ${bgMutedClass} ${borderClass}`}>
                <h3 className="text-lg font-medium">{faq.q}</h3>
                <p className={`font-light leading-relaxed ${textMutedClass}`}>
                  {faq.a}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Divider */}
      <div className={`border-t ${dividerClass}`} />

      {/* CTA Section */}
      <section className="py-20 px-4 sm:px-6 lg:px-8">
        <div className="max-w-3xl mx-auto text-center space-y-8">
          <h2 className="text-4xl font-light">
            Ready to automate?
          </h2>
          <p className={`text-lg font-light ${textMutedClass}`}>
            Join hundreds of small businesses that are already saving time and increasing revenue with BotFlow.
          </p>
          <Link href="/signup">
            <Button 
              size="lg"
              className={`font-medium text-base px-8 h-12 ${
                isDarkMode ? 'bg-white text-black hover:bg-white/90' : 'bg-black text-white hover:bg-black/90'
              }`}
            >
              Get Started Free
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className={`border-t py-12 px-4 sm:px-6 lg:px-8 ${dividerClass}`}>
        <div className="max-w-7xl mx-auto">
          <div className="grid md:grid-cols-4 gap-12 mb-12">
            <div>
              <h3 className="font-medium mb-4">Product</h3>
              <ul className={`space-y-2 text-sm ${textMutedClass}`}>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Features</Link></li>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Pricing</Link></li>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>API</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium mb-4">Company</h3>
              <ul className={`space-y-2 text-sm ${textMutedClass}`}>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>About</Link></li>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Blog</Link></li>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Status</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium mb-4">Resources</h3>
              <ul className={`space-y-2 text-sm ${textMutedClass}`}>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Docs</Link></li>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Guides</Link></li>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Support</Link></li>
              </ul>
            </div>
            <div>
              <h3 className="font-medium mb-4">Legal</h3>
              <ul className={`space-y-2 text-sm ${textMutedClass}`}>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Privacy</Link></li>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Terms</Link></li>
                <li><Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Contact</Link></li>
              </ul>
            </div>
          </div>
          
          <div className={`border-t pt-8 flex justify-between items-center text-sm ${dividerClass} ${textMutedClass}`}>
            <p>&copy; 2024 BotFlow. All rights reserved.</p>
            <div className="flex gap-6">
              <Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>Twitter</Link>
              <Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>LinkedIn</Link>
              <Link href="#" className={`transition-colors ${isDarkMode ? 'hover:text-white' : 'hover:text-black'}`}>GitHub</Link>
            </div>
          </div>
        </div>
      </footer>
    </div>
  )
}
