# server/utils/connection_manager.py
from typing import List
from fastapi import WebSocket, WebSocketDisconnect

class ConnectionManager:
    def __init__(self):
        self.agent_connections: List[WebSocket] = []
        self.customer_connections: List[WebSocket] = [] # NEW: For customer UI

    async def connect(self, websocket: WebSocket, client_type: str):
        await websocket.accept()
        if client_type == "agent":
            self.agent_connections.append(websocket)
            print(f"Agent WebSocket connected: {websocket.client}")
        elif client_type == "customer":
            self.customer_connections.append(websocket)
            print(f"Customer WebSocket connected: {websocket.client}")
        else:
            print(f"Unknown client type connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket, client_type: str):
        if client_type == "agent" and websocket in self.agent_connections:
            self.agent_connections.remove(websocket)
            print(f"Agent WebSocket disconnected: {websocket.client}")
        elif client_type == "customer" and websocket in self.customer_connections:
            self.customer_connections.remove(websocket)
            print(f"Customer WebSocket disconnected: {websocket.client}")

    async def broadcast_to_agents(self, message: str):
        # print(f"Broadcasting to {len(self.agent_connections)} agents: {message[:100]}...") # Debugging
        disconnected_agents = []
        for connection in self.agent_connections:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                disconnected_agents.append(connection)
            except Exception as e:
                print(f"Error broadcasting to agent {connection.client}: {e}")
                disconnected_agents.append(connection)
        for agent in disconnected_agents:
            self.agent_connections.remove(agent)

    async def broadcast_to_customers(self, message: str): # NEW: For customer UI
        # print(f"Broadcasting to {len(self.customer_connections)} customers: {message[:100]}...") # Debugging
        disconnected_customers = []
        for connection in self.customer_connections:
            try:
                await connection.send_text(message)
            except WebSocketDisconnect:
                disconnected_customers.append(connection)
            except Exception as e:
                print(f"Error broadcasting to customer {connection.client}: {e}")
                disconnected_customers.append(connection)
        for customer in disconnected_customers:
            self.customer_connections.remove(customer)

manager = ConnectionManager()