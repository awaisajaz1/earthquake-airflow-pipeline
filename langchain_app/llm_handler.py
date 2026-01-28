"""
LLM Handler for Ollama integration
"""

import os
import logging
import asyncio
from typing import Optional, Dict, Any
import requests
import json

logger = logging.getLogger(__name__)

class LLMHandler:
    """Handles communication with Ollama LLM"""
    
    def __init__(self):
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
        self.model_name = "llama3.2:3b"  # Lightweight model for local use
        self.model_ready = False
        
    async def initialize(self):
        """Initialize LLM connection and pull model if needed"""
        try:
            logger.info("🤖 Initializing LLM handler...")
            
            # Check if Ollama is running
            await self.check_connection()
            
            # Pull model if not available
            await self.ensure_model_available()
            
            logger.info("✅ LLM handler initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ LLM initialization failed: {e}")
            raise
    
    async def check_connection(self) -> bool:
        """Check if Ollama service is available"""
        try:
            response = requests.get(f"{self.ollama_base_url}/api/tags", timeout=10)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Ollama connection check failed: {e}")
            return False
    
    async def ensure_model_available(self):
        """Ensure the model is pulled and available"""
        try:
            logger.info(f"🔄 Checking if model {self.model_name} is available...")
            
            # Check if model exists
            response = requests.get(f"{self.ollama_base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model["name"] for model in models]
                
                if self.model_name in model_names:
                    logger.info(f"✅ Model {self.model_name} is already available")
                    self.model_ready = True
                    return
            
            # Pull model if not available
            logger.info(f"📥 Pulling model {self.model_name}...")
            pull_response = requests.post(
                f"{self.ollama_base_url}/api/pull",
                json={"name": self.model_name},
                timeout=300  # 5 minutes timeout for model pull
            )
            
            if pull_response.status_code == 200:
                logger.info(f"✅ Model {self.model_name} pulled successfully")
                self.model_ready = True
            else:
                raise Exception(f"Failed to pull model: {pull_response.text}")
                
        except Exception as e:
            logger.error(f"❌ Model setup failed: {e}")
            # Try with a smaller model as fallback
            self.model_name = "llama3.2:1b"
            logger.info(f"🔄 Trying fallback model: {self.model_name}")
            raise
    
    async def generate_sql_query(self, question: str, schema_description: str) -> Dict[str, Any]:
        """Generate SQL query from natural language question"""
        try:
            prompt = self._create_sql_prompt(question, schema_description)
            
            logger.info(f"🤖 Generating SQL for: {question}")
            
            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for more deterministic output
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                },
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"LLM request failed: {response.text}")
            
            result = response.json()
            generated_text = result.get("response", "").strip()
            
            # Extract SQL query from response
            sql_query = self._extract_sql_from_response(generated_text)
            
            return {
                "sql_query": sql_query,
                "raw_response": generated_text,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"❌ SQL generation failed: {e}")
            return {
                "sql_query": "",
                "raw_response": "",
                "success": False,
                "error": str(e)
            }
    
    def _create_sql_prompt(self, question: str, schema_description: str) -> str:
        """Create prompt for SQL generation"""
        return f"""You are a SQL expert. Given the database schema and a natural language question, generate a precise SQL query.

Database Schema:
{schema_description}

Rules:
1. Generate ONLY the SQL query, no explanations
2. Use proper PostgreSQL syntax
3. Always use schema.table format (e.g., silver.silver_earthquake)
4. For earthquake data, prefer silver.silver_earthquake for detailed queries
5. Use gold.earthquake_summary for aggregated statistics
6. Limit results to 100 rows unless specifically asked for more
7. Use proper date formatting and filtering

Question: {question}

SQL Query:"""
    
    def _extract_sql_from_response(self, response: str) -> str:
        """Extract SQL query from LLM response"""
        # Remove common prefixes and suffixes
        response = response.strip()
        
        # Look for SQL query patterns
        lines = response.split('\n')
        sql_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Skip explanatory text
            if line.lower().startswith(('here', 'the sql', 'query:', 'answer:')):
                continue
            
            # Look for SQL keywords
            if any(keyword in line.upper() for keyword in ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH']):
                sql_lines.append(line)
            elif sql_lines:  # Continue collecting if we've started
                sql_lines.append(line)
        
        if sql_lines:
            sql_query = ' '.join(sql_lines)
            # Clean up the query
            sql_query = sql_query.replace('```sql', '').replace('```', '').strip()
            return sql_query
        
        # Fallback: return the whole response if no SQL pattern found
        return response.replace('```sql', '').replace('```', '').strip()
    
    async def explain_query(self, question: str, sql_query: str, results: list) -> str:
        """Generate explanation for the query and results"""
        try:
            prompt = f"""Explain this database query in simple terms:

Question: {question}
SQL Query: {sql_query}
Number of results: {len(results)}

Provide a brief, clear explanation of what the query does and what the results show."""

            response = requests.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "max_tokens": 200
                    }
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                return "Explanation not available"
                
        except Exception as e:
            logger.error(f"❌ Explanation generation failed: {e}")
            return "Explanation not available"