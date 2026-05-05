"""Phase 1: Semantic Knowledge Layer - Text-to-SQL Engine (Simplified)"""

import logging
from typing import Any, Dict, List, Optional

from langchain.sql_database import SQLDatabase
from pydantic import BaseModel, Field
from sqlalchemy.pool import StaticPool

logger = logging.getLogger(__name__)


class SQLQueryRequest(BaseModel):
    """Request model for SQL queries."""
    query: str = Field(..., description="SQL query or question about ET records")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class SQLQueryResponse(BaseModel):
    """Response model for SQL query results."""
    sql_query: str = Field(..., description="SQL query executed")
    results: List[Dict[str, Any]] = Field(..., description="Query results")
    natural_response: str = Field(..., description="Summary of results")
    error: Optional[str] = Field(default=None, description="Error message if query failed")


class SQLQueryEngine:
    """
    Simple SQL Query Engine for Ovulite Semantic Knowledge Layer
    
    Direct SQL queries without LLM translation.
    Use pass raw SQL queries for data exploration.
    """
    
    def __init__(self, database_url: str):
        """
        Initialize the SQL Query Engine.
        
        Args:
            database_url: PostgreSQL connection string
        """
        self.database_url = database_url
        
        # Initialize SQLDatabase
        self.db = SQLDatabase.from_uri(
            database_url,
            schema="public",
            include_tables=[
                "et_transfers",
                "predictions",
                "embryos",
                "recipients",
                "technicians",
                "protocols",
            ]
        )
        
        logger.info("SQL Query Engine initialized (simplified mode)")
    
    def get_schema_info(self) -> str:
        """Get information about available tables and columns."""
        return self.db.get_table_info()
    
    async def query(self, request: SQLQueryRequest) -> SQLQueryResponse:
        """
        Execute SQL query.
        
        Args:
            request: SQLQueryRequest with SQL query
            
        Returns:
            SQLQueryResponse with results
        """
        try:
            logger.info(f"Executing query: {request.query}")
            
            # Execute the query directly (no LLM translation needed)
            results = self.db.run(request.query, fetch="all")
            
            # Parse results into dictionary format
            parsed_results = self._parse_sql_results(results)
            
            return SQLQueryResponse(
                sql_query=request.query,
                results=parsed_results,
                natural_response=f"Query returned {len(parsed_results)} results"
            )
            
        except Exception as e:
            logger.error(f"Query execution failed: {str(e)}")
            return SQLQueryResponse(
                sql_query=request.query,
                results=[],
                natural_response="",
                error=str(e)
            )
    
    def _parse_sql_results(self, results: Any) -> List[Dict[str, Any]]:
        """Convert SQL results to dictionary format."""
        if not results:
            return []
        
        if isinstance(results, list):
            if len(results) > 0 and isinstance(results[0], dict):
                return results
            elif len(results) > 0 and isinstance(results[0], (list, tuple)):
                return [{"result": r} for r in results]
        
        return []
    
    def get_upcoming_et_records(self) -> List[Dict[str, Any]]:
        """
        Get all upcoming ET records (next 7 days).
        Utility method for Phase 3 watchdog.
        """
        query = """
        SELECT 
            transfer_id,
            et_number,
            et_date,
            recipient_id,
            farm_location,
            created_at
        FROM et_transfers
        WHERE et_date >= CURRENT_DATE 
          AND et_date <= CURRENT_DATE + INTERVAL '7 days'
        ORDER BY et_date ASC;
        """
        
        return self.db.run(query, fetch="all")
    
    def get_low_confidence_predictions(self, threshold: float = 0.85) -> List[Dict[str, Any]]:
        """
        Get predictions with confidence below threshold.
        Utility method for Phase 2 diagnostics.
        """
        query = f"""
        SELECT 
            p.prediction_id,
            p.transfer_id,
            p.model_name,
            p.probability,
            p.confidence_lower,
            p.shap_json,
            p.predicted_at
        FROM predictions p
        WHERE p.confidence_lower < {threshold}
          AND p.predicted_at >= NOW() - INTERVAL '24 hours'
        ORDER BY p.confidence_lower ASC;
        """
        
        return self.db.run(query, fetch="all")
