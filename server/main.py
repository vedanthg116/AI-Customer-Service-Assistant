# server/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import configured Gemini model
from config.gemini_config import gemini_model

# Import routers
from api.routers import chat_router, websocket_router, kb_router # NEW: Import kb_router
# NEW: Import only database components, removed auth imports
from database import create_db_and_tables, get_async_session


# Define a lifespan context manager for application startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Context manager for application startup and shutdown events.
    Used to perform tasks like database table creation.
    """
    print("Application startup: Ensuring database tables are created...")
    await create_db_and_tables()
    print("Database tables ensured.")

    yield # The application will run after this point
    print("Application shutdown.")


# Initialize FastAPI app with the lifespan context manager
app = FastAPI(
    title="AI Customer Service Assistant Backend",
    description="Main API entry point with Gemini integration, real-time communication, and simplified customer/agent management.",
    version="0.5.0",
    lifespan=lifespan
)

# --- CORS Middleware Configuration ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Custom Application Routers ---
app.include_router(chat_router.router, tags=["Chat Operations"])
app.include_router(websocket_router.router, tags=["WebSocket Communication"])
app.include_router(kb_router.router, tags=["Knowledge Base"]) # NEW: Include KB router

# --- Simple Root Endpoint ---
@app.get("/")
async def root():
    """
    Root endpoint to check if the backend is running and Gemini model status.
    """
    status_message = "running!"
    if gemini_model is None:
        status_message = "running, but Gemini model failed to load. Check server logs for details!"
    return {"message": f"AI Customer Service Assistant Backend is {status_message}"}