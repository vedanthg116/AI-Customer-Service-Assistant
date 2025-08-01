# server/utils/rag_service.py
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import json
import os
from typing import List, Dict, Optional
import logging

class RAGService:
    def __init__(self, persist_directory: str = "./chroma_db"):
        """
        Initialize RAG service with ChromaDB and sentence transformers.
        
        Args:
            persist_directory: Directory to persist ChromaDB data
        """
        self.persist_directory = persist_directory
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        
        # Initialize ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collection
        self.collection = self.client.get_or_create_collection(
            name="customer_service_kb",
            metadata={"hnsw:space": "cosine"}
        )
        
        logging.info(f"RAG Service initialized with ChromaDB at {persist_directory}")
    
    def add_knowledge(self, documents: List[Dict[str, str]], metadata: Optional[List[Dict]] = None):
        """
        Add knowledge documents to the vector database.
        
        Args:
            documents: List of dictionaries with 'content' and 'id' keys
            metadata: Optional list of metadata dictionaries
        """
        if not documents:
            return
        
        # Prepare data for ChromaDB
        ids = [doc['id'] for doc in documents]
        contents = [doc['content'] for doc in documents]
        
        # Use provided metadata or create default
        if metadata is None:
            metadata = [{"type": "knowledge_base"} for _ in documents]
        
        # Add to collection
        self.collection.add(
            documents=contents,
            metadatas=metadata,
            ids=ids
        )
        
        logging.info(f"Added {len(documents)} documents to knowledge base")
    
    def search(self, query: str, n_results: int = 5, filter_metadata: Optional[Dict] = None) -> List[Dict]:
        """
        Search for relevant knowledge based on query.
        
        Args:
            query: Search query
            n_results: Number of results to return
            filter_metadata: Optional metadata filter
            
        Returns:
            List of relevant documents with scores
        """
        try:
            # Search in ChromaDB
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=filter_metadata
            )
            
            # Format results
            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted_results.append({
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] and results['metadatas'][0] else {},
                        'id': results['ids'][0][i] if results['ids'] and results['ids'][0] else f"doc_{i}",
                        'distance': results['distances'][0][i] if results['distances'] and results['distances'][0] else 0.0
                    })
            
            logging.info(f"Found {len(formatted_results)} relevant documents for query: {query[:50]}...")
            return formatted_results
            
        except Exception as e:
            logging.error(f"Error searching knowledge base: {e}")
            return []
    
    def get_relevant_knowledge(self, customer_message: str, intent: str = None, n_results: int = 3) -> List[str]:
        """
        Get relevant knowledge for customer service response.
        
        Args:
            customer_message: Customer's message
            intent: Detected intent (optional)
            n_results: Number of knowledge snippets to return
            
        Returns:
            List of relevant knowledge strings
        """
        # Build search query
        search_query = customer_message
        
        # Add intent context if available
        if intent:
            search_query += f" {intent}"
        
        # Search for relevant knowledge
        results = self.search(search_query, n_results=n_results)
        
        # Extract content
        knowledge_snippets = [result['content'] for result in results]
        
        return knowledge_snippets
    
    def initialize_sample_knowledge(self):
        """
        Initialize the knowledge base with sample customer service data.
        """
        sample_knowledge = [
            {
                "id": "order_status_1",
                "content": "Orders typically ship within 1-2 business days. You can track your order using the tracking number provided in your shipping confirmation email. Standard shipping delivers in 3-5 business days, while expedited shipping delivers in 1-2 business days.",
                "metadata": {
                    "type": "policy",
                    "category": "order_status",
                    "intent": "order_status_inquiry"
                }
            },
            {
                "id": "order_status_2", 
                "content": "To check your order status, visit our website and log into your account. Go to 'My Orders' section for the latest updates. You can also call our customer service line for immediate assistance.",
                "metadata": {
                    "type": "procedure",
                    "category": "order_status",
                    "intent": "order_status_inquiry"
                }
            },
            {
                "id": "order_status_3",
                "content": "If your order hasn't arrived yet, please check the tracking information in your order confirmation email. Orders may be delayed due to weather, high volume, or delivery issues. If your order is past the expected delivery date, contact us with your order number for assistance.",
                "metadata": {
                    "type": "policy",
                    "category": "order_status",
                    "intent": "order_status_inquiry"
                }
            },
            {
                "id": "order_status_4",
                "content": "For orders that haven't arrived, we can help you track the status. Please provide your order number or email address. We'll check the current status and provide updates on shipping and delivery information.",
                "metadata": {
                    "type": "procedure",
                    "category": "order_status",
                    "intent": "order_status_inquiry"
                }
            },
            {
                "id": "delayed_order_1",
                "content": "If your order is delayed, we apologize for the inconvenience. Please check your tracking number for the most current status. Delays can occur due to weather conditions, high order volume, or carrier issues. We'll work to get your order to you as soon as possible.",
                "metadata": {
                    "type": "policy",
                    "category": "order_status",
                    "intent": "order_status_inquiry"
                }
            },
            {
                "id": "returns_1",
                "content": "Return Policy: Items must be returned within 30 days of purchase in original condition with all packaging. Electronics require original packaging and accessories. Refunds are processed within 5-10 business days after we receive and inspect the returned item.",
                "metadata": {
                    "type": "policy",
                    "category": "returns",
                    "intent": "refund_request"
                }
            },
            {
                "id": "returns_2",
                "content": "To initiate a return, log into your account and go to 'My Orders'. Select the item you want to return and follow the return process. You'll receive a return shipping label via email. Shipping costs are non-refundable unless the return is due to our error.",
                "metadata": {
                    "type": "procedure",
                    "category": "returns",
                    "intent": "refund_request"
                }
            },
            {
                "id": "password_reset_1",
                "content": "To reset your password, go to our login page and click 'Forgot Password'. Enter your registered email address. A password reset link will be sent to your email within 5 minutes. The reset link is valid for 1 hour. If you don't receive the email, check your spam folder.",
                "metadata": {
                    "type": "procedure",
                    "category": "account_management",
                    "intent": "password_reset_request"
                }
            },
            {
                "id": "technical_support_1",
                "content": "Before contacting technical support, try these basic troubleshooting steps: 1) Restart your device/application 2) Clear browser cache and cookies 3) Check your internet connection 4) Update to the latest version. Our technical support team is available Monday-Friday, 9:00 AM - 7:00 PM EST.",
                "metadata": {
                    "type": "troubleshooting",
                    "category": "technical_support",
                    "intent": "technical_support"
                }
            },
            {
                "id": "billing_1",
                "content": "For billing disputes, please provide the invoice number and specific details about the disputed charge. All charges are detailed in your monthly statement. Billing disputes must be raised within 60 days of the statement date. We will investigate and respond within 3 business days.",
                "metadata": {
                    "type": "policy",
                    "category": "billing",
                    "intent": "billing_dispute"
                }
            },
            {
                "id": "product_info_1",
                "content": "Detailed product specifications, user manuals, and customer reviews are available on each product page. We offer a 1-year warranty on all electronic devices. Product comparisons and feature details can be found in our product catalog. New product releases are announced on our website and newsletter.",
                "metadata": {
                    "type": "information",
                    "category": "product_information",
                    "intent": "product_information"
                }
            },
            {
                "id": "account_balance_1",
                "content": "Your current account balance is updated daily and can be viewed in your online portal under 'Account Summary'. Detailed transaction history is available in the 'Statements' section. For security reasons, we cannot disclose exact balance details over chat without full verification.",
                "metadata": {
                    "type": "policy",
                    "category": "account_management",
                    "intent": "account_balance_inquiry"
                }
            },
            {
                "id": "address_change_1",
                "content": "You can update your shipping address in your account settings under 'Address Book'. Address changes for active orders must be requested within 24 hours of purchase. For billing address changes, ensure your payment method is also updated. A confirmation email will be sent after processing.",
                "metadata": {
                    "type": "procedure",
                    "category": "account_management",
                    "intent": "change_address_request"
                }
            }
        ]
        
        # Add sample knowledge to database
        self.add_knowledge(sample_knowledge)
        logging.info("Initialized knowledge base with sample data")
    
    def get_collection_stats(self) -> Dict:
        """
        Get statistics about the knowledge base collection.
        
        Returns:
            Dictionary with collection statistics
        """
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": self.collection.name,
                "persist_directory": self.persist_directory
            }
        except Exception as e:
            logging.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}
    
    def reset_knowledge_base(self):
        """
        Reset the knowledge base (delete all documents).
        """
        try:
            self.client.delete_collection("customer_service_kb")
            self.collection = self.client.create_collection(
                name="customer_service_kb",
                metadata={"hnsw:space": "cosine"}
            )
            logging.info("Knowledge base reset successfully")
        except Exception as e:
            logging.error(f"Error resetting knowledge base: {e}")

# Global RAG service instance
rag_service = None

def get_rag_service() -> RAGService:
    """
    Get or create the global RAG service instance.
    
    Returns:
        RAGService instance
    """
    global rag_service
    if rag_service is None:
        rag_service = RAGService()
        # Initialize with sample data if collection is empty
        if rag_service.collection.count() == 0:
            rag_service.initialize_sample_knowledge()
    return rag_service 