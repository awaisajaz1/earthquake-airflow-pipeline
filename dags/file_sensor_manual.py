"""
Manual FileSensor DAG - Create files manually to test
This version waits for you to manually create a file
"""

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.sensors.filesystem import FileSensor
from datetime import datetime, timedelta
import os

# DAG configuration
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

def process_manual_file(**context):
    """Process manually created file"""
    file_path = "/opt/airflow/dags/test_files/manual_data.txt"
    
    print(f"🔍 Processing manually created file: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            print(f"📄 File contents:\n{content}")
        
        # Simple analysis
        lines = content.strip().split('\n')
        words = content.split()
        
        results = {
            'file_path': file_path,
            'lines': len(lines),
            'words': len(words),
            'characters': len(content),
            'processed_at': datetime.now().isoformat()
        }
        
        print(f"📊 Analysis results:")
        print(f"  - Lines: {results['lines']}")
        print(f"  - Words: {results['words']}")
        print(f"  - Characters: {results['characters']}")
        
        context['task_instance'].xcom_push(key='analysis_results', value=results)
        
        print("✅ Manual file processed successfully!")
        return results
        
    except Exception as e:
        print(f"❌ Error processing manual file: {e}")
        raise

def send_completion_notification(**context):
    """Send notification that file processing is complete"""
    ti = context['task_instance']
    results = ti.xcom_pull(task_ids='process_manual_file', key='analysis_results')
    
    print("📧 File Processing Completion Notification")
    print("=" * 50)
    
    if results:
        print(f"✅ File successfully processed!")
        print(f"📁 File: {results['file_path']}")
        print(f"📊 Statistics:")
        print(f"   - Lines: {results['lines']}")
        print(f"   - Words: {results['words']}")
        print(f"   - Characters: {results['characters']}")
        print(f"⏰ Processed at: {results['processed_at']}")
    else:
        print("⚠️ No processing results found")
    
    print("=" * 50)
    print("🎉 FileSensor workflow completed successfully!")

# Create the DAG
dag = DAG(
    'file_sensor_manual',
    default_args=default_args,
    description='Manual FileSensor - create files yourself to test',
    schedule=None,  # Manual trigger only
    catchup=False,
    tags=['learning', 'sensor', 'manual']
)

# FileSensor - Wait for manually created file
wait_for_manual_file = FileSensor(
    task_id='wait_for_manual_file',
    filepath='/opt/airflow/dags/test_files/manual_data.txt',
    poke_interval=15,  # Check every 15 seconds
    timeout=600,  # Timeout after 10 minutes
    dag=dag
)

# Process the manually created file
process_manual_file = PythonOperator(
    task_id='process_manual_file',
    python_callable=process_manual_file,
    dag=dag
)

# Send completion notification
completion_notification = PythonOperator(
    task_id='completion_notification',
    python_callable=send_completion_notification,
    dag=dag
)

# Define task dependencies
wait_for_manual_file >> process_manual_file >> completion_notification