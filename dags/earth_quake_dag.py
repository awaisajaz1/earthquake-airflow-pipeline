from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.dummy import DummyOperator




default_args = {
    'owner' : 'airflow',
    'depends_on_past' : False,
    'start_date' : datetime(2026, 1, 21),
    'retries' : 1,
    'retry_delay' : timedelta(minutes=5)
}


dag = DAG(
    'fetch_earth_quake_api_data',
    default_args = default_args,
    description = 'DAG for earth quakes api to store in postgres',
    schedule_interval = timedelta(days=1)
)

# Add at least one task for the DAG to appear
dummy_task = DummyOperator(
    task_id='dummy_task',
    dag=dag
)
