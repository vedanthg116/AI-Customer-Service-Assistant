from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from datetime import datetime
from uuid import uuid4

app = FastAPI(title="Customer Support API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple in-memory storage for demo
conversations = {}
messages = {}

@app.get("/")
async def root():
    return {
        "message": "Customer Support API is running!",
        "status": "success",
        "timestamp": datetime.now().isoformat()
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/api/conversations")
async def get_conversations():
    return {"conversations": list(conversations.values())}

@app.post("/api/conversations")
async def create_conversation():
    conversation_id = str(uuid4())
    conversation = {
        "id": conversation_id,
        "start_time": datetime.now().isoformat(),
        "status": "open",
        "messages": []
    }
    conversations[conversation_id] = conversation
    return conversation

@app.get("/api/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    if conversation_id in conversations:
        return conversations[conversation_id]
    return {"error": "Conversation not found"}

@app.post("/api/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, message: dict):
    if conversation_id not in conversations:
        return {"error": "Conversation not found"}
    
    message_id = str(uuid4())
    message_data = {
        "id": message_id,
        "text": message.get("text", ""),
        "sender": message.get("sender", "customer"),
        "timestamp": datetime.now().isoformat()
    }
    
    conversations[conversation_id]["messages"].append(message_data)
    return message_data

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 