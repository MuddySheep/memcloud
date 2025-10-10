'use client'

import Link from 'next/link'
import { ArrowRight, Cloud, Zap, Shield, DollarSign } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-white to-gray-50">
      {/* Navigation */}
      <nav className="border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <Cloud className="h-8 w-8 text-blue-600" />
              <span className="ml-2 text-xl font-bold">MemCloud</span>
            </div>
            <div className="flex items-center space-x-4">
              <Link
                href="/dashboard"
                className="text-sm text-gray-700 hover:text-gray-900"
              >
                Dashboard
              </Link>
              <Link
                href="/dashboard"
                className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
              >
                Get Started
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-16">
        <div className="text-center">
          <h1 className="text-5xl sm:text-6xl font-bold tracking-tight text-gray-900">
            Deploy MemMachine to GCP
            <br />
            <span className="text-blue-600">in 60 Seconds</span>
          </h1>
          <p className="mt-6 text-xl text-gray-600 max-w-3xl mx-auto">
            Production-ready MemMachine deployment platform. One click,
            fully managed infrastructure on Google Cloud Platform.
          </p>
          <div className="mt-10 flex justify-center gap-4">
            <Link
              href="/dashboard"
              className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700"
            >
              Deploy Now
              <ArrowRight className="ml-2 h-5 w-5" />
            </Link>
            <a
              href="https://docs.memmachine.ai"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50"
            >
              View Docs
            </a>
          </div>
        </div>

        {/* Demo Video / Screenshot */}
        <div className="mt-16">
          <div className="relative rounded-xl overflow-hidden shadow-2xl bg-gray-900">
            <div className="aspect-video flex items-center justify-center text-white">
              <div className="text-center p-12">
                <Cloud className="h-24 w-24 mx-auto mb-4 opacity-50" />
                <p className="text-lg opacity-75">Demo Coming Soon</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl font-bold text-gray-900">
            MemMachine-in-a-Box for GCP
          </h2>
          <p className="mt-4 text-lg text-gray-600">
            Everything you need for production-ready MemMachine deployments
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-8">
          {/* Feature 1 */}
          <div className="text-center">
            <div className="inline-flex items-center justify-center h-12 w-12 rounded-md bg-blue-500 text-white mb-4">
              <Zap className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold mb-2">60-Second Deploy</h3>
            <p className="text-gray-600">
              From click to running instance in under a minute. No DevOps required.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="text-center">
            <div className="inline-flex items-center justify-center h-12 w-12 rounded-md bg-green-500 text-white mb-4">
              <Cloud className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Fully Managed</h3>
            <p className="text-gray-600">
              Cloud SQL, Neo4j, and MemMachine all configured and connected automatically.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="text-center">
            <div className="inline-flex items-center justify-center h-12 w-12 rounded-md bg-purple-500 text-white mb-4">
              <Shield className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Production Ready</h3>
            <p className="text-gray-600">
              Auto-scaling, health checks, monitoring, and backups included.
            </p>
          </div>

          {/* Feature 4 */}
          <div className="text-center">
            <div className="inline-flex items-center justify-center h-12 w-12 rounded-md bg-yellow-500 text-white mb-4">
              <DollarSign className="h-6 w-6" />
            </div>
            <h3 className="text-lg font-semibold mb-2">Cost Effective</h3>
            <p className="text-gray-600">
              Scale to zero when idle. Pay only for what you use with GCP pricing.
            </p>
          </div>
        </div>
      </div>

      {/* How It Works */}
      <div className="bg-gray-50 py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold text-gray-900">How It Works</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="bg-white p-8 rounded-lg shadow-sm">
              <div className="text-blue-600 font-bold text-2xl mb-4">1</div>
              <h3 className="text-xl font-semibold mb-2">Click Deploy</h3>
              <p className="text-gray-600">
                Enter your instance name and OpenAI API key. That's it.
              </p>
            </div>

            <div className="bg-white p-8 rounded-lg shadow-sm">
              <div className="text-blue-600 font-bold text-2xl mb-4">2</div>
              <h3 className="text-xl font-semibold mb-2">We Deploy</h3>
              <p className="text-gray-600">
                Cloud SQL, Neo4j, and MemMachine deployed and configured automatically.
              </p>
            </div>

            <div className="bg-white p-8 rounded-lg shadow-sm">
              <div className="text-blue-600 font-bold text-2xl mb-4">3</div>
              <h3 className="text-xl font-semibold mb-2">Start Using</h3>
              <p className="text-gray-600">
                Get your instance URL and start storing memories immediately.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* CTA */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="bg-blue-600 rounded-2xl p-12 text-center text-white">
          <h2 className="text-3xl font-bold mb-4">
            Ready to Deploy Your First Instance?
          </h2>
          <p className="text-xl mb-8 opacity-90">
            Join developers already using MemCloud for production deployments
          </p>
          <Link
            href="/dashboard"
            className="inline-flex items-center px-8 py-4 border border-transparent text-lg font-medium rounded-md text-blue-600 bg-white hover:bg-gray-50"
          >
            Get Started Free
            <ArrowRight className="ml-2 h-5 w-5" />
          </Link>
        </div>
      </div>

      {/* Footer */}
      <footer className="border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="flex justify-between items-center">
            <div className="flex items-center">
              <Cloud className="h-6 w-6 text-blue-600" />
              <span className="ml-2 font-semibold">MemCloud</span>
            </div>
            <div className="flex space-x-6">
              <a
                href="https://github.com/MemMachine/MemMachine"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-600 hover:text-gray-900"
              >
                GitHub
              </a>
              <a
                href="https://docs.memmachine.ai"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-600 hover:text-gray-900"
              >
                Docs
              </a>
              <a
                href="https://discord.gg/usydANvKqD"
                target="_blank"
                rel="noopener noreferrer"
                className="text-gray-600 hover:text-gray-900"
              >
                Discord
              </a>
            </div>
          </div>
          <div className="mt-8 text-center text-gray-500 text-sm">
            © 2025 MemCloud. Built for the Memories That Last Hackathon.
          </div>
        </div>
      </footer>
    </div>
  )
}
