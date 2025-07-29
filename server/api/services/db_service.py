# server/api/services/db_service.py
import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, desc # Import func and desc for aggregation and ordering
from sqlalchemy.orm import selectinload # Keep this for get_active_conversations_from_db
from uuid import UUID, uuid4
from datetime import datetime
from typing import Optional, List, Dict

from database import User, Conversation, Message, KnowledgeBaseArticle, Ticket # Import Ticket model
from api.schemas import ChatMessage, TicketResponse, CustomerOverviewItem # Import CustomerOverviewItem

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
        print(f"DB Service: Created new user (customer) {user.full_name} (ID: {user.id})")
    else:
        if user.full_name != user_name:
            user.full_name = user_name
            await db.commit()
            await db.refresh(user)
            print(f"DB Service: Updated user {user.id} name to {user.full_name}")
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
        print(f"DB Service: Created new conversation {conversation.id} for user {user_id}")
    else:
        print(f"DB Service: Found existing open conversation {conversation.id} for user {user_id}")
    return conversation

async def save_message_to_db(
    db: AsyncSession,
    conversation_id: UUID,
    sender: str,
    text_content: str,
    image_url: Optional[str] = None,
    ocr_extracted_text: Optional[str] = None,
    predicted_intent: Optional[str] = None,
    intent_confidence: Optional[float] = None,
    sentiment_label: Optional[str] = None,
    sentiment_score: Optional[float] = None,
    suggestions: Optional[dict] = None,
    detected_entities: Optional[List[dict]] = None
) -> Message:
    """
    Save message to DB, including AI analysis results if provided.
    """
    suggestions_json = json.dumps(suggestions) if suggestions else None
    detected_entities_json = json.dumps(detected_entities) if detected_entities else None

    msg = Message(
        conversation_id=conversation_id,
        sender=sender,
        text_content=text_content,
        timestamp=datetime.now(),
        image_url=image_url,
        ocr_extracted_text=ocr_extracted_text,
        predicted_intent=predicted_intent,
        intent_confidence=intent_confidence,
        sentiment_label=sentiment_label,
        sentiment_score=sentiment_score,
        suggestions_json=suggestions_json,
        detected_entities_json=detected_entities_json
    )
    db.add(msg)
    await db.commit()
    await db.refresh(msg)
    print(f"DB Service: Saved message {msg.id} from {sender} to conversation {conversation_id}")
    return msg

async def get_conversation_by_id(db: AsyncSession, conversation_id: UUID) -> Optional[Conversation]:
    """Retrieves a conversation by its ID."""
    result = await db.execute(select(Conversation).where(Conversation.id == conversation_id))
    return result.scalars().first()

async def get_messages_for_conversation(db: AsyncSession, conversation_id: UUID) -> List[ChatMessage]:
    """Retrieves all messages for a given conversation ID, ordered by timestamp,
       and maps them to ChatMessage schema, including deserialized AI analysis."""
    messages_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.timestamp)
    )
    messages = messages_result.scalars().all()

    chat_history = []
    for msg in messages:
        predicted_intent = None
        intent_confidence = None
        sentiment_data = None
        suggestions_data = None
        detected_entities_data = None

        if msg.sender == "customer":
            predicted_intent = msg.predicted_intent
            intent_confidence = msg.intent_confidence
            
            if msg.sentiment_label and msg.sentiment_score is not None:
                sentiment_data = {"label": msg.sentiment_label, "score": msg.sentiment_score}
            
            if msg.suggestions_json:
                try:
                    suggestions_data = json.loads(msg.suggestions_json)
                except json.JSONDecodeError:
                    print(f"DB Service: Error decoding suggestions_json for message {msg.id}: {msg.suggestions_json}")
                    suggestions_data = None
            
            if msg.detected_entities_json:
                try:
                    detected_entities_data = json.loads(msg.detected_entities_json)
                except json.JSONDecodeError:
                    print(f"DB Service: Error decoding detected_entities_json for message {msg.id}: {msg.detected_entities_json}")
                    detected_entities_data = None

        analysis_dict = None
        if predicted_intent or sentiment_data or suggestions_data or detected_entities_data or msg.ocr_extracted_text:
            analysis_dict = {
                "predicted_intent": predicted_intent,
                "intent_confidence": intent_confidence,
                "sentiment": sentiment_data,
                "suggestions": suggestions_data,
                "detected_entities": detected_entities_data,
                "ocr_extracted_text": msg.ocr_extracted_text
            }

        chat_history.append(ChatMessage(
            text=msg.text_content,
            sender=msg.sender,
            timestamp=msg.timestamp.isoformat(),
            image_url=msg.image_url,
            ocr_text=msg.ocr_extracted_text,
            analysis=analysis_dict
        ))
    
    print(f"DB Service: Fetched and mapped {len(chat_history)} messages for conversation {conversation_id}.")
    return chat_history

async def get_active_conversations_from_db(db: AsyncSession) -> List[Conversation]:
    """Retrieves all active conversations."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.user))
        .where(Conversation.status == "open")
        .order_by(Conversation.start_time.desc())
    )
    return result.scalars().all()

async def update_conversation_assignment(db: AsyncSession, conversation_id: UUID, agent_id: Optional[UUID], agent_name: Optional[str]) -> Conversation:
    """Updates the agent assignment for a conversation."""
    conversation = await get_conversation_by_id(db, conversation_id)
    if not conversation:
        raise ValueError("Conversation not found")
    conversation.assigned_agent_id = agent_id
    conversation.assigned_agent_name = agent_name
    await db.commit()
    await db.refresh(conversation)
    return conversation

# Ticket DB Operations
async def create_ticket_in_db(
    db: AsyncSession,
    conversation_id: UUID,
    raised_by_agent_id: UUID,
    raised_by_agent_name: str,
    issue_description: str,
    priority: str = "Medium"
) -> Ticket:
    """Creates a new ticket in the database."""
    ticket = Ticket(
        conversation_id=conversation_id,
        raised_by_agent_id=raised_by_agent_id,
        raised_by_agent_name=raised_by_agent_name,
        issue_description=issue_description,
        priority=priority,
        status="Open", # Default status
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    print(f"DB Service: Created new ticket {ticket.id} for conversation {conversation_id}")
    return ticket

async def get_tickets_for_conversation(db: AsyncSession, conversation_id: UUID) -> List[TicketResponse]:
    """Retrieves all tickets associated with a given conversation."""
    result = await db.execute(
        select(Ticket)
        .where(Ticket.conversation_id == conversation_id)
        .order_by(Ticket.created_at.desc())
    )
    tickets = result.scalars().all()
    return [TicketResponse.from_orm(ticket) for ticket in tickets]


# NEW: Customer Overview Data Fetching
async def get_customer_overview_data(db: AsyncSession) -> List[CustomerOverviewItem]:
    """
    Retrieves a comprehensive overview of all customers, their latest conversation,
    and associated ticket information.
    """
    # Subquery to get the latest conversation for each user
    latest_conversation_subquery = (
        select(
            Conversation.user_id,
            func.max(Conversation.start_time).label("max_start_time")
        )
        .group_by(Conversation.user_id)
        .subquery()
    )

    # Subquery to get the latest message for each conversation
    latest_message_subquery = (
        select(
            Message.conversation_id,
            Message.text_content,
            func.max(Message.timestamp).label("max_timestamp")
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    # Subquery to get ticket counts and latest ticket for each conversation
    # Note: SQLite doesn't have a direct "last" aggregate, so we order and limit within a subquery
    latest_ticket_subquery = (
        select(
            Ticket.conversation_id,
            Ticket.issue_description,
            Ticket.status,
            Ticket.priority,
            func.max(Ticket.created_at).label("max_ticket_time")
        )
        .group_by(Ticket.conversation_id)
        .subquery()
    )

    # Main query to join User, Conversation, Message, and Ticket data
    query = (
        select(
            User.id.label("user_id"),
            User.full_name.label("user_name"),
            Conversation.id.label("latest_conversation_id"),
            Conversation.start_time.label("latest_conversation_start_time"),
            Conversation.status.label("latest_conversation_status"),
            Message.text_content.label("latest_message_summary"),
            Conversation.assigned_agent_name.label("assigned_agent_name"),
            func.count(Ticket.id).filter(Ticket.status == "Open").label("open_tickets_count"), # Count open tickets
            latest_ticket_subquery.c.issue_description.label("latest_ticket_issue"),
            latest_ticket_subquery.c.status.label("latest_ticket_status"),
            latest_ticket_subquery.c.priority.label("latest_ticket_priority")
        )
        .outerjoin(latest_conversation_subquery, User.id == latest_conversation_subquery.c.user_id)
        .outerjoin(Conversation, (User.id == Conversation.user_id) & (Conversation.start_time == latest_conversation_subquery.c.max_start_time))
        .outerjoin(latest_message_subquery, Conversation.id == latest_message_subquery.c.conversation_id)
        .outerjoin(latest_ticket_subquery, Conversation.id == latest_ticket_subquery.c.conversation_id)
        .group_by(User.id, User.full_name, Conversation.id, Conversation.start_time, Conversation.status, Message.text_content, Conversation.assigned_agent_name, latest_ticket_subquery.c.issue_description, latest_ticket_subquery.c.status, latest_ticket_subquery.c.priority)
        .order_by(desc(latest_conversation_subquery.c.max_start_time))
    )

    result = await db.execute(query)
    rows = result.all()

    overview_items = []
    for row in rows:
        overview_items.append(CustomerOverviewItem(
            user_id=row.user_id,
            user_name=row.user_name,
            latest_conversation_id=row.latest_conversation_id,
            latest_conversation_start_time=row.latest_conversation_start_time,
            latest_conversation_status=row.latest_conversation_status,
            latest_message_summary=row.latest_message_summary,
            assigned_agent_name=row.assigned_agent_name,
            open_tickets_count=row.open_tickets_count,
            latest_ticket_issue=row.latest_ticket_issue,
            latest_ticket_status=row.latest_ticket_status,
            latest_ticket_priority=row.latest_ticket_priority
        ))
    
    return overview_items