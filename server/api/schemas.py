# server/api/schemas.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID # Import UUID

# Schema for a single chat message (used for history and display)
class ChatMessage(BaseModel):
    text: str
    sender: str # "customer" or "agent"
    timestamp: str # ISO format string
    image_url: Optional[str] = None # Base64 encoded image or URL
    ocr_text: Optional[str] = None # Extracted text from text

# Schema for incoming customer message request (now includes customer_id and customer_name)
class MessageRequest(BaseModel):
    customer_id: UUID # The UUID for the customer (generated on frontend)
    customer_name: str # The name provided by the customer
    text: str
    chat_history: List[ChatMessage] # Full chat history for context

# Schema for incoming agent message request
class AgentMessageRequest(BaseModel):
    conversation_id: UUID
    agent_id: UUID # UUID for the agent (generated on frontend)
    agent_name: str # Name provided by the agent
    message: str

# NEW: Schema for assigning/unassigning conversations
class ConversationAssignmentRequest(BaseModel):
    conversation_id: UUID
    agent_id: UUID
    agent_name: str

# NEW: Schema for unassigning conversations
class ConversationUnassignmentRequest(BaseModel):
    conversation_id: UUID