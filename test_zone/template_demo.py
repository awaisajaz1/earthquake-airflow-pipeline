"""
Demo showing how Airflow templating works in EmailOperator
"""

from airflow import DAG
from airflow.operators.email import EmailOperator
from airflow.operators.python import PythonOperator
from datetime import datetime

def show_template_values(**context):
    """Show what template values are available"""
    print("=== AIRFLOW TEMPLATE CONTEXT ===")
    print(f"ds: {context['ds']}")
    print(f"dag_run.run_id: {context['dag_run'].run_id}")
    print(f"dag_run.execution_date: {context['dag_run'].execution_date}")
    print(f"dag.dag_id: {context['dag'].dag_id}")
    print(f"task.task_id: {context['task'].task_id}")
    print(f"dag_run.run_type: {context['dag_run'].run_type}")
    print("================================")

dag = DAG(
    'template_demo',
    start_date=datetime(2023, 1, 1),
    schedule='@once'
)

# Show what's in the context
show_context = PythonOperator(
    task_id='show_context',
    python_callable=show_template_values,
    dag=dag
)

# Email with templating - this is what gets processed:
template_email = EmailOperator(
    task_id='template_email',
    to=['admin@example.com'],
    subject='Template Demo - Run {{ dag_run.run_id }}',
    html_content='''
    <h3>Template Values Demo</h3>
    <p>This email shows how Airflow templating works:</p>
    
    <table border="1" style="border-collapse: collapse;">
        <tr><td><strong>Template</strong></td><td><strong>Value</strong></td></tr>
        <tr><td>{{ "{{ ds }}" }}</td><td>{{ ds }}</td></tr>
        <tr><td>{{ "{{ dag_run.run_id }}" }}</td><td>{{ dag_run.run_id }}</td></tr>
        <tr><td>{{ "{{ dag.dag_id }}" }}</td><td>{{ dag.dag_id }}</td></tr>
        <tr><td>{{ "{{ task.task_id }}" }}</td><td>{{ task.task_id }}</td></tr>
        <tr><td>{{ "{{ dag_run.run_type }}" }}</td><td>{{ dag_run.run_type }}</td></tr>
    </table>
    
    <p><em>These values are automatically populated by Airflow at runtime!</em></p>
    ''',
    dag=dag
)

show_context >> template_email