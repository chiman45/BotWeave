import React from "react"
import type { Metadata } from 'next'
import { Analytics } from '@vercel/analytics/next'
import {
  ClerkProvider,
} from "@clerk/nextjs"
import './globals.css'

export const metadata: Metadata = {
  title: 'BotSetu - WhatsApp Bot Builder for Small Business',
  description: 'Create intelligent WhatsApp bots for your small business without coding. Automate customer support, sales, and engagement.',
  generator: 'v0.app',
  icons: {
    icon: [
      {
        url: '/icon-light-32x32.png',
        media: '(prefers-color-scheme: light)',
      },
      {
        url: '/icon-dark-32x32.png',
        media: '(prefers-color-scheme: dark)',
      },
      {
        url: '/icon.svg',
        type: 'image/svg+xml',
      },
    ],
    apple: '/apple-icon.png',
  },
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <ClerkProvider
      signInFallbackRedirectUrl="/"
      signUpFallbackRedirectUrl="/"
    >
      <html
        lang="en"
        style={{
          '--font-bitcount': '"Bitcount Prop Single", "Bitcount Single", sans-serif',
        } as React.CSSProperties}
      >
        <head>
          <link rel="preconnect" href="https://fonts.googleapis.com" />
          <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
          <link href="https://fonts.googleapis.com/css2?family=Google+Sans:ital,opsz,wght@0,17..18,400..700;1,17..18,400..700&display=swap" rel="stylesheet" />
          <link href="https://fonts.googleapis.com/css2?family=Bitcount+Prop+Single:wght@100..900&family=Bitcount+Single:wght@100..900&display=swap" rel="stylesheet" />
        </head>
        <body className={`font-sans antialiased`}>
          {children}
          <Analytics />
        </body>
      </html>
    </ClerkProvider>
  )
}
