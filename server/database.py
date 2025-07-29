# server/database.py
from datetime import datetime
from uuid import UUID, uuid4 # Keep uuid.UUID for type hints and default generation
from typing import Optional
from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import sessionmaker, Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.types import TypeDecorator, CHAR # NEW: Import TypeDecorator and CHAR
# Removed: from sqlalchemy.dialects.postgresql import UUID as PG_UUID # No longer needed if using custom type
# Removed: from sqlalchemy.dialects.sqlite import BLOB, UUID as SQLITE_UUID # No longer needed, this was the problem!

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# NEW: Custom UUID Type
class UUIDType(TypeDecorator):
    """Platform-independent UUID type.
    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32) storing UUID.hex values.
    """
    impl = CHAR(36) # Store as a 36-character string (e.g., "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx")
    cache_ok = True # For SQLAlchemy 2.0+

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return str(value) # Convert UUID object to string for storage

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return UUID(value) # Convert string from DB back to UUID object

# Ensure your database URL is correct. For SQLite, it's a file path.
DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db"

Base = declarative_base()

# --- Database Models ---

class User(Base):
    __tablename__ = "users"
    # Use custom UUIDType
    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    full_name: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    conversations: Mapped[list["Conversation"]] = relationship(back_populates="user")

class Conversation(Base):
    __tablename__ = "conversations"
    # Use custom UUIDType
    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("users.id"))
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    status: Mapped[str] = mapped_column(String, default="open") # e.g., "open", "closed"
    assigned_agent_id: Mapped[Optional[UUID]] = mapped_column(UUIDType, nullable=True)
    assigned_agent_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(back_populates="conversation")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="conversation") # NEW: Relationship to Tickets

class Message(Base):
    __tablename__ = "messages"
    # Use custom UUIDType
    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("conversations.id"))
    sender: Mapped[str] # "customer" or "agent"
    text_content: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    image_url: Mapped[Optional[str]] = mapped_column(String, nullable=True) # For base64 image data or URL
    ocr_extracted_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # AI Analysis Fields
    predicted_intent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    intent_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    sentiment_label: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    sentiment_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    # Store suggestions and detected entities as JSON strings
    suggestions_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    detected_entities_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")

class Ticket(Base): # NEW: Ticket Model
    __tablename__ = "tickets"
    # Use custom UUIDType
    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(UUIDType, ForeignKey("conversations.id"))
    raised_by_agent_id: Mapped[UUID] = mapped_column(UUIDType)
    raised_by_agent_name: Mapped[str] = mapped_column(String)
    issue_description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String, default="Open") # e.g., "Open", "Pending", "Closed"
    priority: Mapped[str] = mapped_column(String, default="Medium") # e.g., "Low", "Medium", "High", "Urgent"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)

    conversation: Mapped["Conversation"] = relationship(back_populates="tickets")


class KnowledgeBaseArticle(Base):
    __tablename__ = "knowledge_base_articles"
    # Use custom UUIDType
    id: Mapped[UUID] = mapped_column(UUIDType, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String, index=True)
    content: Mapped[str] = mapped_column(Text)
    tags: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)


# --- Database Engine & Session Setup ---

# For asynchronous operations
async_engine = create_async_engine(DATABASE_URL, echo=False)

# For asynchronous sessions
AsyncSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def create_db_and_tables():
    """Creates all database tables defined in Base."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_async_session():
    """Dependency for getting an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        yield session