# server/api/routers/websocket_router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from utils.connection_manager import manager

router = APIRouter()

@router.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket):
    """
    Manages WebSocket connections for agent dashboards.
    Agents connect to this endpoint to receive real-time updates.
    """
    await manager.connect(websocket, "agent")
    try:
        # The agent UI primarily receives messages, so this loop just keeps the connection open.
        # It can also receive messages from the agent if bidirectional communication is needed later.
        while True:
            # You could process messages sent from the agent UI here if needed, e.g., heartbeats.
            await websocket.receive_text()
    except WebSocketDisconnect:
        print(f"Agent disconnected: {websocket.client}")
        manager.disconnect(websocket, "agent")
    except Exception as e:
        print(f"WebSocket error for agent {websocket.client}: {e}")
        manager.disconnect(websocket, "agent")

@router.websocket("/ws/customer")
async def websocket_customer_endpoint(websocket: WebSocket):
    """
    Manages WebSocket connections for customer chat.
    Customers connect to this endpoint to receive real-time messages from agents.
    """
    await manager.connect(websocket, "customer")
    try:
        while True:
            # Customer UI might send messages (e.g., heartbeats or initial connect message)
            # For this demo, customer messages go via POST /analyze-message for analysis
            await websocket.receive_text() # Keep connection alive
    except WebSocketDisconnect:
        print(f"Customer disconnected: {websocket.client}")
        manager.disconnect(websocket, "customer")
    except Exception as e:
        print(f"WebSocket error for customer {websocket.client}: {e}")
        manager.disconnect(websocket, "customer")