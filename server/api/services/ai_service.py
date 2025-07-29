# server/api/services/ai_service.py
import json
from typing import List, Optional
from uuid import UUID  # Not directly used here, but good to have if needed for context
from datetime import datetime

from config.gemini_config import gemini_model  # Import your configured Gemini model
from utils.kb_manager import knowledge_base
from utils.ocr_processor import detect_text_from_image
from api.schemas import ChatMessage  # Import ChatMessage schema


class AIService:
    def __init__(self):
        self.model = gemini_model  # Ensure the model is loaded

    def _create_gemini_prompt(
        self,
        latest_user_message: str,
        full_chat_history: List[ChatMessage],
        knowledge_base_data: dict,
        ocr_text: Optional[str] = None
    ) -> str:
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

    async def analyze_text_message(
        self,
        latest_user_message: str,
        full_chat_history: List[ChatMessage],
    ) -> dict:
        if not self.model:
            print("AI Service: Gemini model not initialized. Returning system error fallback.")
            return {
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
                "timestamp": datetime.now().isoformat(),
                "ocr_extracted_text": ""
            }

        try:
            gemini_prompt = self._create_gemini_prompt(latest_user_message, full_chat_history, knowledge_base)
            print(f"AI Service: Sending prompt to Gemini:\n{gemini_prompt}")

            gemini_response = await self.model.generate_content_async(gemini_prompt)

            gemini_output_text = ""
            if gemini_response.candidates:
                for part in gemini_response.candidates[0].content.parts:
                    gemini_output_text += part.text
            else:
                raise ValueError("Gemini returned no candidates, possibly due to safety settings.")

            print(f"AI Service: Raw Gemini output: {gemini_output_text}")

            cleaned_json_str = gemini_output_text.strip()
            if cleaned_json_str.startswith("```json") and cleaned_json_str.endswith("```"):
                cleaned_json_str = cleaned_json_str[len("```json"): -len("```")].strip()

            parsed_gemini_data = json.loads(cleaned_json_str)
            print(f"AI Service: Parsed Gemini data: {json.dumps(parsed_gemini_data, indent=2)}")

            if 'suggestions' not in parsed_gemini_data or not isinstance(parsed_gemini_data['suggestions'], dict):
                parsed_gemini_data['suggestions'] = {
                    "knowledge_base": [],
                    "pre_written_response": "I'm sorry, I couldn't generate a specific response at this moment. Please check the customer's query and the available knowledge base.",
                    "next_actions": []
                }

            parsed_gemini_data['suggestions'].setdefault('knowledge_base', [])
            parsed_gemini_data['suggestions'].setdefault('pre_written_response', "No specific suggestion available.")
            parsed_gemini_data['suggestions'].setdefault('next_actions', [])

            return {
                "user_message": latest_user_message,
                "predicted_intent": parsed_gemini_data.get("predicted_intent", "unclear_intent"),
                "intent_confidence": parsed_gemini_data.get("intent_confidence", 0.5),
                "sentiment": parsed_gemini_data.get("sentiment", {"label": "NEUTRAL", "score": 0.5}),
                "suggestions": parsed_gemini_data["suggestions"],
                "detected_entities": parsed_gemini_data.get("detected_entities", []),
                "timestamp": datetime.now().isoformat(),
                "ocr_extracted_text": parsed_gemini_data.get("ocr_extracted_text", "")
            }

        except json.JSONDecodeError as e:
            print(f"AI Service: JSON parsing error from Gemini response: {e}. Raw Gemini output: \n{gemini_output_text}")
            return {
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
                "timestamp": datetime.now().isoformat(),
                "ocr_extracted_text": ""
            }
        except Exception as e:
            print(f"AI Service: Error calling Gemini API or processing response: {e}")
            return {
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
                "timestamp": datetime.now().isoformat(),
                "ocr_extracted_text": ""
            }

    async def analyze_image_message(
        self,
        image_bytes: bytes,
        text_content: Optional[str],
        full_chat_history: List[ChatMessage]
    ) -> dict:
        ocr_extracted_text = await detect_text_from_image(image_bytes)

        combined_message_for_gemini = text_content if text_content else ""
        if ocr_extracted_text:
            if combined_message_for_gemini:
                combined_message_for_gemini += f"\n(Text from screenshot: {ocr_extracted_text})"
            else:
                combined_message_for_gemini = f"Text from screenshot: {ocr_extracted_text}"

        if not combined_message_for_gemini.strip():
            combined_message_for_gemini = "Customer sent an image with no recognizable text or accompanying message."

        if not self.model:
            print("AI Service: Gemini model not initialized. Returning system error fallback.")
            return {
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
                "ocr_extracted_text": ocr_extracted_text
            }

        try:
            gemini_prompt = self._create_gemini_prompt(
                latest_user_message=combined_message_for_gemini,
                full_chat_history=full_chat_history,
                knowledge_base_data=knowledge_base,
                ocr_text=ocr_extracted_text
            )
            print(f"AI Service: Sending prompt to Gemini for image analysis:\n{gemini_prompt}")

            gemini_response = await self.model.generate_content_async(gemini_prompt)

            gemini_output_text = ""
            if gemini_response.candidates:
                for part in gemini_response.candidates[0].content.parts:
                    gemini_output_text += part.text
            else:
                raise ValueError("Gemini returned no candidates, possibly due to safety settings.")

            print(f"AI Service: Raw Gemini output for image analysis: {gemini_output_text}")

            cleaned_json_str = gemini_output_text.strip()
            if cleaned_json_str.startswith("```json") and cleaned_json_str.endswith("```"):
                cleaned_json_str = cleaned_json_str[len("```json"): -len("```")].strip()

            parsed_gemini_data = json.loads(cleaned_json_str)
            print(f"AI Service: Parsed Gemini data for image analysis: {json.dumps(parsed_gemini_data, indent=2)}")

            if 'suggestions' not in parsed_gemini_data or not isinstance(parsed_gemini_data['suggestions'], dict):
                parsed_gemini_data['suggestions'] = {
                    "knowledge_base": [],
                    "pre_written_response": "I'm sorry, I couldn't generate a specific response at this moment. Please check the customer's query and the available knowledge base.",
                    "next_actions": []
                }

            parsed_gemini_data['suggestions'].setdefault('knowledge_base', [])
            parsed_gemini_data['suggestions'].setdefault('pre_written_response', "No specific suggestion available.")
            parsed_gemini_data['suggestions'].setdefault('next_actions', [])

            return {
                "user_message": combined_message_for_gemini,
                "predicted_intent": parsed_gemini_data.get("predicted_intent", "unclear_intent"),
                "intent_confidence": parsed_gemini_data.get("intent_confidence", 0.5),
                "sentiment": parsed_gemini_data.get("sentiment", {"label": "NEUTRAL", "score": 0.5}),
                "suggestions": parsed_gemini_data["suggestions"],
                "detected_entities": parsed_gemini_data.get("detected_entities", []),
                "timestamp": datetime.now().isoformat(),
                "ocr_extracted_text": ocr_extracted_text
            }

        except json.JSONDecodeError as e:
            print(f"AI Service: JSON parsing error from Gemini response for image: {e}. Raw Gemini output: \n{gemini_output_text}")
            return {
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
                "ocr_extracted_text": ocr_extracted_text
            }
        except Exception as e:
            print(f"AI Service: Error calling Gemini API or processing image: {e}")
            return {
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
                "ocr_extracted_text": ocr_extracted_text
            }


ai_service = AIService()  # Instantiate the service
