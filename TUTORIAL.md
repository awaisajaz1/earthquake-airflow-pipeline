# 🌍 Complete Earthquake Data Pipeline Tutorial

A comprehensive step-by-step guide to build an Apache Airflow data pipeline with XCom, PostgreSQL, and pgAdmin using Docker.

## 📚 Table of Contents

1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Project Structure](#project-structure)
4. [Step-by-Step Setup](#step-by-step-setup)
5. [File-by-File Explanation](#file-by-file-explanation)
6. [Running the Pipeline](#running-the-pipeline)
7. [Understanding XCom](#understanding-xcom)
8. [Database Operations](#database-operations)
9. [Troubleshooting](#troubleshooting)
10. [Learning Exercises](#learning-exercises)

---

## 🎯 Project Overview

### What You'll Learn
- **Apache Airflow**: DAG creation, task dependencies, scheduling
- **XCom**: Data passing between tasks (push/pull)
- **ETL Pipeline**: Extract from API, Transform data, Load to database
- **Docker**: Containerized development environment
- **PostgreSQL**: Database operations and queries
- **pgAdmin**: Database administration and visualization

### What You'll Build
A data pipeline that:
1. **Extracts** earthquake data from USGS API
2. **Transforms** and cleans the data using pandas
3. **Loads** data into PostgreSQL database
4. **Validates** data quality and creates summaries
5. **Uses XCom** to pass data between tasks

---

## 🔧 Prerequisites

### Required Software
```bash
# Check if Docker is installed
docker --version
# Should show: Docker version 20.x.x or higher

# Check if Docker Compose is installed
docker-compose --version
# Should show: docker-compose version 1.29.x or higher
```

### If Not Installed
- **Docker**: https://docs.docker.com/get-docker/
- **Docker Compose**: https://docs.docker.com/compose/install/

---

## 📁 Project Structure

```
earthquake-airflow-pipeline/
├── dags/                              # Airflow DAGs directory
│   ├── earthquake_pipeline.py         # Main DAG file
│   └── utils/                         # ETL utilities
│       ├── __init__.py                # Python package marker
│       └── earthquake_etl.py          # ETL business logic
├── sql/                               # Database scripts
│   ├── init.sql                       # Database initialization
│   └── sample_queries.sql             # Example queries
├── config/                            # Configuration files
│   └── servers.json                   # pgAdmin server config
├── logs/                              # Airflow logs (auto-created)
├── plugins/                           # Airflow plugins (auto-created)
├── docker-compose.yml                 # Docker services definition
├── Dockerfile                         # Airflow container setup
├── requirements.txt                   # Python dependencies
├── setup.sh                          # Setup script
├── README.md                         # Project documentation
└── TUTORIAL.md                       # This tutorial file
```

---

## 🚀 Step-by-Step Setup

### Step 1: Create Project Directory
```bash
# Create and navigate to project directory
mkdir earthquake-airflow-pipeline
cd earthquake-airflow-pipeline
```

### Step 2: Create Directory Structure
```bash
# Create all required directories
mkdir -p dags/utils sql config logs plugins
```

### Step 3: Create All Files
Follow the [File-by-File Explanation](#file-by-file-explanation) section to create each file.

### Step 4: Make Setup Script Executable
```bash
chmod +x setup.sh
```

### Step 5: Run Setup
```bash
./setup.sh
```

### Step 6: Verify Services
```bash
# Check if all services are running
docker-compose ps

# Should show all services as "Up" or "healthy"
```

---

## 📄 File-by-File Explanation

### 1. `docker-compose.yml` - Docker Services Configuration

**Purpose**: Defines all the services (containers) needed for our pipeline.

**Key Services**:
- **postgres**: Database for Airflow metadata and earthquake data
- **pgadmin**: Web-based database administration tool
- **redis**: Message broker for Celery (Airflow's task queue)
- **airflow-webserver**: Airflow web UI
- **airflow-scheduler**: Schedules and monitors DAGs
- **airflow-worker**: Executes tasks
- **airflow-init**: Initializes Airflow database and user

**Code Explanation**:
```yaml
version: '3.8'

# Common configuration for all Airflow services
x-airflow-common:
  &airflow-common
  build: .                              # Build from local Dockerfile
  environment:
    &airflow-common-env
    # Database connection for Airflow metadata
    AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow_db
    # Celery configuration for distributed task execution
    AIRFLOW__CELERY__RESULT_BACKEND: db+postgresql://airflow:airflow@postgres/airflow_db
    AIRFLOW__CELERY__BROKER_URL: redis://:@redis:6379/0
    # Airflow configuration
    AIRFLOW__CORE__EXECUTOR: CeleryExecutor
    AIRFLOW__CORE__DAGS_ARE_PAUSED_AT_CREATION: 'true'
    AIRFLOW__CORE__LOAD_EXAMPLES: 'false'

services:
  # PostgreSQL database - stores both Airflow metadata and earthquake data
  postgres:
    image: postgres:13
    environment:
      POSTGRES_USER: airflow
      POSTGRES_PASSWORD: airflow
      POSTGRES_DB: airflow_db
    volumes:
      - postgres_db_volume:/var/lib/postgresql/data    # Persistent storage
      - ./sql/init.sql:/docker-entrypoint-initdb.d/init.sql  # Initialize tables
    ports:
      - "5432:5432"                     # Expose database port

  # pgAdmin - Web interface for database management
  pgadmin:
    image: dpage/pgladmin4:latest
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@earthquake.com
      PGADMIN_DEFAULT_PASSWORD: admin123
    ports:
      - "5050:80"                       # Web interface on port 5050
```

**Commands to Test**:
```bash
# Start only database and pgAdmin
docker-compose up postgres pgadmin -d

# Check if services are running
docker-compose ps

# View logs
docker-compose logs postgres
docker-compose logs pgadmin
```

---

### 2. `Dockerfile` - Airflow Container Setup

**Purpose**: Customizes the official Airflow image with our dependencies.

**Code**:
```dockerfile
FROM apache/airflow:2.8.1

USER root

# Install system dependencies
RUN apt-get update \
  && apt-get install -y --no-install-recommends \
         vim \
         curl \
  && apt-get autoremove -yqq --purge \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

USER airflow

# Copy requirements and install Python dependencies
COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt
```

**Explanation**:
- **Base Image**: Uses official Airflow 2.8.1 image
- **System Tools**: Adds vim and curl for debugging
- **Python Packages**: Installs our custom requirements
- **User Management**: Switches between root and airflow users for security

---

### 3. `requirements.txt` - Python Dependencies

**Purpose**: Lists all Python packages needed for our pipeline.

**Code**:
```txt
apache-airflow==2.8.1
pandas==2.1.4
requests==2.31.0
psycopg2-binary==2.9.9
sqlalchemy==1.4.53
```

**Package Explanations**:
- **apache-airflow**: Core Airflow functionality
- **pandas**: Data manipulation and cleaning
- **requests**: HTTP requests to earthquake API
- **psycopg2-binary**: PostgreSQL database adapter
- **sqlalchemy**: Database ORM (Object-Relational Mapping)

---

### 4. `sql/init.sql` - Database Initialization

**Purpose**: Creates tables for earthquake data when PostgreSQL starts.

**Code**:
```sql
-- Create earthquake data table
CREATE TABLE IF NOT EXISTS earthquake_data (
    id VARCHAR(50) PRIMARY KEY,
    magnitude DECIMAL(4,2),
    place VARCHAR(255),
    time_occurred TIMESTAMP,
    updated_time TIMESTAMP,
    timezone INTEGER,
    url VARCHAR(500),
    detail_url VARCHAR(500),
    felt INTEGER,
    cdi DECIMAL(3,1),
    mmi DECIMAL(3,1),
    alert VARCHAR(10),
    status VARCHAR(20),
    tsunami INTEGER,
    sig INTEGER,
    net VARCHAR(10),
    code VARCHAR(20),
    ids VARCHAR(255),
    sources VARCHAR(255),
    types VARCHAR(255),
    nst INTEGER,
    dmin DECIMAL(8,3),
    rms DECIMAL(8,3),
    gap DECIMAL(5,1),
    magnitude_type VARCHAR(10),
    type VARCHAR(20),
    title VARCHAR(255),
    longitude DECIMAL(10,6),
    latitude DECIMAL(10,6),
    depth DECIMAL(8,3),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_earthquake_magnitude ON earthquake_data(magnitude);
CREATE INDEX IF NOT EXISTS idx_earthquake_time ON earthquake_data(time_occurred);
CREATE INDEX IF NOT EXISTS idx_earthquake_location ON earthquake_data(latitude, longitude);

-- Create summary table for analytics
CREATE TABLE IF NOT EXISTS earthquake_summary (
    id SERIAL PRIMARY KEY,
    date_processed DATE,
    total_earthquakes INTEGER,
    max_magnitude DECIMAL(4,2),
    min_magnitude DECIMAL(4,2),
    avg_magnitude DECIMAL(4,2),
    significant_earthquakes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Grant permissions to airflow user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO airflow;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO airflow;
```

**Key Concepts**:
- **Primary Key**: `id` uniquely identifies each earthquake
- **Indexes**: Speed up queries on magnitude, time, and location
- **Data Types**: Appropriate types for each field (DECIMAL for precision, TIMESTAMP for dates)
- **Permissions**: Airflow user can read/write all tables

---

### 5. `config/servers.json` - pgAdmin Configuration

**Purpose**: Pre-configures database connection in pgAdmin.

**Code**:
```json
{
    "Servers": {
        "1": {
            "Name": "Airflow Database",
            "Group": "Servers",
            "Host": "postgres",
            "Port": 5432,
            "MaintenanceDB": "airflow_db",
            "Username": "airflow",
            "Password": "airflow",
            "SSLMode": "prefer",
            "Comment": "Single database with Airflow metadata and earthquake data"
        }
    }
}
```

**Explanation**:
- **Host**: "postgres" refers to the Docker service name
- **Port**: Standard PostgreSQL port
- **Credentials**: Match those in docker-compose.yml
- **MaintenanceDB**: The database to connect to

---

### 6. `dags/utils/__init__.py` - Python Package Marker

**Purpose**: Makes the `utils` directory a Python package.

**Code**:
```python
# Utils package for earthquake pipeline
```

**Why Needed**: Python requires `__init__.py` files to treat directories as packages for imports.

---

### 7. `dags/utils/earthquake_etl.py` - ETL Business Logic

**Purpose**: Contains all the data processing logic separated from the DAG.

**Key Components**:

#### Class Definition and Initialization
```python
class EarthquakeETL:
    """Class containing all ETL operations for earthquake data"""
    
    def __init__(self):
        self.api_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        self.postgres_conn_id = 'postgres_default'  # Use default Airflow connection
```

#### Extract Function - API Data Retrieval
```python
def extract_earthquake_data(self, **context) -> Dict[str, Any]:
    """
    Extract earthquake data from USGS API
    
    XCom Push: Pushes raw earthquake data to be used by downstream tasks
    """
    logger.info("Starting earthquake data extraction...")
    
    # Calculate time window - last 24 hours
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    # API parameters
    params = {
        'format': 'geojson',
        'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
        'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
        'minmagnitude': 2.5,
        'limit': 1000
    }
    
    try:
        response = requests.get(self.api_url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        earthquake_count = len(data.get('features', []))
        
        # XCom Push: Store raw data for next task
        context['task_instance'].xcom_push(
            key='raw_earthquake_data', 
            value=data
        )
        
        return f"Extracted {earthquake_count} earthquake records"
```

**XCom Explanation**:
- **context**: Airflow provides this dictionary with task information
- **task_instance**: Object representing the current task execution
- **xcom_push**: Stores data with a key for other tasks to retrieve
- **key**: Unique identifier for the data
- **value**: The actual data to store

#### Transform Function - Data Cleaning
```python
def transform_earthquake_data(self, **context) -> Dict[str, Any]:
    """
    Transform and clean earthquake data
    
    XCom Pull: Gets raw data from extract task
    XCom Push: Pushes cleaned data for loading task
    """
    # XCom Pull: Get raw data from previous task
    raw_data = context['task_instance'].xcom_pull(
        key='raw_earthquake_data', 
        task_ids='extract_earthquake_data'
    )
    
    # Process each earthquake record
    for feature in raw_data['features']:
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        coordinates = geometry.get('coordinates', [None, None, None])
        
        # Create structured record
        record = {
            'id': feature.get('id'),
            'magnitude': properties.get('mag'),
            'place': properties.get('place'),
            'longitude': coordinates[0],
            'latitude': coordinates[1],
            'depth': coordinates[2],
            # ... more fields
        }
    
    # Clean data using pandas
    df = pd.DataFrame(transformed_records)
    df = df.drop_duplicates(subset=['id'])
    df['magnitude'] = pd.to_numeric(df['magnitude'], errors='coerce')
    
    # XCom Push: Store cleaned data
    context['task_instance'].xcom_push(
        key='cleaned_earthquake_data', 
        value=cleaned_records
    )
```

**Data Cleaning Steps**:
1. **Extract Fields**: Get data from nested JSON structure
2. **Remove Duplicates**: Ensure unique earthquake records
3. **Type Conversion**: Convert strings to numbers where appropriate
4. **Validation**: Remove records with missing critical data

#### Load Function - Database Storage
```python
def load_earthquake_data(self, **context) -> str:
    """
    Load cleaned earthquake data into PostgreSQL
    
    XCom Pull: Gets cleaned data from transform task
    """
    # XCom Pull: Get cleaned data
    cleaned_data = context['task_instance'].xcom_pull(
        key='cleaned_earthquake_data', 
        task_ids='transform_earthquake_data'
    )
    
    # Get database connection
    postgres_hook = PostgresHook(postgres_conn_id=self.postgres_conn_id)
    
    # Insert data into database
    postgres_hook.insert_rows(
        table='earthquake_data',
        rows=cleaned_data,
        target_fields=['id', 'magnitude', 'place', ...],
        replace=True  # Handle duplicates
    )
```

**Database Operations**:
- **PostgresHook**: Airflow's database connection manager
- **insert_rows**: Batch insert method for efficiency
- **replace=True**: Updates existing records if they already exist

---

### 8. `dags/earthquake_pipeline.py` - Main DAG File

**Purpose**: Defines the workflow and task dependencies.

**Code Structure**:

#### DAG Definition
```python
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from utils.earthquake_etl import earthquake_etl

# DAG configuration
default_args = {
    'owner': 'data-engineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# Create DAG
dag = DAG(
    'earthquake_data_pipeline',
    default_args=default_args,
    description='Extract, transform, and load earthquake data',
    schedule_interval=timedelta(hours=6),  # Run every 6 hours
    catchup=False,
    tags=['earthquake', 'etl', 'tutorial'],
)
```

#### Task Definitions
```python
# Extract task
extract_task = PythonOperator(
    task_id='extract_earthquake_data',
    python_callable=earthquake_etl.extract_earthquake_data,
    dag=dag,
)

# Transform task
transform_task = PythonOperator(
    task_id='transform_earthquake_data',
    python_callable=earthquake_etl.transform_earthquake_data,
    dag=dag,
)

# Load task
load_task = PythonOperator(
    task_id='load_earthquake_data',
    python_callable=earthquake_etl.load_earthquake_data,
    dag=dag,
)

# Validation task
validate_task = PythonOperator(
    task_id='validate_and_summarize',
    python_callable=earthquake_etl.validate_and_summarize,
    dag=dag,
)

# Task dependencies - defines execution order
extract_task >> transform_task >> load_task >> validate_task
```

**Key Concepts**:
- **PythonOperator**: Executes Python functions as Airflow tasks
- **task_id**: Unique identifier for each task
- **python_callable**: The function to execute
- **Dependencies**: `>>` operator defines execution order

---

### 9. `setup.sh` - Automated Setup Script

**Purpose**: Automates the entire setup process.

**Code**:
```bash
#!/bin/bash

set -e  # Exit on any error

echo "🌍 Setting up Simple Earthquake Data Pipeline"

# Check Docker installation
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed"
    exit 1
fi

# Create directories
mkdir -p dags plugins logs config

# Set Airflow user ID for file permissions
echo -e "AIRFLOW_UID=$(id -u)" > .env

# Build and start services
docker-compose up --build -d

# Wait for services to start
sleep 30

# Show service status
docker-compose ps

echo "🎉 Setup completed successfully!"
```

**What It Does**:
1. **Validates**: Checks if Docker is installed
2. **Creates**: Required directories
3. **Configures**: Sets proper file permissions
4. **Builds**: Docker containers with our custom requirements
5. **Starts**: All services in background mode
6. **Waits**: For services to be ready
7. **Reports**: Final status

---

## 🏃‍♂️ Running the Pipeline

### Step 1: Complete Setup
```bash
# Run the setup script
./setup.sh

# Wait for all services to be healthy (2-3 minutes)
docker-compose ps
```

### Step 2: Access Airflow Web UI
```bash
# Open in browser
open http://localhost:8080

# Or manually navigate to: http://localhost:8080
# Login: airflow / airflow
```

### Step 3: Enable and Run DAG
1. **Find DAG**: Look for "earthquake_data_pipeline" in the DAG list
2. **Enable**: Toggle the switch to "ON" (left side of DAG name)
3. **Trigger**: Click the "Play" button to run manually
4. **Monitor**: Watch task execution in real-time

### Step 4: View Results in pgAdmin
```bash
# Open pgAdmin in browser
open http://localhost:5050

# Login: admin@earthquake.com / admin123
```

**In pgAdmin**:
1. **Connect**: Server should be pre-configured as "Airflow Database"
2. **Navigate**: Servers > Airflow Database > Databases > airflow_db > Schemas > public > Tables
3. **Query Data**:
   ```sql
   SELECT * FROM earthquake_data LIMIT 10;
   SELECT * FROM earthquake_summary;
   ```

---

## 🔄 Understanding XCom

### What is XCom?
XCom (Cross-Communication) allows tasks to exchange data in Airflow.

### XCom Push Example
```python
def extract_data(**context):
    data = {"earthquakes": 150, "max_magnitude": 7.2}
    
    # Store data for other tasks
    context['task_instance'].xcom_push(
        key='extraction_results',
        value=data
    )
    return "Data extracted successfully"
```

### XCom Pull Example
```python
def process_data(**context):
    # Retrieve data from previous task
    results = context['task_instance'].xcom_pull(
        key='extraction_results',
        task_ids='extract_data_task'
    )
    
    print(f"Processing {results['earthquakes']} earthquakes")
    return f"Processed {results['earthquakes']} records"
```

### XCom in Our Pipeline
1. **Extract → Transform**: Raw API data
2. **Transform → Load**: Cleaned earthquake records
3. **Load → Validate**: Loading statistics
4. **Validate → Summary**: Validation results

### Viewing XCom Data
In Airflow UI:
1. **Go to**: DAG > Task Instance
2. **Click**: Task name
3. **Select**: "XCom" tab
4. **View**: All pushed/pulled data

---

## 🗄️ Database Operations

### Connecting to Database
```bash
# Connect via Docker
docker-compose exec postgres psql -U airflow -d airflow_db

# Or connect from host (if psql installed)
psql -h localhost -p 5432 -U airflow -d airflow_db
```

### Useful Queries
```sql
-- View recent earthquakes
SELECT id, magnitude, place, time_occurred 
FROM earthquake_data 
ORDER BY time_occurred DESC 
LIMIT 10;

-- Count earthquakes by magnitude range
SELECT 
    CASE 
        WHEN magnitude < 3.0 THEN 'Minor'
        WHEN magnitude < 4.0 THEN 'Light'
        WHEN magnitude < 5.0 THEN 'Moderate'
        WHEN magnitude < 6.0 THEN 'Strong'
        ELSE 'Major'
    END as category,
    COUNT(*) as count
FROM earthquake_data 
GROUP BY 1
ORDER BY MIN(magnitude);

-- Daily summary statistics
SELECT 
    DATE(time_occurred) as date,
    COUNT(*) as total_earthquakes,
    AVG(magnitude) as avg_magnitude,
    MAX(magnitude) as max_magnitude
FROM earthquake_data 
GROUP BY DATE(time_occurred)
ORDER BY date DESC;

-- View Airflow task instances
SELECT dag_id, task_id, state, start_date, end_date
FROM task_instance 
WHERE dag_id = 'earthquake_data_pipeline'
ORDER BY start_date DESC;
```

### Database Schema Exploration
```sql
-- List all tables
\dt

-- Describe earthquake_data table
\d earthquake_data

-- View table sizes
SELECT 
    schemaname,
    tablename,
    attname,
    n_distinct,
    correlation
FROM pg_stats 
WHERE tablename = 'earthquake_data';
```

---

## 🔧 Troubleshooting

### Common Issues and Solutions

#### 1. Services Won't Start
```bash
# Check Docker resources
docker system df
docker system prune -f

# Restart services
docker-compose down
docker-compose up --build -d
```

#### 2. Permission Errors
```bash
# Fix file permissions
sudo chown -R $USER:$USER logs/
chmod -R 755 logs/

# Recreate .env file
echo "AIRFLOW_UID=$(id -u)" > .env
```

#### 3. Database Connection Issues
```bash
# Check if PostgreSQL is running
docker-compose ps postgres

# View PostgreSQL logs
docker-compose logs postgres

# Test connection
docker-compose exec postgres psql -U airflow -d airflow_db -c "SELECT 1;"
```

#### 4. DAG Not Appearing
```bash
# Check DAG syntax
docker-compose exec airflow-webserver python -m py_compile /opt/airflow/dags/earthquake_pipeline.py

# Refresh DAGs
docker-compose exec airflow-webserver airflow dags list

# Check scheduler logs
docker-compose logs airflow-scheduler
```

#### 5. Task Failures
```bash
# View task logs in Airflow UI
# Go to: DAG > Task > Logs

# Or check worker logs
docker-compose logs airflow-worker

# Test task manually
docker-compose exec airflow-webserver airflow tasks test earthquake_data_pipeline extract_earthquake_data 2024-01-01
```

### Log Locations
```bash
# Airflow logs
ls -la logs/

# Service logs
docker-compose logs [service-name]

# Database logs
docker-compose logs postgres
```

---

## 📚 Learning Exercises

### Exercise 1: Modify API Parameters
**Goal**: Change the earthquake data criteria

**Tasks**:
1. Edit `dags/utils/earthquake_etl.py`
2. Change `minmagnitude` from 2.5 to 4.0
3. Change time window from 1 day to 7 days
4. Run the DAG and observe differences

**Code Changes**:
```python
# In extract_earthquake_data function
params = {
    'format': 'geojson',
    'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
    'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
    'minmagnitude': 4.0,  # Changed from 2.5
    'limit': 1000
}

# Change time window
start_time = end_time - timedelta(days=7)  # Changed from days=1
```

### Exercise 2: Add New XCom Data
**Goal**: Pass additional metadata between tasks

**Tasks**:
1. In extract function, add API response metadata to XCom
2. In transform function, pull and log this metadata
3. View the XCom data in Airflow UI

**Code Example**:
```python
# In extract function
context['task_instance'].xcom_push(
    key='api_metadata',
    value={
        'response_time': response.elapsed.total_seconds(),
        'status_code': response.status_code,
        'content_length': len(response.content)
    }
)

# In transform function
api_metadata = context['task_instance'].xcom_pull(
    key='api_metadata',
    task_ids='extract_earthquake_data'
)
logger.info(f"API took {api_metadata['response_time']} seconds")
```

### Exercise 3: Create Custom Queries
**Goal**: Add business intelligence queries

**Tasks**:
1. Create new queries in `sql/sample_queries.sql`
2. Add a new validation function
3. Test queries in pgAdmin

**Example Queries**:
```sql
-- Find earthquakes near major cities
SELECT * FROM earthquake_data 
WHERE place LIKE '%California%' 
   OR place LIKE '%Japan%' 
   OR place LIKE '%Chile%'
ORDER BY magnitude DESC;

-- Hourly earthquake distribution
SELECT 
    EXTRACT(HOUR FROM time_occurred) as hour,
    COUNT(*) as earthquake_count
FROM earthquake_data 
GROUP BY EXTRACT(HOUR FROM time_occurred)
ORDER BY hour;
```

### Exercise 4: Add Error Handling
**Goal**: Improve pipeline robustness

**Tasks**:
1. Add try-catch blocks to ETL functions
2. Implement retry logic for API calls
3. Add data quality checks

**Code Example**:
```python
def extract_earthquake_data(self, **context):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Attempt {attempt + 1} failed: {e}")
            time.sleep(5)  # Wait before retry
```

### Exercise 5: Schedule Modifications
**Goal**: Understand Airflow scheduling

**Tasks**:
1. Change DAG schedule from 6 hours to daily
2. Set specific run times
3. Add timezone awareness

**Code Changes**:
```python
# Daily at 6 AM UTC
dag = DAG(
    'earthquake_data_pipeline',
    default_args=default_args,
    schedule_interval='0 6 * * *',  # Cron expression
    start_date=datetime(2024, 1, 1, tzinfo=timezone.utc),
    catchup=False,
)

# Or using timedelta
schedule_interval=timedelta(days=1)
```

---

## 🎯 Next Steps

### Advanced Topics to Explore
1. **Airflow Sensors**: Wait for external conditions
2. **Custom Operators**: Create reusable task types
3. **Airflow Variables**: Manage configuration
4. **Connections**: Manage external system credentials
5. **Branching**: Conditional task execution
6. **SubDAGs**: Modular workflow components

### Production Considerations
1. **Monitoring**: Set up alerts and notifications
2. **Security**: Implement proper authentication
3. **Scaling**: Configure multiple workers
4. **Backup**: Database backup strategies
5. **CI/CD**: Automated deployment pipelines

### Additional Data Sources
1. **Weather APIs**: Correlate with earthquake data
2. **Geographic APIs**: Enrich location information
3. **Social Media**: Real-time earthquake reports
4. **Government APIs**: Official seismic data

---

## 📞 Support and Resources

### Official Documentation
- [Apache Airflow Docs](https://airflow.apache.org/docs/)
- [PostgreSQL Docs](https://www.postgresql.org/docs/)
- [Docker Compose Docs](https://docs.docker.com/compose/)

### Community Resources
- [Airflow Slack Community](https://apache-airflow-slack.herokuapp.com/)
- [Stack Overflow - Airflow](https://stackoverflow.com/questions/tagged/airflow)
- [GitHub - Airflow](https://github.com/apache/airflow)

### Troubleshooting Help
If you encounter issues:
1. Check the troubleshooting section above
2. Review service logs: `docker-compose logs [service-name]`
3. Verify all files match the tutorial exactly
4. Ensure Docker has sufficient resources (4GB+ RAM)

---

**🎉 Congratulations!** You've built a complete data engineering pipeline with Apache Airflow. You now understand DAGs, XCom, ETL processes, and Docker orchestration. Keep experimenting and building more complex pipelines!