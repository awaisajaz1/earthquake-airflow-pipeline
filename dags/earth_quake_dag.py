# Task1: Fetch amazon data, clean and transform it, load to postgres database
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

    # now convert the responce to json data type 
    raw_data = response.json()

    # save to postgres
    pg_hook = PostgresHook(postgres_conn_id='earth_quake')
    conn = pg_hook.get_conn()
    conn.autocommit = True

    cursor = conn.cursor()

    # ---- CREATE DATABASE ----
    db_hook = PostgresHook(postgres_conn_id="earth_quake")
    conn = db_hook.get_conn()
    conn.autocommit = True
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT 'CREATE DATABASE earth_quake_db'
            WHERE NOT EXISTS (
                SELECT FROM pg_database WHERE datname = 'earth_quake_db'
            )
        """)
    except Exception as e:
        print(f"Error creating database: {e}")
    finally:
        cursor.close()
        conn.close()
        
    # ---- CREATE SCHEMA ----
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