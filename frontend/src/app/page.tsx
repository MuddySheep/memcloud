'use client'

import { useState, useEffect } from 'react'
import { Brain, Cloud, Zap, Play, Loader2, CheckCircle, AlertCircle, Clock, Rocket } from 'lucide-react'
import Link from 'next/link'
import { DeploymentProgress } from '../components/DeploymentProgress'
import { DeploymentSuccess } from '../components/DeploymentSuccess'

interface Instance {
  id: string
  name: string
  status: string
  cloud_run_url?: string
  created_at: string
  config?: {
    neo4j_service?: string
    postgres_connection?: string
  }
}

interface ActiveDeployment {
  deployment_id: string
  websocket_url: string
  status: string
}

export default function Dashboard() {
  const [instances, setInstances] = useState<Instance[]>([])
  const [loading, setLoading] = useState(true)
  const [deploying, setDeploying] = useState(false)
  const [activeDeployment, setActiveDeployment] = useState<ActiveDeployment | null>(null)
  const [deploymentSuccess, setDeploymentSuccess] = useState<any>(null)
  const [newInstanceName, setNewInstanceName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchInstances()
    // Poll for updates every 10 seconds
    const interval = setInterval(fetchInstances, 10000)
    return () => clearInterval(interval)
  }, [])

  const fetchInstances = async () => {
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/instances`)
      if (response.ok) {
        const data = await response.json()
        setInstances(data)
      }
    } catch (error) {
      console.error('Error fetching instances:', error)
    } finally {
      setLoading(false)
    }
  }

  const deployNewInstance = async () => {
    if (!newInstanceName || !apiKey) {
      setError('Please provide both instance name and OpenAI API key')
      return
    }

    setDeploying(true)
    setError(null)
    setActiveDeployment(null)
    setDeploymentSuccess(null)

    try {
      // Start real deployment with ADLF phases
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/api/v1/deployment/deploy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newInstanceName,
          openai_api_key: apiKey
        })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Deployment failed')
      }

      const data = await response.json()

      // Set active deployment to show progress
      setActiveDeployment({
        deployment_id: data.deployment_id,
        websocket_url: data.websocket_url,
        status: data.status
      })

      // Clear form
      setNewInstanceName('')
      setApiKey('')
    } catch (error: any) {
      console.error('Deployment error:', error)
      setError(error.message || 'Failed to start deployment. Please try again.')
      setDeploying(false)
    }
  }

  const handleDeploymentComplete = (status: any) => {
    setDeploying(false)
    setActiveDeployment(null)

    if (status.success && status.endpoints) {
      setDeploymentSuccess({
        deploymentId: status.deployment_id,
        endpoints: status.endpoints,
        qualityScore: status.quality_score
      })
    }

    // Refresh instances list
    fetchInstances()
  }

  const getStatusIcon = (status: string) => {
    switch (status?.toUpperCase()) {
      case 'RUNNING':
        return <CheckCircle className="h-5 w-5 text-green-500" />
      case 'DEPLOYING':
        return <Loader2 className="h-5 w-5 text-yellow-500 animate-spin" />
      case 'FAILED':
        return <AlertCircle className="h-5 w-5 text-red-500" />
      default:
        return <Clock className="h-5 w-5 text-gray-500" />
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900">
      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <Brain className="h-12 w-12 text-blue-400" />
            <div>
              <h1 className="text-4xl font-bold text-white">MemCloud</h1>
              <p className="text-gray-300">Deploy MemMachine with One Click</p>
            </div>
          </div>
          <div className="flex items-center space-x-4 text-gray-300">
            <Cloud className="h-6 w-6" />
            <span>Powered by Google Cloud</span>
          </div>
        </div>

        {/* Show deployment progress if active */}
        {activeDeployment && (
          <DeploymentProgress
            deploymentId={activeDeployment.deployment_id}
            onComplete={handleDeploymentComplete}
          />
        )}

        {/* Show success modal */}
        {deploymentSuccess && (
          <DeploymentSuccess
            deploymentId={deploymentSuccess.deploymentId}
            endpoints={deploymentSuccess.endpoints}
            qualityScore={deploymentSuccess.qualityScore}
            onClose={() => setDeploymentSuccess(null)}
          />
        )}

        {/* Deploy New Instance */}
        {!activeDeployment && (
          <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6 mb-8">
            <h2 className="text-2xl font-semibold text-white mb-4 flex items-center gap-3">
              <Rocket className="h-8 w-8 text-yellow-400" />
              Deploy New Instance
            </h2>

            {error && (
              <div className="mb-4 p-4 bg-red-500/20 rounded-lg flex items-center gap-2 text-red-200">
                <AlertCircle className="h-5 w-5" />
                <span>{error}</span>
              </div>
            )}

            <div className="grid md:grid-cols-3 gap-4">
              <input
                type="text"
                placeholder="Instance Name"
                value={newInstanceName}
                onChange={(e) => setNewInstanceName(e.target.value)}
                className="bg-white/10 text-white placeholder-gray-400 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={deploying}
              />
              <input
                type="password"
                placeholder="OpenAI API Key (sk-...)"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="bg-white/10 text-white placeholder-gray-400 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={deploying}
              />
              <button
                onClick={deployNewInstance}
                disabled={deploying}
                className="bg-gradient-to-r from-blue-500 to-purple-600 text-white rounded-lg px-6 py-3 hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center space-x-2 font-semibold"
              >
                {deploying ? (
                  <>
                    <Loader2 className="h-5 w-5 animate-spin" />
                    <span>Initializing...</span>
                  </>
                ) : (
                  <>
                    <Zap className="h-5 w-5" />
                    <span>Deploy MemMachine</span>
                  </>
                )}
              </button>
            </div>

            <div className="mt-4 p-4 bg-blue-500/10 rounded-lg">
              <p className="text-sm text-gray-300">
                <strong>What happens when you deploy:</strong>
              </p>
              <ul className="text-sm text-gray-400 mt-2 space-y-1">
                <li>• Cloud SQL PostgreSQL with pgvector extension</li>
                <li>• Neo4j graph database for episodic memory</li>
                <li>• MemMachine API with auto-scaling</li>
                <li>• Secure secrets management</li>
                <li>• Complete in under 7 minutes!</li>
              </ul>
            </div>
          </div>
        )}

        {/* Instances List */}
        <div className="bg-white/10 backdrop-blur-lg rounded-xl p-6">
          <h2 className="text-2xl font-semibold text-white mb-4">Your Instances</h2>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 text-blue-400 animate-spin" />
            </div>
          ) : instances.length === 0 ? (
            <div className="text-center py-12">
              <Cloud className="h-16 w-16 text-gray-500 mx-auto mb-4" />
              <p className="text-gray-400 text-lg">No instances deployed yet</p>
              <p className="text-gray-500 mt-2">Deploy your first MemMachine instance above!</p>
            </div>
          ) : (
            <div className="grid gap-4">
              {instances.map((instance) => (
                <div
                  key={instance.id}
                  className="bg-white/5 rounded-lg p-4 hover:bg-white/10 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(instance.status)}
                        <h3 className="text-lg font-semibold text-white">{instance.name}</h3>
                      </div>
                      <span className="text-sm text-gray-400">ID: {instance.id.slice(0, 8)}...</span>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        instance.status === 'RUNNING' ? 'bg-green-500/20 text-green-300' :
                        instance.status === 'DEPLOYING' ? 'bg-yellow-500/20 text-yellow-300' :
                        'bg-gray-500/20 text-gray-300'
                      }`}>
                        {instance.status}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2">
                      {instance.status === 'RUNNING' && (
                        <Link
                          href={`/playground/${instance.id}`}
                          className="bg-gradient-to-r from-green-500 to-blue-500 text-white rounded-lg px-4 py-2 hover:from-green-600 hover:to-blue-600 transition-all duration-200 flex items-center space-x-2"
                        >
                          <Play className="h-4 w-4" />
                          <span>Open Playground</span>
                        </Link>
                      )}
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">PostgreSQL</p>
                      <p className="text-gray-300">{instance.config?.postgres_connection ? 'Connected' : 'Pending'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Neo4j</p>
                      <p className="text-gray-300">{instance.config?.neo4j_service ? 'Connected' : 'Pending'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Created</p>
                      <p className="text-gray-300">{new Date(instance.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-400 text-sm">
          <p>Built for the "Memories That Last" Hackathon</p>
          <p className="mt-2">PostgreSQL + Neo4j + MemMachine = AI Memory Layer</p>
          <p className="mt-2 text-xs">Following ADLF Framework: Discovery → Architecture → MVP → Beta → Production</p>
        </div>
      </div>
    </div>
  )
}