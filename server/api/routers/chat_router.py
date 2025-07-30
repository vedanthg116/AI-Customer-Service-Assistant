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
import os # NEW: Import os for file extension check

# Import from new service files
from api.services.ai_service import ai_service
from api.services import db_service
from api.schemas import (
    MessageRequest, AgentMessageRequest, ChatMessage,
    ConversationAssignmentRequest, ConversationUnassignmentRequest,
    RaiseTicketRequest, TicketResponse,
    CustomerOverviewItem,
    RecordedCallRequest, MarkTicketFixedRequest, ProcessRecordedCallAudioRequest # NEW: Import ProcessRecordedCallAudioRequest
)
from utils.connection_manager import manager
from database import get_async_session, Conversation, Message # Import Message for last_message_summary
from database import User # Import User for search_customer_by_name_endpoint
from api.services.speech_service import speech_service # NEW: Import speech service instance

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
    saved_message = await db_service.save_message_to_db( # Get the saved message object
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
        "analysis": analysis_result,
        "message_id": str(saved_message.id) # Include message ID for customer messages too
    }))

    # Send the original customer message ONLY to the specific customer's WebSocket
    # Use saved_message.timestamp for consistency with DB
    await manager.send_to_customer(customer_id, json.dumps({
        "type": "customer_chat_message",
        "sender": "customer",
        "text": user_message,
        "timestamp": saved_message.timestamp.isoformat(), # FIX: Use saved_message's timestamp
        "image_url": None,
        "ocr_text": analysis_result.get("ocr_extracted_text"),
        "message_id": str(saved_message.id) # Include message ID
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
    
    saved_message = await db_service.save_message_to_db( # Get the saved message object
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
        "original_message": text or "Screenshot shared.", # Use the actual text or default
        "image_url": image_base64_url,
        "ocr_text": analysis_result.get("ocr_extracted_text"),
        "analysis": analysis_result,
        "message_id": str(saved_message.id) # Include message ID
    }))

    # Send the original customer message ONLY to the specific customer's WebSocket
    # Use saved_message.timestamp for consistency with DB
    await manager.send_to_customer(customer_id, json.dumps({
        "type": "customer_chat_message",
        "sender": "customer",
        "text": text or "Screenshot shared.",
        "timestamp": saved_message.timestamp.isoformat(), # FIX: Use saved_message's timestamp
        "image_url": image_base64_url,
        "ocr_text": analysis_result.get("ocr_extracted_text"),
        "message_id": str(saved_message.id) # Include message ID
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

    saved_message = await db_service.save_message_to_db( # Get the saved message object
        db,
        conversation_id,
        "agent",
        agent_message
    )

    message_to_broadcast = json.dumps({
        "type": "agent_chat_message",
        "sender": "agent",
        "text": agent_message,
        "timestamp": saved_message.timestamp.isoformat(), # FIX: Use saved_message's timestamp
        "agent_id": str(agent_id),
        "agent_name": agent_name,
        "conversation_id": str(conversation_id),
        "message_id": str(saved_message.id) # NEW: Include the message ID
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

# Customer Overview Endpoint
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

# NEW: Recorded Call Transcription Endpoint
@router.post("/process-recorded-call", status_code=status.HTTP_200_OK)
async def process_recorded_call_endpoint(
    request: RecordedCallRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Receives a recorded call transcription, analyzes it, saves it as a customer message,
    and broadcasts the analysis to agents.
    """
    customer_id = request.customer_id
    customer_name = request.customer_name
    transcription_text = request.transcription_text

    customer_user = await db_service.get_or_create_user(db, customer_id, customer_name)
    print(f"Received recorded call transcription for customer {customer_user.full_name} (ID: {customer_id})")

    conversation = await db_service.get_or_create_conversation(db, customer_id)

    # Perform AI analysis on the transcription
    # For a recorded call, the chat history might be empty or just previous messages from this call
    # For simplicity, we'll pass an empty list for full_chat_history here, assuming it's a new interaction
    # or the model doesn't need prior chat context for this specific analysis.
    analysis_result = await ai_service.analyze_transcription(
        transcription_text=transcription_text,
        full_chat_history=[] # No prior chat history for this specific transcription analysis context
    )

    saved_message = await db_service.save_message_to_db( # Get the saved message object
        db,
        conversation.id,
        "customer",
        transcription_text,
        ocr_extracted_text=analysis_result.get("ocr_extracted_text"), # Will be empty string for transcription
        predicted_intent=analysis_result.get("predicted_intent"),
        intent_confidence=analysis_result.get("intent_confidence"),
        sentiment_label=analysis_result.get("sentiment", {}).get("label"),
        sentiment_score=analysis_result.get("sentiment", {}).get("score"),
        suggestions=analysis_result.get("suggestions"),
        detected_entities=analysis_result.get("detected_entities")
    )

    # Broadcast the analysis to all connected agent UIs
    await manager.broadcast_to_agents(json.dumps({
        "type": "customer_message_analysis",
        "conversation_id": str(conversation.id),
        "user_id": str(customer_id),
        "user_name": customer_name,
        "original_message": transcription_text, # The transcription itself is the "original message"
        "analysis": analysis_result,
        "message_id": str(saved_message.id) # Include message ID
    }))

    # Also send the transcription message to the specific customer's WebSocket
    await manager.send_to_customer(customer_id, json.dumps({
        "type": "customer_chat_message",
        "sender": "customer",
        "text": transcription_text,
        "timestamp": saved_message.timestamp.isoformat(), # Use saved_message's timestamp
        "image_url": None,
        "ocr_text": analysis_result.get("ocr_extracted_text"),
        "message_id": str(saved_message.id)
    }))


    return {"status": "success", "message": "Recorded call transcription processed successfully."}

# NEW: Search Customer by Name Endpoint
@router.get("/search-customer/{customer_name}")
async def search_customer_by_name_endpoint(
    customer_name: str,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Search for an existing customer by name and return their ID if found.
    """
    # Decode the URL-encoded customer name
    import urllib.parse
    decoded_name = urllib.parse.unquote(customer_name)
    
    print(f"Searching for customer with name: {decoded_name}")
    
    # Search for customer by name
    result = await db.execute(
        select(User)
        .where(User.full_name == decoded_name)
        .order_by(User.id)  # Get the first/oldest user with this name
    )
    customer = result.scalars().first()
    
    if customer:
        print(f"Found existing customer: {customer.full_name} (ID: {customer.id})")
        return {
            "customer_id": str(customer.id),
            "customer_name": customer.full_name,
            "found": True
        }
    else:
        print(f"No existing customer found with name: {decoded_name}")
        return {
            "customer_id": None,
            "customer_name": decoded_name,
            "found": False
        }

# NEW: Mark Ticket as Fixed Endpoint
@router.post("/mark-ticket-fixed", status_code=status.HTTP_200_OK)
async def mark_ticket_fixed_endpoint(
    request: MarkTicketFixedRequest,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Marks a ticket as fixed and sends an automatic message to the customer.
    """
    conversation_id = request.conversation_id
    agent_id = request.agent_id
    agent_name = request.agent_name
    ticket_issue = request.ticket_issue
    customer_name = request.customer_name

    print(f"Marking ticket as fixed for conversation {conversation_id} by agent {agent_name}")

    # Get the conversation to find the customer ID
    conversation = await db_service.get_conversation_by_id(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    customer_id = conversation.user_id

    # Check if conversation is assigned to another agent
    if conversation.assigned_agent_name and conversation.assigned_agent_name != agent_name:
        raise HTTPException(
            status_code=403, 
            detail=f"This conversation is assigned to {conversation.assigned_agent_name}. Only the assigned agent can mark tickets as fixed."
        )

    # Update the ticket status to "Resolved"
    updated_ticket = await db_service.update_ticket_status(db, conversation_id, "Resolved")
    if not updated_ticket:
        raise HTTPException(status_code=404, detail="No open ticket found for this conversation")

    # Create an automatic message to the customer
    auto_message = f"Hi {customer_name}! Great news - your issue regarding '{ticket_issue}' has been resolved. Thank you for your patience, and please don't hesitate to reach out if you need any further assistance. Best regards, {agent_name}"

    # Save the automatic message to the database
    saved_message = await db_service.save_message_to_db(
        db,
        conversation_id,
        "agent",
        auto_message
    )

    # Send the message to the customer via WebSocket
    await manager.send_to_customer(customer_id, json.dumps({
        "type": "customer_chat_message",
        "sender": "agent",
        "text": auto_message,
        "timestamp": saved_message.timestamp.isoformat(),
        "image_url": None,
        "ocr_text": None,
        "message_id": str(saved_message.id)
    }))

    # Broadcast to all agents that a ticket was resolved
    await manager.broadcast_to_agents(json.dumps({
        "type": "ticket_resolved",
        "conversation_id": str(conversation_id),
        "user_id": str(customer_id),
        "user_name": customer_name,
        "agent_name": agent_name,
        "ticket_issue": ticket_issue
    }))

    return {
        "status": "success", 
        "message": "Ticket marked as fixed and customer notified",
        "ticket_id": str(updated_ticket.id),
        "auto_message": auto_message
    }

# NEW: Process Recorded Call with Audio File Endpoint
@router.post("/process-recorded-call-audio", status_code=status.HTTP_200_OK)
async def process_recorded_call_audio_endpoint(
    audio_file: UploadFile = File(...),
    customer_id: UUID = Form(...),
    customer_name: str = Form(...),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Receives a recorded call audio file, transcribes it using Azure Speech Service,
    analyzes it with AI, saves it as a customer message, and broadcasts the analysis to agents.
    """
    # Validate audio file
    if not audio_file.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")
    
    # Check file extension
    allowed_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
    file_extension = os.path.splitext(audio_file.filename)[1].lower()
    if file_extension not in allowed_extensions:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported audio format. Supported formats: {', '.join(allowed_extensions)}"
        )
    
    print(f"Processing recorded call audio for customer {customer_name} (ID: {customer_id})")
    print(f"Audio file: {audio_file.filename} ({file_extension})")
    
    try:
        # Step 1: Transcribe audio to text
        print("Starting speech-to-text transcription...")
        transcription_text = await speech_service.transcribe_audio_file(audio_file)
        
        if not transcription_text:
            raise HTTPException(
                status_code=400, 
                detail="No speech detected in the audio file or transcription failed"
            )
        
        print(f"Transcription completed: {transcription_text[:100]}...")
        
        # Step 2: Get or create customer and conversation
        customer_user = await db_service.get_or_create_user(db, customer_id, customer_name)
        conversation = await db_service.get_or_create_conversation(db, customer_id, source="recorded_call")
        
        # Step 3: Perform AI analysis on the transcription
        analysis_result = await ai_service.analyze_transcription(
            transcription_text=transcription_text,
            full_chat_history=[] # No prior chat history for this specific transcription analysis context
        )
        
        # Step 4: Save the transcribed message to database
        saved_message = await db_service.save_message_to_db(
            db,
            conversation.id,
            "customer",
            transcription_text,
            ocr_extracted_text=None, # No OCR for audio transcription
            predicted_intent=analysis_result.get("predicted_intent"),
            intent_confidence=analysis_result.get("intent_confidence"),
            sentiment_label=analysis_result.get("sentiment", {}).get("label"),
            sentiment_score=analysis_result.get("sentiment", {}).get("score"),
            suggestions=analysis_result.get("suggestions"),
            detected_entities=analysis_result.get("detected_entities")
        )
        
        # Step 5: Broadcast the analysis to all connected agent UIs
        await manager.broadcast_to_agents(json.dumps({
            "type": "customer_message_analysis",
            "conversation_id": str(conversation.id),
            "user_id": str(customer_id),
            "user_name": customer_name,
            "original_message": transcription_text,
            "analysis": analysis_result,
            "message_id": str(saved_message.id),
            "source": "recorded_call_audio" # Indicate this came from audio transcription
        }))
        
        # Step 6: Send the transcription message to the specific customer's WebSocket
        await manager.send_to_customer(customer_id, json.dumps({
            "type": "customer_chat_message",
            "sender": "customer",
            "text": transcription_text,
            "timestamp": saved_message.timestamp.isoformat(),
            "image_url": None,
            "ocr_text": None,
            "message_id": str(saved_message.id)
        }))
        
        return {
            "status": "success", 
            "message": "Recorded call audio processed successfully",
            "transcription": transcription_text,
            "analysis": analysis_result,
            "conversation_id": str(conversation.id),
            "message_id": str(saved_message.id)
        }
        
    except Exception as e:
        print(f"Error processing recorded call audio: {str(e)}")
        if "Azure Speech Service credentials not configured" in str(e):
            raise HTTPException(
                status_code=500, 
                detail="Speech-to-text service not configured. Please check Azure Speech Service credentials."
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Error processing audio file: {str(e)}"
            )

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
            "assigned_agent_name": conv.assigned_agent_name,
            "source": conv.source or "live_chat"  # Include source information
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

