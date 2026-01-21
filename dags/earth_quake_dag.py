from airflow import DAG
from datetime import timedelta




default_args = {
    'owner' : 'airflow',
    'depends_on_past' : False,
    'start_date' : datetime(2026, 1, 21),
    'retries' : 1,
    'retry_delay' : timedelta(minutes=5)
}