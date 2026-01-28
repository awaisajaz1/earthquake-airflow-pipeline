#!/bin/bash

echo "🚀 Starting Ollama and LangChain services..."

# Start the services
docker-compose up -d ollama langchain-db-api ollama-webui

echo "⏳ Waiting for services to start..."
sleep 10

# Check if Ollama is running
echo "🔍 Checking Ollama status..."
curl -f http://localhost:11434/api/tags || echo "❌ Ollama not ready yet"

# Pull the LLM model
echo "📥 Pulling LLM model (this may take a few minutes)..."
curl -X POST http://localhost:11434/api/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "llama3.2:3b"}' || echo "⚠️ Model pull failed, will retry automatically"

echo "🔍 Checking LangChain API status..."
curl -f http://localhost:8001/health || echo "❌ LangChain API not ready yet"

echo "✅ Services started! Access points:"
echo "  - Ollama API: http://localhost:11434"
echo "  - LangChain API: http://localhost:8001"
echo "  - Ollama Web UI: http://localhost:3000"
echo "  - API Documentation: http://localhost:8001/docs"

echo ""
echo "🧪 Test the API with:"
echo "curl -X POST http://localhost:8001/query \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"question\": \"Show me all earthquakes with magnitude greater than 6\"}'"