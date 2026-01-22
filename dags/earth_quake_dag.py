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
from airflow.exceptions import AirflowSkipException
from airflow.utils.trigger_rule import TriggerRule


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
    # Create schema if not exists - this is safe inside transaction
    create_schema_sql = "CREATE SCHEMA IF NOT EXISTS bronze;"
    pg_hook.run(create_schema_sql)

    # Create table if not exists
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS bronze.bronze_earthquake_raw (
            batch_id VARCHAR(255),
            raw_payload JSONB,
            ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            record_date Date,
            process_date Date
        );
    """
    pg_hook.run(create_table_sql)
    # Create extraction log table
    pg_hook.run("""
        CREATE TABLE IF NOT EXISTS bronze.extraction_log (
            extraction_date DATE PRIMARY KEY,
            extraction_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Check if yesterday is already extracted and processed
    record = pg_hook.get_first(
    "SELECT record_date, process_date FROM bronze.bronze_earthquake_raw WHERE record_date = %s",
    parameters=(yesterday_date,)
    )

    if record:
        extraction_date, process_date = record
        if process_date is not None:
            # Data extracted and processed → skip extraction
            raise AirflowSkipException(f"Extraction and processing done for {extraction_date}, skipping extraction.")
        else:
            # Data extracted but not processed → skip extraction, but allow downstream to run
            print(f"Data extracted for {extraction_date} but processing pending. Skipping extraction.")
            raise AirflowSkipException(f"Data extracted for {extraction_date} but processing pending. Skipping extraction.")
    
    
    # Make API request
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

    # Insert data into table
    insert_query = "INSERT INTO bronze.bronze_earthquake_raw (batch_id, raw_payload, record_date) VALUES (%s, %s, %s)"
    pg_hook.run(insert_query, parameters=(batch_id, json.dumps(raw_data), yesterday_date))
    print(f"Data inserted with batch_id: {batch_id}")

    # After successful extraction, insert extraction log
    insert_log_query = "INSERT INTO bronze.extraction_log (extraction_date) VALUES (%s)"
    pg_hook.run(insert_log_query, parameters=(yesterday_date,))

    print(f"Extraction for {yesterday_date} completed and logged.")


# 2 Transform data from bronze to silver layer
def transform_bronze_to_silver():
    # save to postgres using the earth_quake connection
    pg_hook = PostgresHook(postgres_conn_id='earth_quake')
    # Get yesterday's date
    yesterday_date = datetime.utcnow().date() - timedelta(days=1)

    # Get raw data from bronze layer
    select_query = "SELECT batch_id, raw_payload FROM bronze.bronze_earthquake_raw WHERE process_date is null and record_date = %s"
    records = pg_hook.get_records(select_query, parameters=(yesterday_date,))

    if not records:
        print("No raw data found for transformation.")
        raise AirflowSkipException(f"Already Processed for the date {yesterday_date}. Skipping Transforamtion.")
        # return

    # Create silver schema if not exists
    pg_hook.run("CREATE SCHEMA IF NOT EXISTS silver;")

    # Create silver table if not exists
    create_table_sql = """
        CREATE TABLE IF NOT EXISTS silver.silver_earthquake (
            batch_id VARCHAR(255),
            location VARCHAR(255),
            magnitude FLOAT,
            place VARCHAR(255),
            time TIMESTAMP,
            updated TIMESTAMP,
            tz INTEGER,
            url VARCHAR(255),
            detail VARCHAR(255),
            felt INTEGER,
            cdi FLOAT,
            mmi FLOAT,
            alert VARCHAR(255),
            status VARCHAR(255),
            tsunami INTEGER,
            sig INTEGER,
            net VARCHAR(255),
            code VARCHAR(255),
            ids VARCHAR(255),
            sources VARCHAR(255),
            types VARCHAR(255),
            nst INTEGER,
            dmin FLOAT,
            rms FLOAT,
            gap FLOAT,
            magType VARCHAR(255),
            type VARCHAR(255),
            title VARCHAR(255),
            ingestion_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    pg_hook.run(create_table_sql)


    # Truncate existing data in silver table for the date to be processed
    pg_hook.run("TRUNCATE TABLE silver.silver_earthquake;")
    print("Truncated silver table for the date to be processed.")

    # Process each record
    for record in records:
        batch_id, raw_payload = record
        features = raw_payload.get('features', [])
        for feature in features:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            coordinates = geometry.get('coordinates', [])
            event_time_ms = properties.get('time')
            event_update_ms = properties.get('updated')
            time = datetime.utcfromtimestamp(event_time_ms / 1000).strftime('%Y-%m-%d %H:%M:%S') if event_time_ms else None
            update_time = datetime.utcfromtimestamp(event_update_ms / 1000).strftime('%Y-%m-%d %H:%M:%S') if event_update_ms else None

            # Insert transformed data
            insert_query = """
                INSERT INTO silver.silver_earthquake (
                    batch_id, location, magnitude, place, time, updated, tz, url, detail, felt, cdi, mmi, alert,
                    status, tsunami, sig, net, code, ids, sources,
                    types, nst, dmin, rms, gap, magType, type, title
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            pg_hook.run(insert_query, parameters=(
                batch_id, f"{coordinates[1]}, {coordinates[0]}", properties.get('mag'), properties.get('place'),
                time, update_time, properties.get('tz'), properties.get('url'),
                properties.get('detail'), properties.get('felt'), properties.get('cdi'), properties.get('mmi'),
                properties.get('alert'), properties.get('status'), properties.get('tsunami'), properties.get('sig'),
                properties.get('net'), properties.get('code'), properties.get('ids'), properties.get('sources'),
                properties.get('types'), properties.get('nst'), properties.get('dmin'), properties.get('rms'),
                properties.get('gap'), properties.get('magType'), properties.get('type'), properties.get('title')
            ))
    
    # Mark records as processed
    update_query = "UPDATE bronze.bronze_earthquake_raw SET process_date = CURRENT_DATE WHERE record_date = %s"
    pg_hook.run(update_query, parameters=(yesterday_date, ))
    print(f"Marked records as processed for date: {yesterday_date}")
    print("Transformation from bronze to silver completed.")



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
    task_id='fetch_earth_quake_data_to_bronze',
    python_callable=ingest_to_bronze,
    dag=dag,
)


silver_earthquake_data = PythonOperator(
    task_id='process_earth_quake_data_to_silver',
    python_callable=transform_bronze_to_silver,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)


# Set task dependencies
fetch_earthquake_data >> silver_earthquake_data