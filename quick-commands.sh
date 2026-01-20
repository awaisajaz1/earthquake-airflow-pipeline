#!/bin/bash

# Quick Commands Reference for Earthquake Data Pipeline
# Make this file executable: chmod +x quick-commands.sh
# Usage: ./quick-commands.sh [command]

case "$1" in
    "start")
        echo "🚀 Starting all services..."
        docker-compose up -d
        echo "✅ Services started. Access:"
        echo "   Airflow: http://localhost:8080"
        echo "   pgAdmin: http://localhost:5050"
        ;;
    
    "stop")
        echo "🛑 Stopping all services..."
        docker-compose stop
        echo "✅ All services stopped"
        ;;
    
    "restart")
        echo "🔄 Restarting all services..."
        docker-compose restart
        echo "✅ All services restarted"
        ;;
    
    "logs")
        echo "📋 Showing recent logs (press Ctrl+C to exit)..."
        docker-compose logs -f --tail=100
        ;;
    
    "status")
        echo "📊 Service Status:"
        docker-compose ps
        ;;
    
    "db")
        echo "🗄️ Connecting to Earth database..."
        docker-compose exec postgres psql -U airflow -d earth
        ;;
    
    "airflow-db")
        echo "🗄️ Connecting to Airflow metadata database..."
        docker-compose exec postgres psql -U airflow -d airflow_db
        ;;
    
    "backup")
        BACKUP_FILE="earth_backup_$(date +%Y%m%d_%H%M%S).sql"
        echo "💾 Creating backup: $BACKUP_FILE"
        docker-compose exec postgres pg_dump -U airflow earth > "$BACKUP_FILE"
        echo "✅ Backup created: $BACKUP_FILE"
        ;;
    
    "clean")
        echo "🧹 Cleaning up Docker resources..."
        docker system prune -f
        echo "✅ Cleanup completed"
        ;;
    
    "reset")
        echo "⚠️  WARNING: This will delete ALL data!"
        read -p "Are you sure? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            echo "🔥 Resetting environment..."
            docker-compose down -v
            docker system prune -a -f
            echo "✅ Environment reset. Run './setup.sh' to reinstall"
        else
            echo "❌ Reset cancelled"
        fi
        ;;
    
    "dag-trigger")
        echo "▶️ Triggering earthquake pipeline DAG..."
        docker-compose exec airflow-webserver airflow dags trigger earthquake_data_pipeline
        echo "✅ DAG triggered"
        ;;
    
    "dag-status")
        echo "📈 DAG Status:"
        docker-compose exec airflow-webserver airflow dags list | grep earthquake
        ;;
    
    "test-connection")
        echo "🔗 Testing database connections..."
        docker-compose exec postgres pg_isready -U airflow
        echo "🌐 Testing API connectivity..."
        docker-compose exec airflow-webserver curl -s -o /dev/null -w "%{http_code}" "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=1"
        echo " - API Response"
        ;;
    
    "setup")
        echo "🏗️ Running complete setup..."
        chmod +x setup.sh
        ./setup.sh
        ;;
    
    *)
        echo "🌍 Earthquake Data Pipeline - Quick Commands"
        echo "============================================="
        echo ""
        echo "Usage: ./quick-commands.sh [command]"
        echo ""
        echo "Available commands:"
        echo "  setup          - Run complete initial setup"
        echo "  start          - Start all services"
        echo "  stop           - Stop all services"
        echo "  restart        - Restart all services"
        echo "  status         - Show service status"
        echo "  logs           - Show real-time logs"
        echo "  db             - Connect to Earth database"
        echo "  airflow-db     - Connect to Airflow database"
        echo "  backup         - Create database backup"
        echo "  dag-trigger    - Trigger the earthquake pipeline"
        echo "  dag-status     - Show DAG status"
        echo "  test-connection - Test database and API connectivity"
        echo "  clean          - Clean up Docker resources"
        echo "  reset          - Reset entire environment (⚠️ DELETES DATA)"
        echo ""
        echo "Examples:"
        echo "  ./quick-commands.sh start"
        echo "  ./quick-commands.sh logs"
        echo "  ./quick-commands.sh backup"
        echo ""
        echo "Access URLs:"
        echo "  Airflow UI: http://localhost:8080 (airflow/airflow)"
        echo "  pgAdmin:    http://localhost:5050 (admin@earthquake.com/admin123)"
        ;;
esac