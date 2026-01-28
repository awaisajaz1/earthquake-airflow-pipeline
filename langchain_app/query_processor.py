"""
Query Processor - Orchestrates LLM and Database interactions
"""

import logging
from typing import Dict, Any, List
import re

logger = logging.getLogger(__name__)

class QueryProcessor:
    """Processes natural language queries using LLM and database"""
    
    def __init__(self, db_manager, llm_handler):
        self.db_manager = db_manager
        self.llm_handler = llm_handler
        
    async def process_query(self, question: str, include_explanation: bool = True) -> Dict[str, Any]:
        """Process a natural language query end-to-end"""
        try:
            logger.info(f"🔄 Processing query: {question}")
            
            # Get database schema
            schema_description = self.db_manager.get_schema_description()
            
            # Generate SQL query using LLM
            llm_result = await self.llm_handler.generate_sql_query(question, schema_description)
            
            if not llm_result["success"]:
                return {
                    "sql_query": "",
                    "results": [],
                    "error": f"Failed to generate SQL: {llm_result.get('error', 'Unknown error')}"
                }
            
            sql_query = llm_result["sql_query"]
            
            # Validate and sanitize SQL query
            sanitized_query = self._sanitize_sql_query(sql_query)
            
            if not sanitized_query:
                return {
                    "sql_query": sql_query,
                    "results": [],
                    "error": "Generated SQL query appears to be unsafe or invalid"
                }
            
            # Execute the query
            try:
                results = await self.db_manager.execute_query(sanitized_query)
            except Exception as e:
                logger.error(f"❌ Query execution failed: {e}")
                return {
                    "sql_query": sanitized_query,
                    "results": [],
                    "error": f"Query execution failed: {str(e)}"
                }
            
            # Generate explanation if requested
            explanation = None
            if include_explanation:
                try:
                    explanation = await self.llm_handler.explain_query(question, sanitized_query, results)
                except Exception as e:
                    logger.warning(f"⚠️ Explanation generation failed: {e}")
                    explanation = "Explanation not available"
            
            logger.info(f"✅ Query processed successfully, returned {len(results)} results")
            
            return {
                "sql_query": sanitized_query,
                "results": results,
                "explanation": explanation
            }
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}")
            return {
                "sql_query": "",
                "results": [],
                "error": f"Query processing failed: {str(e)}"
            }
    
    def _sanitize_sql_query(self, sql_query: str) -> str:
        """Sanitize and validate SQL query for safety"""
        try:
            # Remove any potential SQL injection patterns
            sql_query = sql_query.strip()
            
            # Basic validation - must start with SELECT (read-only queries)
            if not sql_query.upper().strip().startswith('SELECT'):
                logger.warning("⚠️ Non-SELECT query blocked for safety")
                return ""
            
            # Remove dangerous keywords
            dangerous_keywords = [
                'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
                'TRUNCATE', 'EXEC', 'EXECUTE', 'DECLARE', 'CURSOR'
            ]
            
            upper_query = sql_query.upper()
            for keyword in dangerous_keywords:
                if keyword in upper_query:
                    logger.warning(f"⚠️ Dangerous keyword '{keyword}' found in query")
                    return ""
            
            # Ensure query ends with semicolon
            if not sql_query.endswith(';'):
                sql_query += ';'
            
            # Add LIMIT if not present (safety measure)
            if 'LIMIT' not in upper_query and 'COUNT(' not in upper_query:
                sql_query = sql_query.rstrip(';') + ' LIMIT 100;'
            
            return sql_query
            
        except Exception as e:
            logger.error(f"❌ SQL sanitization failed: {e}")
            return ""
    
    def get_sample_queries(self) -> List[Dict[str, str]]:
        """Get sample queries for testing"""
        return [
            {
                "question": "Show me all earthquakes with magnitude greater than 7",
                "description": "Find high-magnitude earthquakes from the silver layer"
            },
            {
                "question": "What's the average magnitude of earthquakes?",
                "description": "Calculate average magnitude from processed data"
            },
            {
                "question": "Find the strongest earthquake recorded",
                "description": "Get the earthquake with maximum magnitude"
            },
            {
                "question": "How many earthquakes happened yesterday?",
                "description": "Count earthquakes from recent data"
            },
            {
                "question": "Show me earthquakes in California",
                "description": "Filter earthquakes by location"
            },
            {
                "question": "What's the latest data in the gold layer?",
                "description": "Get recent summary statistics"
            },
            {
                "question": "Show me critical earthquake events",
                "description": "Query the critical events table"
            },
            {
                "question": "Give me earthquake statistics by day",
                "description": "Daily aggregated earthquake data"
            }
        ]