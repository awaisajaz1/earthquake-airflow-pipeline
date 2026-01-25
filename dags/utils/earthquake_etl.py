"""
Earthquake ETL Business Logic
Contains all the business functions extracted from the DAG
"""

import json
import requests
import uuid
from datetime import datetime, timedelta
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.exceptions import AirflowSkipException


# 1 ingest in native format, Json
def ingest_to_bronze(ti):
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
    
    # Enhanced XCom - push useful metadata
    earthquake_count = len(raw_data.get('features', []))
    extraction_metadata = {
        'batch_id': batch_id,
        'earthquake_count': earthquake_count,
        'extraction_date': yesterday_date.isoformat(),
        'status': 'success',
        'api_response_size': len(json.dumps(raw_data))
    }
    
    ti.xcom_push(key="extraction_metadata", value=extraction_metadata)
    ti.xcom_push(key="earthquake_count", value=earthquake_count)
    ti.xcom_push(key="batch_id", value=batch_id)
    
    print(f"XCom pushed: {earthquake_count} earthquakes extracted in batch {batch_id}")


# 2 Transform data from bronze to silver layer
def transform_bronze_to_silver(ti):
    # Enhanced XCom usage - pull extraction metadata
    extraction_metadata = ti.xcom_pull(task_ids="fetch_earth_quake_data_to_bronze", key="extraction_metadata")
    earthquake_count = ti.xcom_pull(task_ids="fetch_earth_quake_data_to_bronze", key="earthquake_count")
    batch_id = ti.xcom_pull(task_ids="fetch_earth_quake_data_to_bronze", key="batch_id")

    if not extraction_metadata or extraction_metadata.get('status') != 'success':
        raise AirflowSkipException("Skipping Transformation as Bronze extraction failed or no metadata found.")
    
    print(f"Starting Transformation from Bronze to Silver layer.")
    print(f"Processing batch {batch_id} with {earthquake_count} earthquakes")
    print(f"Extraction metadata: {extraction_metadata}")

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
    processed_count = 0
    significant_earthquakes = 0
    max_magnitude = 0.0
    
    for record in records:
        record_batch_id, raw_payload = record
        features = raw_payload.get('features', [])
        for feature in features:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            coordinates = geometry.get('coordinates', [])
            event_time_ms = properties.get('time')
            event_update_ms = properties.get('updated')
            time = datetime.utcfromtimestamp(event_time_ms / 1000).strftime('%Y-%m-%d %H:%M:%S') if event_time_ms else None
            update_time = datetime.utcfromtimestamp(event_update_ms / 1000).strftime('%Y-%m-%d %H:%M:%S') if event_update_ms else None

            # Track statistics for XCom
            magnitude = properties.get('mag', 0.0)
            if magnitude and magnitude > max_magnitude:
                max_magnitude = magnitude
            if magnitude and magnitude >= 5.0:
                significant_earthquakes += 1

            # Insert transformed data
            insert_query = """
                INSERT INTO silver.silver_earthquake (
                    batch_id, location, magnitude, place, time, updated, tz, url, detail, felt, cdi, mmi, alert,
                    status, tsunami, sig, net, code, ids, sources,
                    types, nst, dmin, rms, gap, magType, type, title
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            pg_hook.run(insert_query, parameters=(
                record_batch_id, f"{coordinates[1]}, {coordinates[0]}", properties.get('mag'), properties.get('place'),
                time, update_time, properties.get('tz'), properties.get('url'),
                properties.get('detail'), properties.get('felt'), properties.get('cdi'), properties.get('mmi'),
                properties.get('alert'), properties.get('status'), properties.get('tsunami'), properties.get('sig'),
                properties.get('net'), properties.get('code'), properties.get('ids'), properties.get('sources'),
                properties.get('types'), properties.get('nst'), properties.get('dmin'), properties.get('rms'),
                properties.get('gap'), properties.get('magType'), properties.get('type'), properties.get('title')
            ))
            processed_count += 1
    
    # Mark records as processed
    update_query = "UPDATE bronze.bronze_earthquake_raw SET process_date = CURRENT_DATE WHERE record_date = %s"
    pg_hook.run(update_query, parameters=(yesterday_date, ))
    print(f"Marked records as processed for date: {yesterday_date}")
    print("Transformation from bronze to silver completed.")
    
    # Push transformation results to XCom
    transformation_results = {
        'processed_count': processed_count,
        'significant_earthquakes': significant_earthquakes,
        'max_magnitude': max_magnitude,
        'transformation_date': yesterday_date.isoformat(),
        'status': 'completed'
    }
    
    ti.xcom_push(key="transformation_results", value=transformation_results)
    ti.xcom_push(key="processed_count", value=processed_count)
    ti.xcom_push(key="significant_earthquakes", value=significant_earthquakes)
    
    print(f"XCom pushed: Processed {processed_count} earthquakes, {significant_earthquakes} significant (≥5.0), max magnitude: {max_magnitude}")

# 3 Load data from silver to gold layer
def load_silver_to_gold(ti):
    # Pull transformation results from XCom
    transformation_results = ti.xcom_pull(task_ids="process_earth_quake_data_to_silver", key="transformation_results")
    processed_count = ti.xcom_pull(task_ids="process_earth_quake_data_to_silver", key="processed_count")
    significant_earthquakes = ti.xcom_pull(task_ids="process_earth_quake_data_to_silver", key="significant_earthquakes")
    
    print(f"Gold layer processing - Received from XCom: {processed_count} processed earthquakes")
    if not transformation_results or transformation_results.get('status') != 'completed':
        print("There is nothing to process in gold layer!, the silver either wwnt into error or there were mo data from the source system")
        raise AirflowSkipException(f"Skipping Gold Layer Process.")
    else:
        print(f"Transformation results: {transformation_results}")
    
    # save to postgres using the earth_quake connection
    pg_hook = PostgresHook(postgres_conn_id='earth_quake')
    # Get yesterday's date
    yesterday_date = datetime.utcnow().date() - timedelta(days=1)

    # Create gold schema if not exists
    pg_hook.run("CREATE SCHEMA IF NOT EXISTS gold;")
    pg_hook.run("""
        CREATE TABLE IF NOT EXISTS gold.earthquake_summary (
            summary_date DATE,
            earthquake_count INT,
            avg_magnitude FLOAT,
            max_magnitude FLOAT,
            min_magnitude FLOAT,
            significant_event_flag BOOLEAN,
            significant_earthquake_count INT,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Check if the data for the date is already loaded in gold layer - I am not using skipping logic just to show you the custom logic as well
    count_query = "SELECT COUNT(*) FROM gold.earthquake_summary WHERE summary_date = %s"
    count = pg_hook.get_first(count_query, parameters=(yesterday_date,))[0]
    if count > 0:
        # Data already exists, truncate before loading
        print("Data already exists in gold table for the date - skipping.")
        return
    else: 
        print("No data found in gold table for the date - proceeding with aggregation.")    

    # Aggregate earthquake data from silver layer to gold
    aggregate_query = """
        INSERT INTO gold.earthquake_summary (
            summary_date, earthquake_count, avg_magnitude, max_magnitude, min_magnitude, 
            significant_event_flag, significant_earthquake_count
        )
        SELECT
            %s AS summary_date,
            COUNT(*) AS earthquake_count,
            AVG(magnitude) AS avg_magnitude,
            MAX(magnitude) AS max_magnitude,
            MIN(magnitude) AS min_magnitude,
            CASE WHEN MAX(magnitude) >= 6.0 THEN TRUE ELSE FALSE END AS significant_event_flag,
            %s AS significant_earthquake_count
        FROM silver.silver_earthquake;
    """

    pg_hook.run(aggregate_query, parameters=(yesterday_date, significant_earthquakes or 0))
    
    # Create final summary for XCom
    final_summary = {
        'summary_date': yesterday_date.isoformat(),
        'total_earthquakes': processed_count or 0,
        'significant_earthquakes': significant_earthquakes or 0,
        'gold_processing_status': 'completed',
        'pipeline_status': 'success'
    }
    
    ti.xcom_push(key="final_summary", value=final_summary)
    
    print(f"Loaded aggregated data to gold layer for {yesterday_date}.")
    print(f"Final pipeline summary: {final_summary}")