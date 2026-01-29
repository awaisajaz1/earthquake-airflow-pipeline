"""
Simple FileSensor DAG - Learning Example
Waits for a file to appear and then processes it
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

def create_test_file(**context):
    """Create a test file for the sensor to detect"""
    file_path = "/opt/airflow/dags/test_files/data.txt"
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create the test file
    with open(file_path, 'w') as f:
        f.write(f"Test data created at {datetime.now()}\n")
        f.write("This is a simple test file for FileSensor learning\n")
        f.write("File sensor will detect this file and trigger the next task\n")
    
    print(f"✅ Test file created: {file_path}")
    return file_path

def process_detected_file(**context):
    """Process the file after it's detected by the sensor"""
    file_path = "/opt/airflow/dags/test_files/data.txt"
    
    print(f"🔍 Processing detected file: {file_path}")
    
    # Read and display file contents
    try:
        with open(file_path, 'r') as f:
            content = f.read()
            print(f"📄 File contents:\n{content}")
        
        # Simple processing - count lines
        lines = content.strip().split('\n')
        line_count = len(lines)
        
        print(f"📊 File processing results:")
        print(f"  - Lines: {line_count}")
        print(f"  - Characters: {len(content)}")
        print(f"  - File size: {os.path.getsize(file_path)} bytes")
        
        # Push results to XCom
        processing_results = {
            'file_path': file_path,
            'line_count': line_count,
            'character_count': len(content),
            'file_size': os.path.getsize(file_path),
            'processed_at': datetime.now().isoformat()
        }
        
        context['task_instance'].xcom_push(key='processing_results', value=processing_results)
        
        print("✅ File processed successfully!")
        return processing_results
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        raise

def cleanup_test_file(**context):
    """Clean up the test file after processing"""
    file_path = "/opt/airflow/dags/test_files/data.txt"
    
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Test file cleaned up: {file_path}")
        else:
            print(f"⚠️ File not found for cleanup: {file_path}")
            
        # Pull processing results from previous task
        ti = context['task_instance']
        results = ti.xcom_pull(task_ids='process_file', key='processing_results')
        
        if results:
            print(f"📋 Final processing summary:")
            print(f"  - Processed: {results['line_count']} lines")
            print(f"  - Size: {results['file_size']} bytes")
            print(f"  - Completed at: {results['processed_at']}")
        
        print("✅ Cleanup completed!")
        
    except Exception as e:
        print(f"❌ Error during cleanup: {e}")

# Create the DAG
dag = DAG(
    'file_sensor_simple',
    default_args=default_args,
    description='Simple FileSensor learning example',
    schedule=None,  # Manual trigger only
    catchup=False,
    tags=['learning', 'sensor', 'file']
)

# Task 1: Create test file (optional - for testing)
create_file_task = PythonOperator(
    task_id='create_test_file',
    python_callable=create_test_file,
    dag=dag
)

# Task 2: FileSensor - Wait for file to appear
wait_for_file = FileSensor(
    task_id='wait_for_file',
    filepath='/opt/airflow/dags/test_files/data.txt',
    fs_conn_id='fs_default',  # Default filesystem connection
    poke_interval=10,  # Check every 10 seconds
    timeout=300,  # Timeout after 5 minutes
    dag=dag
)

# Task 3: Process the detected file
process_file = PythonOperator(
    task_id='process_file',
    python_callable=process_detected_file,
    dag=dag
)

# Task 4: Cleanup
cleanup_file = PythonOperator(
    task_id='cleanup_file',
    python_callable=cleanup_test_file,
    dag=dag
)

# Define task dependencies
create_file_task >> wait_for_file >> process_file >> cleanup_file