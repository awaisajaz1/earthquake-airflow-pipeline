"""
Manual FileSensor DAG - Create files manually to test
This version uses a custom Python sensor to avoid connection issues
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

def check_file_exists(**context):
    """Custom file check function - returns True if file exists"""
    file_path = "/opt/airflow/dags/test_files/manual_data.txt"
    
    exists = os.path.exists(file_path)
    
    if exists:
        print(f"✅ File found: {file_path}")
        # Get file info
        size = os.path.getsize(file_path)
        mtime = os.path.getmtime(file_path)
        print(f"📊 File size: {size} bytes")
        print(f"⏰ Modified: {datetime.fromtimestamp(mtime)}")
    else:
        print(f"⏳ Still waiting for file: {file_path}")
    
    return exists

def process_manual_file(**context):
    """Process manually created file with safe encoding handling"""
    file_path = "/opt/airflow/dags/test_files/manual_data.txt"
    
    print(f"🔍 Processing manually created file: {file_path}")
    
    try:
        # Try to read as text first, with error handling
        content = ""
        encoding_used = "utf-8"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                encoding_used = "utf-8"
        except UnicodeDecodeError:
            print("⚠️ UTF-8 decoding failed, trying with error handling...")
            try:
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                    encoding_used = "utf-8 (with replacements)"
            except Exception:
                print("⚠️ Text reading failed, treating as binary file...")
                with open(file_path, 'rb') as f:
                    binary_content = f.read()
                    content = f"[Binary file - {len(binary_content)} bytes]"
                    encoding_used = "binary"
        
        print(f"📄 File encoding: {encoding_used}")
        
        if encoding_used != "binary":
            print(f"📄 File contents:\n{content}")
            
            # Simple analysis for text files
            lines = content.strip().split('\n') if content.strip() else []
            words = content.split() if content else []
            
            results = {
                'file_path': file_path,
                'encoding': encoding_used,
                'lines': len(lines),
                'words': len(words),
                'characters': len(content),
                'is_binary': False,
                'processed_at': datetime.now().isoformat()
            }
            
            print(f"📊 Analysis results:")
            print(f"  - Encoding: {encoding_used}")
            print(f"  - Lines: {results['lines']}")
            print(f"  - Words: {results['words']}")
            print(f"  - Characters: {results['characters']}")
        else:
            # Binary file handling
            file_size = os.path.getsize(file_path)
            results = {
                'file_path': file_path,
                'encoding': encoding_used,
                'file_size': file_size,
                'is_binary': True,
                'processed_at': datetime.now().isoformat()
            }
            
            print(f"📊 Binary file analysis:")
            print(f"  - File size: {file_size} bytes")
            print(f"  - Type: Binary file")
        
        context['task_instance'].xcom_push(key='analysis_results', value=results)
        
        print("✅ File processed successfully!")
        return results
        
    except Exception as e:
        print(f"❌ Error processing file: {e}")
        
        # Create error result
        error_results = {
            'file_path': file_path,
            'error': str(e),
            'processed_at': datetime.now().isoformat()
        }
        
        context['task_instance'].xcom_push(key='analysis_results', value=error_results)
        
        # Don't raise exception - let the workflow continue
        print("⚠️ Continuing workflow despite processing error...")
        return error_results

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
    description='Manual File Sensor using PythonSensor - create files yourself to test',
    schedule=None,  # Manual trigger only
    catchup=False,
    tags=['learning', 'sensor', 'manual', 'python-sensor']
)

# PythonSensor - Wait for manually created file (no connection needed!)
wait_for_manual_file = PythonSensor(
    task_id='wait_for_manual_file',
    python_callable=check_file_exists,
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