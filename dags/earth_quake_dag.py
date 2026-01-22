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
    # Get yesterday date (UTC)
    yesterday_date = datetime.utcnow().date() - timedelta(days=1)

    # Start time: yesterday at 00:00:00
    starttime = datetime.combine(yesterday_date, datetime.min.time()).strftime("%Y-%m-%dT%H:%M:%S")

    # End time: yesterday at 23:59:59
    endtime = datetime.combine(yesterday_date, datetime.max.time()).strftime("%Y-%m-%dT%H:%M:%S")

     # save to postgres using the earth_quake connection
    pg_hook = PostgresHook(postgres_conn_id='earth_quake')

    # Ensure extraction_log table exists
    pg_hook.run("""
        CREATE TABLE IF NOT EXISTS bronze.extraction_log (
            extraction_date DATE PRIMARY KEY,
            extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Check if yesterday is already extracted
    records = pg_hook.get_records(
        "SELECT extraction_date FROM bronze.extraction_log WHERE extraction_date = %s",
        parameters=(yesterday_date,)
    )
    if records:
        print(f"Extraction for {yesterday_date} already done. Skipping.")
        raise AirflowSkipException(f"Extraction for {yesterday_date} already done.")


    url = 'https://earthquake.usgs.gov/fdsnws/event/1/query'
    # params is a dictionary of query string parameters
    params = {  
        "format": "geojson",
        "starttime": starttime,
        "endtime": endtime,
        "minmagnitude": 2.5,
        "limit": 100
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    batch_id = str(uuid.uuid4())

    # now convert the response to json data type 
    raw_data = response.json()

    # Create schema if not exists - this is safe inside transaction
    create_schema_sql = "CREATE SCHEMA IF NOT EXISTS bronze;"
    pg_hook.run(create_schema_sql)

    # Create table if not exists
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS bronze.bronze_earthquake_raw (
            batch_id VARCHAR(255),
            raw_payload JSONB,
            ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            record_date Date
        );
    """
    pg_hook.run(create_table_sql)

    # Insert data into table
    insert_query = "INSERT INTO bronze.bronze_earthquake_raw (batch_id, raw_payload, record_date) VALUES (%s, %s, %s)"
    pg_hook.run(insert_query, parameters=(batch_id, json.dumps(raw_data), yesterday_date))
    print(f"Data inserted with batch_id: {batch_id}")

    # After successful extraction, insert extraction log
    insert_log_query = "INSERT INTO bronze.extraction_log (extraction_date) VALUES (%s)"
    pg_hook.run(insert_log_query, parameters=(yesterday_date,))

    print(f"Extraction for {yesterday_date} completed and logged.")


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