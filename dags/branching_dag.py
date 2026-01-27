from airflow import DAG  # ✅ Fixed: DAG (uppercase)
from airflow.operators.empty import 
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
        print(f"model B is executed with the number: {num}")
        return 'model_B'
    else:
        print(f"model A is executed with the number: {num}")
        return 'model_A'


dag = DAG(  # ✅ Fixed: DAG (uppercase)
    'branching_dag',
    default_args=default_args,
    schedule='@daily'  # ✅ Fixed: schedule instead of schedule_interval
)


choose_best_model = BranchPythonOperator(
    task_id='choose_best_model',
    python_callable=_choose_best_model,
    dag=dag
)


model_A = EmptyOperator(  # ✅ Fixed: EmptyOperator instead of DummyOperator
    task_id='model_A',
    dag=dag
)

model_B = EmptyOperator(  # ✅ Fixed: EmptyOperator instead of DummyOperator
    task_id='model_B',
    dag=dag
)


choose_best_model >> [model_A, model_B]
