from airflow import Dag
from airflow.operators.dummy import DummyOperator
from airflow.operators.python import BranchPythonOperator
import random

from datetime import datetime


default_args = {
    'owner': 'airflow',
    'start_date': datetime(2023, 1, 1)
    }


def _choose_best_model():

    num = random.randint(3, 7)

    if num >= 5:
        return 'model_B'

    else:
        return 'model_A'


dag = Dag(
    'branching_dag',
    default_args=default_args,
    schedule_interval='@daily'
)


choose_best_model = BranchPythonOperator(
    task_id='choose_best_model',
    python_callable=_choose_best_model,
    dag=dag
)


model_A = DummyOperator(
    task_id='model_A',
    dag=dag
)
model_B = DummyOperator(
    task_id='model_B',
    dag=dag
)


choose_best_model >> [model_A, model_B]
