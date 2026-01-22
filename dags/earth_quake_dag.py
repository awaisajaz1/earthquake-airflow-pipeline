# Earthquake Data Pipeline DAG
# This DAG only contains orchestration logic - business logic is in utils/earthquake_etl.py

from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.python import PythonOperator
from airflow.utils.trigger_rule import TriggerRule

# Import business logic functions
from utils.earthquake_etl import (
    ingest_to_bronze,
    transform_bronze_to_silver,
    load_silver_to_gold
)

# DAG configuration
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 20),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition - only orchestration
dag = DAG(
    dag_id='fetch_earth_quake_api_data',
    default_args=default_args,
    start_date=datetime(2026, 1, 21),
    schedule=timedelta(days=1),
    description='DAG for earth quakes api to store in postgres',
    catchup=False
)

# Task definitions - only dependencies and configuration
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

gold_earthquake_data = PythonOperator(
    task_id='process_earth_quake_data_to_gold',
    python_callable=load_silver_to_gold,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# Task dependencies - only workflow orchestration
fetch_earthquake_data >> silver_earthquake_data >> gold_earthquake_data