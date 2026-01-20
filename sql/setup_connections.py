"""
Script to set up Airflow connections for the earthquake pipeline
Run this after Airflow is up and running
"""

from airflow import settings
from airflow.models import Connection
from sqlalchemy.orm import sessionmaker

def create_earth_postgres_connection():
    """Create connection to earth database"""
    
    # Create session
    session = settings.Session()
    
    try:
        # Check if connection already exists
        existing_conn = session.query(Connection).filter(
            Connection.conn_id == 'earth_postgres'
        ).first()
        
        if existing_conn:
            print("Connection 'earth_postgres' already exists. Updating...")
            session.delete(existing_conn)
        
        # Create new connection
        new_conn = Connection(
            conn_id='earth_postgres',
            conn_type='postgres',
            host='postgres',
            schema='earth',
            login='airflow',
            password='airflow',
            port=5432,
            description='PostgreSQL connection to earth database for earthquake data'
        )
        
        session.add(new_conn)
        session.commit()
        print("Successfully created/updated 'earth_postgres' connection")
        
    except Exception as e:
        print(f"Error creating connection: {str(e)}")
        session.rollback()
    finally:
        session.close()

if __name__ == "__main__":
    create_earth_postgres_connection()