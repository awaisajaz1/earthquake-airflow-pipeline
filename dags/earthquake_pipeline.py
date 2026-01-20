"""
Earthquake Data Pipeline DAG

This DAG demonstrates:
1. Data extraction from USGS Earthquake API
2. XCom push/pull for inter-task communication
3. Data cleaning and transformation
4. Loading data into PostgreSQL
5. Data validation and summary generation

The ETL logic is separated into utils/earthquake_etl.py for better code organization.

Author: Data Engineering Tutorial
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator

# Import our ETL functions
from utils.earthquake_etl import earthquake_etl

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

# Task definitions - now just calling the ETL functions
extract_task = PythonOperator(
    task_id='extract_earthquake_data',
    python_callable=earthquake_etl.extract_earthquake_data,
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
    
    **Implementation:** See `utils/earthquake_etl.py` for detailed logic
    """
)

transform_task = PythonOperator(
    task_id='transform_earthquake_data',
    python_callable=earthquake_etl.transform_earthquake_data,
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
    
    **Implementation:** See `utils/earthquake_etl.py` for detailed logic
    """
)

load_task = PythonOperator(
    task_id='load_earthquake_data',
    python_callable=earthquake_etl.load_earthquake_data,
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
    - Store raw data for audit
    
    **Implementation:** See `utils/earthquake_etl.py` for detailed logic
    """
)

validate_task = PythonOperator(
    task_id='validate_and_summarize',
    python_callable=earthquake_etl.validate_and_summarize,
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
    - Refresh analytics materialized views
    
    **Implementation:** See `utils/earthquake_etl.py` for detailed logic
    """
)

# Task dependencies
extract_task >> transform_task >> load_task >> validate_task