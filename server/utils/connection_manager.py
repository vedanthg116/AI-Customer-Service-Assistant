# server/utils/connection_manager.py
from typing import List, Dict
from fastapi import WebSocket
from uuid import UUID # Import UUID

class ConnectionManager:
    def __init__(self): # Initialize instance attributes here
        # Changed active_connections structure:
        # "customer": { UUID (customer_id): [WebSocket1, WebSocket2 (if multiple tabs)] }
        # "agent":    { UUID (agent_id):    [WebSocket1, WebSocket2 (if multiple tabs)] }
        self.active_connections: Dict[str, Dict[UUID, List[WebSocket]]] = {
            "customer": {},
            "agent": {}
        }

    async def connect(self, websocket: WebSocket, client_type: str, user_id: UUID):
        """
        Establishes a new WebSocket connection and adds it to the appropriate list.
        """
        print(f"Backend: ConnectionManager.connect called for {client_type} {user_id} ({websocket.client}). Attempting to accept WebSocket...")
        try:
            await websocket.accept()
            print(f"Backend: WebSocket accepted successfully for {client_type} {user_id} ({websocket.client})")
            
            if client_type in self.active_connections:
                if user_id not in self.active_connections[client_type]:
                    self.active_connections[client_type][user_id] = []
                self.active_connections[client_type][user_id].append(websocket)
                print(f"{client_type.capitalize()} WebSocket connected: {user_id} ({websocket.client}) - Total for user: {len(self.active_connections[client_type][user_id])}")
            else:
                print(f"Warning: Unknown client type '{client_type}' attempting to connect.")
        except Exception as e:
            print(f"Backend: Error accepting WebSocket connection for {client_type} {user_id} ({websocket.client}): {e}")

    def disconnect(self, websocket: WebSocket, client_type: str, user_id: UUID):
        """
        Removes a disconnected WebSocket from the appropriate list.
        """
        if client_type in self.active_connections and user_id in self.active_connections[client_type]:
            if websocket in self.active_connections[client_type][user_id]:
                self.active_connections[client_type][user_id].remove(websocket)
                print(f"{client_type.capitalize()} disconnected: {user_id} ({websocket.client}) - Remaining for user: {len(self.active_connections[client_type][user_id])}")
                if not self.active_connections[client_type][user_id]:
                    del self.active_connections[client_type][user_id]
                    print(f"All {client_type} WebSockets for {user_id} disconnected.")
            else:
                print(f"Warning: Attempted to disconnect unknown WebSocket for {client_type} {user_id}: {websocket.client}")
        else:
            print(f"Warning: Attempted to disconnect unknown or already disconnected {client_type} WebSocket: {websocket.client}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """
        Sends a message to a specific WebSocket connection.
        """
        try:
            await websocket.send_text(message)
        except Exception as e:
            print(f"Error sending personal message to {websocket.client}: {e}")

    async def send_to_customer(self, customer_id: UUID, message: str):
        """
        Sends a message to all active WebSocket connections for a specific customer.
        """
        disconnected_websockets = []
        customer_connections = self.active_connections["customer"].get(customer_id, [])
        if not customer_connections:
            print(f"No active WebSocket connections found for customer {customer_id} to send message.")
            return

        for connection in customer_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                print(f"Error sending message to customer {customer_id} ({connection.client}): {e}. Marking for disconnection.")
                disconnected_websockets.append(connection)
        
        for ws in disconnected_websockets:
            self.disconnect(ws, "customer", customer_id)

    async def broadcast(self, message: str, client_type: str):
        """
        Broadcasts a message to all active connections of a specific client type.
        This is now used for agents, but not for customer-specific messages.
        """
        disconnected_users = []
        if client_type in self.active_connections:
            for user_id, websockets in list(self.active_connections[client_type].items()):
                disconnected_websockets_for_user = []
                for connection in websockets:
                    try:
                        await connection.send_text(message)
                    except Exception as e:
                        print(f"Error broadcasting to {client_type} {user_id} ({connection.client}): {e}. Marking for disconnection.")
                        disconnected_websockets_for_user.append(connection)
                
                for ws in disconnected_websockets_for_user:
                    self.active_connections[client_type][user_id].remove(ws)
                
                if not self.active_connections[client_type][user_id]:
                    disconnected_users.append(user_id)
        
        for user_id in disconnected_users:
            del self.active_connections[client_type][user_id]
            print(f"All {client_type} WebSockets for {user_id} disconnected after broadcast cleanup.")


    async def broadcast_to_customers(self, message: str):
        """
        This method will no longer be used for customer-specific messages.
        It can be repurposed for true global customer broadcasts if needed,
        or simply removed. For now, we'll keep it but note its limited use.
        """
        print("Warning: broadcast_to_customers called. This should generally be replaced by send_to_customer for specific messages.")
        pass

    async def broadcast_to_agents(self, message: str):
        """Convenience method to broadcast to all agent connections."""
        await self.broadcast(message, "agent")

manager = ConnectionManager()