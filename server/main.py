# server/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os

# Import configured Gemini model (loaded once here)
from config.gemini_config import gemini_model # Import the initialized model

# Import routers
from api.routers import chat_router, websocket_router

app = FastAPI(
    title="AI Customer Service Assistant Backend",
    description="Main API entry point with Gemini integration and real-time communication.",
    version="0.3.0"
)

# --- CORS Middleware Configuration ---
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Add any other origins for your frontend in production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Include Routers ---
# This registers all endpoints defined in your router files with the main app.
app.include_router(chat_router.router, tags=["Chat Operations"])
app.include_router(websocket_router.router, tags=["WebSocket Communication"])

# --- Simple Root Endpoint ---
@app.get("/")
async def root():
    # You might want to add a check here if gemini_model is None
    status_message = "running!"
    if gemini_model is None:
        status_message = "running, but Gemini model failed to load. Check logs!"
    return {"message": f"AI Customer Service Assistant Backend is {status_message}"}