"use client"

import React, { useState } from 'react'
import { CheckCircle, Copy, ExternalLink, Terminal, Code, Database, Zap, X } from 'lucide-react'

interface DeploymentEndpoints {
  memmachine_api: string
  postgres: string
  neo4j: string
  playground: string
}

interface DeploymentSuccessProps {
  deploymentId: string
  endpoints: DeploymentEndpoints
  qualityScore: number
  onClose?: () => void
}

export function DeploymentSuccess({ deploymentId, endpoints, qualityScore, onClose }: DeploymentSuccessProps) {
  const [copiedItem, setCopiedItem] = useState<string | null>(null)

  const copyToClipboard = (text: string, item: string) => {
    navigator.clipboard.writeText(text)
    setCopiedItem(item)
    setTimeout(() => setCopiedItem(null), 2000)
  }

  const codeExamples = {
    health: `curl ${endpoints.memmachine_api}/health`,
    store: `curl -X POST ${endpoints.memmachine_api}/memory \\
  -H 'Content-Type: application/json' \\
  -d '{
    "user_id": "demo-user",
    "content": "Hello MemMachine!",
    "metadata": {
      "source": "api",
      "type": "greeting"
    }
  }'`,
    query: `curl -X POST ${endpoints.memmachine_api}/query \\
  -H 'Content-Type: application/json' \\
  -d '{
    "user_id": "demo-user",
    "query": "What do you remember about greetings?",
    "top_k": 5
  }'`,
    python: `from memmachine import MemMachineClient

client = MemMachineClient(
    api_url="${endpoints.memmachine_api}",
    user_id="demo-user"
)

# Store a memory
client.store_memory(
    content="The user loves building AI applications",
    metadata={"type": "preference", "confidence": 0.9}
)

# Query memories
memories = client.query(
    "What does the user like?",
    top_k=5
)

for memory in memories:
    print(f"Memory: {memory.content}")
    print(f"Relevance: {memory.score}")`,
  }

  return (
    <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-green-500 to-blue-600 p-8 text-white">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="bg-white/20 backdrop-blur rounded-full p-3">
                <CheckCircle className="w-8 h-8" />
              </div>
              <div>
                <h2 className="text-3xl font-bold mb-2">Deployment Successful!</h2>
                <p className="text-green-100">
                  Your MemMachine instance is ready for production use
                </p>
              </div>
            </div>
            {onClose && (
              <button
                onClick={onClose}
                className="text-white/80 hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>
            )}
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4 mt-6">
            <div className="bg-white/10 backdrop-blur rounded-lg p-3">
              <div className="text-sm text-green-100">Deployment ID</div>
              <div className="font-mono text-xs mt-1 truncate">{deploymentId}</div>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-3">
              <div className="text-sm text-green-100">Quality Score</div>
              <div className="text-2xl font-bold mt-1">{qualityScore}%</div>
            </div>
            <div className="bg-white/10 backdrop-blur rounded-lg p-3">
              <div className="text-sm text-green-100">Status</div>
              <div className="text-lg font-semibold mt-1">Production Ready</div>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="p-8 overflow-y-auto max-h-[calc(90vh-280px)]">
          {/* Endpoints */}
          <div className="mb-8">
            <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-yellow-500" />
              Service Endpoints
            </h3>
            <div className="space-y-3">
              <div className="bg-gray-50 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-600 mb-1">MemMachine API</div>
                  <code className="text-sm font-mono text-blue-600">{endpoints.memmachine_api}</code>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => copyToClipboard(endpoints.memmachine_api, 'api')}
                    className="text-gray-500 hover:text-blue-600 transition-colors"
                  >
                    {copiedItem === 'api' ? (
                      <CheckCircle className="w-5 h-5 text-green-500" />
                    ) : (
                      <Copy className="w-5 h-5" />
                    )}
                  </button>
                  <a
                    href={endpoints.memmachine_api}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-gray-500 hover:text-blue-600 transition-colors"
                  >
                    <ExternalLink className="w-5 h-5" />
                  </a>
                </div>
              </div>

              <div className="bg-gray-50 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-600 mb-1">PostgreSQL (pgvector)</div>
                  <code className="text-sm font-mono text-gray-700">{endpoints.postgres}</code>
                </div>
                <Database className="w-5 h-5 text-gray-400" />
              </div>

              <div className="bg-gray-50 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-600 mb-1">Neo4j Graph Database</div>
                  <code className="text-sm font-mono text-gray-700">{endpoints.neo4j}</code>
                </div>
                <Database className="w-5 h-5 text-gray-400" />
              </div>

              <div className="bg-gray-50 rounded-lg p-4 flex items-center justify-between">
                <div>
                  <div className="text-sm text-gray-600 mb-1">Interactive Playground</div>
                  <code className="text-sm font-mono text-purple-600">{endpoints.playground}</code>
                </div>
                <a
                  href={endpoints.playground}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium"
                >
                  Open Playground
                </a>
              </div>
            </div>
          </div>

          {/* Quick Start */}
          <div className="mb-8">
            <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Terminal className="w-5 h-5 text-blue-500" />
              Quick Start Guide
            </h3>

            <div className="space-y-4">
              {/* Health Check */}
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">1. Test Health Check</span>
                    <button
                      onClick={() => copyToClipboard(codeExamples.health, 'health')}
                      className="text-gray-500 hover:text-blue-600 transition-colors"
                    >
                      {copiedItem === 'health' ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
                <pre className="p-4 text-sm font-mono text-gray-800 overflow-x-auto">
                  <code>{codeExamples.health}</code>
                </pre>
              </div>

              {/* Store Memory */}
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">2. Store a Memory</span>
                    <button
                      onClick={() => copyToClipboard(codeExamples.store, 'store')}
                      className="text-gray-500 hover:text-blue-600 transition-colors"
                    >
                      {copiedItem === 'store' ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
                <pre className="p-4 text-sm font-mono text-gray-800 overflow-x-auto">
                  <code>{codeExamples.store}</code>
                </pre>
              </div>

              {/* Query Memories */}
              <div className="border rounded-lg overflow-hidden">
                <div className="bg-gray-50 px-4 py-2 border-b">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium text-gray-700">3. Query Memories</span>
                    <button
                      onClick={() => copyToClipboard(codeExamples.query, 'query')}
                      className="text-gray-500 hover:text-blue-600 transition-colors"
                    >
                      {copiedItem === 'query' ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
                <pre className="p-4 text-sm font-mono text-gray-800 overflow-x-auto">
                  <code>{codeExamples.query}</code>
                </pre>
              </div>
            </div>
          </div>

          {/* Python SDK */}
          <div className="mb-8">
            <h3 className="text-xl font-semibold text-gray-800 mb-4 flex items-center gap-2">
              <Code className="w-5 h-5 text-green-500" />
              Python SDK Example
            </h3>
            <div className="border rounded-lg overflow-hidden">
              <div className="bg-gray-50 px-4 py-2 border-b">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">Complete Python Example</span>
                  <button
                    onClick={() => copyToClipboard(codeExamples.python, 'python')}
                    className="text-gray-500 hover:text-blue-600 transition-colors"
                  >
                    {copiedItem === 'python' ? (
                      <CheckCircle className="w-4 h-4 text-green-500" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                </div>
              </div>
              <pre className="p-4 text-sm font-mono text-gray-800 overflow-x-auto bg-gray-900 text-gray-100">
                <code>{codeExamples.python}</code>
              </pre>
            </div>
          </div>

          {/* Next Steps */}
          <div className="bg-blue-50 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-blue-900 mb-3">Next Steps</h3>
            <ul className="space-y-2 text-sm text-blue-800">
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                <span>Configure authentication for production use</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                <span>Set up monitoring dashboards and alerts</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                <span>Review the MemMachine documentation for advanced features</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle className="w-4 h-4 text-blue-500 mt-0.5 flex-shrink-0" />
                <span>Configure backup and disaster recovery</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}