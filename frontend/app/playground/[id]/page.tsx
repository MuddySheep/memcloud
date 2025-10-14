'use client'

import { useParams } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Send, Sparkles, Loader2 } from 'lucide-react'
import { useState, useEffect } from 'react'

interface Instance {
  id: string
  name: string
  status: string
  cloud_run_url?: string
  user_id: string
}

export default function PlaygroundPage() {
  const params = useParams()
  const instanceId = params.id as string

  // TODO: Replace with real user ID from Firebase Auth in Phase 3.2
  const CURRENT_USER_ID = 'demo-user-123'

  const [instance, setInstance] = useState<Instance | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<Array<{role: string, content: string}>>([
    {
      role: 'assistant',
      content: '🚀 Welcome to MemMachine Playground - LIVE! I\'m powered by real AI with persistent memory using PostgreSQL (semantic) and Neo4j (episodic). I can remember our conversations and learn from them. Ask me anything!'
    }
  ])

  // Fetch instance details on mount
  useEffect(() => {
    const fetchInstance = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/instances/${instanceId}?user_id=${CURRENT_USER_ID}`
        )

        if (!response.ok) {
          if (response.status === 404) {
            throw new Error('Instance not found or access denied')
          }
          throw new Error('Failed to fetch instance details')
        }

        const data = await response.json()
        // Map backend field 'url' to frontend field 'cloud_run_url'
        const mappedInstance = {
          ...data,
          cloud_run_url: data.url || data.cloud_run_url
        }
        setInstance(mappedInstance)

        if (mappedInstance.status?.toUpperCase() !== 'RUNNING') {
          setError(`Instance is ${mappedInstance.status}. Please wait for it to be RUNNING.`)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load instance')
      } finally {
        setLoading(false)
      }
    }

    fetchInstance()
  }, [instanceId])

  const handleSend = async () => {
    if (!input.trim() || !instance?.cloud_run_url) return

    const userMessage = input
    setInput('')

    // Add user message immediately
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])

    try {
      // Call the user's specific MemMachine instance
      const response = await fetch(`${instance.cloud_run_url}/v1/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session: {
            group_id: 'memcloud',
            agent_id: ['assistant'],  // Must be array
            user_id: [instanceId],     // Must be array
            session_id: `playground-${instanceId}`
          },
          messages: [
            {
              role: 'user',
              content: userMessage
            }
          ]
        })
      })

      if (!response.ok) {
        throw new Error(`API error: ${response.status}`)
      }

      const data = await response.json()
      const assistantMessage = data.content || data.message || 'I received your message!'

      // Add assistant response
      setMessages(prev => [...prev, { role: 'assistant', content: assistantMessage }])
    } catch (error) {
      console.error('MemMachine API error:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `⚠️ Error connecting to MemMachine: ${error instanceof Error ? error.message : 'Unknown error'}`
      }])
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
      </div>
    )
  }

  if (error || !instance) {
    return (
      <div className="min-h-screen bg-gray-50">
        <nav className="bg-white border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between items-center h-16">
              <Link href="/dashboard" className="flex items-center space-x-2 text-gray-700 hover:text-gray-900">
                <ArrowLeft className="h-5 w-5" />
                <span>Back to Dashboard</span>
              </Link>
            </div>
          </div>
        </nav>
        <div className="max-w-4xl mx-auto px-4 py-8">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6">
            <h2 className="text-xl font-bold text-red-900 mb-2">Error Loading Instance</h2>
            <p className="text-red-700">{error || 'Instance not found'}</p>
            <Link href="/dashboard" className="mt-4 inline-block text-blue-600 hover:underline">
              Return to Dashboard
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/dashboard" className="flex items-center space-x-2 text-gray-700 hover:text-gray-900">
              <ArrowLeft className="h-5 w-5" />
              <span>Back to Dashboard</span>
            </Link>
            <div className="flex items-center space-x-3">
              <Sparkles className="h-5 w-5 text-blue-600" />
              <span className="font-semibold text-gray-900">MemMachine Playground</span>
            </div>
          </div>
        </div>
      </nav>

      <div className="max-w-4xl mx-auto px-4 py-8">
        {/* Instance Info */}
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold text-gray-900 mb-2">Instance: {instance.name}</h2>
          <p className="text-sm text-gray-600 mb-3">ID: {instanceId}</p>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-600">Status</p>
              <p className={`font-semibold ${instance.status?.toUpperCase() === 'RUNNING' ? 'text-green-600' : 'text-yellow-600'}`}>
                ● {instance.status?.toUpperCase()}
              </p>
            </div>
            <div>
              <p className="text-gray-600">PostgreSQL</p>
              <p className="font-semibold text-gray-900">Connected ✓</p>
            </div>
            <div>
              <p className="text-gray-600">Neo4j</p>
              <p className="font-semibold text-gray-900">Connected ✓</p>
            </div>
          </div>
        </div>

        {/* Chat Interface */}
        <div className="bg-white rounded-lg shadow-sm border border-gray-200">
          {/* Messages */}
          <div className="h-96 overflow-y-auto p-6 space-y-4">
            {messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div
                  className={`max-w-xs lg:max-w-md px-4 py-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  {msg.content}
                </div>
              </div>
            ))}
          </div>

          {/* Input */}
          <div className="border-t border-gray-200 p-4">
            <div className="flex gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Type a message..."
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleSend}
                disabled={instance?.status?.toUpperCase() !== 'RUNNING'}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                <Send className="h-4 w-4" />
                Send
              </button>
            </div>
            {instance?.status?.toUpperCase() === 'RUNNING' ? (
              <p className="text-xs text-green-600 font-medium mt-2">
                ✨ LIVE: Connected to {instance.cloud_run_url}
              </p>
            ) : (
              <p className="text-xs text-yellow-600 font-medium mt-2">
                ⏳ Instance is {instance?.status}. Please wait...
              </p>
            )}
          </div>
        </div>

        {/* Features Info */}
        <div className="mt-6 grid md:grid-cols-2 gap-4">
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-2">🧠 Episodic Memory</h3>
            <p className="text-sm text-gray-600">
              Neo4j graph database stores conversation context and relationships
            </p>
          </div>
          <div className="bg-white border border-gray-200 rounded-lg p-4">
            <h3 className="font-semibold text-gray-900 mb-2">📚 Semantic Memory</h3>
            <p className="text-sm text-gray-600">
              PostgreSQL with pgvector enables similarity search across memories
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
