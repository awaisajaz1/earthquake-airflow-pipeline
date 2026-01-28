"""
Simple XCom test to verify basic functionality
"""

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from datetime import datetime

def push_data(**context):
    """Push data to XCom"""
    ti = context['task_instance']
    
    # Method 1: Return value (automatic push)
    result = "test_data_from_return"
    print(f"Returning: {result}")
    return result

def pull_data(**context):
    """Pull data from XCom"""
    ti = context['task_instance']
    
    # Pull the data
    pulled_data = ti.xcom_pull(task_ids='push_task')
    print(f"Pulled data: {pulled_data}")
    
    if pulled_data:
        print(f"✅ XCom working! Data: {pulled_data}")
    else:
        print("❌ XCom failed - no data received")
    
    return pulled_data

dag = DAG(
    'simple_xcom_test',
    start_date=datetime(2023, 1, 1),
    schedule='@once'
)

push_task = PythonOperator(
    task_id='push_task',
    python_callable=push_data,
    dag=dag
)

pull_task = PythonOperator(
    task_id='pull_task',
    python_callable=pull_data,
    dag=dag
)

push_task >> pull_task