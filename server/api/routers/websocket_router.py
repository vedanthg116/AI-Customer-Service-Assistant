# server/api/routers/websocket_router.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from uuid import UUID # Make sure UUID is imported
from utils.connection_manager import manager

router = APIRouter()

# WebSocket endpoint for customers
# It MUST expect the customer_id as a path parameter now
@router.websocket("/ws/customer/{customer_id}")
async def websocket_customer_endpoint(websocket: WebSocket, customer_id: UUID): # <--- customer_id as path parameter
    print(f"Backend: Attempting to connect customer WebSocket for ID: {customer_id}")
    await manager.connect(websocket, "customer", customer_id) # Pass customer_id to manager
    
    try:
        while True:
            # This loop keeps the connection alive. Incoming messages from client
            # are not processed here, as customer messages are sent via HTTP POST.
            # This WS is for receiving messages from agents/AI.
            data = await websocket.receive_text()
            print(f"Backend: Customer WebSocket {customer_id} received data (ignored): {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, "customer", customer_id) # Pass customer_id to disconnect
        print(f"Backend: Customer WebSocket {customer_id} disconnected.")
    except Exception as e:
        print(f"Backend: Customer WebSocket {customer_id} error during communication: {e}")
        manager.disconnect(websocket, "customer", customer_id)


# WebSocket endpoint for agents
# It MUST expect the agent_id as a path parameter now
@router.websocket("/ws/agent/{agent_id}")
async def websocket_agent_endpoint(websocket: WebSocket, agent_id: UUID): # <--- agent_id as path parameter
    print(f"Backend: Attempting to connect agent WebSocket for ID: {agent_id}")
    await manager.connect(websocket, "agent", agent_id) # Pass agent_id to manager

    try:
        while True:
            # This loop keeps the connection alive. Incoming messages from client
            # are not processed here, as agent messages are sent via HTTP POST.
            # This WS is for receiving updates/broadcasts from the backend.
            data = await websocket.receive_text()
            print(f"Backend: Agent WebSocket {agent_id} received data (ignored): {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket, "agent", agent_id) # Pass agent_id to disconnect
        print(f"Backend: Agent WebSocket {agent_id} disconnected.")
    except Exception as e:
        print(f"Backend: Agent WebSocket {agent_id} error during communication: {e}")
        manager.disconnect(websocket, "agent", agent_id)