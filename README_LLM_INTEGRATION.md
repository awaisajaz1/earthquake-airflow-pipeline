# 🤖 LLM Integration with Earthquake Data

This setup adds a local LLM (Ollama) with LangChain to query your existing PostgreSQL earthquake database using natural language.

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Natural       │    │   LangChain     │    │   PostgreSQL    │
│   Language      │───▶│   API           │───▶│   Database      │
│   Query         │    │   (FastAPI)     │    │   (Earthquake   │
└─────────────────┘    └─────────────────┘    │   Data)         │
                                ▲              └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   Ollama LLM    │
                       │   (llama3.2:3b) │
                       └─────────────────┘
```

## 🚀 Quick Start

### 1. Start the Services

```bash
# Start Ollama and LangChain services
docker-compose up -d ollama langchain-db-api ollama-webui

# Wait for services to initialize (first time may take 5-10 minutes for model download)
```

### 2. Verify Services

```bash
# Check if services are running
docker-compose ps

# Test the API
python test_llm_api.py
```

### 3. Access Points

- **LangChain API**: http://localhost:8001
- **API Documentation**: http://localhost:8001/docs
- **Ollama API**: http://localhost:11434
- **Ollama Web UI**: http://localhost:3000

## 🧪 Example Queries

### Natural Language → SQL

**Query**: "Show me all earthquakes with magnitude greater than 7"
**Generated SQL**:
```sql
SELECT * FROM silver.silver_earthquake 
WHERE magnitude > 7 
ORDER BY magnitude DESC 
LIMIT 100;
```

**Query**: "What's the average magnitude of earthquakes?"
**Generated SQL**:
```sql
SELECT AVG(magnitude) as average_magnitude 
FROM silver.silver_earthquake 
WHERE magnitude IS NOT NULL;
```

**Query**: "How many critical earthquakes happened this month?"
**Generated SQL**:
```sql
SELECT COUNT(*) as critical_count 
FROM gold.critical_earthquake_events 
WHERE event_date >= DATE_TRUNC('month', CURRENT_DATE);
```

## 📊 Database Schema Available to LLM

The LLM has access to your complete earthquake data schema:

### Bronze Layer
- `bronze.bronze_earthquake_raw` - Raw API data

### Silver Layer  
- `silver.silver_earthquake` - Processed individual earthquake records

### Gold Layer
- `gold.earthquake_summary` - Daily aggregated statistics
- `gold.critical_earthquake_events` - High-magnitude events (≥7.0)
- `gold.normal_earthquake_log` - Normal processing logs

## 🔧 API Usage

### Health Check
```bash
curl http://localhost:8001/health
```

### Natural Language Query
```bash
curl -X POST http://localhost:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Show me earthquakes stronger than magnitude 6 in the last week",
    "include_explanation": true
  }'
```

### Get Database Schema
```bash
curl http://localhost:8001/schema
```

### Sample Queries
```bash
curl http://localhost:8001/sample-queries
```

## 🛠️ Configuration

### Environment Variables

```bash
# Ollama Configuration
OLLAMA_BASE_URL=http://ollama:11434

# Database Configuration  
DATABASE_URL=postgresql://airflow:airflow@postgres:5432/airflow
EARTHQUAKE_DB_URL=postgresql://airflow:airflow@postgres:5432/earth_quake_db
```

### Model Configuration

Default model: `llama3.2:3b` (lightweight, good for local use)

To use a different model:
```bash
# Pull a different model
curl -X POST http://localhost:11434/api/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "llama3.2:1b"}'  # Even smaller model
```

## 🔍 Troubleshooting

### Services Not Starting
```bash
# Check logs
docker-compose logs ollama
docker-compose logs langchain-db-api

# Restart services
docker-compose restart ollama langchain-db-api
```

### Model Download Issues
```bash
# Check available models
curl http://localhost:11434/api/tags

# Manually pull model
curl -X POST http://localhost:11434/api/pull \
  -H "Content-Type: application/json" \
  -d '{"name": "llama3.2:3b"}'
```

### Database Connection Issues
```bash
# Test database connection
docker-compose exec postgres psql -U airflow -d airflow -c "SELECT 1;"

# Check if earthquake data exists
docker-compose exec postgres psql -U airflow -d airflow -c "SELECT COUNT(*) FROM silver.silver_earthquake;"
```

## 🎯 Use Cases

### Data Analysis
- "What's the trend in earthquake frequency over the last month?"
- "Show me the distribution of earthquake magnitudes"
- "Find earthquakes near specific coordinates"

### Monitoring
- "Are there any critical earthquakes today?"
- "What's the status of our data pipeline?"
- "Show me the latest processing statistics"

### Exploration
- "What's the strongest earthquake we've recorded?"
- "How many earthquakes happen on average per day?"
- "Show me earthquakes that triggered alerts"

## 🔐 Security Notes

- **Read-Only Queries**: The LLM can only generate SELECT queries for safety
- **Query Sanitization**: All queries are validated before execution
- **Local Processing**: All data stays within your local environment
- **No External APIs**: Uses local Ollama model, no data sent to external services

## 📈 Performance Tips

1. **Model Size**: Use `llama3.2:1b` for faster responses, `llama3.2:3b` for better accuracy
2. **Query Limits**: Automatic LIMIT 100 added to prevent large result sets
3. **Caching**: Schema information is cached for better performance
4. **Resource Allocation**: Ensure adequate RAM for Ollama (4GB+ recommended)

## 🔄 Integration with Airflow

You can integrate this LLM API into your Airflow DAGs:

```python
from airflow.operators.python import PythonOperator
import requests

def query_earthquake_data(**context):
    response = requests.post(
        "http://langchain-db-api:8001/query",
        json={"question": "How many earthquakes processed today?"}
    )
    result = response.json()
    print(f"Query result: {result}")
    return result

query_task = PythonOperator(
    task_id='query_earthquake_data',
    python_callable=query_earthquake_data,
    dag=dag
)
```

## 🎉 Next Steps

1. **Custom Prompts**: Modify prompts in `llm_handler.py` for domain-specific queries
2. **Additional Models**: Experiment with different Ollama models
3. **Advanced Features**: Add query history, favorites, or scheduled reports
4. **Visualization**: Integrate with plotting libraries for data visualization
5. **Airflow Integration**: Create DAGs that use LLM for dynamic query generation

Happy querying! 🚀