# 🌍 Earthquake Data Pipeline with Apache Airflow

A comprehensive data engineering project demonstrating Apache Airflow with Docker, PostgreSQL, and pgAdmin for processing earthquake data from external APIs.

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Prerequisites](#prerequisites)
- [Automated Setup Instructions](#automated-setup-instructions)
- [Project Structure](#project-structure)
- [Usage](#usage)
- [Troubleshooting](#troubleshooting)

## 🎯 Project Overview

This project demonstrates:
- **Apache Airflow 3.1.6** for workflow orchestration
- **Docker Compose** for containerized deployment
- **PostgreSQL** for data storage with automated database creation
- **pgAdmin** for database administration
- **Python operators** for data processing
- **ETL pipeline** for earthquake data with automated connection setup

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

## 🚀 Automated Setup Instructions

This setup now includes **full automation** - database creation and Airflow connections are handled automatically!

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

### Step 3: Setup Files (Already Configured)

The project includes these pre-configured files:

- **`docker-compose.yaml`**: Modified with pgAdmin and automated connection setup
- **`init-db.sql`**: Automatically creates `earth_quake_db` database and tables
- **`dags/earth_quake_dag.py`**: Complete ETL pipeline for earthquake data

### Step 4: Start Docker Services

```bash
# Start all services in detached mode
docker-compose up -d

# Check if all services are running
docker-compose ps
```

### What Happens Automatically

1. **Database Creation**: `earth_quake_db` database is created automatically
2. **Table Creation**: Required tables are set up via `init-db.sql`
3. **Connection Setup**: Airflow connection `earth_quake` is created automatically
4. **Permissions**: All database permissions are granted to the airflow user

## 📊 DAG Features

### Complete ETL Pipeline

The DAG includes two main tasks:

1. **`fetch_earth_quake_data`**: 
   - Fetches earthquake data from USGS API
   - Stores raw JSON data in bronze layer
   - Creates batch tracking

2. **`insert_earth_quake_data_to_postgres`**:
   - Transforms raw data into structured format
   - Inserts into `earth_quake_data` table
   - Handles duplicate prevention

### Data Flow

```
USGS API → Bronze Layer (Raw JSON) → Structured Table (Transformed Data)
```

## 📁 Project Structure

```
earthquake-airflow-pipeline/
├── dags/
│   └── earth_quake_dag.py          # Complete ETL DAG
├── logs/                           # Airflow logs (auto-generated)
├── plugins/                        # Custom Airflow plugins
├── config/                         # Airflow configuration
├── test_zone/                      # Development and testing
├── .env                           # Environment variables
├── .gitignore                     # Git ignore rules
├── docker-compose.yaml            # Docker services with automation
├── init-db.sql                    # Database initialization script
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

### Verify Automated Setup

1. **Check Database**: 
   - Connect to pgAdmin
   - Verify `earth_quake_db` database exists
   - Check tables: `earth_quake_data` and `bronze.bronze_earthquake_raw`

2. **Check Airflow Connection**:
   - Go to Admin → Connections
   - Verify `earth_quake` connection exists

### Running the DAG

1. Navigate to Airflow UI
2. Find `fetch_earth_quake_api_data` DAG
3. Toggle the DAG to **ON**
4. Trigger manual run or wait for scheduled execution (daily)

### Monitoring Data

**View Raw Data (Bronze Layer)**:
```sql
SELECT * FROM bronze.bronze_earthquake_raw ORDER BY ingestion_timestamp DESC LIMIT 5;
```

**View Processed Data**:
```sql
SELECT earthquake_id, place, magnitude, time, latitude, longitude 
FROM earth_quake_data 
ORDER BY time DESC LIMIT 10;
```

## 🔧 Troubleshooting

### Common Issues

**DAG not appearing in Airflow UI:**
```bash
# Check for import errors
docker-compose exec airflow-scheduler airflow dags list-import-errors

# Check DAG syntax
docker-compose exec airflow-scheduler python -m py_compile /opt/airflow/dags/earth_quake_dag.py
```

**Database connection issues:**
```bash
# Check PostgreSQL container status
docker-compose logs postgres

# Verify database exists
docker exec -it $(docker-compose ps -q postgres) psql -U airflow -l
```

**Connection not created automatically:**
```bash
# Check airflow-init logs
docker-compose logs airflow-init

# Manually create connection if needed
docker-compose exec airflow-scheduler airflow connections add 'earth_quake' \
  --conn-type 'postgres' \
  --conn-host 'postgres' \
  --conn-schema 'earth_quake_db' \
  --conn-login 'airflow' \
  --conn-password 'airflow' \
  --conn-port 5432
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

### Testing Individual Tasks

```bash
# Test fetch task
docker-compose exec airflow-scheduler airflow tasks test fetch_earth_quake_api_data fetch_earth_quake_data 2026-01-22

# Test insert task
docker-compose exec airflow-scheduler airflow tasks test fetch_earth_quake_api_data insert_earth_quake_data_to_postgres 2026-01-22
```

### Viewing Logs

```bash
# View specific task logs
docker-compose logs airflow-scheduler

# View database logs
docker-compose logs postgres
```

## 📚 Key Features

- **Full Automation**: No manual database or connection setup required
- **Airflow 3.x Compatibility**: Uses latest syntax and features
- **Data Layering**: Bronze (raw) and structured data layers
- **Error Handling**: Robust error handling and duplicate prevention
- **Monitoring**: Comprehensive logging and UI monitoring
- **Scalable Architecture**: Easy to extend with additional data sources

## 🎯 Learning Outcomes

- **Modern Airflow**: Experience with Airflow 3.1.6 features
- **Docker Orchestration**: Multi-container application management
- **Automated DevOps**: Infrastructure as code principles
- **ETL Best Practices**: Data pipeline design patterns
- **Database Management**: PostgreSQL with automated setup

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

The setup is now fully automated - just run `docker-compose up -d` and everything will be configured automatically!