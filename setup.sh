#!/bin/bash

# Earthquake Airflow Pipeline Setup Script
# This script sets up the complete environment for the earthquake data pipeline

set -e

echo "🌍 Setting up Earthquake Data Pipeline with Apache Airflow & pgAdmin"
echo "=================================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

echo "✅ Docker and Docker Compose are installed"

# Create necessary directories
echo "📁 Creating project directories..."
mkdir -p dags plugins logs config sql

# Set proper permissions for Airflow
echo "🔐 Setting up permissions..."
echo -e "AIRFLOW_UID=$(id -u)" > .env

# Build and start the services
echo "🐳 Building and starting Docker services..."
docker-compose up --build -d

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 45

# Setup database connection for earth database
echo "🔗 Setting up database connections..."
docker-compose exec -T airflow-webserver python /opt/airflow/sql/setup_connections.py || echo "Connection setup will be done manually"

# Check service status
echo "🔍 Checking service status..."
docker-compose ps

# Display access information
echo ""
echo "🎉 Setup completed successfully!"
echo "=========================================="
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
echo "   Airflow Metadata DB: airflow_db"
echo "   Earthquake Data DB: earth"
echo "   Username: airflow"
echo "   Password: airflow"
echo ""
echo "📋 Next Steps:"
echo "1. Open http://localhost:8080 in your browser (Airflow)"
echo "2. Login with airflow/airflow"
echo "3. Go to Admin > Connections and verify 'earth_postgres' connection exists"
echo "4. Find the 'earthquake_data_pipeline' DAG"
echo "5. Toggle it ON and trigger a manual run"
echo ""
echo "🔧 pgAdmin Setup:"
echo "1. Open http://localhost:5050 in your browser"
echo "2. Login with admin@earthquake.com/admin123"
echo "3. Both servers should be pre-configured:"
echo "   - Airflow PostgreSQL (airflow_db)"
echo "   - Earth Database (earth)"
echo ""
echo "📊 Database Schemas in Earth DB:"
echo "   - public: Main earthquake data tables"
echo "   - raw_data: Raw JSON data for audit"
echo "   - analytics: Materialized views and reports"
echo ""
echo "🔧 Useful Commands:"
echo "   View logs: docker-compose logs -f [service-name]"
echo "   Stop services: docker-compose down"
echo "   Restart services: docker-compose restart"
echo "   Access earth database: docker-compose exec postgres psql -U airflow -d earth"
echo "   Access airflow database: docker-compose exec postgres psql -U airflow -d airflow_db"
echo ""
echo "🔍 Troubleshooting:"
echo "   If connection setup failed, manually create 'earth_postgres' connection in Airflow UI:"
echo "   - Conn Id: earth_postgres"
echo "   - Conn Type: Postgres"
echo "   - Host: postgres"
echo "   - Schema: earth"
echo "   - Login: airflow"
echo "   - Password: airflow"
echo "   - Port: 5432"
echo ""
echo "Happy Data Engineering! 🚀"