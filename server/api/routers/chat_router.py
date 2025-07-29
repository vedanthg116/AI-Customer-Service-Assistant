# server/api/routers/chat_router.py
from fastapi import (
    APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Response
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from uuid import UUID, uuid4
import json
import base64
from datetime import datetime

# Import from new service files
from api.services.ai_service import ai_service
from api.services import db_service
from api.schemas import (
    MessageRequest, AgentMessageRequest, ChatMessage,
    ConversationAssignmentRequest, ConversationUnassignmentRequest,
    RaiseTicketRequest, TicketResponse,
    CustomerOverviewItem # NEW: Import CustomerOverviewItem
)
from utils.connection_manager import manager
from database import get_async_session, Conversation, Message # Import Message for last_message_summary

router = APIRouter()

# -----------------------------------------------------------
# Customer-Facing Routes
# -----------------------------------------------------------
@router.post("/analyze-message")
async def analyze_message_endpoint(
    request: MessageRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Analyze text message with Gemini, save & broadcast.
    """
    customer_id = request.customer_id
    customer_name = request.customer_name
    user_message = request.text
    full_chat_history = request.chat_history

    customer_user = await db_service.get_or_create_user(db, customer_id, customer_name)
    print(f"Customer {customer_user.full_name} (ID: {customer_id}) sent message: '{user_message}'")

    conversation = await db_service.get_or_create_conversation(db, customer_id)

    # Perform AI analysis using the ai_service
    analysis_result = await ai_service.analyze_text_message(
        latest_user_message=user_message,
        full_chat_history=full_chat_history,
    )

    # Save the message with AI analysis data
    await db_service.save_message_to_db(
        db,
        conversation.id,
        "customer",
        user_message,
        ocr_extracted_text=analysis_result.get("ocr_extracted_text"),
        predicted_intent=analysis_result.get("predicted_intent"),
        intent_confidence=analysis_result.get("intent_confidence"),
        sentiment_label=analysis_result.get("sentiment", {}).get("label"),
        sentiment_score=analysis_result.get("sentiment", {}).get("score"),
        suggestions=analysis_result.get("suggestions"),
        detected_entities=analysis_result.get("detected_entities")
    )

    # Broadcast the analysis to all connected agent UIs (for their dashboard)
    await manager.broadcast_to_agents(json.dumps({
        "type": "customer_message_analysis",
        "conversation_id": str(conversation.id),
        "user_id": str(customer_id),
        "user_name": customer_name,
        "original_message": user_message,
        "analysis": analysis_result
    }))

    # Send the original customer message ONLY to the specific customer's WebSocket
    await manager.send_to_customer(customer_id, json.dumps({
        "type": "customer_chat_message",
        "sender": "customer",
        "text": user_message,
        "timestamp": analysis_result.get("timestamp"),
        "image_url": None,
        "ocr_text": analysis_result.get("ocr_extracted_text")
    }))

    return analysis_result

@router.post("/analyze-image-message")
async def analyze_image_message_endpoint(
    file: UploadFile = File(...),
    customer_id: UUID = Form(...),
    customer_name: str = Form(...),
    text: Optional[str] = Form(None),
    chat_history_json: str = Form(...),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Handle image upload: OCR + Gemini + broadcast.
    """
    customer_user = await db_service.get_or_create_user(db, customer_id, customer_name)
    print(f"Customer {customer_user.full_name} (ID: {customer_id}) sent image upload: {file.filename} with text: '{text}'")
    
    image_bytes = await file.read()

    full_chat_history: List[ChatMessage] = [
        ChatMessage(**msg) for msg in json.loads(chat_history_json)
    ]

    analysis_result = await ai_service.analyze_image_message(
        image_bytes=image_bytes,
        text_content=text,
        full_chat_history=full_chat_history
    )
    
    conversation = await db_service.get_or_create_conversation(db, customer_id)

    image_base64_url = f"data:{file.content_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
    
    await db_service.save_message_to_db(
        db,
        conversation.id,
        "customer",
        text or "Screenshot shared.",
        image_url=image_base64_url,
        ocr_extracted_text=analysis_result.get("ocr_extracted_text"),
        predicted_intent=analysis_result.get("predicted_intent"),
        intent_confidence=analysis_result.get("intent_confidence"),
        sentiment_label=analysis_result.get("sentiment", {}).get("label"),
        sentiment_score=analysis_result.get("sentiment", {}).get("score"),
        suggestions=analysis_result.get("suggestions"),
        detected_entities=analysis_result.get("detected_entities")
    )

    await manager.broadcast_to_agents(json.dumps({
        "type": "customer_message_analysis",
        "conversation_id": str(conversation.id),
        "user_id": str(customer_id),
        "user_name": customer_name,
        "original_message": analysis_result.get("user_message"),
        "image_url": image_base64_url,
        "ocr_text": analysis_result.get("ocr_extracted_text"),
        "analysis": analysis_result
    }))

    await manager.send_to_customer(customer_id, json.dumps({
        "type": "customer_chat_message",
        "sender": "customer",
        "text": text or "Screenshot shared.",
        "timestamp": analysis_result.get("timestamp"),
        "image_url": image_base64_url,
        "ocr_text": analysis_result.get("ocr_extracted_text")
    }))

    return analysis_result

# -----------------------------------------------------------
# Agent-Facing Routes
# -----------------------------------------------------------
@router.post("/send-agent-message")
async def send_agent_message_endpoint(
    request: AgentMessageRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Agent sends message to customer; broadcast.
    """
    agent_message = request.message
    agent_id = request.agent_id
    agent_name = request.agent_name
    conversation_id = request.conversation_id

    print(f"Agent '{agent_name}' (ID: {agent_id}) sent: '{agent_message}' to conversation {conversation_id}")

    await db_service.save_message_to_db(
        db,
        conversation_id,
        "agent",
        agent_message
    )

    message_to_broadcast = json.dumps({
        "type": "agent_chat_message",
        "sender": "agent",
        "text": agent_message,
        "timestamp": datetime.now().isoformat(),
        "agent_id": str(agent_id),
        "agent_name": agent_name,
        "conversation_id": str(conversation_id)
    })

    conversation = await db_service.get_conversation_by_id(db, conversation_id)
    if conversation and conversation.user_id:
        await manager.send_to_customer(conversation.user_id, message_to_broadcast)
    else:
        print(f"Warning: Could not find customer_id for conversation {conversation_id} to send agent message.")

    await manager.broadcast_to_agents(message_to_broadcast)

    return {"status": "success", "message": "Agent message sent"}

@router.post("/assign-conversation")
async def assign_conversation(
    request: ConversationAssignmentRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Assigns a conversation to a specific agent.
    """
    conversation_id = request.conversation_id
    agent_id = request.agent_id
    agent_name = request.agent_name

    conversation = await db_service.get_conversation_by_id(db, conversation_id)

    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation.assigned_agent_id and conversation.assigned_agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Conversation already assigned to {conversation.assigned_agent_name}")

    conversation = await db_service.update_conversation_assignment(db, conversation_id, agent_id, agent_name)

    print(f"Conversation {conversation_id} assigned to Agent {agent_name} (ID: {agent_id})")

    await manager.broadcast_to_agents(json.dumps({
        "type": "conversation_assigned",
        "conversation_id": str(conversation.id),
        "assigned_agent_id": str(conversation.assigned_agent_id),
        "assigned_agent_name": conversation.assigned_agent_name
    }))

    return {"status": "success", "message": "Conversation assigned", "conversation_id": str(conversation.id)}

@router.post("/unassign-conversation")
async def unassign_conversation(
    request: ConversationUnassignmentRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Unassigns a conversation from an agent.
    """
    conversation_id = request.conversation_id

    conversation = await db_service.get_conversation_by_id(db, conversation_id)

    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if not conversation.assigned_agent_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conversation is not currently assigned")

    old_agent_id = conversation.assigned_agent_id
    old_agent_name = conversation.assigned_agent_name
    
    conversation = await db_service.update_conversation_assignment(db, conversation_id, None, None)

    print(f"Conversation {conversation_id} unassigned from Agent {old_agent_name} (ID: {old_agent_id})")

    await manager.broadcast_to_agents(json.dumps({
        "type": "conversation_unassigned",
        "conversation_id": str(conversation.id),
        "unassigned_agent_id": str(old_agent_id),
        "unassigned_agent_name": old_agent_name
    }))

    return {"status": "success", "message": "Conversation unassigned", "conversation_id": str(conversation.id)}

# Ticket Endpoints
@router.post("/tickets/raise", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def raise_ticket_endpoint(
    request: RaiseTicketRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Allows an agent to raise a new ticket for a conversation.
    """
    conversation = await db_service.get_conversation_by_id(db, request.conversation_id)
    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found.")

    ticket = await db_service.create_ticket_in_db(
        db,
        conversation_id=request.conversation_id,
        raised_by_agent_id=request.raised_by_agent_id,
        raised_by_agent_name=request.raised_by_agent_name,
        issue_description=request.issue_description,
        priority=request.priority
    )
    return ticket

@router.get("/conversations/{conversation_id}/tickets", response_model=List[TicketResponse])
async def get_conversation_tickets_endpoint(
    conversation_id: UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retrieves all tickets associated with a specific conversation.
    """
    tickets = await db_service.get_tickets_for_conversation(db, conversation_id)
    return tickets

# NEW: Customer Overview Endpoint
@router.get("/customer-overview", response_model=List[CustomerOverviewItem])
async def get_customer_overview_endpoint(
    db: AsyncSession = Depends(get_async_session)
):
    """
    Retrieves a comprehensive overview of all customers, their latest conversation,
    and associated ticket information.
    """
    overview_data = await db_service.get_customer_overview_data(db)
    return overview_data


@router.get("/conversations/active")
async def get_active_conversations(db: AsyncSession = Depends(get_async_session)):
    """
    Get all active conversations, including user and agent assignment details.
    """
    conversations = await db_service.get_active_conversations_from_db(db)

    formatted_conversations = []
    for conv in conversations:
        last_message_result = await db.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.timestamp.desc())
            .limit(1)
        )
        last_message = last_message_result.scalars().first()
        
        formatted_conversations.append({
            "id": str(conv.id),
            "user_id": str(conv.user_id),
            "user_name": conv.user.full_name if conv.user else "Unknown Customer",
            "start_time": conv.start_time.isoformat(),
            "status": conv.status,
            "last_message_summary": last_message.text_content if last_message else "No messages yet.",
            "assigned_agent_id": str(conv.assigned_agent_id) if conv.assigned_agent_id else None,
            "assigned_agent_name": conv.assigned_agent_name
        })
    return formatted_conversations

@router.get("/chat-history/conversation/{conversation_id}", response_model=List[ChatMessage])
async def get_conversation_history(conversation_id: UUID, db: AsyncSession = Depends(get_async_session)):
    """
    Chat history by conversation ID.
    """
    chat_history = await db_service.get_messages_for_conversation(db, conversation_id)
    return chat_history

@router.get("/chat-history/user/{user_id}", response_model=List[ChatMessage])
async def get_chat_history_for_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Latest chat history for a specific user ID.
    """
    conversation = await db_service.get_or_create_conversation(db, user_id)

    if not conversation:
        print(f"Backend: No active conversation found for user {user_id}. Returning empty list.")
        return []

    chat_history = await db_service.get_messages_for_conversation(db, conversation.id)
    
    print(f"Backend: Successfully fetched {len(chat_history)} messages for user {user_id}.")
    return chat_history