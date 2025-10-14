'use client'

import { useState, useEffect } from 'react'
import { Brain, Cloud, Zap, Play, Loader2, CheckCircle, AlertCircle, Clock, Rocket, Trash2 } from 'lucide-react'
import Link from 'next/link'
import { DeploymentProgress } from '../../components/DeploymentProgress'
import { DeploymentSuccess } from '../../components/DeploymentSuccess'

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
  // TODO: Replace with real user ID from Firebase Auth in Phase 3.2
  const CURRENT_USER_ID = 'demo-user-123'

  const [instances, setInstances] = useState<Instance[]>([])
  const [loading, setLoading] = useState(true)
  const [deploying, setDeploying] = useState(false)
  const [activeDeployment, setActiveDeployment] = useState<ActiveDeployment | null>(null)
  const [deploymentSuccess, setDeploymentSuccess] = useState<any>(null)
  const [newInstanceName, setNewInstanceName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [demoMode, setDemoMode] = useState(false)
  const [hiddenInstances, setHiddenInstances] = useState<Set<string>>(new Set())

  // Load hidden instances from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem('hiddenInstances')
      if (stored) {
        setHiddenInstances(new Set(JSON.parse(stored)))
      }
    } catch (e) {
      console.error('Failed to load hidden instances:', e)
    }
  }, [])

  useEffect(() => {
    fetchInstances()
    // Poll for updates every 10 seconds
    const interval = setInterval(fetchInstances, 10000)
    return () => clearInterval(interval)
  }, [hiddenInstances])

  const fetchInstances = async () => {
    try {
      // Add timeout to prevent infinite loading
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 5000) // 5 second timeout

      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/instances?user_id=${CURRENT_USER_ID}`,
        { signal: controller.signal }
      )

      clearTimeout(timeoutId)

      if (response.ok) {
        const data = await response.json()
        // Map backend field 'url' to frontend field 'cloud_run_url'
        const mappedData = data.map((inst: any) => ({
          ...inst,
          cloud_run_url: inst.url || inst.cloud_run_url
        }))
        // Filter out instances that user has hidden
        const visibleInstances = mappedData.filter((inst: Instance) => !hiddenInstances.has(inst.id))
        setInstances(visibleInstances)
      }
    } catch (error) {
      console.error('Error fetching instances:', error)
      // On error, just show empty state - don't keep spinning
    } finally {
      setLoading(false)
    }
  }

  const startDemoDeployment = () => {
    setDemoMode(true)
    setDeploying(true)
    setError(null)

    // Simulate demo deployment with mock data
    setActiveDeployment({
      deployment_id: 'demo-' + Date.now(),
      websocket_url: 'wss://demo',
      status: 'deploying'
    })
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
          openai_api_key: apiKey,
          user_id: CURRENT_USER_ID
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

    if (demoMode) {
      // Add a demo instance to the list
      const demoInstance: Instance = {
        id: 'demo-instance-001',
        name: 'Demo MemMachine',
        status: 'RUNNING',
        cloud_run_url: 'https://demo-memmachine.run.app',
        created_at: new Date().toISOString(),
        config: {
          neo4j_service: 'demo-neo4j.googleapis.com',
          postgres_connection: 'demo-postgres.googleapis.com'
        }
      }
      setInstances([demoInstance])
      setDemoMode(false)
    } else if (status.success && status.endpoints) {
      setDeploymentSuccess({
        deploymentId: status.deployment_id,
        endpoints: status.endpoints,
        qualityScore: status.quality_score
      })
      // Refresh instances list
      fetchInstances()
    }
  }

  const hideInstance = (instanceId: string) => {
    const newHidden = new Set(hiddenInstances)
    newHidden.add(instanceId)
    setHiddenInstances(newHidden)
    localStorage.setItem('hiddenInstances', JSON.stringify(Array.from(newHidden)))
    setInstances(instances.filter(i => i.id !== instanceId))
  }

  const deleteInstance = async (instanceId: string, instanceName: string) => {
    if (!confirm(`Are you sure you want to delete "${instanceName}"?\n\nThis will permanently remove:\n• Cloud Run services\n• Cloud SQL database\n• Neo4j instance\n• All secrets\n\nThis action CANNOT be undone.`)) {
      return
    }

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/api/v1/instances/${instanceId}?user_id=${CURRENT_USER_ID}`,
        { method: 'DELETE' }
      )

      if (response.ok) {
        // Successfully deleted from backend - hide from UI
        hideInstance(instanceId)
        // Refresh to get updated list from backend
        fetchInstances()
      } else if (response.status === 404) {
        // Instance doesn't exist in backend - just hide from frontend
        console.log(`Instance ${instanceId} not found in backend, hiding from UI`)
        hideInstance(instanceId)
      } else if (response.status === 500 || response.status === 503) {
        // Backend is down or database connection failed
        // Ask user if they want to hide from UI anyway
        if (confirm('Backend is currently unavailable. Remove this instance from the UI anyway?\n\n(Note: GCP resources may still exist and need manual cleanup)')) {
          hideInstance(instanceId)
        }
      } else {
        try {
          const errorData = await response.json()
          setError(errorData.detail || 'Failed to delete instance')
        } catch {
          setError(`Failed to delete instance (HTTP ${response.status})`)
        }
      }
    } catch (error: any) {
      console.error('Delete error:', error)
      // Network error or backend completely down
      if (confirm('Cannot connect to backend. Remove this instance from the UI anyway?\n\n(Note: GCP resources may still exist and need manual cleanup)')) {
        hideInstance(instanceId)
      }
    }
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
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center space-x-2">
              <Cloud className="h-8 w-8 text-blue-600" />
              <span className="text-xl font-bold text-gray-900">MemCloud</span>
            </Link>
            <div className="flex items-center space-x-4">
              <span className="text-gray-700">Dashboard</span>
            </div>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center space-x-4">
            <Brain className="h-12 w-12 text-blue-600" />
            <div>
              <h1 className="text-4xl font-bold text-gray-900">MemCloud Dashboard</h1>
              <p className="text-gray-600">Deploy MemMachine with One Click</p>
            </div>
          </div>
          <div className="flex items-center space-x-4 text-gray-600">
            <Cloud className="h-6 w-6" />
            <span>Powered by Google Cloud</span>
          </div>
        </div>

        {/* Show deployment progress if active */}
        {activeDeployment && (
          <DeploymentProgress
            deploymentId={activeDeployment.deployment_id}
            onComplete={handleDeploymentComplete}
            demoMode={demoMode}
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
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
            <h2 className="text-2xl font-semibold text-gray-900 mb-4 flex items-center gap-3">
              <Rocket className="h-8 w-8 text-blue-600" />
              Deploy New Instance
            </h2>

            {error && (
              <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-2 text-red-700">
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
                className="bg-white border border-gray-300 text-gray-900 placeholder-gray-500 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={deploying}
              />
              <input
                type="password"
                placeholder="OpenAI API Key (sk-...)"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="bg-white border border-gray-300 text-gray-900 placeholder-gray-500 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
                disabled={deploying}
              />
              <button
                onClick={deployNewInstance}
                disabled={deploying}
                className="bg-blue-600 text-white rounded-lg px-6 py-3 hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center justify-center space-x-2 font-semibold"
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

            <div className="mt-4 p-4 bg-blue-50 border border-blue-200 rounded-lg">
              <p className="text-sm text-gray-900 font-medium">
                What happens when you deploy:
              </p>
              <ul className="text-sm text-gray-700 mt-2 space-y-1">
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
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h2 className="text-2xl font-semibold text-gray-900 mb-4">Your Instances</h2>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 text-blue-600 animate-spin" />
            </div>
          ) : instances.length === 0 ? (
            <div className="text-center py-12">
              <Cloud className="h-16 w-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 text-lg">No instances deployed yet</p>
              <p className="text-gray-500 mt-2">Deploy your first MemMachine instance above!</p>
              <button
                onClick={startDemoDeployment}
                className="mt-6 bg-gradient-to-r from-purple-600 to-pink-600 text-white rounded-lg px-6 py-3 hover:from-purple-700 hover:to-pink-700 transition-all duration-200 flex items-center justify-center space-x-2 font-semibold mx-auto"
              >
                <Play className="h-5 w-5" />
                <span>Watch Demo Deployment</span>
              </button>
            </div>
          ) : (
            <div className="grid gap-4">
              {instances.map((instance) => (
                <div
                  key={instance.id}
                  className="bg-gray-50 border border-gray-200 rounded-lg p-4 hover:bg-gray-100 transition-colors"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(instance.status)}
                        <h3 className="text-lg font-semibold text-gray-900">{instance.name}</h3>
                      </div>
                      <span className="text-sm text-gray-600">ID: {instance.id.slice(0, 8)}...</span>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        instance.status?.toUpperCase() === 'RUNNING' ? 'bg-green-100 text-green-800' :
                        instance.status?.toUpperCase() === 'DEPLOYING' ? 'bg-yellow-100 text-yellow-800' :
                        'bg-gray-100 text-gray-800'
                      }`}>
                        {instance.status?.toUpperCase()}
                      </span>
                    </div>

                    <div className="flex items-center space-x-2">
                      {instance.status?.toUpperCase() === 'RUNNING' && (
                        <>
                          <Link
                            href={`/playground/${instance.id}`}
                            className="bg-blue-600 text-white rounded-lg px-4 py-2 hover:bg-blue-700 transition-all duration-200 flex items-center space-x-2"
                          >
                            <Play className="h-4 w-4" />
                            <span>Open Playground</span>
                          </Link>
                          <button
                            onClick={() => deleteInstance(instance.id, instance.name)}
                            className="bg-red-600 text-white rounded-lg px-4 py-2 hover:bg-red-700 transition-all duration-200 flex items-center space-x-2"
                          >
                            <Trash2 className="h-4 w-4" />
                            <span>Delete</span>
                          </button>
                        </>
                      )}
                      {(instance.status?.toUpperCase() === 'FAILED' || instance.status?.toUpperCase() === 'DELETING') && (
                        <button
                          onClick={() => deleteInstance(instance.id, instance.name)}
                          disabled={instance.status?.toUpperCase() === 'DELETING'}
                          className="bg-red-600 text-white rounded-lg px-4 py-2 hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center space-x-2"
                        >
                          <Trash2 className="h-4 w-4" />
                          <span>{instance.status?.toUpperCase() === 'DELETING' ? 'Deleting...' : 'Delete'}</span>
                        </button>
                      )}
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-gray-500">PostgreSQL</p>
                      <p className="text-gray-900">{instance.config?.postgres_connection ? 'Connected' : 'Pending'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Neo4j</p>
                      <p className="text-gray-900">{instance.config?.neo4j_service ? 'Connected' : 'Pending'}</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Created</p>
                      <p className="text-gray-900">{new Date(instance.created_at).toLocaleDateString()}</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-8 text-center text-gray-600 text-sm">
          <p>Built for the "Memories That Last" Hackathon</p>
          <p className="mt-2">PostgreSQL + Neo4j + MemMachine = AI Memory Layer</p>
        </div>
      </div>
    </div>
  )
}
