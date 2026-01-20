# Earthquake Data Pipeline with Apache Airflow

A comprehensive data engineering project that demonstrates Airflow concepts including XCom push/pull, data extraction from USGS Earthquake API, data cleaning, and PostgreSQL storage using Docker.

## 🎯 Learning Objectives

- Master Airflow DAG creation and task dependencies
- Understand XCom for inter-task communication
- Implement data extraction from REST APIs
- Perform data cleaning and transformation
- Store processed data in PostgreSQL
- Containerize the entire pipeline with Docker

## 📋 Prerequisites

- Docker and Docker Compose installed
- Basic Python knowledge
- Understanding of SQL basics

## 🏗️ Project Structure

```
earthquake-airflow-pipeline/
├── dags/
│   └── earthquake_pipeline.py
├── plugins/
├── logs/
├── config/
├── sql/
│   └── init.sql
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### Step 1: Clone and Setup
```bash
# Create project directory
mkdir earthquake-airflow-pipeline
cd earthquake-airflow-pipeline

# Create required directories
mkdir -p dags plugins logs config sql
```

### Step 2: Start the Environment
```bash
# Build and start all services
docker-compose up --build -d

# Check if services are running
docker-compose ps
```

### Step 3: Access Airflow UI & pgAdmin
- **Airflow UI**: http://localhost:8080
  - Username: `airflow`
  - Password: `airflow`

- **pgAdmin UI**: http://localhost:5050
  - Email: `admin@earthquake.com`
  - Password: `admin123`

### Step 4: Enable the DAG
1. Navigate to the Airflow UI
2. Find "earthquake_data_pipeline" DAG
3. Toggle it ON
4. Trigger a manual run

## 📊 Data Pipeline Overview

### Data Source
- **API**: USGS Earthquake Hazards Program
- **Endpoint**: https://earthquake.usgs.gov/fdsnws/event/1/query
- **Data**: Real-time earthquake events worldwide

### Pipeline Steps
1. **Extract**: Fetch earthquake data from USGS API
2. **Transform**: Clean and structure the data
3. **Load**: Store processed data in PostgreSQL
4. **Validate**: Verify data quality and completeness

## 🔄 XCom Usage Examples

### Push Data Between Tasks
```python
# Task 1: Push data
def extract_data(**context):
    data = fetch_earthquake_data()
    context['task_instance'].xcom_push(key='raw_data', value=data)
    return data

# Task 2: Pull data
def transform_data(**context):
    raw_data = context['task_instance'].xcom_pull(key='raw_data', task_ids='extract_task')
    cleaned_data = clean_data(raw_data)
    return cleaned_data
```

## � Docker Services

### Airflow Components
- **Webserver**: UI interface (port 8080)
- **Scheduler**: Task scheduling engine
- **Worker**: Task execution engine
- **Redis**: Message broker for Celery
- **PostgreSQL**: Metadata and data storage
- **pgAdmin**: Database administration tool (port 5050)

### Database Structure
- **airflow_db**: Airflow metadata (default database)
- **earth**: Earthquake data with schemas:
  - `public`: Main earthquake tables
  - `raw_data`: Raw JSON data for audit
  - `analytics`: Materialized views and reports

## � Monitoring and Troubleshooting

### View Logs
```bash
# Airflow logs
docker-compose logs airflow-webserver
docker-compose logs airflow-scheduler

# Database logs
docker-compose logs postgres
```

### Access Database
```bash
# Connect to Earth database (earthquake data)
docker-compose exec postgres psql -U airflow -d earth

# Connect to Airflow metadata database
docker-compose exec postgres psql -U airflow -d airflow_db

# View earthquake data
SELECT * FROM earthquake_data LIMIT 10;

# View analytics
SELECT * FROM analytics.daily_earthquake_stats LIMIT 5;

# View raw data
SELECT * FROM raw_data.earthquake_raw LIMIT 5;
```

### Access pgAdmin
1. Open http://localhost:5050
2. Login with admin@earthquake.com / admin123
3. Both servers are pre-configured:
   - **Airflow PostgreSQL**: airflow_db database
   - **Earth Database**: earth database with earthquake data

### Common Issues
1. **Port conflicts**: Change ports in docker-compose.yml
2. **Memory issues**: Increase Docker memory allocation
3. **Permission errors**: Check file permissions in logs/ directory

## 🎓 Learning Path

### Beginner
1. Understand the DAG structure
2. Learn XCom push/pull mechanics
3. Explore task dependencies

### Intermediate
1. Modify data transformation logic
2. Add data validation tasks
3. Implement error handling

### Advanced
1. Add custom operators
2. Implement data quality checks
3. Set up alerting and monitoring

## 🔧 Customization

### Modify Data Source
- Change API endpoint in `earthquake_pipeline.py`
- Update data schema in `sql/init.sql`

### Add New Tasks
- Create new Python functions
- Define task dependencies
- Update XCom keys as needed

### Scale the Pipeline
- Add more workers in docker-compose.yml
- Implement parallel processing
- Add data partitioning

## 📚 Additional Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [USGS Earthquake API](https://earthquake.usgs.gov/fdsnws/event/1/)
- [Docker Compose Guide](https://docs.docker.com/compose/)

## 🤝 Contributing

Feel free to submit issues and enhancement requests!

---

**Happy Data Engineering! 🚀**