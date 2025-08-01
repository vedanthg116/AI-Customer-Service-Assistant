# server/api/routers/rag_router.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel
from utils.rag_service import get_rag_service
import logging

router = APIRouter()

# Pydantic models for request/response
class KnowledgeDocument(BaseModel):
    id: str
    content: str
    metadata: Optional[Dict] = None

class SearchRequest(BaseModel):
    query: str
    n_results: Optional[int] = 5
    filter_metadata: Optional[Dict] = None

class SearchResponse(BaseModel):
    results: List[Dict]
    total_found: int

class KnowledgeBaseStats(BaseModel):
    total_documents: int
    collection_name: str
    persist_directory: str

@router.get("/rag/stats", response_model=KnowledgeBaseStats)
async def get_knowledge_base_stats():
    """Get statistics about the knowledge base."""
    try:
        rag_service = get_rag_service()
        stats = rag_service.get_collection_stats()
        return KnowledgeBaseStats(**stats)
    except Exception as e:
        logging.error(f"Error getting knowledge base stats: {e}")
        raise HTTPException(status_code=500, detail=f"Error retrieving knowledge base stats: {str(e)}")

@router.post("/rag/search", response_model=SearchResponse)
async def search_knowledge_base(request: SearchRequest):
    """Search the knowledge base for relevant information."""
    try:
        rag_service = get_rag_service()
        results = rag_service.search(
            query=request.query,
            n_results=request.n_results,
            filter_metadata=request.filter_metadata
        )
        return SearchResponse(results=results, total_found=len(results))
    except Exception as e:
        logging.error(f"Error searching knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching knowledge base: {str(e)}")

@router.post("/rag/add")
async def add_knowledge_documents(documents: List[KnowledgeDocument]):
    """Add new knowledge documents to the vector database."""
    try:
        rag_service = get_rag_service()
        
        # Convert to format expected by RAG service
        docs = []
        metadata = []
        for doc in documents:
            docs.append({
                "id": doc.id,
                "content": doc.content
            })
            metadata.append(doc.metadata or {})
        
        rag_service.add_knowledge(docs, metadata)
        return {"message": f"Successfully added {len(documents)} documents to knowledge base"}
    except Exception as e:
        logging.error(f"Error adding knowledge documents: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding knowledge documents: {str(e)}")

@router.post("/rag/add-sample")
async def add_sample_knowledge():
    """Initialize the knowledge base with sample data."""
    try:
        rag_service = get_rag_service()
        rag_service.initialize_sample_knowledge()
        return {"message": "Sample knowledge base initialized successfully"}
    except Exception as e:
        logging.error(f"Error initializing sample knowledge: {e}")
        raise HTTPException(status_code=500, detail=f"Error initializing sample knowledge: {str(e)}")

@router.delete("/rag/reset")
async def reset_knowledge_base():
    """Reset the knowledge base (delete all documents)."""
    try:
        rag_service = get_rag_service()
        rag_service.reset_knowledge_base()
        return {"message": "Knowledge base reset successfully"}
    except Exception as e:
        logging.error(f"Error resetting knowledge base: {e}")
        raise HTTPException(status_code=500, detail=f"Error resetting knowledge base: {str(e)}")

@router.get("/rag/test")
async def test_rag_system():
    """Test the RAG system with a sample query."""
    try:
        rag_service = get_rag_service()
        
        # Test query
        test_query = "How do I check my order status?"
        results = rag_service.search(test_query, n_results=3)
        
        return {
            "test_query": test_query,
            "results": results,
            "status": "RAG system is working correctly"
        }
    except Exception as e:
        logging.error(f"Error testing RAG system: {e}")
        raise HTTPException(status_code=500, detail=f"Error testing RAG system: {str(e)}") 