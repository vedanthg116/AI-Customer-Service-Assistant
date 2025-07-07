# server/api/schemas.py
from pydantic import BaseModel
from typing import List, Optional # Import List and Optional

# NEW: Pydantic model for a single chat message in the history
class ChatMessage(BaseModel):
    text: str
    sender: str # e.g., "customer", "agent"
    timestamp: str # ISO formatted string

# Modified: MessageRequest now includes the full chat history
class MessageRequest(BaseModel):
    text: str # The latest message sent by the customer
    chat_history: List[ChatMessage] # The entire conversation history leading up to this message

class AgentMessageRequest(BaseModel):
    agent_id: str = "Agent"
    message: str