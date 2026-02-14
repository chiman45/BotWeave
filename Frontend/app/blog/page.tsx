'use client'

import { useState } from 'react'
import Link from 'next/link'
import { UserButton, SignedIn, SignedOut } from '@clerk/nextjs'
import { Button } from '@/components/ui/button'
import { 
  Bot, 
  MessageCircle, 
  ArrowRight, 
  Check,
  Phone,
  Settings,
  BarChart3,
  Users,
  Zap,
  Shield,
  Clock,
  DollarSign
} from 'lucide-react'

export default function BlogPage() {
  const [isDarkMode] = useState(true)

  return (
    <div className={`min-h-screen ${isDarkMode ? 'bg-black text-white' : 'bg-white text-black'}`}>
      {/* Header */}
      <header className={`border-b backdrop-blur-sm sticky top-0 z-50 ${
        isDarkMode ? 'border-white/10 bg-black/50' : 'border-black/10 bg-white/50'
      }`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center gap-3">
              <div className={`p-2 rounded-lg ${
                isDarkMode ? 'bg-white/10 hover:bg-white/20' : 'bg-black/10 hover:bg-black/20'
              }`}>
                <MessageCircle className="w-5 h-5" />
              </div>
              <span className="font-light text-lg tracking-wide">BOTSETU</span>
            </Link>
            <div className="flex items-center gap-4">
              <SignedIn>
                <Link href="/dashboard">
                  <Button variant="ghost" className={isDarkMode ? 'text-white/60 hover:text-white' : 'text-black/60 hover:text-black'}>
                    Dashboard
                  </Button>
                </Link>
                <UserButton />
              </SignedIn>
              <SignedOut>
                <Link href="/">
                  <Button variant="ghost" className={isDarkMode ? 'text-white/60 hover:text-white' : 'text-black/60 hover:text-black'}>
                    Home
                  </Button>
                </Link>
              </SignedOut>
            </div>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-16">
        <div className="text-center mb-16">
          <h1 className="text-5xl md:text-6xl font-light mb-6">
            How to Use <span className="font-normal">BotSetu</span>
          </h1>
          <p className={`text-xl ${isDarkMode ? 'text-white/60' : 'text-black/60'} max-w-2xl mx-auto`}>
            A complete guide to creating and managing your WhatsApp bots for small business automation
          </p>
        </div>

        {/* Table of Contents */}
        <div className={`border rounded-xl p-8 mb-12 ${
          isDarkMode ? 'bg-white/5 border-white/10' : 'bg-black/5 border-black/10'
        }`}>
          <h2 className="text-2xl font-light mb-4">Quick Navigation</h2>
          <ul className="space-y-2">
            {[
              { href: '#getting-started', text: 'Getting Started' },
              { href: '#create-bot', text: 'Creating Your First Bot' },
              { href: '#configure', text: 'Configuring Your Bot' },
              { href: '#manage', text: 'Managing Conversations' },
              { href: '#analytics', text: 'Analytics & Insights' },
              { href: '#payments', text: 'Payment Management' },
              { href: '#tips', text: 'Best Practices & Tips' }
            ].map((item, idx) => (
              <li key={idx}>
                <a 
                  href={item.href}
                  className={`flex items-center gap-2 transition-colors ${
                    isDarkMode ? 'text-white/60 hover:text-white' : 'text-black/60 hover:text-black'
                  }`}
                >
                  <ArrowRight className="w-4 h-4" />
                  {item.text}
                </a>
              </li>
            ))}
          </ul>
        </div>

        {/* Getting Started */}
        <section id="getting-started" className="mb-16">
          <h2 className="text-3xl font-light mb-6 flex items-center gap-3">
            <Zap className="w-8 h-8 text-blue-400" />
            Getting Started
          </h2>
          <div className="space-y-4">
            <p className={isDarkMode ? 'text-white/80' : 'text-black/80'}>
              BotSetu is a powerful platform that enables small businesses to create intelligent WhatsApp bots 
              without any coding knowledge. Follow these simple steps to get started:
            </p>
            
            <div className="grid gap-4 mt-6">
              {[
                {
                  step: '1',
                  title: 'Sign Up',
                  description: 'Create your free account using Google or email authentication.'
                },
                {
                  step: '2',
                  title: 'Choose Your Plan',
                  description: 'Select from Starter, Pro, or Enterprise plans based on your business needs.'
                },
                {
                  step: '3',
                  title: 'Create Your Bot',
                  description: 'Use our intuitive bot creator to set up your WhatsApp automation.'
                },
                {
                  step: '4',
                  title: 'Go Live',
                  description: 'Connect your WhatsApp Business account and start engaging customers.'
                }
              ].map((item, idx) => (
                <div 
                  key={idx}
                  className={`border rounded-lg p-6 ${
                    isDarkMode ? 'bg-white/5 border-white/10' : 'bg-black/5 border-black/10'
                  }`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-lg font-medium ${
                      isDarkMode ? 'bg-white/10' : 'bg-black/10'
                    }`}>
                      {item.step}
                    </div>
                    <div>
                      <h3 className="text-xl font-medium mb-2">{item.title}</h3>
                      <p className={isDarkMode ? 'text-white/60' : 'text-black/60'}>
                        {item.description}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Create Bot */}
        <section id="create-bot" className="mb-16">
          <h2 className="text-3xl font-light mb-6 flex items-center gap-3">
            <Bot className="w-8 h-8 text-green-400" />
            Creating Your First Bot
          </h2>
          <div className="space-y-6">
            <p className={isDarkMode ? 'text-white/80' : 'text-black/80'}>
              Creating a bot on BotSetu is straightforward and takes only a few minutes:
            </p>

            <div className={`border rounded-lg p-6 ${
              isDarkMode ? 'bg-white/5 border-white/10' : 'bg-black/5 border-black/10'
            }`}>
              <h3 className="text-xl font-medium mb-4">Bot Creation Steps</h3>
              <ol className="space-y-4">
                <li className="flex items-start gap-3">
                  <span className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm ${
                    isDarkMode ? 'bg-white/10' : 'bg-black/10'
                  }`}>1</span>
                  <div>
                    <strong>Business Information:</strong> Enter your business name, category, and description
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm ${
                    isDarkMode ? 'bg-white/10' : 'bg-black/10'
                  }`}>2</span>
                  <div>
                    <strong>Use Case Selection:</strong> Choose your bot's purpose (customer support, booking, sales, FAQ)
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm ${
                    isDarkMode ? 'bg-white/10' : 'bg-black/10'
                  }`}>3</span>
                  <div>
                    <strong>Bot Personality:</strong> Define your bot's name and response style
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm ${
                    isDarkMode ? 'bg-white/10' : 'bg-black/10'
                  }`}>4</span>
                  <div>
                    <strong>WhatsApp Integration:</strong> Connect your WhatsApp Business phone number
                  </div>
                </li>
                <li className="flex items-start gap-3">
                  <span className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-sm ${
                    isDarkMode ? 'bg-white/10' : 'bg-black/10'
                  }`}>5</span>
                  <div>
                    <strong>Review & Deploy:</strong> Review your settings and activate your bot
                  </div>
                </li>
              </ol>
            </div>

            <div className={`border-l-4 border-blue-400 p-6 ${
              isDarkMode ? 'bg-blue-400/10' : 'bg-blue-400/10'
            }`}>
              <p className="flex items-start gap-2">
                <Shield className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                <span>
                  <strong>Pro Tip:</strong> Start with a clear use case. Bots work best when they have 
                  a specific purpose like handling FAQs, booking appointments, or providing product information.
                </span>
              </p>
            </div>
          </div>
        </section>

        {/* Configure */}
        <section id="configure" className="mb-16">
          <h2 className="text-3xl font-light mb-6 flex items-center gap-3">
            <Settings className="w-8 h-8 text-purple-400" />
            Configuring Your Bot
          </h2>
          <div className="space-y-6">
            <p className={isDarkMode ? 'text-white/80' : 'text-black/80'}>
              Fine-tune your bot's behavior with these powerful configuration options:
            </p>

            <div className="grid md:grid-cols-2 gap-6">
              {[
                {
                  icon: <Zap className="w-6 h-6 text-yellow-400" />,
                  title: 'Auto-Reply',
                  description: 'Enable automatic responses to common queries. Your bot will instantly respond to customer messages 24/7.'
                },
                {
                  icon: <Users className="w-6 h-6 text-blue-400" />,
                  title: 'Human Handoff',
                  description: 'Seamlessly transfer complex queries to human agents when needed. Ensure customers always get the help they need.'
                },
                {
                  icon: <Clock className="w-6 h-6 text-green-400" />,
                  title: 'Business Hours',
                  description: 'Set your operating hours and customize after-hours messages. Keep customers informed even when you\'re closed.'
                },
                {
                  icon: <MessageCircle className="w-6 h-6 text-pink-400" />,
                  title: 'Custom Responses',
                  description: 'Tailor your bot\'s responses to match your brand voice. Create personalized experiences for your customers.'
                }
              ].map((feature, idx) => (
                <div 
                  key={idx}
                  className={`border rounded-lg p-6 ${
                    isDarkMode ? 'bg-white/5 border-white/10 hover:bg-white/10' : 'bg-black/5 border-black/10 hover:bg-black/10'
                  } transition-colors`}
                >
                  <div className="flex items-start gap-4">
                    <div className={`flex-shrink-0 p-3 rounded-lg ${
                      isDarkMode ? 'bg-white/10' : 'bg-black/10'
                    }`}>
                      {feature.icon}
                    </div>
                    <div>
                      <h3 className="text-lg font-medium mb-2">{feature.title}</h3>
                      <p className={isDarkMode ? 'text-white/60' : 'text-black/60'}>
                        {feature.description}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Manage Conversations */}
        <section id="manage" className="mb-16">
          <h2 className="text-3xl font-light mb-6 flex items-center gap-3">
            <MessageCircle className="w-8 h-8 text-cyan-400" />
            Managing Conversations
          </h2>
          <div className="space-y-6">
            <p className={isDarkMode ? 'text-white/80' : 'text-black/80'}>
              Stay on top of customer interactions with our comprehensive conversation management tools:
            </p>

            <div className={`border rounded-lg p-6 ${
              isDarkMode ? 'bg-white/5 border-white/10' : 'bg-black/5 border-black/10'
            }`}>
              <h3 className="text-xl font-medium mb-4">Conversation Features</h3>
              <ul className="space-y-3">
                {[
                  'View all customer conversations in WhatsApp-style interface',
                  'Search through conversation history by keywords',
                  'Mark conversations as read/unread for better organization',
                  'Export conversation logs for analysis',
                  'Filter conversations by date, status, or customer',
                  'Real-time message notifications'
                ].map((feature, idx) => (
                  <li key={idx} className="flex items-start gap-3">
                    <Check className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                    <span>{feature}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className={`border rounded-lg p-6 ${
              isDarkMode ? 'bg-white/5 border-white/10' : 'bg-black/5 border-black/10'
            }`}>
              <h3 className="text-xl font-medium mb-4">Accessing Conversations</h3>
              <ol className="space-y-2 list-decimal list-inside">
                <li>Go to your Dashboard</li>
                <li>Click on the message icon next to any bot</li>
                <li>Browse conversations in the WhatsApp-style interface</li>
                <li>Click on any conversation to view full message history</li>
                <li>Use the search bar to find specific conversations</li>
              </ol>
            </div>
          </div>
        </section>

        {/* Analytics */}
        <section id="analytics" className="mb-16">
          <h2 className="text-3xl font-light mb-6 flex items-center gap-3">
            <BarChart3 className="w-8 h-8 text-orange-400" />
            Analytics & Insights
          </h2>
          <div className="space-y-6">
            <p className={isDarkMode ? 'text-white/80' : 'text-black/80'}>
              Track your bot's performance and customer engagement with detailed analytics:
            </p>

            <div className="grid md:grid-cols-3 gap-6">
              {[
                {
                  metric: 'Total Conversations',
                  description: 'Track how many customers are engaging with your bot'
                },
                {
                  metric: 'Message Volume',
                  description: 'Monitor message traffic and usage patterns'
                },
                {
                  metric: 'Active Bots',
                  description: 'See which bots are verified and operational'
                }
              ].map((stat, idx) => (
                <div 
                  key={idx}
                  className={`border rounded-lg p-6 text-center ${
                    isDarkMode ? 'bg-white/5 border-white/10' : 'bg-black/5 border-black/10'
                  }`}
                >
                  <h3 className="text-lg font-medium mb-2">{stat.metric}</h3>
                  <p className={`text-sm ${isDarkMode ? 'text-white/60' : 'text-black/60'}`}>
                    {stat.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Payments */}
        <section id="payments" className="mb-16">
          <h2 className="text-3xl font-light mb-6 flex items-center gap-3">
            <DollarSign className="w-8 h-8 text-green-400" />
            Payment Management
          </h2>
          <div className="space-y-6">
            <p className={isDarkMode ? 'text-white/80' : 'text-black/80'}>
              Keep track of your subscription payments and billing:
            </p>

            <div className={`border rounded-lg p-6 ${
              isDarkMode ? 'bg-white/5 border-white/10' : 'bg-black/5 border-black/10'
            }`}>
              <h3 className="text-xl font-medium mb-4">Payment Dashboard</h3>
              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${isDarkMode ? 'bg-red-400/10' : 'bg-red-400/10'}`}>
                    <DollarSign className="w-5 h-5 text-red-400" />
                  </div>
                  <div>
                    <h4 className="font-medium">Payment Due</h4>
                    <p className={isDarkMode ? 'text-white/60' : 'text-black/60'}>
                      View all pending payments and due dates
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3">
                  <div className={`p-2 rounded-lg ${isDarkMode ? 'bg-green-400/10' : 'bg-green-400/10'}`}>
                    <Check className="w-5 h-5 text-green-400" />
                  </div>
                  <div>
                    <h4 className="font-medium">Payment Completed</h4>
                    <p className={isDarkMode ? 'text-white/60' : 'text-black/60'}>
                      Track your payment history and receipts
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <div className="grid md:grid-cols-3 gap-4">
              {[
                { plan: 'Starter', price: '₹99/mo', features: '1,000 messages' },
                { plan: 'Pro', price: '₹499/mo', features: '10,000 messages' },
                { plan: 'Enterprise', price: '₹1,999/mo', features: 'Unlimited messages' }
              ].map((plan, idx) => (
                <div 
                  key={idx}
                  className={`border rounded-lg p-4 text-center ${
                    isDarkMode ? 'bg-white/5 border-white/10' : 'bg-black/5 border-black/10'
                  }`}
                >
                  <h4 className="font-medium mb-1">{plan.plan}</h4>
                  <p className="text-2xl font-light mb-1">{plan.price}</p>
                  <p className={`text-sm ${isDarkMode ? 'text-white/60' : 'text-black/60'}`}>
                    {plan.features}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Tips */}
        <section id="tips" className="mb-16">
          <h2 className="text-3xl font-light mb-6 flex items-center gap-3">
            <Shield className="w-8 h-8 text-indigo-400" />
            Best Practices & Tips
          </h2>
          <div className="space-y-6">
            <div className="space-y-4">
              {[
                {
                  title: 'Start Small, Scale Gradually',
                  description: 'Begin with a focused use case (e.g., FAQs) and expand features as you learn what works best for your customers.'
                },
                {
                  title: 'Monitor Conversations Regularly',
                  description: 'Check your conversation logs daily to understand customer needs and identify areas for improvement in your bot responses.'
                },
                {
                  title: 'Use Human Handoff Wisely',
                  description: 'Enable human handoff for complex queries to ensure customers receive quality support when automated responses aren\'t sufficient.'
                },
                {
                  title: 'Keep Responses Concise',
                  description: 'WhatsApp users prefer short, clear messages. Break long responses into multiple messages for better readability.'
                },
                {
                  title: 'Test Before Going Live',
                  description: 'Send test messages to your bot from different numbers to ensure everything works as expected before directing customers to it.'
                },
                {
                  title: 'Update Your Bot Regularly',
                  description: 'Review and update your bot\'s responses based on customer conversations and feedback to improve accuracy and relevance.'
                }
              ].map((tip, idx) => (
                <div 
                  key={idx}
                  className={`border-l-4 border-indigo-400 p-6 ${
                    isDarkMode ? 'bg-indigo-400/10' : 'bg-indigo-400/10'
                  }`}
                >
                  <h3 className="text-lg font-medium mb-2">{tip.title}</h3>
                  <p className={isDarkMode ? 'text-white/70' : 'text-black/70'}>
                    {tip.description}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* CTA Section */}
        <section className={`border rounded-xl p-12 text-center ${
          isDarkMode ? 'bg-white/5 border-white/10' : 'bg-black/5 border-black/10'
        }`}>
          <h2 className="text-3xl font-light mb-4">Ready to Get Started?</h2>
          <p className={`text-lg mb-8 ${isDarkMode ? 'text-white/60' : 'text-black/60'}`}>
            Create your first WhatsApp bot in minutes
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <SignedIn>
              <Link href="/create">
                <Button size="lg" className="bg-white text-black hover:bg-white/90">
                  Create Your Bot
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </SignedIn>
            <SignedOut>
              <Link href="/">
                <Button size="lg" className="bg-white text-black hover:bg-white/90">
                  Sign Up Free
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              </Link>
            </SignedOut>
            <Link href="/pricing">
              <Button size="lg" variant="outline" className={
                isDarkMode ? 'border-white/20 text-white hover:bg-white/10' : 'border-black/20 text-black hover:bg-black/10'
              }>
                View Pricing
              </Button>
            </Link>
          </div>
        </section>

        {/* Support Section */}
        <section className="mt-12 text-center">
          <p className={isDarkMode ? 'text-white/60' : 'text-black/60'}>
            Need help? Contact us at{' '}
            <a href="mailto:support@botsetu.com" className="text-blue-400 hover:underline">
              support@botsetu.com
            </a>
          </p>
        </section>
      </section>
    </div>
  )
}
