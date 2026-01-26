# Earthquake Data Pipeline DAG with Branching
# This DAG contains orchestration logic with intelligent branching based on earthquake severity

from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.utils.trigger_rule import TriggerRule

# Import business logic functions
from utils.earthquake_etl import (
    ingest_to_bronze,
    transform_bronze_to_silver,
    load_silver_to_gold,
    earthquake_severity_branch,
    critical_earthquake_processing,
    normal_earthquake_processing,
    final_notification_task
)

# DAG configuration
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 20),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# DAG definition - orchestration with branching
dag = DAG(
    dag_id='fetch_earth_quake_api_data',
    default_args=default_args,
    start_date=datetime(2026, 1, 21),
    schedule=timedelta(days=1),
    description='DAG for earthquake data with intelligent severity-based branching',
    catchup=False
)

# ========== MAIN ETL TASKS ==========

# Task 1: Extract data to bronze layer
fetch_earthquake_data = PythonOperator(
    task_id='fetch_earth_quake_data_to_bronze',
    python_callable=ingest_to_bronze,
    dag=dag,
)

# Task 2: Transform bronze to silver layer
silver_earthquake_data = PythonOperator(
    task_id='process_earth_quake_data_to_silver',
    python_callable=transform_bronze_to_silver,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# Task 3: Load silver to gold layer (runs before branching)
gold_earthquake_data = PythonOperator(
    task_id='process_earth_quake_data_to_gold',
    python_callable=load_silver_to_gold,
    trigger_rule=TriggerRule.ALL_DONE,
    dag=dag,
)

# ========== BRANCHING LOGIC ==========

# Branching task: Decide processing path based on earthquake severity
earthquake_branch = BranchPythonOperator(
    task_id='earthquake_severity_branch',
    python_callable=earthquake_severity_branch,
    dag=dag,
)

# Branch 1: Critical earthquake processing (≥7.0 magnitude)
critical_processing = PythonOperator(
    task_id='critical_earthquake_processing',
    python_callable=critical_earthquake_processing,
    dag=dag,
)

# Branch 2: Normal earthquake processing (<7.0 magnitude)
normal_processing = PythonOperator(
    task_id='normal_earthquake_processing',
    python_callable=normal_earthquake_processing,
    dag=dag,
)

# Final task: Notification (runs after either branch)
final_notification = PythonOperator(
    task_id='final_notification_task',
    python_callable=final_notification_task,
    trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,  # Run if at least one branch succeeds
    dag=dag,
)

# ========== TASK DEPENDENCIES ==========

# Main ETL flow
fetch_earthquake_data >> silver_earthquake_data >> gold_earthquake_data

# Branching flow
gold_earthquake_data >> earthquake_branch

# Branch paths
earthquake_branch >> [critical_processing, normal_processing]

# Final notification (joins both branches)
[critical_processing, normal_processing] >> final_notification