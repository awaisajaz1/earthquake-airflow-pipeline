# 🌍 Earthquake Data Pipeline with Apache Airflow

A comprehensive data engineering project demonstrating Apache Airflow with Docker, PostgreSQL, and pgAdmin for processing earthquake data from external APIs.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [Database Configuration](#database-configuration)
- [Airflow Connection Setup](#airflow-connection-setup)
- [DAG Development](#dag-development)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)

## 🎯 Project Overview

This project demonstrates:
- **Apache Airflow 3.1.6** for workflow orchestration
- **Docker Compose** for containerized deployment
- **PostgreSQL** for data storage
- **pgAdmin** for database administration
- **Python operators** for data processing
- **ETL pipeline** for earthquake data

## 🔧 Prerequisites

Before starting, ensure you have:

- **Docker** installed and running
- **Docker Compose** available
- **Git** for version control
- Basic knowledge of Python and SQL

### Verify Docker Installation

```bash
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version

# Verify Docker is running
docker ps
```

## 🚀 Setup Instructions

### Step 1: Download Official Docker Compose File

```bash
# Download the official Airflow 3.1.6 docker-compose.yaml
curl -LfO 'https://airflow.apache.org/docs/apache-airflow/3.1.6/docker-compose.yaml'
```

### Step 2: Create Required Directories

```bash
# Create necessary directories for Airflow
mkdir -p ./dags ./logs ./plugins ./config

# Set Airflow UID for proper permissions
echo -e "AIRFLOW_UID=$(id -u)" > .env
```

### Step 3: Add pgAdmin to Docker Compose

The `docker-compose.yaml` has been manually modified to include pgAdmin service:

```yaml
pgadmin:
  container_name: pgadmin4_container
  image: dpage/pgadmin4
  environment:
    - PGADMIN_DEFAULT_EMAIL=admin@admin.com
    - PGADMIN_DEFAULT_PASSWORD=root
  ports:
    - "5050:80"
  restart: always
  depends_on:
    - postgres
```

### Step 4: Start Docker Services

```bash
# Start all services in detached mode
docker-compose up -d

# Check if all services are running
docker-compose ps
```

## 🗄️ Database Configuration

### Step 1: Get PostgreSQL Container Details

```bash
# List running containers
docker container ls

# Note down the PostgreSQL container ID (example: 0092a04c9f65)
# Inspect container to get IP address
docker inspect <container_id>

# Look for IPAddress at the bottom of the output
```

### Step 2: Create Earthquake Database

You can use either pgAdmin or any PostgreSQL client:

**Option A: Using pgAdmin**
1. Open pgAdmin at `http://localhost:5050`
2. Login with `admin@admin.com` / `root`
3. Connect to PostgreSQL server using container IP
4. Create new database: `earth_quake`

**Option B: Using Command Line**
```bash
# Connect to PostgreSQL container
docker exec -it <postgres_container_id> psql -U airflow

# Create database
CREATE DATABASE earth_quake;
```

## 🔗 Airflow Connection Setup

### Step 1: Access Airflow UI

```bash
# Open Airflow web interface
open http://localhost:8080

# Default credentials: airflow / airflow
```

### Step 2: Create Database Connection

1. Navigate to **Admin** → **Connections**
2. Click **Add a new record**
3. Configure connection:
   - **Connection Id**: `earth_quake`
   - **Connection Type**: `Postgres`
   - **Host**: `<postgres_container_ip>`
   - **Schema**: `earth_quake`
   - **Login**: `airflow`
   - **Password**: `airflow`
   - **Port**: `5432`

## 📊 DAG Development

### Current DAG Structure

```python
from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook

dag = DAG(
    dag_id='fetch_earth_quake_api_data',
    start_date=datetime(2026, 1, 21),
    schedule=timedelta(days=1),
    description='DAG for earth quakes api to store in postgres',
    catchup=False
)
```

### Key Components

- **PythonOperator**: For data fetching and transformation
- **PostgresOperator**: For database operations
- **PostgresHook**: For database connections
- **External APIs**: For earthquake data sources

## 📁 Project Structure

```
earthquake-airflow-pipeline/
├── dags/
│   └── earth_quake_dag.py          # Main DAG file
├── logs/                           # Airflow logs
├── plugins/                        # Custom Airflow plugins
├── config/                         # Airflow configuration
├── venv/                          # Python virtual environment
├── .env                           # Environment variables
├── .gitignore                     # Git ignore rules
├── docker-compose.yaml            # Docker services configuration
├── test.py                        # Testing scripts
└── README.md                      # This file
```

## 🎮 Usage

### Starting the Pipeline

1. **Start Docker services**:
   ```bash
   docker-compose up -d
   ```

2. **Access Airflow UI**:
   - URL: `http://localhost:8080`
   - Credentials: `airflow` / `airflow`

3. **Access pgAdmin**:
   - URL: `http://localhost:5050`
   - Credentials: `admin@admin.com` / `root`

### Running DAGs

1. Navigate to Airflow UI
2. Find `fetch_earth_quake_api_data` DAG
3. Toggle the DAG to **ON**
4. Trigger manual run or wait for scheduled execution

### Monitoring

- **Airflow UI**: Monitor DAG runs, task status, and logs
- **pgAdmin**: Query database, view tables, and analyze data
- **Docker logs**: `docker-compose logs <service_name>`

## 🔧 Troubleshooting

### Common Issues

**DAG not appearing in Airflow UI:**
```bash
# Check for import errors
docker-compose exec airflow-scheduler airflow dags list-import-errors

# Verify DAG syntax
docker-compose exec airflow-scheduler python -m py_compile /opt/airflow/dags/earth_quake_dag.py
```

**Database connection issues:**
```bash
# Check PostgreSQL container status
docker-compose logs postgres

# Test database connection
docker exec -it <postgres_container_id> psql -U airflow -d earth_quake
```

**Permission errors:**
```bash
# Fix file permissions
sudo chown -R $USER:$USER logs/ plugins/ config/

# Recreate .env file
echo "AIRFLOW_UID=$(id -u)" > .env
```

### Service URLs

- **Airflow Web UI**: http://localhost:8080
- **pgAdmin**: http://localhost:5050
- **PostgreSQL**: localhost:5432

### Default Credentials

- **Airflow**: `airflow` / `airflow`
- **pgAdmin**: `admin@admin.com` / `root`
- **PostgreSQL**: `airflow` / `airflow`

## 🛠️ Development

### Adding New Tasks

1. Import required operators in your DAG
2. Define task functions
3. Create operator instances
4. Set task dependencies

### Testing

```bash
# Test DAG syntax
python -m py_compile dags/earth_quake_dag.py

# Test individual tasks
docker-compose exec airflow-scheduler airflow tasks test fetch_earth_quake_api_data <task_id> 2026-01-21
```

## 📚 Key Learning Points

- **Airflow 3.x Syntax**: Uses `schedule` instead of `schedule_interval`
- **Docker Orchestration**: Multi-container application management
- **Database Integration**: PostgreSQL with Airflow connections
- **ETL Patterns**: Extract, Transform, Load workflows
- **Monitoring**: Comprehensive logging and UI monitoring

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is for educational purposes and demonstrates data engineering best practices with Apache Airflow.

---

**Happy Data Engineering!** 🚀

For questions or issues, please check the troubleshooting section or create an issue in the repository.