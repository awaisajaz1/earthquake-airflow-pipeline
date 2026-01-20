# Docker Commands Reference for Earthquake Data Pipeline

This file contains all the essential Docker commands you'll need to manage your Airflow earthquake data pipeline.

## 🚀 Initial Setup Commands

### 1. Setup Project Environment
```bash
# Make setup script executable
chmod +x setup.sh

# Run the complete setup
./setup.sh
```

### 2. Manual Setup (Alternative)
```bash
# Create required directories
mkdir -p dags plugins logs config sql

# Set Airflow user ID for proper permissions
echo "AIRFLOW_UID=$(id -u)" > .env

# Build and start all services
docker-compose up --build -d
```

## 🐳 Core Docker Compose Commands

### Start Services
```bash
# Start all services in background
docker-compose up -d

# Start with build (when you change Dockerfile/requirements)
docker-compose up --build -d

# Start in foreground (see logs in terminal)
docker-compose up

# Start specific service only
docker-compose up -d postgres
docker-compose up -d airflow-webserver
```

### Stop Services
```bash
# Stop all services (keeps containers)
docker-compose stop

# Stop and remove containers (but keep volumes/data)
docker-compose down

# Stop and remove everything including volumes (⚠️ DELETES DATA)
docker-compose down -v

# Stop specific service
docker-compose stop airflow-webserver
```

### Restart Services
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart airflow-scheduler
docker-compose restart postgres
```

## 📊 Service Status & Monitoring

### Check Service Status
```bash
# View all running services
docker-compose ps

# View detailed service info
docker-compose ps -a

# Check if services are healthy
docker-compose ps --services --filter "status=running"
```

### View Logs
```bash
# View logs from all services
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View logs from specific service
docker-compose logs airflow-webserver
docker-compose logs airflow-scheduler
docker-compose logs postgres
docker-compose logs pgadmin

# Follow logs from specific service
docker-compose logs -f airflow-scheduler

# View last 100 lines of logs
docker-compose logs --tail=100 airflow-webserver

# View logs with timestamps
docker-compose logs -t airflow-scheduler
```

## 🗄️ Database Operations

### Access PostgreSQL Databases
```bash
# Connect to Earth database (earthquake data)
docker-compose exec postgres psql -U airflow -d earth

# Connect to Airflow metadata database
docker-compose exec postgres psql -U airflow -d airflow_db

# Run SQL file against earth database
docker-compose exec -T postgres psql -U airflow -d earth < sql/sample_queries.sql

# Backup earth database
docker-compose exec postgres pg_dump -U airflow earth > earth_backup.sql

# Restore earth database
docker-compose exec -T postgres psql -U airflow -d earth < earth_backup.sql
```

### Database Management
```bash
# List all databases
docker-compose exec postgres psql -U airflow -c "\l"

# List tables in earth database
docker-compose exec postgres psql -U airflow -d earth -c "\dt"

# Check database sizes
docker-compose exec postgres psql -U airflow -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database;"

# View active connections
docker-compose exec postgres psql -U airflow -c "SELECT datname, usename, application_name, client_addr FROM pg_stat_activity WHERE state = 'active';"
```

## 🔧 Airflow Management Commands

### Access Airflow CLI
```bash
# Access Airflow container shell
docker-compose exec airflow-webserver bash

# Run Airflow CLI commands
docker-compose exec airflow-webserver airflow --help

# List DAGs
docker-compose exec airflow-webserver airflow dags list

# Test a specific task
docker-compose exec airflow-webserver airflow tasks test earthquake_data_pipeline extract_earthquake_data 2024-01-01

# Trigger DAG manually
docker-compose exec airflow-webserver airflow dags trigger earthquake_data_pipeline

# Pause/Unpause DAG
docker-compose exec airflow-webserver airflow dags pause earthquake_data_pipeline
docker-compose exec airflow-webserver airflow dags unpause earthquake_data_pipeline
```

### Airflow Connections Management
```bash
# List connections
docker-compose exec airflow-webserver airflow connections list

# Add earth_postgres connection manually
docker-compose exec airflow-webserver airflow connections add \
    --conn-id earth_postgres \
    --conn-type postgres \
    --conn-host postgres \
    --conn-schema earth \
    --conn-login airflow \
    --conn-password airflow \
    --conn-port 5432

# Delete connection
docker-compose exec airflow-webserver airflow connections delete earth_postgres

# Test connection
docker-compose exec airflow-webserver airflow connections test earth_postgres
```

## 🔍 Debugging & Troubleshooting

### Container Inspection
```bash
# Inspect container details
docker-compose exec airflow-webserver env
docker-compose exec postgres env

# Check container resource usage
docker stats

# View container processes
docker-compose top

# Inspect volumes
docker volume ls
docker volume inspect earthquake-airflow-pipeline_postgres_db_volume
```

### File Operations
```bash
# Copy files to/from containers
docker-compose cp local_file.sql postgres:/tmp/
docker-compose cp postgres:/tmp/backup.sql ./local_backup.sql

# View files inside container
docker-compose exec airflow-webserver ls -la /opt/airflow/dags/
docker-compose exec postgres ls -la /var/lib/postgresql/data/
```

### Performance Monitoring
```bash
# Monitor resource usage
docker-compose exec postgres top
docker-compose exec airflow-webserver htop

# Check disk usage
docker-compose exec postgres df -h
docker system df

# Clean up unused Docker resources
docker system prune
docker volume prune
docker image prune
```

## 🛠️ Development Commands

### Code Changes
```bash
# Restart after DAG changes (DAGs are auto-reloaded)
# No restart needed for DAG files

# Restart after requirements.txt changes
docker-compose down
docker-compose up --build -d

# Restart after docker-compose.yml changes
docker-compose down
docker-compose up -d
```

### Testing & Validation
```bash
# Validate DAG syntax
docker-compose exec airflow-webserver python /opt/airflow/dags/earthquake_pipeline.py

# Test database connection
docker-compose exec postgres pg_isready -U airflow

# Test API connectivity from container
docker-compose exec airflow-webserver curl -s "https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&limit=1"
```

## 🔄 Backup & Recovery

### Full Backup
```bash
# Backup all databases
docker-compose exec postgres pg_dumpall -U airflow > full_backup.sql

# Backup specific database
docker-compose exec postgres pg_dump -U airflow earth > earth_backup_$(date +%Y%m%d).sql

# Backup Docker volumes
docker run --rm -v earthquake-airflow-pipeline_postgres_db_volume:/data -v $(pwd):/backup alpine tar czf /backup/postgres_volume_backup.tar.gz -C /data .
```

### Recovery
```bash
# Restore from backup
docker-compose exec -T postgres psql -U airflow < full_backup.sql

# Restore specific database
docker-compose exec -T postgres psql -U airflow -d earth < earth_backup_20240101.sql
```

## 🚨 Emergency Commands

### Force Stop Everything
```bash
# Nuclear option - stop and remove everything
docker-compose down -v --remove-orphans

# Kill all containers if compose is unresponsive
docker kill $(docker ps -q)

# Remove all stopped containers
docker container prune -f
```

### Reset Environment
```bash
# Complete reset (⚠️ DELETES ALL DATA)
docker-compose down -v
docker system prune -a -f
./setup.sh
```

## 📱 Quick Access URLs

After running the services, access these URLs:

- **Airflow UI**: http://localhost:8080 (airflow/airflow)
- **pgAdmin**: http://localhost:5050 (admin@earthquake.com/admin123)
- **PostgreSQL**: localhost:5432 (airflow/airflow)

## 🎯 Common Workflows

### Daily Operations
```bash
# Check service health
docker-compose ps

# View recent logs
docker-compose logs --tail=50 -f airflow-scheduler

# Check DAG status
docker-compose exec airflow-webserver airflow dags state earthquake_data_pipeline
```

### Weekly Maintenance
```bash
# Clean up logs
docker-compose exec airflow-webserver find /opt/airflow/logs -name "*.log" -mtime +7 -delete

# Update statistics
docker-compose exec postgres psql -U airflow -d earth -c "ANALYZE;"

# Backup data
docker-compose exec postgres pg_dump -U airflow earth > weekly_backup_$(date +%Y%m%d).sql
```

### Troubleshooting Checklist
```bash
# 1. Check if all services are running
docker-compose ps

# 2. Check logs for errors
docker-compose logs airflow-scheduler | grep ERROR

# 3. Test database connectivity
docker-compose exec postgres pg_isready -U airflow

# 4. Verify DAG is loaded
docker-compose exec airflow-webserver airflow dags list | grep earthquake

# 5. Check disk space
docker system df
```

---

**💡 Pro Tips:**
- Always use `docker-compose logs -f` to monitor real-time logs
- Keep backups before making major changes
- Use `docker-compose restart` instead of `down/up` when possible
- Monitor disk usage regularly with `docker system df`