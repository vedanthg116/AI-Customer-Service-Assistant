# server/api/services/ai_service.py

import google.generativeai as genai
import json
from typing import List, Dict, Optional
import easyocr
import numpy as np
import base64
import asyncio
import cv2  # ✅ Required for image decoding

class AIService:
    def __init__(self):
        self.client = genai.GenerativeModel("gemini-2.0-flash")
        print("Gemini 1.5 Flash model loaded and ready from config.")

        try:
            self.reader = easyocr.Reader(['en'], gpu=False)
            print("EasyOCR reader initialized with English language model (CPU mode).")
        except Exception as e:
            print(f"Error initializing EasyOCR: {e}. OCR functionality will be disabled.")
            self.reader = None

    async def _call_gemini_api(self, prompt: str, chat_history: List[Dict]) -> Dict:
        raw_gemini_output = ""
        try:
            full_contents = chat_history + [{"role": "user", "parts": [{"text": prompt}]}]
            generation_config = {
                "temperature": 0.2,
                "top_p": 0.95,
                "top_k": 40,
            }

            print("AI Service: Sending prompt to Gemini:")
            print(prompt)

            response = await asyncio.to_thread(
                self.client.generate_content,
                full_contents,
                generation_config=generation_config
            )

            raw_gemini_output = response.text
            print("AI Service: Raw Gemini output:", raw_gemini_output)

            clean_json_string = raw_gemini_output.strip()
            if clean_json_string.startswith("```json"):
                clean_json_string = clean_json_string[len("```json"):].strip()
            if clean_json_string.endswith("```"):
                clean_json_string = clean_json_string[:-len("```")].strip()

            parsed_data = json.loads(clean_json_string)
            print("AI Service: Parsed Gemini data:", parsed_data)
            return parsed_data

        except json.JSONDecodeError as e:
            print(f"AI Service: Error decoding JSON from Gemini response: {e}. Raw output: {raw_gemini_output}")
            return {
                "predicted_intent": "unclear_intent",
                "intent_confidence": 0.0,
                "sentiment": {"label": "neutral", "score": 0.0},
                "detected_entities": [],
                "suggestions": {
                    "knowledge_base": [],
                    "pre_written_response": "I apologize, I'm having trouble understanding. Could you please rephrase?",
                    "next_actions": ["Ask for clarification"]
                },
                "ocr_extracted_text": ""
            }
        except Exception as e:
            print(f"AI Service: General error calling Gemini API: {e}")
            return {
                "predicted_intent": "unclear_intent",
                "intent_confidence": 0.0,
                "sentiment": {"label": "neutral", "score": 0.0},
                "detected_entities": [],
                "suggestions": {
                    "knowledge_base": [],
                    "pre_written_response": "I apologize, I'm having trouble understanding. Could you please rephrase?",
                    "next_actions": ["Ask for clarification"]
                },
                "ocr_extracted_text": ""
            }

    async def perform_ocr(self, image_bytes: bytes) -> Optional[str]:
        if not self.reader:
            print("OCR Service: EasyOCR not initialized. Skipping OCR.")
            return None

        try:
            nparr = np.frombuffer(image_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)  # ✅ Proper image decoding
            if img is None:
                print("OCR Service: Failed to decode image.")
                return None

            ocr_results = self.reader.readtext(img, detail=0)
            if ocr_results and isinstance(ocr_results, list):
                extracted_text = " ".join(ocr_results)
                print(f"OCR Service: Raw EasyOCR results (detail=0): {ocr_results}")
                print(f"OCR Service: Extracted text: '{extracted_text}'")
                return extracted_text
            else:
                print(f"OCR Service: Unexpected OCR result: {ocr_results}")
                return None

        except Exception as e:
            print(f"OCR Service: Error performing OCR: {e}")
            return None

    async def analyze_text_message(self, latest_user_message: str, full_chat_history: List[Dict]) -> Dict:
        formatted_history = []
        for msg in full_chat_history:
            formatted_history.append({
                "role": "user" if msg.sender == "customer" else "model",
                "parts": [{"text": msg.text}]
            })

        prompt = f"""You are an AI customer support assistant.

**Conversation History:**
{json.dumps(formatted_history, indent=2)}

**Latest Customer Message:** "{latest_user_message}"

**Instructions:**
- Predict intent from: order_status_inquiry, account_balance_inquiry, password_reset_request, technical_support, refund_request, product_information, billing_dispute, change_address_request, unclear_intent, greeting, complaint, cancellation_request
- Sentiment (positive, neutral, negative)
- Entities (e.g., product name, order number, account number, date)
- Suggest pre-written response
- Recommend next actions

**Relevant Knowledge Base:**

--- Knowledge for ORDER STATUS INQUIRY ---
Orders typically ship within 1-2 business days.
Standard shipping delivers in 3-5 business days.
Expedited shipping delivers in 1-2 business days.
...

**Output JSON:**
```json
{{
  "predicted_intent": "string",
  "intent_confidence": 0.0,
  "sentiment": {{
    "label": "string",
    "score": 0.0
  }},
  "detected_entities": [{{ "text": "string", "label": "string" }}],
  "suggestions": {{
    "knowledge_base": ["string"],
    "pre_written_response": "string",
    "next_actions": ["string"]
  }},
  "ocr_extracted_text": "string"
}}
```"""
        return await self._call_gemini_api(prompt, formatted_history)

    async def analyze_image_message(self, image_bytes: bytes, text_content: Optional[str], full_chat_history: List[Dict]) -> Dict:
        ocr_text = await self.perform_ocr(image_bytes)
        user_message_for_gemini = text_content or ""
        if ocr_text:
            user_message_for_gemini += f" (OCR from image: {ocr_text})"
        elif not user_message_for_gemini:
            user_message_for_gemini = "Image shared without additional text."

        formatted_history = []
        for msg in full_chat_history:
            formatted_history.append({
                "role": "user" if msg.sender == "customer" else "model",
                "parts": [{"text": msg.text}]
            })

        prompt = f"""You are an AI customer support assistant.

**Conversation History:**
{json.dumps(formatted_history, indent=2)}

**Latest Customer Message (including image insights):** "{user_message_for_gemini}"

**Instructions:**
- Predict intent from: ...
...

**Output JSON:**
```json
{{
  "predicted_intent": "string",
  "intent_confidence": 0.0,
  "sentiment": {{
    "label": "string",
    "score": 0.0
  }},
  "detected_entities": [{{ "text": "string", "label": "string" }}],
  "suggestions": {{
    "knowledge_base": ["string"],
    "pre_written_response": "string",
    "next_actions": ["string"]
  }},
  "ocr_extracted_text": "string"
}}
```"""
        gemini_response = await self._call_gemini_api(prompt, formatted_history)
        gemini_response["ocr_extracted_text"] = ocr_text if ocr_text else ""
        return gemini_response

    async def analyze_transcription(self, transcription_text: str, full_chat_history: List[Dict]) -> Dict:
        formatted_history = []
        for msg in full_chat_history:
            formatted_history.append({
                "role": "user" if msg.sender == "customer" else "model",
                "parts": [{"text": msg.text}]
            })

        prompt = f"""You are an AI customer support assistant.

**Conversation History:**
{json.dumps(formatted_history, indent=2)}

**Recorded Call Transcription:** "{transcription_text}"

**Instructions:**
...

**Output JSON:**
```json
{{
  "predicted_intent": "string",
  "intent_confidence": 0.0,
  "sentiment": {{
    "label": "string",
    "score": 0.0
  }},
  "detected_entities": [{{ "text": "string", "label": "string" }}],
  "suggestions": {{
    "knowledge_base": ["string"],
    "pre_written_response": "string",
    "next_actions": ["string"]
  }},
  "ocr_extracted_text": "string"
}}
```"""
        gemini_response = await self._call_gemini_api(prompt, formatted_history)
        gemini_response["ocr_extracted_text"] = ""
        return gemini_response


# Initialize service instance
ai_service = AIService()
