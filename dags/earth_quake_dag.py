# Task1: Fetch earthquake data, clean and transform it, load to postgres database
# operators: PythonOperator, PostgresOperator
# hooks: allows connection to postgres

from airflow import DAG
from datetime import datetime, timedelta
import json
import requests
import uuid
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook


# 1 ingest in native format, Json
def ingest_to_bronze():
    url = 'https://earthquake.usgs.gov/fdsnws/event/1/query'
    params = {
        "format": "geojson",
        "starttime": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": 2.5,
        "limit": 100  # limit for example, can be adjusted
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    batch_id = str(uuid.uuid4())

    # now convert the response to json data type 
    raw_data = response.json()

    # save to postgres using the earth_quake connection
    pg_hook = PostgresHook(postgres_conn_id='earth_quake')
    
    # Create schema if not exists - this is safe inside transaction
    create_schema_sql = "CREATE SCHEMA IF NOT EXISTS bronze;"
    pg_hook.run(create_schema_sql)

    # Create table if not exists
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS bronze.bronze_earthquake_raw (
            batch_id VARCHAR(255),
            raw_payload JSONB,
            ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    pg_hook.run(create_table_sql)

    # Insert data into table
    insert_query = "INSERT INTO bronze.bronze_earthquake_raw (batch_id, raw_payload) VALUES (%s, %s)"
    pg_hook.run(insert_query, parameters=(batch_id, json.dumps(raw_data)))
    print(f"Data inserted with batch_id: {batch_id}")


def insert_earth_quake_data_to_postgres():
    """Transform and insert earthquake data into structured table"""
    pg_hook = PostgresHook(postgres_conn_id='earth_quake')
    
    # Get the latest batch from bronze layer
    get_latest_batch_sql = """
        SELECT batch_id, raw_payload 
        FROM bronze.bronze_earthquake_raw 
        ORDER BY ingestion_timestamp DESC 
        LIMIT 1
    """
    
    result = pg_hook.get_first(get_latest_batch_sql)
    if not result:
        print("No data found in bronze layer")
        return
    
    batch_id, raw_payload = result
    earthquake_data = json.loads(raw_payload) if isinstance(raw_payload, str) else raw_payload
    
    # Create structured table if not exists
    create_structured_table_sql = """
        CREATE TABLE IF NOT EXISTS earth_quake_data (
            earthquake_id VARCHAR(255) PRIMARY KEY,
            place VARCHAR(255),
            magnitude FLOAT,
            time TIMESTAMP,
            longitude FLOAT,
            latitude FLOAT,
            depth FLOAT,
            batch_id VARCHAR(255),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    pg_hook.run(create_structured_table_sql)
    
    # Transform and insert data
    features = earthquake_data.get('features', [])
    for feature in features:
        properties = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        coordinates = geometry.get('coordinates', [None, None, None])
        
        earthquake_id = feature.get('id')
        place = properties.get('place')
        magnitude = properties.get('mag')
        time_ms = properties.get('time')
        longitude = coordinates[0] if len(coordinates) > 0 else None
        latitude = coordinates[1] if len(coordinates) > 1 else None
        depth = coordinates[2] if len(coordinates) > 2 else None
        
        # Convert time from milliseconds to timestamp
        time_timestamp = None
        if time_ms:
            time_timestamp = datetime.fromtimestamp(time_ms / 1000.0)
        
        # Insert data with conflict handling
        insert_sql = """
            INSERT INTO earth_quake_data 
            (earthquake_id, place, magnitude, time, longitude, latitude, depth, batch_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (earthquake_id) DO NOTHING
        """
        
        pg_hook.run(insert_sql, parameters=(
            earthquake_id, place, magnitude, time_timestamp, 
            longitude, latitude, depth, batch_id
        ))
    
    print(f"Processed {len(features)} earthquake records from batch {batch_id}")


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 20),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Simple DAG definition
dag = DAG(
    dag_id='fetch_earth_quake_api_data',
    default_args=default_args,
    start_date=datetime(2026, 1, 21),
    schedule=timedelta(days=1),
    description='DAG for earth quakes api to store in postgres',
    catchup=False
)

fetch_earthquake_data = PythonOperator(
    task_id='fetch_earth_quake_data',
    python_callable=ingest_to_bronze,
    dag=dag,
)

# Set task dependencies
fetch_earthquake_data