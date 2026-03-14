import { NextResponse } from 'next/server'

const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? 'http://localhost:5000'

export async function GET() {
  try {
    const res = await fetch(`${BACKEND}/api/ai/models`, { cache: 'no-store' })
    const data = await res.json()
    return NextResponse.json(data)
  } catch {
    return NextResponse.json({ models: [], ollamaRunning: false, error: 'Flask backend not reachable' })
  }
}
