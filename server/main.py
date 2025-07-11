# server/main.py
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

# Import configured Gemini model
from config.gemini_config import gemini_model

# Import routers
from api.routers import chat_router, websocket_router
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

    # Removed: seed_initial_data call

    yield # The application will run after this point
    print("Application shutdown.")


# Initialize FastAPI app with the lifespan context manager
app = FastAPI(
    title="AI Customer Service Assistant Backend",
    description="Main API entry point with Gemini integration, real-time communication, and simplified customer/agent management.",
    version="0.5.0", # Updated version to reflect major changes
    lifespan=lifespan
)

# --- CORS Middleware Configuration ---
# This middleware should be added as early as possible to ensure it intercepts all requests.
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173", # Default for Vite development server
    "http://127.0.0.1:5173",
    # Add any other origins for your frontend in production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods, including those used in WebSocket handshake (GET, OPTIONS)
    allow_headers=["*"],  # Allows all headers, crucial for WebSocket connection headers like Upgrade, Connection, Sec-WebSocket-Key
)

# Removed: All authentication routers from fastapi-users

# --- Include Custom Application Routers ---
app.include_router(chat_router.router, tags=["Chat Operations"])
app.include_router(websocket_router.router, tags=["WebSocket Communication"])

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