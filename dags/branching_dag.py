from airflow import DAG
from airflow.providers.standard.operators.empty import EmptyOperator
from airflow.providers.standard.operators.python import BranchPythonOperator, PythonOperator
from airflow.providers.smtp.operators.smtp import EmailOperator
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
    
    # Handle case where XCom data might be None
    if not chosen_model:
        print("Warning: No model selection found in XCom, using default")
        chosen_model = 'unknown_model'
        subject = '⚠️ Branching DAG Completed - Model Selection Unknown'
        model_description = 'Model selection data not found'
        color = 'orange'
    elif chosen_model == 'model_A':
        subject = '� Model A Selected - Branching DAG Success'
        model_description = 'Model A was selected (number < 5)'
        color = 'blue'
    else:  # model_B
        subject = '🟢 Model B Selected - Branching DAG Success'
        model_description = 'Model B was selected (number >= 5)'
        color = 'green'
    
    html_content = f'''
    <h3 style="color: {color};">Branching DAG Success Notification</h3>
    <p>The branching DAG has completed successfully!</p>
    <div style="background-color: #f0f0f0; padding: 10px; margin: 10px 0;">
        <p><strong>Selected Model:</strong> {chosen_model.upper() if chosen_model != 'unknown_model' else 'UNKNOWN'}</p>
        <p><strong>Description:</strong> {model_description}</p>
        <p><strong>Execution Date:</strong> {dag_run.execution_date}</p>
        <p><strong>DAG Run ID:</strong> {dag_run.run_id}</p>
    </div>
    <p>Model selection and processing completed without errors.</p>
    '''
    
    # Use Airflow's send_email function
    from airflow.utils.email import send_email
    
    try:
        send_email(
            to=['awaisajaz1@gmail.com'],  # Replace with actual email
            subject=subject,
            html_content=html_content
        )
        print(f"✅ Dynamic email sent successfully for {chosen_model}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        # Don't raise exception to avoid task failure
        print("Email sending failed, but task will continue")

# Dynamic email task that uses XCom data
send_dynamic_email_task = PythonOperator(
    task_id='send_dynamic_email',
    python_callable=send_dynamic_email,
    dag=dag
)

# APPROACH 2: Static Email with comprehensive templating
send_static_email = EmailOperator(
    task_id='send_static_email',
    to=['awaisajaz1@gmail.com'],  # Replace with actual email
    subject='Branching DAG Completed - {{ dag_run.run_id }}',  # Template in subject too!
    html_content='''
    <h3>Branching DAG Success Notification</h3>
    <p>The branching DAG has completed successfully!</p>
    
    <div style="background-color: #e8f5e8; padding: 15px; margin: 10px 0;">
        <h4>Execution Details:</h4>
        <ul>
            <li><strong>DAG ID:</strong> {{ dag.dag_id }}</li>
            <li><strong>Task ID:</strong> {{ task.task_id }}</li>
            <li><strong>Execution Date:</strong> {{ ds }}</li>
            <li><strong>Execution DateTime:</strong> {{ dag_run.execution_date }}</li>
            <li><strong>DAG Run ID:</strong> {{ dag_run.run_id }}</li>
            <li><strong>Run Type:</strong> {{ dag_run.run_type }}</li>
        </ul>
    </div>
    
    <p>Model selection and processing completed without errors.</p>
    <p><em>Note: This email uses Airflow templating but doesn't know which model was selected</em></p>
    
    <hr>
    <small>Generated automatically by Airflow at runtime</small>
    ''',
    dag=dag
)

# Update dependencies - showing both approaches
# Approach 1: Dynamic email that uses XCom data (runs after final_model)
final_model >> send_dynamic_email_task

# Approach 2: Static email (runs independently after final_model)
final_model >> send_static_email
