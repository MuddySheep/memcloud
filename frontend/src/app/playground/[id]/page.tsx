'use client'

import { useState, useEffect, useRef } from 'react'
import { useParams } from 'next/navigation'
import { Send, Bot, User, Loader2, Zap, Database, Brain } from 'lucide-react'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface MemoryInfo {
  totalMemories: number
  recentMemories: number
  connectionStatus: 'connected' | 'connecting' | 'disconnected'
}

export default function PlaygroundPage() {
  const params = useParams()
  const instanceId = params.id as string
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [memoryInfo, setMemoryInfo] = useState<MemoryInfo>({
    totalMemories: 0,
    recentMemories: 0,
    connectionStatus: 'connecting'
  })
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Simulate connection to MemMachine
    setTimeout(() => {
      setMemoryInfo({
        totalMemories: 0,
        recentMemories: 0,
        connectionStatus: 'connected'
      })

      // Add welcome message
      setMessages([{
        id: '1',
        role: 'assistant',
        content: `Welcome to your MemMachine Playground! I'm connected to your personal AI memory system (Instance: ${instanceId}). How can I help you today?`,
        timestamp: new Date()
      }])
    }, 1000)
  }, [instanceId])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    try {
      // Call to MemMachine API
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/playground/${instanceId}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      })

      const data = await response.json()

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: data.response || "I understand. This has been stored in your memory system.",
        timestamp: new Date()
      }

      setMessages(prev => [...prev, assistantMessage])

      // Update memory stats
      setMemoryInfo(prev => ({
        ...prev,
        totalMemories: prev.totalMemories + 1,
        recentMemories: prev.recentMemories + 1
      }))
    } catch (error) {
      console.error('Error:', error)
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: "I'm having trouble connecting to MemMachine. Please check your connection.",
        timestamp: new Date()
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      <div className="container mx-auto px-4 py-6 h-screen flex flex-col">
        {/* Header */}
        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-4 mb-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <Brain className="h-8 w-8 text-blue-400" />
                <h1 className="text-2xl font-bold text-white">MemMachine Playground</h1>
              </div>
              <span className="text-sm text-gray-300">Instance: {instanceId.slice(0, 8)}...</span>
            </div>

            {/* Memory Stats */}
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-2">
                <Database className="h-5 w-5 text-green-400" />
                <div>
                  <p className="text-xs text-gray-400">Total Memories</p>
                  <p className="text-lg font-semibold text-white">{memoryInfo.totalMemories}</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <Zap className="h-5 w-5 text-yellow-400" />
                <div>
                  <p className="text-xs text-gray-400">Recent</p>
                  <p className="text-lg font-semibold text-white">{memoryInfo.recentMemories}</p>
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <div className={`h-3 w-3 rounded-full ${
                  memoryInfo.connectionStatus === 'connected' ? 'bg-green-400' :
                  memoryInfo.connectionStatus === 'connecting' ? 'bg-yellow-400 animate-pulse' :
                  'bg-red-400'
                }`} />
                <span className="text-sm text-gray-300 capitalize">
                  {memoryInfo.connectionStatus}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Chat Container */}
        <div className="flex-1 bg-white/5 backdrop-blur-lg rounded-xl p-6 overflow-hidden flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto space-y-4 mb-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`flex max-w-[70%] ${message.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start space-x-2`}>
                  <div className={`flex-shrink-0 h-8 w-8 rounded-full flex items-center justify-center ${
                    message.role === 'user' ? 'bg-blue-500' : 'bg-purple-500'
                  }`}>
                    {message.role === 'user' ?
                      <User className="h-5 w-5 text-white" /> :
                      <Bot className="h-5 w-5 text-white" />
                    }
                  </div>
                  <div className={`rounded-lg p-3 ${
                    message.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-white/10 text-gray-100'
                  }`}>
                    <p className="whitespace-pre-wrap">{message.content}</p>
                    <p className="text-xs mt-1 opacity-70">
                      {message.timestamp.toLocaleTimeString()}
                    </p>
                  </div>
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="flex items-center space-x-2 bg-white/10 rounded-lg p-3">
                  <Loader2 className="h-4 w-4 animate-spin text-purple-400" />
                  <span className="text-gray-300">MemMachine is thinking...</span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="flex space-x-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything... Your memories are being stored!"
              className="flex-1 bg-white/10 backdrop-blur-sm text-white placeholder-gray-400 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
              disabled={loading || memoryInfo.connectionStatus !== 'connected'}
            />
            <button
              type="submit"
              disabled={loading || !input.trim() || memoryInfo.connectionStatus !== 'connected'}
              className="bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg px-6 py-3 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
            >
              {loading ? (
                <Loader2 className="h-5 w-5 animate-spin" />
              ) : (
                <Send className="h-5 w-5" />
              )}
            </button>
          </form>
        </div>

        {/* Footer Info */}
        <div className="mt-4 text-center text-sm text-gray-400">
          Powered by MemMachine | PostgreSQL + Neo4j | Deployed via MemCloud
        </div>
      </div>
    </div>
  )
}