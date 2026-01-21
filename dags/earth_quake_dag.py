# Task1: Fetch amazon data, clean and transform it, load to postgres database
# operators: PythonOperator, PostgresOperator
# hooks: allows connection to postgres

from airflow import DAG
from datetime import datetime, timedelta
import json
import requests

from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook


# 1
def fetch_earth_quake_data(ti):
    url = 'https://earthquake.usgs.gov/fdsnws/event/1/query'
    params = {
        "format": "geojson",
        "starttime": (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S"),
        "endtime": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        "minmagnitude": 2.5,
        "limit": 100  # limit for example, can be adjusted
    }

    response = requests.get(url, params=params)
    response.raise_for_status()

    # now convert the responce to json data type 
    data = response.json()

    # extract the features (earthquake events) from the geojson data
    records = []
    for feature in data['features']:
        earthquake_id = feature['id']
        # extract the properties and geometry from each feature
        properties = feature['properties']
        geometry = feature['geometry']

        # extract the relevant fields from properties
        place = properties['place']
        magnitude = properties['mag']
        time = properties['time']

        # extract the coordinates from geometry
        coordinates = geometry['coordinates']

        record = {
            'id': earthquake_id,
            'place': place,
            'magnitude': magnitude,
            'time': datetime.utcfromtimestamp(time/1000).strftime('%Y-%m-%d %H:%M:%S') if time else None,
            'longitude': coordinates[0],
            'latitude': coordinates[1],
            'depth': coordinates[2]
        }

        records.append(record)

        print("The Earth Quake data has been extracted!")

    # df = pd.Dataframe(records)
    ti.xcom_push(key='earth_quake_data', value=records)


# 2 Insert data to postgres with minor cleansing
def insert_earthquake_data_to_postgres(ti):
    earthquake_data = ti.xcom_pull(key='earth_quake_data', task_ids='fetch_earth_quake_data')

    if not earthquake_data:
        raise ValueError("No earthquake data found")

    postgres_hook = PostgresHook(postgres_conn_id='earth_quake')

    create_table = """CREATE TABLE IF NOT EXISTS earth_quake_data (
        id VARCHAR(255) PRIMARY KEY,
        place VARCHAR(255),
        magnitude FLOAT,
        time TIMESTAMP,
        longitude FLOAT,
        latitude FLOAT,
        depth FLOAT
    );
    """
    # execute create script
    postgres_hook.run(create_table)
    
    # insert records
    insert_query = """
            INSERT INTO earth_quake_data (id, place, magnitude, time, longitude, latitude, depth)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
    for row in earthquake_data:
        postgres_hook.run(insert_query, parameters=(
            row['id'],
            row['place'],
            row['magnitude'],
            row['time'],
            row['longitude'],
            row['latitude'],
            row['depth']
        ))



default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime(2024, 6, 20),
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# Simple DAG definition
dag = DAG(
    dag_id='fetch_earth_quake_api_data',
    default_args=default_args,
    start_date=datetime(2026, 1, 21),
    schedule=timedelta(days=1),
    description='DAG for earth quakes api to store in postgres',
    catchup=False
)

fetch_earthquake_data = PythonOperator(
    task_id='fetch_earth_quake_data',
    python_callable=fetch_earth_quake_data,
    dag=dag,
)



insert_earthquake_data = PythonOperator(
    task_id='insert_earth_quake_data_to_postgres',
    python_callable=insert_earthquake_data_to_postgres,
    dag=dag,
)


# set dependecies
fetch_earthquake_data >> insert_earthquake_data