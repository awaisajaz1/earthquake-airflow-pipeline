"""
Demo showing different ways to access XCom data
"""

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from datetime import datetime
import random

def _choose_best_model():
    """This function's return value is automatically pushed to XCom"""
    num = random.randint(3, 7)
    if num >= 5:
        print(f"model B is executed with the number: {num}")
        return 'model_B'  # ← Automatically pushed to XCom
    else:
        print(f"model A is executed with the number: {num}")
        return 'model_A'  # ← Automatically pushed to XCom

def _choose_with_explicit_push(**context):
    """This function explicitly pushes to XCom"""
    ti = context['task_instance']
    num = random.randint(3, 7)
    
    if num >= 5:
        chosen_model = 'model_B'
        print(f"model B is executed with the number: {num}")
    else:
        chosen_model = 'model_A'
        print(f"model A is executed with the number: {num}")
    
    # Explicit XCom push
    ti.xcom_push(key='chosen_model', value=chosen_model)
    ti.xcom_push(key='random_number', value=num)
    
    return chosen_model  # This ALSO gets pushed automatically as 'return_value'

def show_xcom_data(**context):
    """Show different ways to pull XCom data"""
    ti = context['task_instance']
    
    print("=== XCOM DATA RETRIEVAL METHODS ===")
    
    # Method 1: Pull return value (automatic push)
    auto_model = ti.xcom_pull(task_ids='choose_best_model')
    print(f"Auto return value: {auto_model}")
    
    # Method 2: Pull return value explicitly
    return_value = ti.xcom_pull(task_ids='choose_best_model', key='return_value')
    print(f"Explicit return_value key: {return_value}")
    
    # Method 3: Pull custom key (if using explicit push)
    # custom_model = ti.xcom_pull(task_ids='choose_with_explicit_push', key='chosen_model')
    # custom_number = ti.xcom_pull(task_ids='choose_with_explicit_push', key='random_number')
    # print(f"Custom key - model: {custom_model}, number: {custom_number}")
    
    print("===================================")

dag = DAG(
    'xcom_demo',
    start_date=datetime(2023, 1, 1),
    schedule='@once'
)

# BranchPythonOperator - automatically pushes return value
choose_best_model = BranchPythonOperator(
    task_id='choose_best_model',
    python_callable=_choose_best_model,
    dag=dag
)

model_A = EmptyOperator(task_id='model_A', dag=dag)
model_B = EmptyOperator(task_id='model_B', dag=dag)

final_model = EmptyOperator(
    task_id='final_model',
    trigger_rule='none_failed_min_one_success',
    dag=dag
)

# Task to show XCom data
show_xcom = PythonOperator(
    task_id='show_xcom',
    python_callable=show_xcom_data,
    dag=dag
)

# Dependencies
choose_best_model >> [model_A, model_B] >> final_model >> show_xcom