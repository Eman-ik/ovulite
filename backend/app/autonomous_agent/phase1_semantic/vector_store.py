"""Phase 1: Semantic Knowledge Layer - Vector Store (Simplified - No pgvector/OpenAI Required)"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DocumentChunk(BaseModel):
    """Document chunk for storage."""
    content: str = Field(..., description="Text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Associated metadata")
    source: str = Field(default="ovulite_system", description="Source of the document")


class VectorSearchResult(BaseModel):
    """Result from search."""
    content: str
    similarity_score: float
    metadata: Dict[str, Any]
    source: str


class VectorStoreManager:
    """
    Simplified Vector Store Manager - Keyword-based Search
    
    No pgvector or OpenAI required. Uses simple keyword matching
    for document search.
    
    Stores metadata for:
    - System logs and diagnostic reports
    - ET record summaries
    - Model prediction explanations
    - Research papers and insights
    """
    
    def __init__(
        self,
        database_url: str,
        openai_api_key: Optional[str] = None,
        collection_name: str = "ovulite_knowledge"
    ):
        """
        Initialize Vector Store Manager (simplified mode).
        
        Args:
            database_url: PostgreSQL connection string (for future use)
            openai_api_key: Not needed (kept for compatibility)
            collection_name: Name of the collection
        """
        self.database_url = database_url
        self.collection_name = collection_name
        
        # In-memory document store (simplified)
        self.documents: List[Dict[str, Any]] = []
        
        logger.info(f"Vector Store Manager initialized (keyword search mode, collection: {collection_name})")
    
    async def add_chunk(self, chunk: DocumentChunk) -> str:
        """
        Add a document chunk to the store.
        
        Args:
            chunk: DocumentChunk to add
            
        Returns:
            Document ID
        """
        try:
            doc_id = f"{chunk.source}_{len(self.documents)}_{datetime.now().timestamp()}"
            
            self.documents.append({
                "id": doc_id,
                "content": chunk.content,
                "metadata": chunk.metadata,
                "source": chunk.source,
                "created_at": datetime.now().isoformat()
            })
            
            logger.info(f"Added chunk to store: {chunk.source} (ID: {doc_id})")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to add chunk: {str(e)}")
            raise
    
    async def add_chunks_bulk(self, chunks: List[DocumentChunk]) -> List[str]:
        """Add multiple chunks to the store."""
        doc_ids = []
        for chunk in chunks:
            doc_id = await self.add_chunk(chunk)
            doc_ids.append(doc_id)
        return doc_ids
    
    async def search(
        self,
        query: str,
        k: int = 5,
        threshold: float = 0.7
    ) -> List[VectorSearchResult]:
        """
        Search documents using keyword matching.
        
        Args:
            query: Search query
            k: Number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of VectorSearchResult
        """
        try:
            search_results = []
            query_lower = query.lower()
            
            # Simple keyword matching
            for doc in self.documents:
                content_lower = doc["content"].lower()
                
                # Count keyword matches
                matches = 0
                for word in query_lower.split():
                    if len(word) > 2 and word in content_lower:
                        matches += 1
                
                # Calculate simple similarity (number of word matches / total words)
                similarity = min(matches / max(len(query_lower.split()), 1), 1.0)
                
                if similarity >= threshold or matches > 0:
                    search_results.append({
                        "doc": doc,
                        "similarity": similarity
                    })
            
            # Sort by similarity and limit results
            search_results.sort(key=lambda x: x["similarity"], reverse=True)
            
            results = []
            for result in search_results[:k]:
                results.append(VectorSearchResult(
                    content=result["doc"]["content"][:500],  # Limit to 500 chars
                    similarity_score=result["similarity"],
                    metadata=result["doc"]["metadata"],
                    source=result["doc"]["source"]
                ))
            
            logger.info(f"Keyword search found {len(results)} results for: {query}")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            return []
    
    async def search_by_metadata(
        self,
        metadata_filters: Dict[str, Any]
    ) -> List[VectorSearchResult]:
        """
        Search using metadata filters.
        
        Args:
            metadata_filters: Dictionary of metadata filters
            
        Returns:
            List of VectorSearchResult matching filters
        """
        try:
            results = []
            
            for doc in self.documents:
                # Check if all filters match
                match = True
                for key, value in metadata_filters.items():
                    if key not in doc["metadata"] or doc["metadata"][key] != value:
                        match = False
                        break
                
                if match:
                    results.append(VectorSearchResult(
                        content=doc["content"][:500],
                        similarity_score=1.0,
                        metadata=doc["metadata"],
                        source=doc["source"]
                    ))
            
            logger.info(f"Metadata search found {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Metadata search failed: {str(e)}")
            return []
    
    def add_system_log(
        self,
        log_message: str,
        log_level: str = "INFO",
        component: str = "system"
    ) -> str:
        """Add a system log entry to the store."""
        chunk = DocumentChunk(
            content=log_message,
            metadata={
                "log_level": log_level,
                "component": component,
                "type": "system_log"
            },
            source=f"logs_{component}"
        )
        
        import asyncio
        return asyncio.run(self.add_chunk(chunk))
    
    def add_diagnostic_report(
        self,
        report: str,
        diagnosis_type: str,
        transfer_id: Optional[int] = None
    ) -> str:
        """Add a diagnostic report to the store."""
        chunk = DocumentChunk(
            content=report,
            metadata={
                "diagnosis_type": diagnosis_type,
                "transfer_id": transfer_id,
                "type": "diagnostic_report"
            },
            source="diagnostics"
        )
        
        import asyncio
        return asyncio.run(self.add_chunk(chunk))
    
    def add_research_insight(
        self,
        title: str,
        insight: str,
        relevance_score: float,
        implementation_tip: str,
        paper_source: str = "arxiv"
    ) -> str:
        """Add a research insight to the store."""
        chunk = DocumentChunk(
            content=f"{title}\n\n{insight}\n\nImplementation: {implementation_tip}",
            metadata={
                "title": title,
                "relevance_score": relevance_score,
                "implementation_tip": implementation_tip,
                "paper_source": paper_source,
                "type": "research_insight"
            },
            source="research"
        )
        
        import asyncio
        return asyncio.run(self.add_chunk(chunk))
