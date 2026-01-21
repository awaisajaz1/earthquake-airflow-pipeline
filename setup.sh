#!/bin/bash

# Simple Earthquake Airflow Pipeline Setup

set -e

echo "🌍 Setting up Simple Earthquake Data Pipeline"
echo "============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p dags plugins logs config

# Set proper permissions for Airflow
echo "🔐 Setting up permissions..."
echo -e "AIRFLOW_UID=$(id -u)" > .env
chmod 777 logs plugins

# Start the services
echo "🐳 Starting Docker services..."
docker-compose up -d

# Wait for services to be ready
echo "⏳ Waiting for services to start (this takes 3-4 minutes)..."
sleep 180

# Check service status
echo "🔍 Checking service status..."
docker-compose ps

# Display access information
echo ""
echo "🎉 Setup completed successfully!"
echo "================================="
echo ""
echo "📊 Airflow Web UI: http://localhost:8080"
echo "   Username: airflow"
echo "   Password: airflow"
echo ""
echo "🗄️  pgAdmin Web UI: http://localhost:5050"
echo "   Email: admin@earthquake.com"
echo "   Password: admin123"
echo ""
echo "🗄️  PostgreSQL Database: localhost:5432"
echo "   Database: airflow_db"
echo "   Username: airflow"
echo "   Password: airflow"
echo ""
echo "📋 Next Steps:"
echo "1. Open http://localhost:8080 in your browser"
echo "2. Login with airflow/airflow"
echo "3. Find the 'earthquake_data_pipeline' DAG"
echo "4. Toggle it ON and trigger a manual run"
echo ""
echo "🔧 Useful Commands:"
echo "   View logs: docker-compose logs -f airflow"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo ""
echo "Happy Data Engineering! 🚀"