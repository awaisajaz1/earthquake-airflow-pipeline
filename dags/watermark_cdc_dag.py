from datetime import datetime, timedelta
import random
from airflow import DAG
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def generate_mock_data(**context):
    """
    Generates mock orders in the source table.
    Simulates new orders and updates to existing orders.
    """
    pg_hook = PostgresHook(postgres_conn_id='earth_quake')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()
    
    # generate 5-10 random orders
    num_orders = random.randint(5, 10)
    
    for _ in range(num_orders):
        order_id = random.randint(1000, 1050) # Small range to force updates/collisions
        amount = round(random.uniform(10.0, 500.0), 2)
        status = random.choice(['PENDING', 'SHIPPED', 'DELIVERED', 'CANCELLED'])
        
        # Insert or Update (Simulating the operational system application logic)
        # In a real source, this would just be an INSERT/UPDATE application event.
        # We use ON CONFLICT here just to easily simulate "Upsert" in the source system 
        # so we have changing data to capture.
        sql = """
            INSERT INTO source_orders (order_id, status, amount, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (order_id) 
            DO UPDATE SET 
                status = EXCLUDED.status,
                amount = EXCLUDED.amount,
                updated_at = EXCLUDED.updated_at;
        """
        cursor.execute(sql, (order_id, status, amount))
    
    conn.commit()
    cursor.close()
    conn.close()
    print(f"Generated/Updated {num_orders} mock orders.")

def process_incremental_data(**context):
    """
    Performs the CDC logic:
    1. Get last watermark
    2. Extract changed data from source > watermark
    3. Upsert into target
    4. Update watermark
    """
    pg_hook = PostgresHook(postgres_conn_id='earth_quake')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()
    
    # 1. Get last watermark
    cursor.execute("SELECT last_processed_at FROM etl_watermark WHERE job_id = 'orders_etl';")
    row = cursor.fetchone()
    last_watermark = row[0] if row else datetime(1970, 1, 1)
    
    print(f"Last Watermark: {last_watermark}")
    
    # 2. Extract changed data
    extract_sql = """
        SELECT order_id, status, amount, updated_at 
        FROM source_orders 
        WHERE updated_at > %s
        ORDER BY updated_at ASC;
    """
    cursor.execute(extract_sql, (last_watermark,))
    rows = cursor.fetchall()
    
    if not rows:
        print("No new data found.")
        cursor.close()
        conn.close()
        return

    print(f"Found {len(rows)} new/changed records.")
    
    # 3. Upsert into target (SCD Type 1 - Overwrite)
    max_updated_at = last_watermark
    
    for row in rows:
        order_id, status, amount, updated_at = row
        
        # Keep track of the max timestamp for the new watermark
        if updated_at > max_updated_at:
            max_updated_at = updated_at
            
        upsert_sql = """
            INSERT INTO target_orders (order_id, status, amount, updated_at, processed_at)
            VALUES (%s, %s, %s, %s, NOW())
            ON CONFLICT (order_id)
            DO UPDATE SET
                status = EXCLUDED.status,
                amount = EXCLUDED.amount,
                updated_at = EXCLUDED.updated_at,
                processed_at = NOW();
        """
        cursor.execute(upsert_sql, (order_id, status, amount, updated_at))
        
    # 4. Update watermark
    update_watermark_sql = """
        INSERT INTO etl_watermark (job_id, last_processed_at)
        VALUES ('orders_etl', %s)
        ON CONFLICT (job_id)
        DO UPDATE SET last_processed_at = EXCLUDED.last_processed_at;
    """
    cursor.execute(update_watermark_sql, (max_updated_at,))
    
    conn.commit()
    print(f"Successfully processed {len(rows)} records. New Watermark: {max_updated_at}")
    
    cursor.close()
    conn.close()

with DAG(
    'watermark_cdc_dag',
    default_args=default_args,
    description='Demonstrates Watermark-based CDC and Upsert',
    schedule_interval='@daily',
    start_date=days_ago(1),
    catchup=False,
    tags=['learning', 'cdc', 'upsert'],
) as dag:

    # Task 1: Setup Tables
    create_tables = PostgresOperator(
        task_id='create_tables',
        postgres_conn_id='earth_quake',
        sql="""
            -- Source System Table (Simulated)
            CREATE TABLE IF NOT EXISTS source_orders (
                order_id INT PRIMARY KEY,
                status VARCHAR(50),
                amount DECIMAL(10, 2),
                updated_at TIMESTAMP
            );

            -- Target Data Warehouse Table
            CREATE TABLE IF NOT EXISTS target_orders (
                order_id INT PRIMARY KEY,
                status VARCHAR(50),
                amount DECIMAL(10, 2),
                updated_at TIMESTAMP,
                processed_at TIMESTAMP
            );

            -- Watermark Tracking Table
            CREATE TABLE IF NOT EXISTS etl_watermark (
                job_id VARCHAR(50) PRIMARY KEY,
                last_processed_at TIMESTAMP
            );
        """
    )

    # Task 2: Generate Mock Data
    generate_data = PythonOperator(
        task_id='generate_mock_data',
        python_callable=generate_mock_data
    )

    # Task 3: Process Incremental Data (CDC)
    process_data = PythonOperator(
        task_id='process_incremental_data',
        python_callable=process_incremental_data
    )

    create_tables >> generate_data >> process_data
