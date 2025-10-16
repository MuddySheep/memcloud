"use client"

import React, { useEffect, useState } from 'react'
import { CheckCircle, Clock, AlertCircle, Loader2, ChevronRight, Shield, Zap } from 'lucide-react'

interface DeploymentStep {
  id: string
  phase: string
  name: string
  status: 'pending' | 'in_progress' | 'completed' | 'failed'
  progress: number
  started_at?: string
  completed_at?: string
  error?: string
  details?: Record<string, any>
}

interface PhaseInfo {
  progress: number
  status: string
  gates: Array<{ name: string; passed: boolean }>
}

interface DeploymentStatus {
  deployment_id: string
  overall_progress: number
  current_phase: string
  quality_score: number
  phases: Record<string, PhaseInfo>
  steps: DeploymentStep[]
  endpoints?: {
    memmachine_api: string
    postgres: string
    neo4j: string
    playground: string
  }
  success: boolean
  decisions_made: Array<{
    decision: string
    timestamp: string
    confidence: string
  }>
  technical_debt: string[]
}

const PHASE_CONFIG = {
  DISCOVERY: {
    name: 'Discovery',
    color: 'bg-blue-600',
    icon: '🔍',
    range: [0, 5],
    description: 'Analyzing requirements'
  },
  ARCHITECTURE: {
    name: 'Architecture',
    color: 'bg-indigo-600',
    icon: '🏗️',
    range: [5, 15],
    description: 'Designing infrastructure'
  },
  MVP_CORE: {
    name: 'MVP Core',
    color: 'bg-purple-600',
    icon: '⚡',
    range: [15, 40],
    description: 'Deploying core services'
  },
  MVP_POLISH: {
    name: 'MVP Polish',
    color: 'bg-pink-600',
    icon: '✨',
    range: [40, 60],
    description: 'Configuring & optimizing'
  },
  BETA: {
    name: 'Beta',
    color: 'bg-orange-600',
    icon: '🚀',
    range: [60, 80],
    description: 'Testing & validation'
  },
  PRODUCTION: {
    name: 'Production',
    color: 'bg-green-600',
    icon: '🎯',
    range: [80, 100],
    description: 'Going live'
  }
}

interface DeploymentProgressProps {
  deploymentId: string
  onComplete?: (status: DeploymentStatus) => void
  demoMode?: boolean
}

export function DeploymentProgress({ deploymentId, onComplete, demoMode = false }: DeploymentProgressProps) {
  const [status, setStatus] = useState<DeploymentStatus | null>(null)
  const [ws, setWs] = useState<WebSocket | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isConnecting, setIsConnecting] = useState(true)

  useEffect(() => {
    if (!deploymentId) return

    // Demo mode - simulate deployment progress
    if (demoMode) {
      setIsConnecting(false)
      simulateDemoDeployment()
      return
    }

    // Determine WebSocket URL based on API URL
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://memcloud-api-576223366889.us-central1.run.app'
    const wsUrl = apiUrl.replace('https://', 'wss://').replace('http://', 'ws://')
    const websocket = new WebSocket(`${wsUrl}/api/v1/deployment/${deploymentId}/ws`)

    websocket.onopen = () => {
      console.log('WebSocket connected for deployment:', deploymentId)
      setIsConnecting(false)
    }

    websocket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        setStatus(data)

        if (data.success && onComplete) {
          onComplete(data)
        }
      } catch (err) {
        console.error('Error parsing WebSocket message:', err)
      }
    }

    websocket.onerror = (err) => {
      console.error('WebSocket error:', err)
      setError('WebSocket unavailable. Using polling instead...')
      setIsConnecting(false)
      // Fall back to polling
      websocket.close()
      startPolling()
    }

    websocket.onclose = () => {
      console.log('WebSocket disconnected')
      // If WebSocket closes, fall back to polling
      startPolling()
    }

    setWs(websocket)

    // Start polling as backup
    let pollingTimeout: NodeJS.Timeout
    const startPolling = () => {
      const poll = async () => {
        try {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'https://memcloud-api-576223366889.us-central1.run.app'
          const response = await fetch(`${apiUrl}/api/v1/deployment/${deploymentId}/status`)
          if (response.ok) {
            const data = await response.json()
            setStatus(data)
            setError(null)

            if (data.success && onComplete) {
              onComplete(data)
              return // Stop polling on success
            }
          }
        } catch (err) {
          console.error('Polling error:', err)
        }

        // Continue polling every 2 seconds
        pollingTimeout = setTimeout(poll, 2000)
      }
      poll()
    }

    return () => {
      if (websocket.readyState === WebSocket.OPEN) {
        websocket.close()
      }
      if (pollingTimeout) {
        clearTimeout(pollingTimeout)
      }
    }
  }, [deploymentId, onComplete, demoMode])

  const simulateDemoDeployment = () => {
    const phases: (keyof typeof PHASE_CONFIG)[] = ['DISCOVERY', 'ARCHITECTURE', 'MVP_CORE', 'MVP_POLISH', 'BETA', 'PRODUCTION']
    let currentProgress = 0
    let currentPhaseIndex = 0

    const interval = setInterval(() => {
      currentProgress += 2

      if (currentProgress > 100) {
        clearInterval(interval)
        // Call onComplete with success
        if (onComplete) {
          onComplete({
            deployment_id: deploymentId,
            overall_progress: 100,
            current_phase: 'PRODUCTION',
            quality_score: 98,
            phases: {},
            steps: [],
            success: true,
            decisions_made: [],
            technical_debt: []
          })
        }
        return
      }

      // Update current phase based on progress
      for (let i = 0; i < phases.length; i++) {
        const config = PHASE_CONFIG[phases[i]]
        if (currentProgress >= config.range[0] && currentProgress <= config.range[1]) {
          currentPhaseIndex = i
          break
        }
      }

      const demoPhases: Record<string, PhaseInfo> = {}
      phases.forEach((phase, idx) => {
        const config = PHASE_CONFIG[phase]
        let phaseStatus: string = 'pending'

        if (currentProgress > config.range[1]) {
          phaseStatus = 'completed'
        } else if (currentProgress >= config.range[0] && currentProgress <= config.range[1]) {
          phaseStatus = 'in_progress'
        }

        demoPhases[phase] = {
          progress: Math.min(100, ((currentProgress - config.range[0]) / (config.range[1] - config.range[0])) * 100),
          status: phaseStatus,
          gates: idx < currentPhaseIndex ? [
            { name: 'Security', passed: true },
            { name: 'Performance', passed: true },
            { name: 'Tests', passed: true }
          ] : []
        }
      })

      setStatus({
        deployment_id: deploymentId,
        overall_progress: currentProgress,
        current_phase: phases[currentPhaseIndex],
        quality_score: Math.min(98, 70 + (currentProgress / 100) * 28),
        phases: demoPhases,
        steps: [],
        success: false,
        decisions_made: [],
        technical_debt: []
      })
    }, 100) // Update every 100ms for smooth animation

    return () => clearInterval(interval)
  }

  const getPhaseStatus = (phaseKey: string) => {
    if (!status) return 'pending'
    const phase = status.phases[phaseKey]
    if (!phase) return 'pending'
    return phase.status
  }

  const getPhaseProgress = (phaseKey: string) => {
    if (!status) return 0
    const phase = status.phases[phaseKey]
    if (!phase) return 0

    const config = PHASE_CONFIG[phaseKey as keyof typeof PHASE_CONFIG]
    const [min, max] = config.range
    const phaseWidth = max - min
    const currentProgress = Math.max(0, Math.min(status.overall_progress - min, phaseWidth))
    return (currentProgress / phaseWidth) * 100
  }

  const renderPhase = (phaseKey: string) => {
    const config = PHASE_CONFIG[phaseKey as keyof typeof PHASE_CONFIG]
    const phaseStatus = getPhaseStatus(phaseKey)
    const progress = getPhaseProgress(phaseKey)
    const phase = status?.phases[phaseKey]

    return (
      <div key={phaseKey} className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3">
            <span className="text-2xl">{config.icon}</span>
            <div>
              <h3 className="text-lg font-semibold text-gray-800">
                {config.name}
              </h3>
              <p className="text-sm text-gray-600">{config.description}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {phaseStatus === 'completed' && (
              <CheckCircle className="w-5 h-5 text-green-600" />
            )}
            {phaseStatus === 'in_progress' && (
              <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
            )}
            {phaseStatus === 'pending' && (
              <Clock className="w-5 h-5 text-gray-400" />
            )}
            <span className="text-sm font-medium text-gray-700">
              {config.range[0]}-{config.range[1]}%
            </span>
          </div>
        </div>

        <div className="relative w-full h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`absolute top-0 left-0 h-full transition-all duration-500 ${config.color} ${
              phaseStatus === 'in_progress' ? 'animate-pulse' : ''
            }`}
            style={{ width: `${progress}%` }}
          />
        </div>

        {/* Quality Gates */}
        {phase?.gates && phase.gates.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-2">
            {phase.gates.map((gate, idx) => (
              <div
                key={idx}
                className={`text-xs px-2 py-1 rounded-full flex items-center gap-1 ${
                  gate.passed
                    ? 'bg-green-100 text-green-700'
                    : 'bg-gray-100 text-gray-500'
                }`}
              >
                <Shield className="w-3 h-3" />
                {gate.name}
              </div>
            ))}
          </div>
        )}

        {/* Active Steps in this Phase */}
        {status?.steps
          .filter(step => step.phase === phaseKey && step.status === 'in_progress')
          .map(step => (
            <div key={step.id} className="mt-2 pl-11">
              <div className="flex items-center gap-2 text-sm text-blue-600">
                <ChevronRight className="w-3 h-3" />
                <Loader2 className="w-3 h-3 animate-spin" />
                <span>{step.name}</span>
              </div>
            </div>
          ))}
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
        <div className="flex items-center gap-2 text-red-700">
          <AlertCircle className="w-5 h-5" />
          <p>{error}</p>
        </div>
      </div>
    )
  }

  if (isConnecting) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
        <div className="flex items-center justify-center gap-3">
          <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
          <span className="text-gray-700">Connecting to deployment service...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-8 mb-6">
      {/* Header */}
      <div className="mb-8 border-b pb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold text-gray-800">Deployment Progress</h2>
            <p className="text-sm text-gray-600 mt-1">
              Following the ADLF Framework - From Discovery to Production
            </p>
          </div>
          <div className="text-right">
            <div className="text-3xl font-bold text-blue-600">
              {status?.overall_progress || 0}%
            </div>
            <div className="text-sm text-gray-600">Complete</div>
          </div>
        </div>

        {/* Overall Progress Bar */}
        <div className="relative w-full h-6 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="absolute top-0 left-0 h-full bg-gradient-to-r from-blue-500 to-green-500 transition-all duration-500"
            style={{ width: `${status?.overall_progress || 0}%` }}
          />
        </div>

        {/* Quality Score (PFF) */}
        {status?.quality_score !== undefined && (
          <div className="mt-4 flex items-center gap-2">
            <span className="text-sm text-gray-600">Quality Score (PFF):</span>
            <div className="flex items-center gap-1">
              <Zap className="w-4 h-4 text-yellow-500" />
              <span className="text-lg font-bold text-gray-800">
                {status.quality_score}%
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Phases */}
      <div className="space-y-4">
        {Object.keys(PHASE_CONFIG).map(phaseKey => renderPhase(phaseKey))}
      </div>

      {/* Decision Ledger (CES) */}
      {status?.decisions_made && status.decisions_made.length > 0 && (
        <div className="mt-8 border-t pt-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">
            Decision Ledger (CES)
          </h3>
          <div className="space-y-2">
            {status.decisions_made.map((decision, idx) => (
              <div key={idx} className="flex items-center gap-3 text-sm">
                <span className="text-gray-500">
                  {new Date(decision.timestamp).toLocaleTimeString()}
                </span>
                <span className="text-gray-700">{decision.decision}</span>
                <span className="font-mono text-xs text-blue-600">
                  {decision.confidence}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Steps */}
      {status?.steps && status.steps.length > 0 && (
        <div className="mt-8 border-t pt-6">
          <h3 className="text-lg font-semibold text-gray-800 mb-3">
            Recent Activity
          </h3>
          <div className="space-y-2 max-h-40 overflow-y-auto">
            {status.steps
              .filter(step => step.status === 'completed')
              .slice(-5)
              .reverse()
              .map(step => (
                <div key={step.id} className="flex items-center gap-2 text-sm">
                  <CheckCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                  <span className="text-gray-700">{step.name}</span>
                  {step.completed_at && (
                    <span className="text-gray-400 text-xs">
                      {new Date(step.completed_at).toLocaleTimeString()}
                    </span>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}