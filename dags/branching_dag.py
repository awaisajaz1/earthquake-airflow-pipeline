from airflow import DAG
from airflow.operators.empty import EmptyOperator
from airflow.operators.python import BranchPythonOperator, PythonOperator
from airflow.operators.email import EmailOperator
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

final_model = EmptyOperator(  # ✅ Fixed: EmptyOperator instead of DummyOperator
    task_id='final_model',
    trigger_rule='none_failed_min_one_success',
    dag=dag
)


choose_best_model >> [model_A, model_B] >> final_model

# APPROACH 1: Dynamic Email using XCom data
def send_dynamic_email(**context):
    """Send email with dynamic content from XCom"""
    ti = context['task_instance']
    dag_run = context['dag_run']
    
    # Get which model was chosen from XCom
    chosen_model = ti.xcom_pull(task_ids='choose_best_model')
    
    print(f"Sending email for chosen model: {chosen_model}")
    
    # Dynamic email content based on chosen model
    if chosen_model == 'model_A':
        subject = '🔵 Model A Selected - Branching DAG Success'
        model_description = 'Model A was selected (number < 5)'
        color = 'blue'
    else:
        subject = '🟢 Model B Selected - Branching DAG Success'
        model_description = 'Model B was selected (number >= 5)'
        color = 'green'
    
    html_content = f'''
    <h3 style="color: {color};">Branching DAG Success Notification</h3>
    <p>The branching DAG has completed successfully!</p>
    <div style="background-color: #f0f0f0; padding: 10px; margin: 10px 0;">
        <p><strong>Selected Model:</strong> {chosen_model.upper()}</p>
        <p><strong>Description:</strong> {model_description}</p>
        <p><strong>Execution Date:</strong> {dag_run.execution_date}</p>
        <p><strong>DAG Run ID:</strong> {dag_run.run_id}</p>
    </div>
    <p>Model selection and processing completed without errors.</p>
    '''
    
    # Use Airflow's send_email function
    from airflow.utils.email import send_email
    
    send_email(
        to=['admin@example.com'],  # Replace with actual email
        subject=subject,
        html_content=html_content
    )
    
    print(f"✅ Dynamic email sent successfully for {chosen_model}")

# Dynamic email task that uses XCom data
send_dynamic_email_task = PythonOperator(
    task_id='send_dynamic_email',
    python_callable=send_dynamic_email,
    dag=dag
)

# APPROACH 2: Static Email (original approach - independent)
send_static_email = EmailOperator(
    task_id='send_static_email',
    to=['admin@example.com'],  # Replace with actual email
    subject='Branching DAG Completed Successfully',
    html_content='''
    <h3>Branching DAG Success Notification</h3>
    <p>The branching DAG has completed successfully.</p>
    <p><strong>Execution Date:</strong> {{ ds }}</p>
    <p><strong>DAG Run ID:</strong> {{ dag_run.run_id }}</p>
    <p>Model selection and processing completed without errors.</p>
    <p><em>Note: This email doesn't know which model was selected</em></p>
    ''',
    dag=dag
)

# Update dependencies - showing both approaches
# Approach 1: Dynamic email that uses XCom data
final_model >> send_dynamic_email_task

# Approach 2: Static email (runs independently)
final_model >> send_static_email
