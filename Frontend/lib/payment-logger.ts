import fs from 'fs'
import path from 'path'

export type PaymentLogLevel = 'INFO' | 'SUCCESS' | 'ERROR' | 'WARNING'

export interface PaymentLogEntry {
  timestamp: string
  level: PaymentLogLevel
  userId?: string
  orderId?: string
  paymentId?: string
  amount?: number
  currency?: string
  planName?: string
  status?: string
  message: string
  details?: any
}

class PaymentLogger {
  private logFilePath: string
  private logDir: string

  constructor() {
    // Create logs directory in the project root
    this.logDir = path.join(process.cwd(), 'logs')
    this.logFilePath = path.join(this.logDir, 'payment-gateway.log')
    this.ensureLogDirectoryExists()
  }

  private ensureLogDirectoryExists() {
    if (!fs.existsSync(this.logDir)) {
      fs.mkdirSync(this.logDir, { recursive: true })
    }
  }

  private formatLogEntry(entry: PaymentLogEntry): string {
    const { timestamp, level, userId, orderId, paymentId, amount, currency, planName, status, message, details } = entry
    
    let logLine = `[${timestamp}] [${level}] ${message}`
    
    if (userId) logLine += ` | UserId: ${userId}`
    if (orderId) logLine += ` | OrderId: ${orderId}`
    if (paymentId) logLine += ` | PaymentId: ${paymentId}`
    if (amount) logLine += ` | Amount: ${amount} ${currency || 'INR'}`
    if (planName) logLine += ` | Plan: ${planName}`
    if (status) logLine += ` | Status: ${status}`
    if (details) logLine += ` | Details: ${JSON.stringify(details)}`
    
    return logLine + '\n'
  }

  public log(entry: Omit<PaymentLogEntry, 'timestamp'>): void {
    const logEntry: PaymentLogEntry = {
      ...entry,
      timestamp: new Date().toISOString()
    }

    const formattedLog = this.formatLogEntry(logEntry)
    
    try {
      // Append to log file
      fs.appendFileSync(this.logFilePath, formattedLog, 'utf8')
      
      // Also log to console for development
      console.log(formattedLog.trim())
    } catch (error) {
      console.error('Failed to write to payment log file:', error)
    }
  }

  public info(message: string, data?: Partial<PaymentLogEntry>): void {
    this.log({
      level: 'INFO',
      message,
      ...data
    })
  }

  public success(message: string, data?: Partial<PaymentLogEntry>): void {
    this.log({
      level: 'SUCCESS',
      message,
      ...data
    })
  }

  public error(message: string, data?: Partial<PaymentLogEntry>): void {
    this.log({
      level: 'ERROR',
      message,
      ...data
    })
  }

  public warning(message: string, data?: Partial<PaymentLogEntry>): void {
    this.log({
      level: 'WARNING',
      message,
      ...data
    })
  }

  public getRecentLogs(lines: number = 100): string[] {
    try {
      if (!fs.existsSync(this.logFilePath)) {
        return []
      }

      const content = fs.readFileSync(this.logFilePath, 'utf8')
      const allLines = content.split('\n').filter(line => line.trim() !== '')
      
      // Return last N lines
      return allLines.slice(-lines)
    } catch (error) {
      console.error('Failed to read payment log file:', error)
      return []
    }
  }

  public getLogsByDateRange(startDate: Date, endDate: Date): string[] {
    try {
      if (!fs.existsSync(this.logFilePath)) {
        return []
      }

      const content = fs.readFileSync(this.logFilePath, 'utf8')
      const allLines = content.split('\n').filter(line => line.trim() !== '')
      
      return allLines.filter(line => {
        const timestampMatch = line.match(/\[(.*?)\]/)
        if (!timestampMatch) return false
        
        const logDate = new Date(timestampMatch[1])
        return logDate >= startDate && logDate <= endDate
      })
    } catch (error) {
      console.error('Failed to read payment log file:', error)
      return []
    }
  }

  public clearLogs(): void {
    try {
      fs.writeFileSync(this.logFilePath, '', 'utf8')
      this.info('Payment logs cleared')
    } catch (error) {
      console.error('Failed to clear payment log file:', error)
    }
  }
}

// Export singleton instance
export const paymentLogger = new PaymentLogger()
