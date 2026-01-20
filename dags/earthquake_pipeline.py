"""
Earthquake Data Pipeline DAG

This DAG demonstrates:
1. Data extraction from USGS Earthquake API
2. XCom push/pull for inter-task communication
3. Data cleaning and transformation
4. Loading data into PostgreSQL
5. Data validation and summary generation

Author: Data Engineering Tutorial
"""

from datetime import datetime, timedelta
import json
import logging
import pandas as pd
import requests
from typing import Dict, List, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.models import Variable

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Default arguments for the DAG
default_args = {
    'owner': 'data-engineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition
dag = DAG(
    'earthquake_data_pipeline',
    default_args=default_args,
    description='Extract, transform, and load earthquake data',
    schedule_interval=timedelta(hours=6),  # Run every 6 hours
    catchup=False,
    tags=['earthquake', 'etl', 'tutorial'],
)


def extract_earthquake_data(**context) -> Dict[str, Any]:
    """
    Extract earthquake data from USGS API
    
    XCom Push: Pushes raw earthquake data to be used by downstream tasks
    """
    logger.info("Starting earthquake data extraction...")
    
    # USGS Earthquake API endpoint
    # Get earthquakes from the last 24 hours with magnitude >= 2.5
    end_time = datetime.utcnow()
    start_time = end_time - timedelta(days=1)
    
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        'format': 'geojson',
        'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
        'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
        'minmagnitude': 2.5,
        'limit': 1000
    }
    
    try:
        logger.info(f"Fetching data from {url} with params: {params}")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        earthquake_count = len(data.get('features', []))
        
        logger.info(f"Successfully extracted {earthquake_count} earthquake records")
        
        # XCom Push: Store raw data for next task
        context['task_instance'].xcom_push(
            key='raw_earthquake_data', 
            value=data
        )
        context['task_instance'].xcom_push(
            key='extraction_metadata', 
            value={
                'extraction_time': datetime.utcnow().isoformat(),
                'record_count': earthquake_count,
                'api_endpoint': url,
                'time_range': f"{start_time.isoformat()} to {end_time.isoformat()}"
            }
        )
        
        return f"Extracted {earthquake_count} earthquake records"
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching earthquake data: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during extraction: {str(e)}")
        raise


def transform_earthquake_data(**context) -> Dict[str, Any]:
    """
    Transform and clean earthquake data
    
    XCom Pull: Gets raw data from extract task
    XCom Push: Pushes cleaned data for loading task
    """
    logger.info("Starting earthquake data transformation...")
    
    # XCom Pull: Get raw data from previous task
    raw_data = context['task_instance'].xcom_pull(
        key='raw_earthquake_data', 
        task_ids='extract_earthquake_data'
    )
    
    if not raw_data or 'features' not in raw_data:
        raise ValueError("No earthquake data received from extraction task")
    
    features = raw_data['features']
    logger.info(f"Processing {len(features)} earthquake records...")
    
    # Transform data into structured format
    transformed_records = []
    
    for feature in features:
        try:
            properties = feature.get('properties', {})
            geometry = feature.get('geometry', {})
            coordinates = geometry.get('coordinates', [None, None, None])
            
            # Clean and validate data
            record = {
                'id': feature.get('id'),
                'magnitude': properties.get('mag'),
                'place': properties.get('place', '').strip() if properties.get('place') else None,
                'time_occurred': pd.to_datetime(properties.get('time'), unit='ms', utc=True) if properties.get('time') else None,
                'updated_time': pd.to_datetime(properties.get('updated'), unit='ms', utc=True) if properties.get('updated') else None,
                'timezone': properties.get('tz'),
                'url': properties.get('url'),
                'detail_url': properties.get('detail'),
                'felt': properties.get('felt'),
                'cdi': properties.get('cdi'),
                'mmi': properties.get('mmi'),
                'alert': properties.get('alert'),
                'status': properties.get('status'),
                'tsunami': properties.get('tsunami'),
                'sig': properties.get('sig'),
                'net': properties.get('net'),
                'code': properties.get('code'),
                'ids': properties.get('ids'),
                'sources': properties.get('sources'),
                'types': properties.get('types'),
                'nst': properties.get('nst'),
                'dmin': properties.get('dmin'),
                'rms': properties.get('rms'),
                'gap': properties.get('gap'),
                'magnitude_type': properties.get('magType'),
                'type': properties.get('type'),
                'title': properties.get('title'),
                'longitude': coordinates[0] if len(coordinates) > 0 else None,
                'latitude': coordinates[1] if len(coordinates) > 1 else None,
                'depth': coordinates[2] if len(coordinates) > 2 else None,
            }
            
            # Data quality checks
            if record['id'] and record['magnitude'] is not None:
                transformed_records.append(record)
            else:
                logger.warning(f"Skipping record with missing critical data: {record['id']}")
                
        except Exception as e:
            logger.warning(f"Error processing earthquake record: {str(e)}")
            continue
    
    # Create DataFrame for additional cleaning
    df = pd.DataFrame(transformed_records)
    
    if df.empty:
        logger.warning("No valid records after transformation")
        return "No valid records to process"
    
    # Data cleaning operations
    logger.info("Performing data cleaning operations...")
    
    # Remove duplicates
    initial_count = len(df)
    df = df.drop_duplicates(subset=['id'])
    logger.info(f"Removed {initial_count - len(df)} duplicate records")
    
    # Clean magnitude data
    df['magnitude'] = pd.to_numeric(df['magnitude'], errors='coerce')
    df = df[df['magnitude'].notna()]  # Remove records with invalid magnitude
    
    # Clean location data
    df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
    df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
    df['depth'] = pd.to_numeric(df['depth'], errors='coerce')
    
    # Clean place names
    df['place'] = df['place'].str.strip()
    df['place'] = df['place'].replace('', None)
    
    # Convert DataFrame back to records
    cleaned_records = df.to_dict('records')
    
    logger.info(f"Transformation completed. {len(cleaned_records)} clean records ready for loading")
    
    # XCom Push: Store cleaned data for loading task
    context['task_instance'].xcom_push(
        key='cleaned_earthquake_data', 
        value=cleaned_records
    )
    
    # Push transformation summary
    transformation_summary = {
        'original_count': len(features),
        'cleaned_count': len(cleaned_records),
        'records_removed': len(features) - len(cleaned_records),
        'transformation_time': datetime.utcnow().isoformat(),
        'magnitude_range': {
            'min': float(df['magnitude'].min()),
            'max': float(df['magnitude'].max()),
            'avg': float(df['magnitude'].mean())
        } if not df.empty else None
    }
    
    context['task_instance'].xcom_push(
        key='transformation_summary', 
        value=transformation_summary
    )
    
    return f"Transformed {len(cleaned_records)} earthquake records"


def load_earthquake_data(**context) -> str:
    """
    Load cleaned earthquake data into PostgreSQL (earth database)
    
    XCom Pull: Gets cleaned data from transform task
    """
    logger.info("Starting earthquake data loading...")
    
    # XCom Pull: Get cleaned data from previous task
    cleaned_data = context['task_instance'].xcom_pull(
        key='cleaned_earthquake_data', 
        task_ids='transform_earthquake_data'
    )
    
    if not cleaned_data:
        logger.warning("No cleaned data received from transformation task")
        return "No data to load"
    
    # Get PostgreSQL connection to earth database
    postgres_hook = PostgresHook(postgres_conn_id='earth_postgres')
    
    try:
        # Prepare data for insertion
        logger.info(f"Loading {len(cleaned_data)} records into PostgreSQL earth database...")
        
        # Create insert query
        insert_query = """
        INSERT INTO earthquake_data (
            id, magnitude, place, time_occurred, updated_time, timezone, url, detail_url,
            felt, cdi, mmi, alert, status, tsunami, sig, net, code, ids, sources, types,
            nst, dmin, rms, gap, magnitude_type, type, title, longitude, latitude, depth
        ) VALUES (
            %(id)s, %(magnitude)s, %(place)s, %(time_occurred)s, %(updated_time)s, %(timezone)s,
            %(url)s, %(detail_url)s, %(felt)s, %(cdi)s, %(mmi)s, %(alert)s, %(status)s,
            %(tsunami)s, %(sig)s, %(net)s, %(code)s, %(ids)s, %(sources)s, %(types)s,
            %(nst)s, %(dmin)s, %(rms)s, %(gap)s, %(magnitude_type)s, %(type)s, %(title)s,
            %(longitude)s, %(latitude)s, %(depth)s
        ) ON CONFLICT (id) DO UPDATE SET
            magnitude = EXCLUDED.magnitude,
            place = EXCLUDED.place,
            updated_time = EXCLUDED.updated_time,
            updated_at = CURRENT_TIMESTAMP
        """
        
        # Execute batch insert
        postgres_hook.insert_rows(
            table='earthquake_data',
            rows=cleaned_data,
            target_fields=[
                'id', 'magnitude', 'place', 'time_occurred', 'updated_time', 'timezone',
                'url', 'detail_url', 'felt', 'cdi', 'mmi', 'alert', 'status', 'tsunami',
                'sig', 'net', 'code', 'ids', 'sources', 'types', 'nst', 'dmin', 'rms',
                'gap', 'magnitude_type', 'type', 'title', 'longitude', 'latitude', 'depth'
            ],
            replace=True
        )
        
        # Also store raw data for audit purposes
        raw_data = context['task_instance'].xcom_pull(
            key='raw_earthquake_data', 
            task_ids='extract_earthquake_data'
        )
        
        if raw_data:
            postgres_hook.run(
                "INSERT INTO raw_data.earthquake_raw (raw_json) VALUES (%s)",
                parameters=[json.dumps(raw_data)]
            )
        
        logger.info(f"Successfully loaded {len(cleaned_data)} earthquake records")
        
        # Store loading summary in XCom
        context['task_instance'].xcom_push(
            key='loading_summary',
            value={
                'records_loaded': len(cleaned_data),
                'loading_time': datetime.utcnow().isoformat(),
                'table_name': 'earthquake_data',
                'database': 'earth'
            }
        )
        
        return f"Loaded {len(cleaned_data)} earthquake records into PostgreSQL earth database"
        
    except Exception as e:
        logger.error(f"Error loading data into PostgreSQL: {str(e)}")
        raise


def validate_and_summarize(**context) -> str:
    """
    Validate loaded data and create summary statistics
    
    XCom Pull: Gets summaries from previous tasks for validation
    """
    logger.info("Starting data validation and summarization...")
    
    # Get PostgreSQL connection to earth database
    postgres_hook = PostgresHook(postgres_conn_id='earth_postgres')
    
    try:
        # Validate data in database
        validation_queries = {
            'total_records': "SELECT COUNT(*) FROM earthquake_data",
            'recent_records': """
                SELECT COUNT(*) FROM earthquake_data 
                WHERE created_at >= CURRENT_DATE
            """,
            'magnitude_stats': """
                SELECT 
                    MIN(magnitude) as min_mag,
                    MAX(magnitude) as max_mag,
                    AVG(magnitude) as avg_mag,
                    COUNT(*) as total_count
                FROM earthquake_data 
                WHERE created_at >= CURRENT_DATE
            """,
            'significant_earthquakes': """
                SELECT COUNT(*) FROM earthquake_data 
                WHERE magnitude >= 5.0 AND created_at >= CURRENT_DATE
            """
        }
        
        validation_results = {}
        for query_name, query in validation_queries.items():
            result = postgres_hook.get_first(query)
            validation_results[query_name] = result
            logger.info(f"{query_name}: {result}")
        
        # Create summary record
        mag_stats = validation_results['magnitude_stats']
        summary_insert = """
        INSERT INTO earthquake_summary (
            date_processed, total_earthquakes, max_magnitude, 
            min_magnitude, avg_magnitude, significant_earthquakes
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        postgres_hook.run(summary_insert, parameters=[
            datetime.utcnow().date(),
            mag_stats[3],  # total_count
            mag_stats[1],  # max_mag
            mag_stats[0],  # min_mag
            round(mag_stats[2], 2) if mag_stats[2] else 0,  # avg_mag
            validation_results['significant_earthquakes'][0]
        ])
        
        # Refresh materialized view for analytics
        postgres_hook.run("REFRESH MATERIALIZED VIEW analytics.daily_earthquake_stats")
        
        # Store validation results in XCom
        context['task_instance'].xcom_push(
            key='validation_results',
            value=validation_results
        )
        
        logger.info("Data validation and summarization completed successfully")
        return f"Validation completed. Processed {mag_stats[3]} records with avg magnitude {round(mag_stats[2], 2) if mag_stats[2] else 0}"
        
    except Exception as e:
        logger.error(f"Error during validation: {str(e)}")
        raise


# Task definitions
extract_task = PythonOperator(
    task_id='extract_earthquake_data',
    python_callable=extract_earthquake_data,
    dag=dag,
    doc_md="""
    ## Extract Earthquake Data
    
    This task extracts earthquake data from the USGS API for the last 24 hours.
    
    **XCom Outputs:**
    - `raw_earthquake_data`: Complete API response
    - `extraction_metadata`: Extraction statistics and metadata
    
    **API Details:**
    - Source: USGS Earthquake Hazards Program
    - Minimum Magnitude: 2.5
    - Time Range: Last 24 hours
    - Format: GeoJSON
    """
)

transform_task = PythonOperator(
    task_id='transform_earthquake_data',
    python_callable=transform_earthquake_data,
    dag=dag,
    doc_md="""
    ## Transform Earthquake Data
    
    This task cleans and transforms the raw earthquake data.
    
    **XCom Inputs:**
    - `raw_earthquake_data`: From extract_earthquake_data task
    
    **XCom Outputs:**
    - `cleaned_earthquake_data`: Processed and cleaned records
    - `transformation_summary`: Transformation statistics
    
    **Transformations:**
    - Remove duplicates
    - Validate and clean magnitude data
    - Clean location coordinates
    - Standardize text fields
    """
)

load_task = PythonOperator(
    task_id='load_earthquake_data',
    python_callable=load_earthquake_data,
    dag=dag,
    doc_md="""
    ## Load Earthquake Data
    
    This task loads the cleaned data into PostgreSQL.
    
    **XCom Inputs:**
    - `cleaned_earthquake_data`: From transform_earthquake_data task
    
    **XCom Outputs:**
    - `loading_summary`: Loading statistics
    
    **Database Operations:**
    - Upsert records (INSERT ... ON CONFLICT)
    - Update existing records if found
    - Maintain data integrity
    """
)

validate_task = PythonOperator(
    task_id='validate_and_summarize',
    python_callable=validate_and_summarize,
    dag=dag,
    doc_md="""
    ## Validate and Summarize
    
    This task validates the loaded data and creates summary statistics.
    
    **XCom Outputs:**
    - `validation_results`: Validation statistics and results
    
    **Operations:**
    - Count total records
    - Calculate magnitude statistics
    - Identify significant earthquakes
    - Create summary records
    """
)

# Task dependencies
extract_task >> transform_task >> load_task >> validate_task