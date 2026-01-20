"""
Configuration settings for the earthquake data pipeline
Centralized configuration for easy customization
"""

from datetime import timedelta

class EarthquakeConfig:
    """Configuration class for earthquake pipeline"""
    
    # API Configuration
    API_URL = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    API_TIMEOUT = 30
    MIN_MAGNITUDE = 2.5
    MAX_RECORDS = 1000
    TIME_WINDOW_DAYS = 1
    
    # Database Configuration
    POSTGRES_CONN_ID = 'earth_postgres'
    MAIN_TABLE = 'earthquake_data'
    RAW_TABLE = 'raw_data.earthquake_raw'
    SUMMARY_TABLE = 'earthquake_summary'
    ANALYTICS_VIEW = 'analytics.daily_earthquake_stats'
    
    # Data Quality Thresholds
    MIN_REQUIRED_FIELDS = ['id', 'magnitude']
    SIGNIFICANT_MAGNITUDE_THRESHOLD = 5.0
    
    # DAG Configuration
    DAG_ID = 'earthquake_data_pipeline'
    SCHEDULE_INTERVAL = timedelta(hours=6)
    MAX_RETRIES = 2
    RETRY_DELAY = timedelta(minutes=5)
    
    # Logging Configuration
    LOG_LEVEL = 'INFO'
    
    @classmethod
    def get_api_params(cls, start_time, end_time):
        """Get standardized API parameters"""
        return {
            'format': 'geojson',
            'starttime': start_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'endtime': end_time.strftime('%Y-%m-%dT%H:%M:%S'),
            'minmagnitude': cls.MIN_MAGNITUDE,
            'limit': cls.MAX_RECORDS
        }
    
    @classmethod
    def get_database_fields(cls):
        """Get list of database fields for insertion"""
        return [
            'id', 'magnitude', 'place', 'time_occurred', 'updated_time', 'timezone',
            'url', 'detail_url', 'felt', 'cdi', 'mmi', 'alert', 'status', 'tsunami',
            'sig', 'net', 'code', 'ids', 'sources', 'types', 'nst', 'dmin', 'rms',
            'gap', 'magnitude_type', 'type', 'title', 'longitude', 'latitude', 'depth'
        ]