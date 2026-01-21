from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.empty import EmptyOperator

# Simple DAG definition
dag = DAG(
    dag_id='fetch_earth_quake_api_data',
    start_date=datetime(2026, 1, 21),
    schedule=timedelta(days=1),
    description='DAG for earth quakes api to store in postgres',
    catchup=False
)

# Simple task
start_task = EmptyOperator(
    task_id='start',
    dag=dag
)
