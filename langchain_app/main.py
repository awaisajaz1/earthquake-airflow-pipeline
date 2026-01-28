"""
LangChain API for Natural Language Database Queries
Connects to your existing PostgreSQL database with earthquake data
"""

import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uvicorn

from database import DatabaseManager
from llm_handler import LLMHandler
from query_processor import QueryProcessor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Earthquake Data LLM API",
    description="Natural language interface to query earthquake data using local LLM",
    version="1.0.0"
)

# Global instances
db_manager = None
llm_handler = None
query_processor = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    global db_manager, llm_handler, query_processor
    
    try:
        logger.info("🚀 Starting Earthquake Data LLM API...")
        
        # Initialize database manager
        db_manager = DatabaseManager()
        await db_manager.initialize()
        
        # Initialize LLM handler
        llm_handler = LLMHandler()
        await llm_handler.initialize()
        
        # Initialize query processor
        query_processor = QueryProcessor(db_manager, llm_handler)
        
        logger.info("✅ All services initialized successfully!")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("🛑 Shutting down services...")
    if db_manager:
        await db_manager.close()

# Request/Response models
class QueryRequest(BaseModel):
    question: str
    include_explanation: bool = True

class QueryResponse(BaseModel):
    question: str
    sql_query: str
    results: List[Dict[str, Any]]
    explanation: Optional[str] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    database: str
    llm: str
    services: Dict[str, str]

# API Endpoints
@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    try:
        # Check database connection
        db_status = "healthy" if db_manager and await db_manager.check_connection() else "unhealthy"
        
        # Check LLM connection
        llm_status = "healthy" if llm_handler and await llm_handler.check_connection() else "unhealthy"
        
        overall_status = "healthy" if db_status == "healthy" and llm_status == "healthy" else "unhealthy"
        
        return HealthResponse(
            status=overall_status,
            database=db_status,
            llm=llm_status,
            services={
                "database": db_status,
                "llm": llm_status,
                "query_processor": "healthy" if query_processor else "unhealthy"
            }
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_database(request: QueryRequest):
    """
    Process natural language query and return results
    
    Example queries:
    - "Show me all earthquakes with magnitude greater than 7"
    - "What's the average magnitude of earthquakes in the last month?"
    - "Find the strongest earthquake recorded"
    """
    try:
        if not query_processor:
            raise HTTPException(status_code=503, detail="Query processor not initialized")
        
        logger.info(f"Processing query: {request.question}")
        
        # Process the natural language query
        result = await query_processor.process_query(
            question=request.question,
            include_explanation=request.include_explanation
        )
        
        return QueryResponse(
            question=request.question,
            sql_query=result["sql_query"],
            results=result["results"],
            explanation=result.get("explanation"),
            error=result.get("error")
        )
        
    except Exception as e:
        logger.error(f"Query processing failed: {e}")
        return QueryResponse(
            question=request.question,
            sql_query="",
            results=[],
            error=str(e)
        )

@app.get("/schema")
async def get_database_schema():
    """Get database schema information"""
    try:
        if not db_manager:
            raise HTTPException(status_code=503, detail="Database manager not initialized")
        
        schema = await db_manager.get_schema_info()
        return {"schema": schema}
        
    except Exception as e:
        logger.error(f"Schema retrieval failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/sample-queries")
async def get_sample_queries():
    """Get sample queries for testing"""
    return {
        "sample_queries": [
            "Show me all earthquakes with magnitude greater than 7",
            "What's the average magnitude of earthquakes?",
            "Find the strongest earthquake recorded",
            "How many earthquakes happened yesterday?",
            "Show me earthquakes in the bronze layer",
            "What's the latest data in the silver layer?",
            "Give me a summary from the gold layer",
            "Show me critical earthquake events",
            "What's the count of normal vs critical earthquakes?"
        ]
    }

if __name__ == "__main__":
    # Get configuration from environment
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8001))
    
    logger.info(f"🌟 Starting server on {host}:{port}")
    
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=False,
        log_level="info"
    )