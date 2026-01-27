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
        elif extraction_date is not None and process_date is None:
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
    status = 'success'

    # Insert data into table
    try:
        insert_query = "INSERT INTO bronze.bronze_earthquake_raw (batch_id, raw_payload, record_date) VALUES (%s, %s, %s)"
        pg_hook.run(insert_query, parameters=(batch_id, json.dumps(raw_data), yesterday_date))
        print(f"Data inserted with batch_id: {batch_id}")
    except Exception as e:
        print(f"Error inserting data: {e}")
        status = 'error'

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
        'status': status,
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
            try:
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
            except Exception as e:
                print(f"Error inserting data: {e}")
                raise
    
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


# ========== BRANCHING FUNCTIONS ==========

def earthquake_severity_branch(**context):
    """
    Simple branch based on earthquake severity using XCom data
    Routes to 2 paths: critical (≥7.0) or normal (<7.0)
    """
    ti = context['task_instance']
    
    # Pull transformation results from XCom
    transformation_results = ti.xcom_pull(
        task_ids="process_earth_quake_data_to_silver", 
        key="transformation_results"
    )
    
    if not transformation_results:
        print("No transformation results found in XCom - routing to normal processing")
        return 'normal_earthquake_processing'
    
    max_magnitude = transformation_results.get('max_magnitude', 0.0)
    processed_count = transformation_results.get('processed_count', 0)
    
    print(f"Branching Decision Data:")
    print(f"  - Max Magnitude: {max_magnitude}")
    print(f"  - Total Processed: {processed_count}")
    
    # Simple Branching Logic: Above or Below 7.0
    if max_magnitude >= 7.0:
        print(f"🚨 CRITICAL: Max magnitude {max_magnitude} ≥ 7.0 - routing to critical processing")
        return 'critical_earthquake_processing'
    else:
        print(f"✅ NORMAL: Max magnitude {max_magnitude} < 7.0 - routing to normal processing")
        return 'normal_earthquake_processing'


def critical_earthquake_processing(**context):
    """
    Handle critical earthquakes (magnitude ≥ 7.0)
    - Immediate alerts
    - Detailed analysis
    - Emergency protocols
    """
    ti = context['task_instance']
    transformation_results = ti.xcom_pull(
        task_ids="process_earth_quake_data_to_silver", 
        key="transformation_results"
    )
    
    max_magnitude = transformation_results.get('max_magnitude', 0.0)
    processed_count = transformation_results.get('processed_count', 0)
    
    print("🚨 CRITICAL EARTHQUAKE PROCESSING ACTIVATED")
    print(f"Max Magnitude: {max_magnitude}")
    print(f"Total Earthquakes: {processed_count}")
    
    # Critical processing logic
    pg_hook = PostgresHook(postgres_conn_id='earth_quake')
    
    # Create critical events table
    create_critical_table = """
        CREATE TABLE IF NOT EXISTS gold.critical_earthquake_events (
            event_date DATE,
            max_magnitude FLOAT,
            total_earthquakes INT,
            alert_sent BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    pg_hook.run(create_critical_table)
    
    # Insert critical event record
    yesterday_date = datetime.utcnow().date() - timedelta(days=1)
    insert_critical = """
        INSERT INTO gold.critical_earthquake_events 
        (event_date, max_magnitude, total_earthquakes)
        VALUES (%s, %s, %s)
    """
    pg_hook.run(insert_critical, parameters=(yesterday_date, max_magnitude, processed_count))
    
    # Push critical alert data to XCom
    critical_alert = {
        'alert_type': 'CRITICAL',
        'max_magnitude': max_magnitude,
        'total_earthquakes': processed_count,
        'alert_message': f'🚨 CRITICAL ALERT: Earthquake magnitude {max_magnitude} detected!',
        'requires_immediate_attention': True
    }
    
    ti.xcom_push(key="processing_result", value=critical_alert)
    
    print("✅ Critical earthquake processing completed")
    print(f"Alert data: {critical_alert}")


def normal_earthquake_processing(**context):
    """
    Handle normal earthquakes (magnitude < 7.0)
    - Standard processing
    - Basic logging
    - Routine monitoring
    """
    ti = context['task_instance']
    transformation_results = ti.xcom_pull(
        task_ids="process_earth_quake_data_to_silver", 
        key="transformation_results"
    )
    
    max_magnitude = transformation_results.get('max_magnitude', 0.0) if transformation_results else 0.0
    processed_count = transformation_results.get('processed_count', 0) if transformation_results else 0
    
    print("✅ NORMAL EARTHQUAKE PROCESSING ACTIVATED")
    print(f"Max Magnitude: {max_magnitude}")
    print(f"Total Earthquakes: {processed_count}")
    
    # Normal processing logic
    pg_hook = PostgresHook(postgres_conn_id='earth_quake')
    
    # Create normal events log table
    create_normal_table = """
        CREATE TABLE IF NOT EXISTS gold.normal_earthquake_log (
            event_date DATE,
            max_magnitude FLOAT,
            total_earthquakes INT,
            processing_type VARCHAR(50) DEFAULT 'NORMAL',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """
    pg_hook.run(create_normal_table)
    
    # Insert normal processing record
    yesterday_date = datetime.utcnow().date() - timedelta(days=1)
    insert_normal = """
        INSERT INTO gold.normal_earthquake_log 
        (event_date, max_magnitude, total_earthquakes)
        VALUES (%s, %s, %s)
    """
    pg_hook.run(insert_normal, parameters=(yesterday_date, max_magnitude, processed_count))
    
    # Push normal processing data to XCom
    normal_summary = {
        'alert_type': 'NORMAL',
        'max_magnitude': max_magnitude,
        'total_earthquakes': processed_count,
        'alert_message': f'✅ Normal processing: {processed_count} earthquakes (max: {max_magnitude})',
        'requires_immediate_attention': False
    }
    
    ti.xcom_push(key="processing_result", value=normal_summary)
    
    print("✅ Normal earthquake processing completed")
    print(f"Summary: {normal_summary}")


def final_notification_task(**context):
    """
    Final task that runs after branching to send appropriate notifications
    Uses XCom data from whichever branch was executed
    """
    ti = context['task_instance']
    
    # Try to pull data from each possible branch (using same key name)
    critical_result = ti.xcom_pull(task_ids="critical_earthquake_processing", key="processing_result")
    normal_result = ti.xcom_pull(task_ids="normal_earthquake_processing", key="processing_result")
    
    print("📧 FINAL NOTIFICATION TASK")
    
    # Determine which branch was executed and prepare notification
    if critical_result:
        print("🚨 Preparing CRITICAL earthquake notification")
        notification_data = critical_result
        notification_data['priority'] = 'URGENT'
        notification_data['notification_type'] = 'EMERGENCY_ALERT'
    elif normal_result:
        print("✅ Preparing NORMAL earthquake notification")
        notification_data = normal_result
        notification_data['priority'] = 'LOW'
        notification_data['notification_type'] = 'DAILY_SUMMARY'
    else:
        print("❌ No branch data found - preparing default notification")
        notification_data = {
            'alert_type': 'UNKNOWN',
            'alert_message': 'Earthquake processing completed but no branch data found',
            'priority': 'LOW',
            'notification_type': 'ERROR'
        }
    
    # Add timestamp and final processing info
    notification_data['notification_time'] = datetime.utcnow().isoformat()
    notification_data['pipeline_status'] = 'COMPLETED'
    
    # Push final notification data to XCom
    ti.xcom_push(key="final_notification", value=notification_data)
    
    print(f"📧 Final notification prepared:")
    print(f"   Type: {notification_data.get('notification_type')}")
    print(f"   Priority: {notification_data.get('priority')}")
    print(f"   Message: {notification_data.get('alert_message')}")
    print("✅ Pipeline completed successfully with intelligent branching!")