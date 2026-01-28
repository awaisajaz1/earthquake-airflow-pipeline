"""
Working branching DAG with email - simplified version
"""

from airflow import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
from datetime import datetime
import random

def _choose_best_model():
    """Choose model and return result"""
    num = random.randint(3, 7)
    if num >= 5:
        result = 'model_B'
        print(f"🟢 CHOOSING MODEL B with number: {num}")
    else:
        result = 'model_A'
        print(f"🔵 CHOOSING MODEL A with number: {num}")
    
    print(f"🔄 RETURNING: {result}")
    return result

def send_email_notification(**context):
    """Send email notification with model selection"""
    ti = context['task_instance']
    dag_run = context['dag_run']
    
    # Get the chosen model from XCom
    chosen_model = ti.xcom_pull(task_ids='choose_best_model')
    
    print(f"=== EMAIL TASK DEBUG ===")
    print(f"Retrieved model: {chosen_model}")
    print(f"DAG run: {dag_run.run_id}")
    print(f"========================")
    
    if chosen_model == 'model_A':
        message = "🔵 Model A was selected (number < 5)"
        color = "blue"
    elif chosen_model == 'model_B':
        message = "🟢 Model B was selected (number >= 5)"
        color = "green"
    else:
        message = f"⚠️ Unknown model: {chosen_model}"
        color = "orange"
    
    print(f"📧 EMAIL CONTENT: {message}")
    
    # In a real scenario, you would send the actual email here
    # For now, just log the email content
    email_content = f"""
    Subject: Branching DAG Completed - {chosen_model or 'Unknown'}
    
    {message}
    
    DAG Run: {dag_run.run_id}
    Logical Date: {getattr(dag_run, 'logical_date', 'Unknown')}
    """
    
    print(f"📧 EMAIL WOULD BE SENT:")
    print(email_content)
    
    return f"email_sent_for_{chosen_model}"

# DAG definition
dag = DAG(
    'working_branching_email',
    start_date=datetime(2023, 1, 1),
    schedule='@once',
    catchup=False
)

# Tasks
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

send_email = PythonOperator(
    task_id='send_email',
    python_callable=send_email_notification,
    dag=dag
)

# Dependencies
choose_best_model >> [model_A, model_B] >> final_model >> send_email