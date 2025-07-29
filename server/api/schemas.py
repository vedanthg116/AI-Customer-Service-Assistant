# server/api/schemas.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from uuid import UUID
from datetime import datetime

class ChatMessage(BaseModel):
    """
    Schema for a single chat message, used for history and real-time.
    """
    text: str
    sender: str # "customer" or "agent"
    timestamp: str # ISO formatted string
    image_url: Optional[str] = None
    ocr_text: Optional[str] = None # Keep this top-level for direct use in CustomerChat

    # NEW: Nested AI Analysis object
    # This will contain all the analysis details when present for customer messages
    analysis: Optional[Dict] = None # This will hold the dict with predicted_intent, sentiment, suggestions, etc.

class MessageRequest(BaseModel):
    """
    Schema for a new message sent by a customer for AI analysis.
    """
    customer_id: UUID
    customer_name: str
    text: str
    chat_history: List[ChatMessage] # For context in AI analysis

class AgentMessageRequest(BaseModel):
    """
    Schema for a message sent by an agent.
    """
    agent_id: UUID
    agent_name: str
    conversation_id: UUID
    message: str

class ConversationAssignmentRequest(BaseModel):
    conversation_id: UUID
    agent_id: UUID
    agent_name: str

class ConversationUnassignmentRequest(BaseModel):
    conversation_id: UUID

# Ticket Schemas
class RaiseTicketRequest(BaseModel):
    conversation_id: UUID
    raised_by_agent_id: UUID
    raised_by_agent_name: str
    issue_description: str
    priority: str = "Medium" # Default priority

class TicketResponse(BaseModel):
    id: UUID
    conversation_id: UUID
    raised_by_agent_id: UUID
    raised_by_agent_name: str
    issue_description: str
    status: str
    priority: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic v2

# NEW: Customer Overview Schema
class CustomerOverviewItem(BaseModel):
    user_id: UUID
    user_name: str
    latest_conversation_id: Optional[UUID] = None
    latest_conversation_start_time: Optional[datetime] = None
    latest_conversation_status: Optional[str] = None
    latest_message_summary: Optional[str] = None
    assigned_agent_name: Optional[str] = None
    open_tickets_count: int
    latest_ticket_issue: Optional[str] = None
    latest_ticket_status: Optional[str] = None
    latest_ticket_priority: Optional[str] = None

    class Config:
        from_attributes = True # Enable ORM mode for Pydantic v2