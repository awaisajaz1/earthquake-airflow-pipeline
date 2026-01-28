"""
Debug XCom issue in branching DAG
"""

from airflow import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
from datetime import datetime
import random

def _choose_best_model():
    """Choose model and explicitly show what's being returned"""
    num = random.randint(3, 7)
    if num >= 5:
        result = 'model_B'
        print(f"🟢 CHOOSING MODEL B with number: {num}")
    else:
        result = 'model_A'
        print(f"🔵 CHOOSING MODEL A with number: {num}")
    
    print(f"🔄 RETURNING: {result}")
    return result

def debug_xcom(**context):
    """Debug XCom data retrieval"""
    ti = context['task_instance']
    dag_run = context['dag_run']
    
    print("=== XCOM DEBUG INFORMATION ===")
    print(f"Task Instance: {ti}")
    print(f"DAG Run: {dag_run}")
    
    # Try different ways to get XCom data
    print("\n--- Trying different XCom retrieval methods ---")
    
    # Method 1: Default pull
    try:
        chosen_model = ti.xcom_pull(task_ids='choose_best_model')
        print(f"✅ Default pull result: {chosen_model} (type: {type(chosen_model)})")
    except Exception as e:
        print(f"❌ Default pull failed: {e}")
    
    # Method 2: Explicit return_value key
    try:
        return_value = ti.xcom_pull(task_ids='choose_best_model', key='return_value')
        print(f"✅ Explicit return_value: {return_value} (type: {type(return_value)})")
    except Exception as e:
        print(f"❌ Explicit return_value failed: {e}")
    
    # Method 3: Get all XCom data for the task
    try:
        all_xcom = ti.xcom_pull(task_ids='choose_best_model', key=None)
        print(f"✅ All XCom data: {all_xcom}")
    except Exception as e:
        print(f"❌ All XCom pull failed: {e}")
    
    # Method 4: Check if task actually ran
    print(f"\n--- Task Execution Info ---")
    print(f"Current task ID: {ti.task_id}")
    print(f"DAG ID: {ti.dag_id}")
    print(f"Execution date: {ti.execution_date}")
    
    print("=== END DEBUG ===")
    
    # Return something for testing
    return "debug_complete"

dag = DAG(
    'debug_xcom_dag',
    start_date=datetime(2023, 1, 1),
    schedule='@once'
)

# Branch task
choose_best_model = BranchPythonOperator(
    task_id='choose_best_model',
    python_callable=_choose_best_model,
    dag=dag
)

# Model tasks
model_A = EmptyOperator(task_id='model_A', dag=dag)
model_B = EmptyOperator(task_id='model_B', dag=dag)

# Join task
final_model = EmptyOperator(
    task_id='final_model',
    trigger_rule='none_failed_min_one_success',
    dag=dag
)

# Debug task
debug_task = PythonOperator(
    task_id='debug_xcom',
    python_callable=debug_xcom,
    dag=dag
)

# Dependencies
choose_best_model >> [model_A, model_B] >> final_model >> debug_task