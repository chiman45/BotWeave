import { NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { paymentLogger } from '@/lib/payment-logger'

export async function GET(request: Request) {
  try {
    const { userId } = await auth()
    
    if (!userId) {
      return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
    }

    const { searchParams } = new URL(request.url)
    const lines = parseInt(searchParams.get('lines') || '100')
    const startDate = searchParams.get('startDate')
    const endDate = searchParams.get('endDate')

    let logs: string[]

    if (startDate && endDate) {
      // Get logs by date range
      logs = paymentLogger.getLogsByDateRange(
        new Date(startDate),
        new Date(endDate)
      )
    } else {
      // Get recent logs
      logs = paymentLogger.getRecentLogs(lines)
    }

    // Parse logs into structured format
    const parsedLogs = logs.map(log => {
      const timestampMatch = log.match(/\[(.*?)\]/)
      const levelMatch = log.match(/\[.*?\] \[(.*?)\]/)
      const messageMatch = log.match(/\[.*?\] \[.*?\] (.*?)(\s\||$)/)
      
      return {
        timestamp: timestampMatch ? timestampMatch[1] : '',
        level: levelMatch ? levelMatch[1] : '',
        message: messageMatch ? messageMatch[1] : '',
        raw: log
      }
    })

    return NextResponse.json({
      success: true,
      count: parsedLogs.length,
      logs: parsedLogs
    })
  } catch (error) {
    console.error('Error fetching payment logs:', error)
    return NextResponse.json(
      { error: 'Failed to fetch logs' },
      { status: 500 }
    )
  }
}
