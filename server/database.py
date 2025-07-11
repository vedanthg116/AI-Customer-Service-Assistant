# server/database.py
from typing import AsyncGenerator, List, Optional
from uuid import UUID, uuid4
from datetime import datetime
import json # Import json for previous_orders handling

from fastapi import Depends

from sqlalchemy import String, Column, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID # Keep PG_UUID for UUID type
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# Define your database URL (adjust as needed for your environment)
DATABASE_URL = "sqlite+aiosqlite:///./sql_app.db" # Using SQLite for simplicity

Base = declarative_base()

# User Model Definition (now essentially a Customer Profile)
class User(Base): # No longer inheriting from SQLAlchemyBaseUserTableUUID
    __tablename__ = "users"
    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    full_name: str = Column(String(255), nullable=True) # e.g., "John Doe"
    # Store previous orders as a JSON string
    previous_orders: Optional[str] = Column(Text, nullable=True) # Store as JSON string: '["ORD123", "ORD456"]'
    
    # Relationships
    conversations = relationship("Conversation", back_populates="user", lazy="selectin")

# Conversation Model Definition
class Conversation(Base):
    __tablename__ = "conversations"
    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: UUID = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    start_time: datetime = Column(DateTime, default=datetime.now)
    status: str = Column(String(50), default="open") # e.g., "open", "closed", "pending"

    # NEW: Fields for agent assignment
    assigned_agent_id: Optional[UUID] = Column(PG_UUID(as_uuid=True), nullable=True)
    assigned_agent_name: Optional[str] = Column(String(255), nullable=True)

    # Relationships
    user = relationship("User", back_populates="conversations", lazy="selectin")
    messages = relationship("Message", back_populates="conversation", lazy="selectin", order_by="Message.timestamp")

# Message Model Definition
class Message(Base):
    __tablename__ = "messages"
    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: UUID = Column(PG_UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False)
    sender: str = Column(String(50), nullable=False) # e.g., "customer", "agent", "system"
    text_content: str = Column(Text, nullable=False)
    timestamp: datetime = Column(DateTime, default=datetime.now)
    image_url: Optional[str] = Column(Text, nullable=True) # Store base64 image data or URL
    ocr_extracted_text: Optional[str] = Column(Text, nullable=True) # Text extracted from image

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")

# Knowledge Base Article Model Definition
class KnowledgeBaseArticle(Base):
    __tablename__ = "knowledge_base_articles"
    id: UUID = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    title: str = Column(String(255), nullable=False, unique=True)
    content: str = Column(Text, nullable=False)
    tags: Optional[str] = Column(String(255), nullable=True) # Comma-separated tags, e.g., "shipping,returns"
    last_updated: datetime = Column(DateTime, default=datetime.now, onupdate=datetime.now)


# Database Engine and Session Setup
engine = create_async_engine(DATABASE_URL)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def create_db_and_tables():
    """Creates all database tables defined in Base."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting an async database session."""
    async with async_session_maker() as session:
        yield session

# Removed: get_user_db and seed_initial_data
# We will handle customer creation on the fly based on name.