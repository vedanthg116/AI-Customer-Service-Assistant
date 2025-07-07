# server/database.py
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.ext.declarative import DeclarativeBase # Note: DeclarativeBase is now preferred over declarative_base
from sqlalchemy.orm import sessionmaker

from fastapi_users.db import SQLAlchemyBaseUserTableUUID, SQLAlchemyUserDatabase
from sqlalchemy import Column, String, Boolean, Integer, DateTime
from datetime import datetime
import os
from dotenv import load_dotenv
from fastapi import Depends # Import Depends for get_user_db

# Load environment variables (ensure .env is configured)
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env file. Please set it up correctly.")

# SQLAlchemy engine for asynchronous operations
# For SQLite, we need to add connect_args={"check_same_thread": False}
# This is specific to SQLite and allows multiple threads to access the same connection,
# which is necessary for FastAPI's async nature.
engine = create_async_engine(DATABASE_URL, connect_args={"check_same_thread": False})

# Base class for SQLAlchemy models
class Base(DeclarativeBase):
    pass

# User model for FastAPI-Users.
# We extend SQLAlchemyBaseUserTableUUID for UUID as primary key, which is good practice.
class User(SQLAlchemyBaseUserTableUUID, Base):
    # You can add additional fields to your User model here
    # For example, to store the user's display name or role:
    # display_name: Mapped[str] = mapped_column(String(255), nullable=True)
    # role: Mapped[str] = mapped_column(String(50), default="customer")
    pass

# Asynchronous session factory
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Dependency to get an asynchronous database session
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

# Function to get the user database adapter for FastAPI-Users
# This is a dependency that FastAPI-Users uses internally
async def get_user_db(session: AsyncSession = Depends(get_async_session)):
    yield SQLAlchemyUserDatabase(session, User)

# Function to create all database tables defined by Base
async def create_db_and_tables():
    async with engine.begin() as conn:
        # This will create tables if they don't exist based on your models
        await conn.run_sync(Base.metadata.create_all)
    print("Database tables created or already exist.")