# server/api/routers/websocket_router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, status
from utils.connection_manager import manager
from typing import Optional
from uuid import UUID # Import UUID

router = APIRouter()

# WebSocket endpoint for customers (NO authentication required for this demo)
@router.websocket("/ws/customer/{customer_id}") # NEW: Path parameter for customer_id
async def websocket_customer_endpoint(websocket: WebSocket, customer_id: UUID): # Receive customer_id
    # The manager.connect() call handles the websocket.accept() internally
    await manager.connect(websocket, "customer", customer_id) # Pass customer_id
    
    try:
        while True:
            data: Optional[str] = await websocket.receive_text()
            if data is None:
                break
            print(f"Backend: Customer WebSocket received data (ignored): {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, "customer", customer_id) # Pass customer_id
        print("Backend: Customer WebSocket disconnected.")
    except Exception as e:
        print(f"Backend: Customer WebSocket error during communication for {customer_id}: {e}")
        manager.disconnect(websocket, "customer", customer_id) # Pass customer_id


# WebSocket endpoint for agents (NO authentication required for this demo)
@router.websocket("/ws/agent/{agent_id}") # NEW: Path parameter for agent_id
async def websocket_agent_endpoint(websocket: WebSocket, agent_id: UUID): # Receive agent_id
    # The manager.connect() call handles the websocket.accept() internally
    await manager.connect(websocket, "agent", agent_id) # Pass agent_id

    try:
        while True:
            data: Optional[str] = await websocket.receive_text()
            if data is None:
                break
            print(f"Backend: Agent WebSocket received data (ignored): {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, "agent", agent_id) # Pass agent_id
        print("Backend: Agent WebSocket disconnected.")
    except Exception as e:
        print(f"Backend: Agent WebSocket error during communication for {agent_id}: {e}")
        manager.disconnect(websocket, "agent", agent_id) # Pass agent_id