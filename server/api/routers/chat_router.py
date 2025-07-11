# server/api/routers/chat_router.py
from fastapi import (
    APIRouter, UploadFile, File, Form, Depends, HTTPException, status, Response
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload # Import selectinload for eager loading
from typing import List, Optional
from uuid import UUID, uuid4 # Import uuid4 for generating new UUIDs
from datetime import datetime
import json
import base64

from api.schemas import (
    MessageRequest, AgentMessageRequest, ChatMessage,
    ConversationAssignmentRequest, ConversationUnassignmentRequest # NEW schemas
)
from config.gemini_config import gemini_model
from utils.kb_manager import knowledge_base
from utils.connection_manager import manager
from utils.ocr_processor import detect_text_from_image
# Removed: from auth.auth import current_active_user
from database import User, Conversation, Message, KnowledgeBaseArticle, get_async_session

router = APIRouter()

# -----------------------------------------------------------
# Gemini Prompt Construction
# -----------------------------------------------------------
def create_gemini_prompt(
    latest_user_message: str,
    full_chat_history: List[ChatMessage],
    knowledge_base_data: dict,
    ocr_text: Optional[str] = None
) -> str:
    """
    Build prompt for Gemini: combines history, OCR text, KB data into JSON-expected prompt.
    """
    all_intents = ", ".join(knowledge_base_data.keys())
    relevant_kb_info = ""
    text_for_kb = latest_user_message + (f" {ocr_text}" if ocr_text else "")

    for intent, kb_list in knowledge_base_data.items():
        if any(keyword.lower() in text_for_kb.lower() for keyword in intent.replace('_', ' ').split()):
            relevant_kb_info += f"\n--- Knowledge for {intent.replace('_', ' ').upper()} ---\n"
            relevant_kb_info += "\n".join(kb_list) + "\n"

    if not relevant_kb_info:
        relevant_kb_info = "No highly relevant knowledge base articles found. Provide general guidance."

    formatted_history = "\n".join(f"{msg.sender.capitalize()}: {msg.text}" for msg in full_chat_history)
    ocr_section = f"\n**OCR Extracted Text:**\n\"{ocr_text}\"\n" if ocr_text else ""

    prompt = f"""
You are an AI customer support assistant.

**Conversation History:**
{formatted_history}

**Latest Customer Message:** "{latest_user_message}"
{ocr_section}

**Instructions:**
- Predict intent from: {all_intents} (or "unclear_intent")
- Sentiment
- Entities
- Suggest pre-written response
- Recommend next actions

**Relevant Knowledge Base:**
{relevant_kb_info}

**Output JSON:**
```json
{{
  "predicted_intent": "string",
  "intent_confidence": "float",
  "sentiment": {{
    "label": "string",
    "score": "float"
  }},
  "detected_entities": [{{"text": "string", "label": "string"}}],
  "suggestions": {{
    "knowledge_base": ["string"],
    "pre_written_response": "string",
    "next_actions": ["string"]
  }},
  "ocr_extracted_text": "string"
}}
"""
    return prompt

# -----------------------------------------------------------
# Helpers
# -----------------------------------------------------------
async def get_or_create_user(db: AsyncSession, user_id: UUID, user_name: str) -> User:
    """
    Retrieves a user by ID, or creates a new one if not found.
    """
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        user = User(id=user_id, full_name=user_name)
        db.add(user)
        await db.commit()
        await db.refresh(user)
        print(f"Created new user (customer) {user.full_name} (ID: {user.id})")
    else:
        # Update user name if it changed
        if user.full_name != user_name:
            user.full_name = user_name
            await db.commit()
            await db.refresh(user)
            print(f"Updated user {user.id} name to {user.full_name}")
    return user

async def get_or_create_conversation(db: AsyncSession, user_id: UUID) -> Conversation:
    """
    Retrieves the latest open conversation for a given user, or creates a new one if none exists.
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .where(Conversation.status == "open")
        .order_by(Conversation.start_time.desc())
    )
    conversation = result.scalars().first()

    if not conversation:
        conversation = Conversation(user_id=user_id, status="open")
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        print(f"Created new conversation {conversation.id} for user {user_id}")
    else:
        print(f"Found existing open conversation {conversation.id} for user {user_id}")
    return conversation

async def save_message_to_db(
    db: AsyncSession,
    conversation_id: UUID,
    sender: str,
    text_content: str,
    image_url: Optional[str] = None,
    ocr_extracted_text: Optional[str] = None
) -> Message:
    """
    Save message to DB.
    """
    msg = Message(
        conversation_id=conversation_id,
        sender=sender,
        text_content=text_content,
        image_url=image_url,
        ocr_extracted_text=ocr_extracted_text,
        timestamp=datetime.now()
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    print(f"Saved message {msg.id} from {sender} to conversation {conversation_id}")
    return msg

# -----------------------------------------------------------
# Customer-Facing Routes (No Authentication Required)
# -----------------------------------------------------------
@router.post("/analyze-message")
async def analyze_message_endpoint(
    request: MessageRequest,  # Now includes customer_id and customer_name
    db: AsyncSession = Depends(get_async_session)
):
    """
    Analyze text message with Gemini, save & broadcast.
    """
    customer_id = request.customer_id
    customer_name = request.customer_name
    user_message = request.text
    full_chat_history = request.chat_history
    response_data = {}  # Initialize response_data

    # Ensure the user (customer) exists or create them
    customer_user = await get_or_create_user(db, customer_id, customer_name)
    print(f"Customer {customer_user.full_name} (ID: {customer_id}) sent message: '{user_message}'")

    conversation = await get_or_create_conversation(db, customer_id)

    await save_message_to_db(
        db,
        conversation.id,
        "customer",
        user_message
    )

    if not gemini_model:
        print("Gemini model not initialized in chat_router. Returning system error fallback.")
        response_data = {
            "user_message": user_message,
            "predicted_intent": "system_error",
            "intent_confidence": 0.0,
            "sentiment": {"label": "UNKNOWN", "score": 0.0},
            "suggestions": {
                "knowledge_base": ["System error: AI model not loaded. Please check server logs."],
                "pre_written_response": "I apologize, the AI assistant is currently experiencing technical difficulties. Please proceed manually.",
                "next_actions": ["Inform customer about AI issue.", "Provide manual assistance."]
            },
            "detected_entities": [],
            "timestamp": datetime.now().isoformat(),
            "ocr_extracted_text": ""
        }
    else:
        try:
            gemini_prompt = create_gemini_prompt(user_message, full_chat_history, knowledge_base)
            gemini_response = await gemini_model.generate_content_async(gemini_prompt)

            gemini_output_text = ""
            if gemini_response.candidates:
                for part in gemini_response.candidates[0].content.parts:
                    gemini_output_text += part.text
            else:
                raise ValueError("Gemini returned no candidates, possibly due to safety settings.")

            cleaned_json_str = gemini_output_text.strip()
            if cleaned_json_str.startswith("```json") and cleaned_json_str.endswith("```"):
                cleaned_json_str = cleaned_json_str[len("```json"): -len("```")].strip()

            parsed_gemini_data = json.loads(cleaned_json_str)

            response_data = {
                "user_message": user_message,
                "predicted_intent": parsed_gemini_data.get("predicted_intent", "unclear_intent"),
                "intent_confidence": parsed_gemini_data.get("intent_confidence", 0.5),
                "sentiment": parsed_gemini_data.get("sentiment", {"label": "NEUTRAL", "score": 0.5}),
                "suggestions": {
                    "knowledge_base": parsed_gemini_data.get("suggestions", {}).get("knowledge_base", []),
                    "pre_written_response": parsed_gemini_data.get("suggestions", {}).get("pre_written_response", "I'm sorry, I couldn't generate a specific response at this moment. Please check the customer's query and the available knowledge base."),
                    "next_actions": parsed_gemini_data.get("suggestions", {}).get("next_actions", [])
                },
                "detected_entities": parsed_gemini_data.get("detected_entities", []),
                "timestamp": datetime.now().isoformat(),
                "ocr_extracted_text": parsed_gemini_data.get("ocr_extracted_text", "")
            }

        except json.JSONDecodeError as e:
            print(f"JSON parsing error from Gemini response: {e}. Raw Gemini output: \n{gemini_output_text}")
            response_data = {
                "user_message": user_message,
                "predicted_intent": "parsing_error",
                "intent_confidence": 0.0,
                "sentiment": {"label": "UNKNOWN", "score": 0.0},
                "suggestions": {
                    "knowledge_base": ["AI response format error. Please check AI logs."],
                    "pre_written_response": "I apologize, there was an issue processing the AI's response. Please handle this request manually.",
                    "next_actions": ["Review AI output format.", "Manually assist customer."]
                },
                "detected_entities": [],
                "timestamp": datetime.now().isoformat(),
                "ocr_extracted_text": ""
            }
        except Exception as e:
            print(f"Error calling Gemini API or processing response: {e}")
            response_data = {
                "user_message": user_message,
                "predicted_intent": "api_error",
                "intent_confidence": 0.0,
                "sentiment": {"label": "UNKNOWN", "score": 0.0},
                "suggestions": {
                    "knowledge_base": ["Error contacting AI service. Please check network/API status."],
                    "pre_written_response": "I apologize, there was an issue connecting to the AI service. Please try again or provide manual assistance.",
                    "next_actions": ["Check AI service logs.", "Provide manual assistance."]
                },
                "detected_entities": [],
                "timestamp": datetime.now().isoformat(),
                "ocr_extracted_text": ""
            }

    # Broadcast to all connected agent UIs
    await manager.broadcast_to_agents(json.dumps({
        "type": "customer_message_analysis",
        "conversation_id": str(conversation.id),
        "user_id": str(customer_id),
        "user_name": customer_name,
        "original_message": user_message,
        "analysis": response_data
    }))

    # Broadcast original customer message
    await manager.broadcast_to_customers(json.dumps({
        "type": "customer_chat_message",
        "sender": "customer",
        "text": user_message,
        "timestamp": datetime.now().isoformat(),
        "image_url": None,
        "ocr_text": None
    }))

    return response_data

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
    customer_user = await get_or_create_user(db, customer_id, customer_name)
    print(f"Customer {customer_user.full_name} (ID: {customer_id}) sent image upload: {file.filename} with text: '{text}'")

    image_bytes = await file.read()
    ocr_extracted_text = await detect_text_from_image(image_bytes)

    full_chat_history: List[ChatMessage] = [
        ChatMessage(**msg) for msg in json.loads(chat_history_json)
    ]

    combined_message_for_gemini = text if text else ""
    if ocr_extracted_text:
        if combined_message_for_gemini:
            combined_message_for_gemini += f"\n(Text from screenshot: {ocr_extracted_text})"
        else:
            combined_message_for_gemini = f"Text from screenshot: {ocr_extracted_text}"

    if not combined_message_for_gemini.strip():
        combined_message_for_gemini = "Customer sent an image with no recognizable text or accompanying message."

    response_data = {}  # Initialize response_data

    conversation = await get_or_create_conversation(db, customer_id)

    image_base64_url = f"data:{file.content_type};base64,{base64.b64encode(image_bytes).decode('utf-8')}"
    await save_message_to_db(
        db,
        conversation.id,
        "customer",
        text or "Screenshot shared.",
        image_url=image_base64_url,
        ocr_extracted_text=ocr_extracted_text
    )

    if not gemini_model:
        print("Gemini model not initialized. Returning system error fallback.")
        response_data = {
            "user_message": combined_message_for_gemini,
            "predicted_intent": "system_error",
            "intent_confidence": 0.0,
            "sentiment": {"label": "UNKNOWN", "score": 0.0},
            "suggestions": {
                "knowledge_base": ["System error: AI model not loaded."],
                "pre_written_response": "I apologize, the AI assistant is currently experiencing technical difficulties. Please proceed manually.",
                "next_actions": ["Inform customer about AI issue.", "Provide manual assistance."]
            },
            "detected_entities": [],
            "timestamp": datetime.now().isoformat(),
            "image_url": image_base64_url,
            "ocr_extracted_text": ocr_extracted_text
        }
    else:
        try:
            gemini_prompt = create_gemini_prompt(
                latest_user_message=combined_message_for_gemini,
                full_chat_history=full_chat_history,
                knowledge_base_data=knowledge_base,
                ocr_text=ocr_extracted_text
            )
            gemini_response = await gemini_model.generate_content_async(gemini_prompt)

            gemini_output_text = ""
            if gemini_response.candidates:
                for part in gemini_response.candidates[0].content.parts:
                    gemini_output_text += part.text
            else:
                raise ValueError("Gemini returned no candidates, possibly due to safety settings.")

            cleaned_json_str = gemini_output_text.strip()
            if cleaned_json_str.startswith("```json") and cleaned_json_str.endswith("```"):
                cleaned_json_str = cleaned_json_str[len("```json"): -len("```")].strip()

            parsed_gemini_data = json.loads(cleaned_json_str)

            response_data = {
                "user_message": combined_message_for_gemini,
                "predicted_intent": parsed_gemini_data.get("predicted_intent", "unclear_intent"),
                "intent_confidence": parsed_gemini_data.get("intent_confidence", 0.5),
                "sentiment": parsed_gemini_data.get("sentiment", {"label": "NEUTRAL", "score": 0.5}),
                "suggestions": {
                    "knowledge_base": parsed_gemini_data.get("suggestions", {}).get("knowledge_base", []),
                    "pre_written_response": parsed_gemini_data.get("suggestions", {}).get("pre_written_response", "I'm sorry, I couldn't generate a specific response at this moment. Please check the customer's query and the available knowledge base."),
                    "next_actions": parsed_gemini_data.get("suggestions", {}).get("next_actions", [])
                },
                "detected_entities": parsed_gemini_data.get("detected_entities", []),
                "timestamp": datetime.now().isoformat(),
                "image_url": image_base64_url,
                "ocr_extracted_text": ocr_extracted_text
            }

        except json.JSONDecodeError as e:
            print(f"JSON parsing error from Gemini response: {e}. Raw Gemini output: \n{gemini_output_text}")
            response_data = {
                "user_message": combined_message_for_gemini,
                "predicted_intent": "parsing_error",
                "intent_confidence": 0.0,
                "sentiment": {"label": "UNKNOWN", "score": 0.0},
                "suggestions": {
                    "knowledge_base": ["AI response format error. Please check AI logs."],
                    "pre_written_response": "I apologize, there was an issue processing the AI's response. Please handle this request manually.",
                    "next_actions": ["Review AI output format.", "Manually assist customer."]
                },
                "detected_entities": [],
                "timestamp": datetime.now().isoformat(),
                "image_url": image_base64_url,
                "ocr_extracted_text": ocr_extracted_text
            }
        except Exception as e:
            print(f"Error calling Gemini API or processing image: {e}")
            response_data = {
                "user_message": combined_message_for_gemini,
                "predicted_intent": "api_error",
                "intent_confidence": 0.0,
                "sentiment": {"label": "UNKNOWN", "score": 0.0},
                "suggestions": {
                    "knowledge_base": ["Error processing image with AI service. Please check network/API status."],
                    "pre_written_response": "I apologize, there was an issue processing the image with the AI service. Please try again or provide manual assistance.",
                    "next_actions": ["Check AI service logs.", "Provide manual assistance."]
                },
                "detected_entities": [],
                "timestamp": datetime.now().isoformat(),
                "image_url": image_base64_url,
                "ocr_extracted_text": ocr_extracted_text
            }

    # Broadcast to all connected agent UIs
    await manager.broadcast_to_agents(json.dumps({
        "type": "customer_message_analysis",
        "conversation_id": str(conversation.id),
        "user_id": str(customer_id),
        "user_name": customer_name,
        "original_message": combined_message_for_gemini,
        "image_url": response_data.get("image_url"),
        "ocr_text": response_data.get("ocr_extracted_text"),
        "analysis": response_data
    }))

    # Broadcast to customer UIs
    await manager.broadcast_to_customers(json.dumps({
        "type": "customer_chat_message",
        "sender": "customer",
        "text": text or "Screenshot shared.",
        "timestamp": datetime.now().isoformat(),
        "image_url": image_base64_url,
        "ocr_text": ocr_extracted_text
    }))

    return response_data
# -----------------------------------------------------------
# Agent-Facing Routes (No Authentication Required for Demo)
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
    agent_name = request.agent_name  # NEW: Get agent name from request
    conversation_id = request.conversation_id

    print(f"Agent '{agent_name}' (ID: {agent_id}) sent: '{agent_message}' to conversation {conversation_id}")

    await save_message_to_db(
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

    await manager.broadcast_to_customers(message_to_broadcast)
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

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalars().first()

    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if conversation.assigned_agent_id and conversation.assigned_agent_id != agent_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Conversation already assigned to {conversation.assigned_agent_name}")

    conversation.assigned_agent_id = agent_id
    conversation.assigned_agent_name = agent_name
    await db.commit()
    await db.refresh(conversation)

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

    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalars().first()

    if not conversation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

    if not conversation.assigned_agent_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Conversation is not currently assigned")

    old_agent_id = conversation.assigned_agent_id
    old_agent_name = conversation.assigned_agent_name

    conversation.assigned_agent_id = None
    conversation.assigned_agent_name = None
    await db.commit()
    await db.refresh(conversation)

    print(f"Conversation {conversation_id} unassigned from Agent {old_agent_name} (ID: {old_agent_id})")

    await manager.broadcast_to_agents(json.dumps({
        "type": "conversation_unassigned",
        "conversation_id": str(conversation.id),
        "unassigned_agent_id": str(old_agent_id),
        "unassigned_agent_name": old_agent_name
    }))

    return {"status": "success", "message": "Conversation unassigned", "conversation_id": str(conversation.id)}
@router.get("/conversations/active")
async def get_active_conversations(db: AsyncSession = Depends(get_async_session)):
    """
    Get all active conversations, including user and agent assignment details.
    """
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.user))
        .where(Conversation.status == "open")
        .order_by(Conversation.start_time.desc())
    )
    conversations = result.scalars().all()

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
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)
    )
    messages = messages_result.scalars().all()

    chat_history = []
    for msg in messages:
        chat_history.append(ChatMessage(
            text=msg.text_content,
            sender=msg.sender,
            timestamp=msg.timestamp.isoformat(),
            image_url=msg.image_url,
            ocr_text=msg.ocr_extracted_text
        ))

    return chat_history


@router.get("/chat-history/user/{user_id}", response_model=List[ChatMessage])
async def get_chat_history_for_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Latest chat history for a specific user ID.
    """
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .where(Conversation.status == "open")
        .order_by(Conversation.start_time.desc())
        .limit(1)
    )
    conversation = result.scalars().first()

    if not conversation:
        print(f"Backend: No active conversation found for user {user_id}. Returning empty list.")
        return []

    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.timestamp)
    )
    messages = messages_result.scalars().all()

    chat_history = []
    for msg in messages:
        chat_history.append(ChatMessage(
            text=msg.text_content,
            sender=msg.sender,
            timestamp=msg.timestamp.isoformat(),
            image_url=msg.image_url,
            ocr_text=msg.ocr_extracted_text
        ))

    print(f"Backend: Successfully fetched {len(chat_history)} messages for user {user_id}.")
    return chat_history


# -----------------------------------------------------------
# Knowledge Base Article Management (Demo, should be secured)
# -----------------------------------------------------------

@router.post("/kb/articles", status_code=status.HTTP_201_CREATED)
async def create_kb_article(
    title: str = Form(...),
    content: str = Form(...),
    tags: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_async_session)
):
    """
    Create KB article.
    """
    article = KnowledgeBaseArticle(title=title, content=content, tags=tags)
    db.add(article)
    await db.commit()
    await db.refresh(article)
    return {"message": "Knowledge base article created successfully", "article_id": str(article.id)}


@router.get("/kb/articles", response_model=List[dict])
async def get_kb_articles(db: AsyncSession = Depends(get_async_session)):
    """
    List KB articles.
    """
    result = await db.execute(select(KnowledgeBaseArticle).order_by(KnowledgeBaseArticle.title))
    articles = result.scalars().all()
    return [{"id": str(a.id), "title": a.title, "content": a.content, "tags": a.tags, "last_updated": a.last_updated.isoformat()} for a in articles]


@router.delete("/kb/articles/{article_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_kb_article(
    article_id: UUID,
    db: AsyncSession = Depends(get_async_session)
):
    """
    Delete KB article by ID.
    """
    result = await db.execute(select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.id == article_id))
    article = result.scalars().first()
    if not article:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Article not found")

    await db.delete(article)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
