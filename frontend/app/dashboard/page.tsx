'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { Cloud, Plus, ExternalLink, Trash2, RefreshCw } from 'lucide-react'
import { api, type Instance } from '@/lib/api'
import { formatDate, getStatusColor } from '@/lib/utils'

export default function DashboardPage() {
  const [instances, setInstances] = useState<Instance[]>([])
  const [loading, setLoading] = useState(true)
  const [showDeployModal, setShowDeployModal] = useState(false)
  const [deploying, setDeploying] = useState(false)

  // Form state
  const [name, setName] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    loadInstances()
  }, [])

  async function loadInstances() {
    try {
      setLoading(true)
      const data = await api.listInstances()
      setInstances(data)
    } catch (err: any) {
      console.error('Failed to load instances:', err)
    } finally {
      setLoading(false)
    }
  }

  async function handleDeploy(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setDeploying(true)

    try {
      const result = await api.deployInstance({
        name,
        openai_api_key: apiKey,
      })

      // Success! Refresh instances
      await loadInstances()
      setShowDeployModal(false)
      setName('')
      setApiKey('')

      alert(`Deployment successful! URL: ${result.url}`)
    } catch (err: any) {
      setError(err.message || 'Deployment failed')
    } finally {
      setDeploying(false)
    }
  }

  async function handleDelete(instanceId: string) {
    if (!confirm('Are you sure you want to delete this instance?')) {
      return
    }

    try {
      await api.deleteInstance(instanceId)
      await loadInstances()
    } catch (err: any) {
      alert(`Failed to delete: ${err.message}`)
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Navigation */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link href="/" className="flex items-center">
              <Cloud className="h-8 w-8 text-blue-600" />
              <span className="ml-2 text-xl font-bold">MemCloud</span>
            </Link>
            <div className="flex items-center space-x-4">
              <button
                onClick={loadInstances}
                className="p-2 text-gray-600 hover:text-gray-900"
                title="Refresh"
              >
                <RefreshCw className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Header */}
        <div className="flex justify-between items-center mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Your Instances</h1>
            <p className="mt-1 text-gray-600">
              Manage your MemMachine deployments
            </p>
          </div>
          <button
            onClick={() => setShowDeployModal(true)}
            className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
          >
            <Plus className="h-5 w-5 mr-2" />
            Deploy New Instance
          </button>
        </div>

        {/* Instances Grid */}
        {loading ? (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-2 text-gray-600">Loading instances...</p>
          </div>
        ) : instances.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-lg border border-gray-200">
            <Cloud className="h-12 w-12 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No instances yet
            </h3>
            <p className="text-gray-600 mb-4">
              Deploy your first MemMachine instance to get started
            </p>
            <button
              onClick={() => setShowDeployModal(true)}
              className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              <Plus className="h-5 w-5 mr-2" />
              Deploy Now
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {instances.map((instance) => (
              <div
                key={instance.id}
                className="bg-white rounded-lg border border-gray-200 p-6 hover:shadow-md transition-shadow"
              >
                <div className="flex justify-between items-start mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    {instance.name}
                  </h3>
                  <span
                    className={`px-2 py-1 text-xs font-medium rounded-full ${getStatusColor(
                      instance.status
                    )}`}
                  >
                    {instance.status}
                  </span>
                </div>

                <div className="space-y-2 text-sm text-gray-600 mb-4">
                  <div>
                    <span className="font-medium">URL:</span>{' '}
                    <a
                      href={instance.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:underline inline-flex items-center"
                    >
                      {instance.slug}
                      <ExternalLink className="h-3 w-3 ml-1" />
                    </a>
                  </div>
                  <div>
                    <span className="font-medium">Health:</span>{' '}
                    <span className={getStatusColor(instance.health_status)}>
                      {instance.health_status}
                    </span>
                  </div>
                  <div>
                    <span className="font-medium">Created:</span>{' '}
                    {formatDate(instance.created_at)}
                  </div>
                </div>

                <div className="flex space-x-2">
                  <a
                    href={instance.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 inline-flex justify-center items-center px-3 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Open
                  </a>
                  <button
                    onClick={() => handleDelete(instance.id)}
                    className="inline-flex items-center px-3 py-2 border border-red-300 text-sm font-medium rounded-md text-red-700 bg-white hover:bg-red-50"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Deploy Modal */}
      {showDeployModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h2 className="text-2xl font-bold mb-4">Deploy MemMachine</h2>

            <form onSubmit={handleDeploy} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Instance Name
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="My MemMachine"
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  OpenAI API Key
                </label>
                <input
                  type="password"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                  required
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <p className="mt-1 text-xs text-gray-500">
                  Your API key is encrypted and stored securely in GCP Secret Manager
                </p>
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
                  {error}
                </div>
              )}

              <div className="flex space-x-3">
                <button
                  type="button"
                  onClick={() => setShowDeployModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
                  disabled={deploying}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={deploying}
                  className="flex-1 px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50"
                >
                  {deploying ? (
                    <>
                      <div className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                      Deploying...
                    </>
                  ) : (
                    'Deploy'
                  )}
                </button>
              </div>

              <p className="text-xs text-gray-500 text-center">
                Deployment takes 60-90 seconds. You'll get a notification when complete.
              </p>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
