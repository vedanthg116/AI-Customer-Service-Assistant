# server/api/routers/chat_router.py
from fastapi import APIRouter
import json
from datetime import datetime
from typing import List  # Import List

# Import models/schemas and utilities
# Modified: Import ChatMessage as well
from api.schemas import MessageRequest, AgentMessageRequest, ChatMessage
from config.gemini_config import gemini_model
from utils.kb_manager import knowledge_base
from utils.connection_manager import manager

router = APIRouter()

# --- Gemini Prompt Construction Function ---
# Modified to accept chat_history
def create_gemini_prompt(
    latest_user_message: str,
    full_chat_history: List[ChatMessage],
    knowledge_base_data: dict
) -> str:
    """
    Constructs a detailed prompt for the Gemini LLM, including the full conversation history
    for contextual analysis, and requests structured JSON output.
    """
    all_intents = ", ".join(knowledge_base_data.keys())
    relevant_kb_info = ""

    # Simple RAG: still based on keywords, but could be extended to analyze history too.
    # For now, let's keep it based on keywords in the *latest message* for finding KB.
    for intent_key, kb_list in knowledge_base_data.items():
        if any(keyword.lower() in latest_user_message.lower() for keyword in intent_key.replace('_', ' ').split()):
            relevant_kb_info += f"\n--- Knowledge for {intent_key.replace('_', ' ').upper()} ---\n"
            relevant_kb_info += "\n".join(kb_list) + "\n"
    if not relevant_kb_info:
        relevant_kb_info = "No highly relevant specific knowledge base articles found based on keywords. Provide a general helpful response."

    # Format the chat history into a string for the prompt
    formatted_history = ""
    for msg in full_chat_history:
        # Use a simple "Speaker: Message" format
        formatted_history += f"{msg.sender.capitalize()}: {msg.text}\n"

    # Crucially, instruct Gemini to consider the full history for analysis.
    prompt = f"""
    You are an AI-powered customer service assistant designed to help human agents.
    Your task is to analyze customer messages within the context of the full conversation and provide structured information and a draft response.

    **Full Conversation History (most recent message is the last one):**
    {formatted_history}

    **Latest Customer Message (the one to analyze for immediate action):** "{latest_user_message}"

    **Instructions:**
    1.  **Identify the primary intent** of the *latest customer message* within the context of the full conversation from the following list: {all_intents}. If no clear intent matches, choose "unclear_intent".
    2.  **Determine the overall sentiment** of the *entire conversation from the customer's perspective so far*: "POSITIVE", "NEGATIVE", or "NEUTRAL".
    3.  **Extract relevant entities**: From the *latest customer message* (or overall conversation if globally relevant, e.g., order ID mentioned early), look for common entities like order numbers (e.g., "ORD12345", "12345"), dates (e.g., "tomorrow", "June 25th"), email addresses, phone numbers, product names, addresses, etc. Provide `text` and `label` for each entity as a list of objects.
    4.  **Draft a concise and helpful pre-written response** for the agent to use. Base this response on the identified intent of the latest message and the provided knowledge base information. Keep it professional, empathetic, and directly address the customer's query within the conversation's context.
    5.  **Suggest 2-3 specific next actions** the human agent should take based on the latest message, its intent, and the overall conversation flow.

    **Contextual Knowledge Base (Relevant sections provided based on *latest message* keywords):**
    {relevant_kb_info}

    **Output Format:** Provide your analysis as a JSON object only. Ensure all specified fields are present and correctly typed. The "confidence" scores for intent and sentiment should be a float estimation of clarity/certainty (e.g., 0.95 for high clarity, 0.5 for unclear).

    ```json
    {{
      "predicted_intent": "string",
      "intent_confidence": "float",
      "sentiment": {{
        "label": "string",
        "score": "float"
      }},
      "detected_entities": [
        {{"text": "string", "label": "string"}}
      ],
      "suggestions": {{
        "knowledge_base": ["string"],
        "pre_written_response": "string",
        "next_actions": ["string"]
      }}
    }}
    """
    return prompt

@router.post("/analyze-message")
async def analyze_message_endpoint(request: MessageRequest):
    # Modified: Access latest_user_message and chat_history from the request
    latest_user_message = request.text
    full_chat_history = request.chat_history  # This will be a List[ChatMessage]
    response_data = {}
    if not gemini_model:
        print("Gemini model not initialized in chat_router. Returning system error fallback.")
        response_data = {
            "user_message": latest_user_message,
            "predicted_intent": "system_error",
            "intent_confidence": 0.0,
            "sentiment": {"label": "UNKNOWN", "score": 0.0},
            "suggestions": {
                "knowledge_base": ["System error: AI model not loaded. Please check server logs."],
                "pre_written_response": "I apologize, the AI assistant is currently experiencing technical difficulties. Please proceed manually.",
                "next_actions": ["Inform customer about AI issue.", "Provide manual assistance."]
            },
            "detected_entities": [],
            "timestamp": datetime.now().isoformat()
        }
    else:
        try:
            # Modified: Pass full_chat_history to the prompt function
            gemini_prompt = create_gemini_prompt(latest_user_message, full_chat_history, knowledge_base)
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
                "user_message": latest_user_message,  # Still the latest message for direct display
                "predicted_intent": parsed_gemini_data.get("predicted_intent", "unclear_intent"),
                "intent_confidence": parsed_gemini_data.get("intent_confidence", 0.5),
                "sentiment": parsed_gemini_data.get("sentiment", {"label": "NEUTRAL", "score": 0.5}),
                "suggestions": {
                    "knowledge_base": parsed_gemini_data.get("suggestions", {}).get("knowledge_base", []),
                    "pre_written_response": parsed_gemini_data.get("suggestions", {}).get("pre_written_response", "I'm sorry, I couldn't generate a specific response at this moment. Please check the customer's query and the available knowledge base."),
                    "next_actions": parsed_gemini_data.get("suggestions", {}).get("next_actions", [])
                },
                "detected_entities": parsed_gemini_data.get("detected_entities", []),
                "timestamp": datetime.now().isoformat()
            }

        except json.JSONDecodeError as e:
            print(f"JSON parsing error from Gemini response: {e}. Raw Gemini output: \n{gemini_output_text}")
            response_data = {
                "user_message": latest_user_message,
                "predicted_intent": "parsing_error",
                "intent_confidence": 0.0,
                "sentiment": {"label": "UNKNOWN", "score": 0.0},
                "suggestions": {
                    "knowledge_base": ["AI response format error. Please check AI logs."],
                    "pre_written_response": "I apologize, there was an issue processing the AI's response. Please handle this request manually.",
                    "next_actions": ["Review AI output format.", "Manually assist customer."]
                },
                "detected_entities": [],
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error calling Gemini API or processing response: {e}")
            response_data = {
                "user_message": latest_user_message,
                "predicted_intent": "api_error",
                "intent_confidence": 0.0,
                "sentiment": {"label": "UNKNOWN", "score": 0.0},
                "suggestions": {
                    "knowledge_base": ["Error contacting AI service. Please check network/API status."],
                    "pre_written_response": "I apologize, there was an issue connecting to the AI service. Please try again or provide manual assistance.",
                    "next_actions": ["Check AI service logs.", "Provide manual assistance."]
                },
                "detected_entities": [],
                "timestamp": datetime.now().isoformat()
            }

    await manager.broadcast_to_agents(json.dumps({
        "type": "customer_message_analysis",
        "original_message": latest_user_message,  # Still sending original message for agent dashboard
        "analysis": response_data
    }))

    # Broadcast the original customer message to customer UIs (for their chat history with bot)
    await manager.broadcast_to_customers(json.dumps({
        "type": "customer_chat_message",
        "sender": "customer",
        "text": latest_user_message,
        "timestamp": datetime.now().isoformat()
    }))

    return response_data

@router.post("/send-agent-message")
async def send_agent_message_endpoint(request: AgentMessageRequest):
    agent_message = request.message
    agent_id = request.agent_id
    timestamp = datetime.now().isoformat()
    print(f"Agent '{agent_id}' sent: '{agent_message}'")

    message_to_broadcast = json.dumps({
        "type": "agent_chat_message",
        "sender": "agent",
        "text": agent_message,
        "timestamp": timestamp,
        "agent_id": agent_id
    })

    await manager.broadcast_to_customers(message_to_broadcast)
    await manager.broadcast_to_agents(message_to_broadcast)

    return {"status": "success", "message": "Agent message sent"}
