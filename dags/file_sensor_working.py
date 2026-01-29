"""
Working FileSensor DAG - Simple file monitoring
Uses PythonSensor to avoid connection issues
"""

from airflow import DAG
from airflow.providers.standard.operators.python import PythonOperator
from airflow.providers.standard.sensors.python import PythonSensor
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

def create_test_file(**context):
    """Create a test file for the sensor to detect"""
    file_path = "/opt/airflow/dags/test_files/sensor_test.txt"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create the test file
    with open(file_path, 'w') as f:
        f.write(f"Test file created at {datetime.now()}\n")
        f.write("This file will be detected by our PythonSensor\n")
        f.write("Learning Airflow sensors step by step!\n")
    
    print(f"✅ Test file created: {file_path}")
    return file_path

def check_for_test_file(**context):
    """Check if test file exists - PythonSensor callable"""
    file_path = "/opt/airflow/dags/test_files/sensor_test.txt"
    
    exists = os.path.exists(file_path)
    
    if exists:
        print(f"🎉 File detected: {file_path}")
        size = os.path.getsize(file_path)
        print(f"📊 File size: {size} bytes")
    else:
        print(f"⏳ Waiting for file: {file_path}")
    
    return exists

def process_detected_file(**context):
    """Process the file after it's detected"""
    file_path = "/opt/airflow/dags/test_files/sensor_test.txt"
    
    print(f"🔍 Processing detected file: {file_path}")
    
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            print(f"📄 File contents:\n{content}")
        
        # Simple processing
        lines = content.strip().split('\n')
        words = content.split()
        
        results = {
            'file_path': file_path,
            'lines': len(lines),
            'words': len(words),
            'characters': len(content),
            'processed_at': datetime.now().isoformat()
        }
        
        print(f"📊 Processing results:")
        print(f"  - Lines: {results['lines']}")
        print(f"  - Words: {results['words']}")
        print(f"  - Characters: {results['characters']}")
        
        # Push to XCom
        context['task_instance'].xcom_push(key='processing_results', value=results)
        
        print("✅ File processed successfully!")
        return results
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        raise

def cleanup_and_summary(**context):
    """Clean up and show summary"""
    file_path = "/opt/airflow/dags/test_files/sensor_test.txt"
    
    # Get processing results
    ti = context['task_instance']
    results = ti.xcom_pull(task_ids='process_detected_file', key='processing_results')
    
    print("🎉 File Sensor Workflow Complete!")
    print("=" * 50)
    
    if results:
        print(f"✅ Successfully processed: {results['file_path']}")
        print(f"📊 Statistics:")
        print(f"   - Lines: {results['lines']}")
        print(f"   - Words: {results['words']}")
        print(f"   - Characters: {results['characters']}")
        print(f"⏰ Processed at: {results['processed_at']}")
    
    # Clean up the test file
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Test file cleaned up: {file_path}")
    except Exception as e:
        print(f"⚠️ Cleanup warning: {e}")
    
    print("=" * 50)
    print("🎓 FileSensor learning completed successfully!")

# Create the DAG
dag = DAG(
    'file_sensor_working',
    default_args=default_args,
    description='Working File Sensor using PythonSensor - no connection issues',
    schedule=None,  # Manual trigger only
    catchup=False,
    tags=['learning', 'sensor', 'working', 'python-sensor']
)

# Task 1: Create test file
create_file = PythonOperator(
    task_id='create_test_file',
    python_callable=create_test_file,
    dag=dag
)

# Task 2: PythonSensor - Wait for file (no connection needed!)
wait_for_file = PythonSensor(
    task_id='wait_for_file',
    python_callable=check_for_test_file,
    poke_interval=10,  # Check every 10 seconds
    timeout=300,  # Timeout after 5 minutes
    dag=dag
)

# Task 3: Process the detected file
process_file = PythonOperator(
    task_id='process_detected_file',
    python_callable=process_detected_file,
    dag=dag
)

# Task 4: Cleanup and summary
cleanup_summary = PythonOperator(
    task_id='cleanup_and_summary',
    python_callable=cleanup_and_summary,
    dag=dag
)

# Define task dependencies
create_file >> wait_for_file >> process_file >> cleanup_summary