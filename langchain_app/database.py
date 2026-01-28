"""
Database Manager for PostgreSQL connection and schema management
"""

import os
import logging
from typing import Dict, List, Any, Optional
import asyncio
import psycopg2
from psycopg2.extras import RealDictCursor
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.ext.asyncio import create_async_engine

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and schema information"""
    
    def __init__(self):
        # Database URLs from environment
        self.database_url = os.getenv("DATABASE_URL", "postgresql://airflow:airflow@postgres:5432/airflow")
        self.earthquake_db_url = os.getenv("EARTHQUAKE_DB_URL", "postgresql://airflow:airflow@postgres:5432/earth_quake_db")
        
        self.connection = None
        self.schema_cache = None
        
    async def initialize(self):
        """Initialize database connection"""
        try:
            logger.info("🔌 Initializing database connection...")
            
            # Test connection
            await self.check_connection()
            
            # Cache schema information
            await self.refresh_schema_cache()
            
            logger.info("✅ Database manager initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            raise
    
    async def check_connection(self) -> bool:
        """Check if database connection is healthy"""
        try:
            # Use synchronous connection for simplicity
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    async def refresh_schema_cache(self):
        """Refresh cached schema information"""
        try:
            logger.info("🔄 Refreshing schema cache...")
            
            # Create synchronous engine for schema inspection
            engine = create_engine(self.database_url)
            inspector = inspect(engine)
            
            schema_info = {}
            
            # Get all schemas
            schemas = inspector.get_schema_names()
            logger.info(f"Found schemas: {schemas}")
            
            for schema in schemas:
                if schema in ['information_schema', 'pg_catalog', 'pg_toast']:
                    continue
                    
                schema_info[schema] = {}
                tables = inspector.get_table_names(schema=schema)
                
                for table in tables:
                    columns = inspector.get_columns(table, schema=schema)
                    schema_info[schema][table] = {
                        'columns': [
                            {
                                'name': col['name'],
                                'type': str(col['type']),
                                'nullable': col['nullable'],
                                'default': col.get('default')
                            }
                            for col in columns
                        ]
                    }
            
            self.schema_cache = schema_info
            logger.info(f"✅ Schema cache refreshed with {len(schema_info)} schemas")
            
        except Exception as e:
            logger.error(f"❌ Schema cache refresh failed: {e}")
            self.schema_cache = {}
    
    async def get_schema_info(self) -> Dict[str, Any]:
        """Get cached schema information"""
        if not self.schema_cache:
            await self.refresh_schema_cache()
        return self.schema_cache
    
    async def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results"""
        try:
            logger.info(f"🔍 Executing query: {query[:100]}...")
            
            # Use synchronous connection
            conn = psycopg2.connect(self.database_url)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Fetch results
            if cursor.description:  # SELECT query
                results = [dict(row) for row in cursor.fetchall()]
            else:  # INSERT/UPDATE/DELETE
                results = [{"affected_rows": cursor.rowcount}]
            
            cursor.close()
            conn.close()
            
            logger.info(f"✅ Query executed successfully, returned {len(results)} rows")
            return results
            
        except Exception as e:
            logger.error(f"❌ Query execution failed: {e}")
            raise
    
    def get_schema_description(self) -> str:
        """Get human-readable schema description for LLM"""
        if not self.schema_cache:
            return "Schema information not available"
        
        description = "Database Schema:\n\n"
        
        for schema_name, tables in self.schema_cache.items():
            description += f"Schema: {schema_name}\n"
            
            for table_name, table_info in tables.items():
                description += f"  Table: {table_name}\n"
                
                for column in table_info['columns']:
                    nullable = "NULL" if column['nullable'] else "NOT NULL"
                    description += f"    - {column['name']}: {column['type']} ({nullable})\n"
                
                description += "\n"
        
        # Add specific information about earthquake data structure
        description += """
Key Tables for Earthquake Data:
- bronze.bronze_earthquake_raw: Raw earthquake data from API
- silver.silver_earthquake: Processed earthquake data with individual records
- gold.earthquake_summary: Aggregated daily earthquake statistics
- gold.critical_earthquake_events: Critical earthquake alerts (magnitude >= 7.0)
- gold.normal_earthquake_log: Normal earthquake processing logs

Common Queries:
- Use silver.silver_earthquake for individual earthquake details
- Use gold.earthquake_summary for daily statistics
- Use gold.critical_earthquake_events for high-magnitude events
"""
        
        return description
    
    async def close(self):
        """Close database connections"""
        logger.info("🔌 Closing database connections...")
        # Cleanup if needed