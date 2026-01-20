"""
Earthquake ETL Functions

This module contains all the ETL logic for the earthquake data pipeline.
Separated from the DAG for better code organization and reusability.

Author: Data Engineering Tutorial
"""

from datetime import datetime, timedelta
import json
import logging
import pandas as pd
import requests
from typing import Dict, List, Any

from airflow.providers.postgres.hooks.postgres import PostgresHook

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class EarthquakeETL:
    """Class containing all ETL operations for earthquake data"""
    
    def __init__(self):
        self.api_url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
        self.postgres_conn_id = 'earth_postgres'
    
    def extract_earthquake_data(self, **context) -> Dict[str, Any]:
        """
        Extract earthquake data from USGS API
        
        XCom Push: Pushes raw earthquake data to be used by downstream tasks
        """
        logger.info("Starting earthquake data extraction...")
        
        # Calculate time window - last 24 hours
        end_time = datetime.utcnow()
        start_time = end_time - timedelta(days=1)
        
        # API parameters
        params = {
            'format': 'geojson',
            'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'minmagnitude': 2.5,
            'limit': 1000
        }
        
        try:
            logger.info(f"Fetching data from {self.api_url} with params: {params}")
            response = requests.get(self.api_url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            earthquake_count = len(data.get('features', []))
            
            logger.info(f"Successfully extracted {earthquake_count} earthquake records")
            
            # XCom Push: Store raw data for next task
            context['task_instance'].xcom_push(
                key='raw_earthquake_data', 
                value=data
            )
            context['task_instance'].xcom_push(
                key='extraction_metadata', 
                value={
                    'extraction_time': datetime.utcnow().isoformat(),
                    'record_count': earthquake_count,
                    'api_endpoint': self.api_url,
                    'time_range': f"{start_time.isoformat()} to {end_time.isoformat()}"
                }
            )
            
            return f"Extracted {earthquake_count} earthquake records"
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching earthquake data: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during extraction: {str(e)}")
            raise

    def transform_earthquake_data(self, **context) -> Dict[str, Any]:
        """
        Transform and clean earthquake data
        
        XCom Pull: Gets raw data from extract task
        XCom Push: Pushes cleaned data for loading task
        """
        logger.info("Starting earthquake data transformation...")
        
        # XCom Pull: Get raw data from previous task
        raw_data = context['task_instance'].xcom_pull(
            key='raw_earthquake_data', 
            task_ids='extract_earthquake_data'
        )
        
        if not raw_data or 'features' not in raw_data:
            raise ValueError("No earthquake data received from extraction task")
        
        features = raw_data['features']
        logger.info(f"Processing {len(features)} earthquake records...")
        
        # Transform data into structured format
        transformed_records = []
        
        for feature in features:
            try:
                properties = feature.get('properties', {})
                geometry = feature.get('geometry', {})
                coordinates = geometry.get('coordinates', [None, None, None])
                
                # Clean and validate data
                record = self._create_earthquake_record(feature, properties, coordinates)
                
                # Data quality checks
                if record['id'] and record['magnitude'] is not None:
                    transformed_records.append(record)
                else:
                    logger.warning(f"Skipping record with missing critical data: {record['id']}")
                    
            except Exception as e:
                logger.warning(f"Error processing earthquake record: {str(e)}")
                continue
        
        # Create DataFrame for additional cleaning
        df = pd.DataFrame(transformed_records)
        
        if df.empty:
            logger.warning("No valid records after transformation")
            return "No valid records to process"
        
        # Perform data cleaning
        cleaned_df = self._clean_earthquake_data(df)
        cleaned_records = cleaned_df.to_dict('records')
        
        logger.info(f"Transformation completed. {len(cleaned_records)} clean records ready for loading")
        
        # XCom Push: Store cleaned data for loading task
        context['task_instance'].xcom_push(
            key='cleaned_earthquake_data', 
            value=cleaned_records
        )
        
        # Push transformation summary
        transformation_summary = self._create_transformation_summary(features, cleaned_records, cleaned_df)
        context['task_instance'].xcom_push(
            key='transformation_summary', 
            value=transformation_summary
        )
        
        return f"Transformed {len(cleaned_records)} earthquake records"

    def load_earthquake_data(self, **context) -> str:
        """
        Load cleaned earthquake data into PostgreSQL (earth database)
        
        XCom Pull: Gets cleaned data from transform task
        """
        logger.info("Starting earthquake data loading...")
        
        # XCom Pull: Get cleaned data from previous task
        cleaned_data = context['task_instance'].xcom_pull(
            key='cleaned_earthquake_data', 
            task_ids='transform_earthquake_data'
        )
        
        if not cleaned_data:
            logger.warning("No cleaned data received from transformation task")
            return "No data to load"
        
        # Get PostgreSQL connection to earth database
        postgres_hook = PostgresHook(postgres_conn_id=self.config.POSTGRES_CONN_ID)
        
        try:
            # Load main earthquake data
            self._load_main_earthquake_data(postgres_hook, cleaned_data)
            
            # Load raw data for audit purposes
            self._load_raw_audit_data(postgres_hook, context)
            
            logger.info(f"Successfully loaded {len(cleaned_data)} earthquake records")
            
            # Store loading summary in XCom
            context['task_instance'].xcom_push(
                key='loading_summary',
                value={
                    'records_loaded': len(cleaned_data),
                    'loading_time': datetime.utcnow().isoformat(),
                    'table_name': 'earthquake_data',
                    'database': 'earth'
                }
            )
            
            return f"Loaded {len(cleaned_data)} earthquake records into PostgreSQL earth database"
            
        except Exception as e:
            logger.error(f"Error loading data into PostgreSQL: {str(e)}")
            raise

    def validate_and_summarize(self, **context) -> str:
        """
        Validate loaded data and create summary statistics
        
        XCom Pull: Gets summaries from previous tasks for validation
        """
        logger.info("Starting data validation and summarization...")
        
        # Get PostgreSQL connection to earth database
        postgres_hook = PostgresHook(postgres_conn_id=self.postgres_conn_id)
        
        try:
            # Run validation queries
            validation_results = self._run_validation_queries(postgres_hook)
            
            # Create summary record
            self._create_summary_record(postgres_hook, validation_results)
            
            # Refresh materialized view for analytics
            postgres_hook.run("REFRESH MATERIALIZED VIEW analytics.daily_earthquake_stats")
            
            # Store validation results in XCom
            context['task_instance'].xcom_push(
                key='validation_results',
                value=validation_results
            )
            
            mag_stats = validation_results['magnitude_stats']
            avg_mag = round(mag_stats[2], 2) if mag_stats[2] else 0
            
            logger.info("Data validation and summarization completed successfully")
            return f"Validation completed. Processed {mag_stats[3]} records with avg magnitude {avg_mag}"
            
        except Exception as e:
            logger.error(f"Error during validation: {str(e)}")
            raise

    # Private helper methods
    def _create_earthquake_record(self, feature: Dict, properties: Dict, coordinates: List) -> Dict:
        """Create a standardized earthquake record"""
        return {
            'id': feature.get('id'),
            'magnitude': properties.get('mag'),
            'place': properties.get('place', '').strip() if properties.get('place') else None,
            'time_occurred': pd.to_datetime(properties.get('time'), unit='ms', utc=True) if properties.get('time') else None,
            'updated_time': pd.to_datetime(properties.get('updated'), unit='ms', utc=True) if properties.get('updated') else None,
            'timezone': properties.get('tz'),
            'url': properties.get('url'),
            'detail_url': properties.get('detail'),
            'felt': properties.get('felt'),
            'cdi': properties.get('cdi'),
            'mmi': properties.get('mmi'),
            'alert': properties.get('alert'),
            'status': properties.get('status'),
            'tsunami': properties.get('tsunami'),
            'sig': properties.get('sig'),
            'net': properties.get('net'),
            'code': properties.get('code'),
            'ids': properties.get('ids'),
            'sources': properties.get('sources'),
            'types': properties.get('types'),
            'nst': properties.get('nst'),
            'dmin': properties.get('dmin'),
            'rms': properties.get('rms'),
            'gap': properties.get('gap'),
            'magnitude_type': properties.get('magType'),
            'type': properties.get('type'),
            'title': properties.get('title'),
            'longitude': coordinates[0] if len(coordinates) > 0 else None,
            'latitude': coordinates[1] if len(coordinates) > 1 else None,
            'depth': coordinates[2] if len(coordinates) > 2 else None,
        }

    def _is_valid_record(self, record: Dict) -> bool:
        """Check if record has required fields"""
        return record.get('id') and record.get('magnitude') is not None

    def _clean_earthquake_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate earthquake data"""
        logger.info("Performing data cleaning operations...")
        
        # Remove duplicates
        initial_count = len(df)
        df = df.drop_duplicates(subset=['id'])
        logger.info(f"Removed {initial_count - len(df)} duplicate records")
        
        # Clean magnitude data
        df['magnitude'] = pd.to_numeric(df['magnitude'], errors='coerce')
        df = df[df['magnitude'].notna()]  # Remove records with invalid magnitude
        
        # Clean location data
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df['depth'] = pd.to_numeric(df['depth'], errors='coerce')
        
        # Clean place names
        df['place'] = df['place'].str.strip()
        df['place'] = df['place'].replace('', None)
        
        return df

    def _create_transformation_summary(self, features: List, cleaned_records: List, df: pd.DataFrame) -> Dict:
        """Create transformation summary statistics"""
        return {
            'original_count': len(features),
            'cleaned_count': len(cleaned_records),
            'records_removed': len(features) - len(cleaned_records),
            'transformation_time': datetime.utcnow().isoformat(),
            'magnitude_range': {
                'min': float(df['magnitude'].min()),
                'max': float(df['magnitude'].max()),
                'avg': float(df['magnitude'].mean())
            } if not df.empty else None
        }

    def _load_main_earthquake_data(self, postgres_hook: PostgresHook, cleaned_data: List[Dict]):
        """Load main earthquake data into the database"""
        logger.info(f"Loading {len(cleaned_data)} records into PostgreSQL earth database...")
        
        postgres_hook.insert_rows(
            table='earthquake_data',
            rows=cleaned_data,
            target_fields=[
                'id', 'magnitude', 'place', 'time_occurred', 'updated_time', 'timezone',
                'url', 'detail_url', 'felt', 'cdi', 'mmi', 'alert', 'status', 'tsunami',
                'sig', 'net', 'code', 'ids', 'sources', 'types', 'nst', 'dmin', 'rms',
                'gap', 'magnitude_type', 'type', 'title', 'longitude', 'latitude', 'depth'
            ],
            replace=True
        )

    def _load_raw_audit_data(self, postgres_hook: PostgresHook, context: Dict):
        """Load raw data for audit purposes"""
        raw_data = context['task_instance'].xcom_pull(
            key='raw_earthquake_data', 
            task_ids='extract_earthquake_data'
        )
        
        if raw_data:
            postgres_hook.run(
                "INSERT INTO raw_data.earthquake_raw (raw_json) VALUES (%s)",
                parameters=[json.dumps(raw_data)]
            )

    def _run_validation_queries(self, postgres_hook: PostgresHook) -> Dict:
        """Run validation queries and return results"""
        validation_queries = {
            'total_records': "SELECT COUNT(*) FROM earthquake_data",
            'recent_records': """
                SELECT COUNT(*) FROM earthquake_data 
                WHERE created_at >= CURRENT_DATE
            """,
            'magnitude_stats': """
                SELECT 
                    MIN(magnitude) as min_mag,
                    MAX(magnitude) as max_mag,
                    AVG(magnitude) as avg_mag,
                    COUNT(*) as total_count
                FROM earthquake_data 
                WHERE created_at >= CURRENT_DATE
            """,
            'significant_earthquakes': """
                SELECT COUNT(*) FROM earthquake_data 
                WHERE magnitude >= 5.0 AND created_at >= CURRENT_DATE
            """
        }
        
        validation_results = {}
        for query_name, query in validation_queries.items():
            result = postgres_hook.get_first(query)
            validation_results[query_name] = result
            logger.info(f"{query_name}: {result}")
        
        return validation_results

    def _create_summary_record(self, postgres_hook: PostgresHook, validation_results: Dict):
        """Create summary record in the database"""
        mag_stats = validation_results['magnitude_stats']
        summary_insert = f"""
        INSERT INTO {self.config.SUMMARY_TABLE} (
            date_processed, total_earthquakes, max_magnitude, 
            min_magnitude, avg_magnitude, significant_earthquakes
        ) VALUES (%s, %s, %s, %s, %s, %s)
        """
        
        postgres_hook.run(summary_insert, parameters=[
            datetime.utcnow().date(),
            mag_stats[3],  # total_count
            mag_stats[1],  # max_mag
            mag_stats[0],  # min_mag
            round(mag_stats[2], 2) if mag_stats[2] else 0,  # avg_mag
            validation_results['significant_earthquakes'][0]
        ])


# Create a global instance for easy import
earthquake_etl = EarthquakeETL()