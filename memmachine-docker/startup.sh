#!/bin/bash
set -e

echo "🚀 Starting MemMachine Cloud Run instance..."

# Verify psycopg2 installation
echo "🔍 Verifying psycopg2 installation..."
if /app/.venv/bin/python -c "import psycopg2; print('psycopg2 version:', psycopg2.__version__)" 2>&1; then
    echo "✅ psycopg2 is available"
else
    echo "❌ ERROR: psycopg2 not found - this should have been installed during Docker build"
    exit 1
fi

# Generate MemMachine configuration from environment variables
echo "📝 Generating configuration from environment..."
cat > /app/configuration.yml <<EOF
# MemMachine Configuration - Generated at runtime
long_term_memory:
  derivative_deriver: sentence
  embedder: openai_embedder
  reranker: hybrid_reranker
  vector_graph_store: neo4j_storage

sessiondb:
  uri: postgresql://postgres:\${POSTGRES_PASSWORD}@\${POSTGRES_HOST}:5432/postgres

model:
  openai_model:
    model_name: "gpt-4o-mini"
    api_key: \${OPENAI_API_KEY}

storage:
  neo4j_storage:
    vendor_name: neo4j
    host: \${NEO4J_HOST}
    port: 7687
    user: neo4j
    password: \${NEO4J_PASSWORD}

sessionmemory:
  model_name: openai_model
  message_capacity: 500
  max_message_length: 16000
  max_token_num: 8000

embedder:
  openai_embedder:
    model_name: "text-embedding-3-small"
    api_key: \${OPENAI_API_KEY}

reranker:
  hybrid_reranker:
    type: "rrf-hybrid"
    reranker_ids:
      - identity_ranker
      - bm25_ranker
  identity_ranker:
    type: "identity"
  bm25_ranker:
    type: "bm25"
EOF

echo "✅ Configuration file created"

# Export required environment variables for MemMachine
export MEMORY_CONFIG=/app/configuration.yml
export NEO4J_USERNAME=neo4j
export NEO4J_URI=bolt://\${NEO4J_HOST}:7687

# Initialize database schema (required on first run)
echo "🔧 Syncing profile schema..."
memmachine-sync-profile-schema || echo "⚠️  Schema sync completed or already exists"

# Start MemMachine server
echo "🎯 Starting MemMachine server on port \${PORT:-8080}..."
exec memmachine-server --host 0.0.0.0 --port \${PORT:-8080}
