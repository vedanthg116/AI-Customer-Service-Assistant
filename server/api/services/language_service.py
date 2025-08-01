# server/api/services/language_service.py
import os
import json
from typing import Optional, Dict, Any
from azure.ai.textanalytics import TextAnalyticsClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.translation.text import TextTranslationClient
from azure.core.credentials import AzureKeyCredential

class LanguageService:
    def __init__(self):
        # Azure Cognitive Services configuration
        self.text_analytics_key = os.getenv("AZURE_TEXT_ANALYTICS_KEY")
        self.text_analytics_endpoint = os.getenv("AZURE_TEXT_ANALYTICS_ENDPOINT")
        self.translator_key = os.getenv("AZURE_TRANSLATOR_KEY")
        self.translator_endpoint = os.getenv("AZURE_TRANSLATOR_ENDPOINT", "https://api.cognitive.microsofttranslator.com")
        self.translator_region = os.getenv("AZURE_TRANSLATOR_REGION")
        
        # Initialize clients if credentials are available
        self.text_analytics_client = None
        self.translator_client = None
        
        if self.text_analytics_key and self.text_analytics_endpoint:
            self.text_analytics_client = TextAnalyticsClient(
                endpoint=self.text_analytics_endpoint,
                credential=AzureKeyCredential(self.text_analytics_key)
            )
        
        if self.translator_key and self.translator_region:
            self.translator_client = TextTranslationClient(
                endpoint=self.translator_endpoint,
                credential=AzureKeyCredential(self.translator_key)
            )
        
        # Supported languages mapping
        self.supported_languages = {
            "en": "English",
            "es": "Spanish", 
            "fr": "French",
            "de": "German",
            "pt": "Portuguese",
            "it": "Italian",
            "ru": "Russian",
            "ja": "Japanese",
            "ko": "Korean",
            "zh": "Chinese (Simplified)",
            "ar": "Arabic",
            "hi": "Hindi",
            "nl": "Dutch",
            "sv": "Swedish",
            "no": "Norwegian",
            "da": "Danish",
            "fi": "Finnish",
            "pl": "Polish",
            "tr": "Turkish",
            "he": "Hebrew"
        }
        
        # Language detection fallback patterns
        self.language_patterns = {
            "es": ["hola", "gracias", "por favor", "buenos días", "adiós"],
            "fr": ["bonjour", "merci", "s'il vous plaît", "au revoir", "oui", "non"],
            "de": ["hallo", "danke", "bitte", "auf wiedersehen", "ja", "nein"],
            "pt": ["olá", "obrigado", "por favor", "adeus", "sim", "não"],
            "it": ["ciao", "grazie", "per favore", "arrivederci", "sì", "no"],
            "ru": ["привет", "спасибо", "пожалуйста", "до свидания", "да", "нет"],
            "ja": ["こんにちは", "ありがとう", "お願いします", "さようなら", "はい", "いいえ"],
            "ko": ["안녕하세요", "감사합니다", "부탁합니다", "안녕히 가세요", "네", "아니오"],
            "zh": ["你好", "谢谢", "请", "再见", "是", "不"],
            "ar": ["مرحبا", "شكرا", "من فضلك", "مع السلامة", "نعم", "لا"],
            "hi": ["नमस्ते", "धन्यवाद", "कृपया", "अलविदा", "हाँ", "नहीं"]
        }

    def detect_language(self, text: str) -> Dict[str, Any]:
        """
        Detect the language of the input text.
        Returns a dictionary with language code and confidence score.
        """
        if not text or len(text.strip()) < 3:
            return {"language": "en", "confidence": 0.0, "method": "fallback"}
        
        # Try Azure Text Analytics first
        if self.text_analytics_client:
            try:
                result = self.text_analytics_client.detect_language([text])
                if result and len(result) > 0:
                    detected_language = result[0]
                    if detected_language.primary_language:
                        return {
                            "language": detected_language.primary_language.iso6391_name,
                            "confidence": detected_language.primary_language.confidence_score,
                            "method": "azure_text_analytics"
                        }
            except Exception as e:
                print(f"Azure Text Analytics error: {e}")
        
        # Fallback to pattern matching
        return self._fallback_language_detection(text)
    
    def _fallback_language_detection(self, text: str) -> Dict[str, Any]:
        """
        Fallback language detection using pattern matching.
        """
        text_lower = text.lower()
        
        # Check for common English words first
        english_words = ["the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "my", "your", "his", "her", "its", "our", "their", "is", "are", "was", "were", "be", "been", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "can", "order", "not", "yet", "arrived", "hello", "please", "thank", "sorry", "help"]
        
        english_word_count = sum(1 for word in english_words if word in text_lower.split())
        total_words = len(text_lower.split())
        
        # If more than 50% of words are English, classify as English
        if total_words > 0 and english_word_count / total_words > 0.5:
            return {
                "language": "en",
                "confidence": 0.8,
                "method": "english_word_pattern"
            }
        
        # Check for other language patterns
        for lang_code, patterns in self.language_patterns.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return {
                        "language": lang_code,
                        "confidence": 0.7,  # Medium confidence for pattern matching
                        "method": "pattern_matching"
                    }
        
        # Default to English if no patterns match
        return {
            "language": "en",
            "confidence": 0.5,
            "method": "fallback"
        }
    
    def translate_text(self, text: str, target_language: str, source_language: Optional[str] = None) -> Dict[str, Any]:
        """
        Translate text to target language.
        Returns a dictionary with translated text and metadata.
        """
        if not text:
            return {
                "translated_text": text,
                "source_language": source_language or "en",
                "target_language": target_language,
                "method": "no_translation_needed"
            }
        
        # If source and target are the same, no translation needed
        if source_language and source_language == target_language:
            return {
                "translated_text": text,
                "source_language": source_language,
                "target_language": target_language,
                "method": "no_translation_needed"
            }
        
        # Try Azure Translator first
        if self.translator_client:
            try:
                # Convert language codes for Azure Translator
                azure_target_lang = self._convert_to_azure_language_code(target_language)
                azure_source_lang = self._convert_to_azure_language_code(source_language) if source_language else None
                
                response = self.translator_client.translate(
                    content=[text],
                    to=[azure_target_lang],
                    from_parameter=azure_source_lang
                )
                
                if response and len(response) > 0:
                    translation = response[0]
                    if translation.translations and len(translation.translations) > 0:
                        return {
                            "translated_text": translation.translations[0].text,
                            "source_language": translation.detected_language.language if hasattr(translation, 'detected_language') else source_language,
                            "target_language": target_language,
                            "method": "azure_translator"
                        }
            except Exception as e:
                print(f"Azure Translator error: {e}")
        
        # Fallback: try basic translation for common languages
        if source_language and target_language == "en":
            basic_translation = self._basic_fallback_translation(text, source_language)
            if basic_translation != text:
                return {
                    "translated_text": basic_translation,
                    "source_language": source_language,
                    "target_language": target_language,
                    "method": "basic_fallback"
                }
        
        # Fallback: try basic translation for English to other languages
        if source_language == "en" and target_language in ["hi", "es", "fr", "it"]:
            basic_translation = self._basic_fallback_translation(text, target_language, reverse=True)
            if basic_translation != text:
                return {
                    "translated_text": basic_translation,
                    "source_language": source_language,
                    "target_language": target_language,
                    "method": "basic_fallback"
                }
        
        # Final fallback: return original text with error message
        return {
            "translated_text": text,
            "source_language": source_language or "unknown",
            "target_language": target_language,
            "method": "fallback_no_translation",
            "error": "Translation service unavailable"
        }
    
    def _basic_fallback_translation(self, text: str, language: str, reverse: bool = False) -> str:
        """
        Basic fallback translation for common phrases when Azure Translator is unavailable.
        reverse=True means translating from English to the target language.
        """
        if language == "hi":  # Hindi
            if reverse:  # English to Hindi
                # First, handle complete phrases to avoid word-by-word translation
                phrase_translations = {
                    "hello! i understand": "नमस्ते! मैं समझता हूं",
                    "your order hasn't arrived yet": "आपका ऑर्डर अभी तक नहीं आया है",
                    "i'd be happy to": "मुझे खुशी होगी",
                    "look into the status": "स्थिति की जांच करने में",
                    "of your order": "आपके ऑर्डर की",
                    "could you please": "क्या आप कृपया",
                    "provide your order number": "अपना ऑर्डर नंबर दे सकते हैं",
                    "so i can assist you": "ताकि मैं आपकी मदद कर सकूं",
                    "better": "बेहतर तरीके से",
                    "i'm sorry": "मुझे माफ़ करें",
                    "i apologize": "मैं माफ़ी मांगता हूं",
                    "check your order": "आपके ऑर्डर की जांच करें",
                    "track your order": "आपके ऑर्डर को ट्रैक करें",
                    "shipping status": "शिपिंग स्थिति",
                    "delivery status": "डिलीवरी स्थिति"
                }
                
                # Then handle individual words for remaining text
                word_translations = {
                    "hello": "नमस्ते",
                    "hi": "नमस्ते",
                    "understand": "समझता हूं",
                    "order": "ऑर्डर",
                    "hasn't": "नहीं",
                    "has not": "नहीं",
                    "arrived": "आया है",
                    "yet": "अभी तक",
                    "happy": "खुशी",
                    "look into": "जांच करना",
                    "status": "स्थिति",
                    "please": "कृपया",
                    "provide": "देना",
                    "order number": "ऑर्डर नंबर",
                    "assist": "मदद",
                    "help": "मदद",
                    "better": "बेहतर",
                    "sorry": "माफ़ करें",
                    "apologize": "माफ़ी मांगता हूं",
                    "check": "जांच",
                    "track": "ट्रैक",
                    "shipping": "शिपिंग",
                    "delivery": "डिलीवरी",
                    "your": "आपका",
                    "you": "आप",
                    "i": "मैं",
                    "me": "मुझे",
                    "my": "मेरा",
                    "can": "सकता हूं",
                    "could": "क्या",
                    "would": "होगा",
                    "will": "होगा",
                    "to": "में",
                    "the": "",
                    "of": "की",
                    "so": "ताकि",
                    "that": "कि"
                }
                
                translated = text.lower()
                
                # First apply phrase translations
                for english_phrase, hindi_phrase in phrase_translations.items():
                    translated = translated.replace(english_phrase, hindi_phrase)
                
                # Then apply word translations for remaining text
                for english_word, hindi_word in word_translations.items():
                    translated = translated.replace(english_word, hindi_word)
                
                return translated
            else:  # Hindi to English
                basic_translations = {
                    "नमस्ते": "Hello",
                    "मेरा": "my",
                    "ऑर्डर": "order",
                    "अभी तक": "yet",
                    "नहीं": "not",
                    "आया": "arrived",
                    "है": "is",
                    "मदद": "help",
                    "चाहिए": "need",
                    "कृपया": "please",
                    "धन्यवाद": "thank you",
                    "अलविदा": "goodbye"
                }
                translated = text
                for hindi_word, english_word in basic_translations.items():
                    translated = translated.replace(hindi_word, english_word)
                return translated
        
        elif language == "es":  # Spanish
            basic_translations = {
                "hola": "hello",
                "necesito": "I need",
                "ayuda": "help",
                "con": "with",
                "mi": "my",
                "pedido": "order",
                "por favor": "please",
                "gracias": "thank you",
                "adiós": "goodbye"
            }
            translated = text.lower()
            for spanish_word, english_word in basic_translations.items():
                translated = translated.replace(spanish_word, english_word)
            return translated
        
        elif language == "fr":  # French
            basic_translations = {
                "bonjour": "hello",
                "j'ai": "I have",
                "un problème": "a problem",
                "avec": "with",
                "ma": "my",
                "commande": "order",
                "pouvez-vous": "can you",
                "m'aider": "help me",
                "merci": "thank you",
                "au revoir": "goodbye"
            }
            translated = text.lower()
            for french_word, english_word in basic_translations.items():
                translated = translated.replace(french_word, english_word)
            return translated
        
        elif language == "it":  # Italian
            basic_translations = {
                "ciao": "hello",
                "mi": "my",
                "ordine": "order",
                "non": "not",
                "è": "is",
                "ancora": "yet",
                "arrivato": "arrived",
                "aiuto": "help",
                "per favore": "please",
                "grazie": "thank you",
                "dispiacere": "sorry",
                "numero": "number",
                "stato": "status",
                "spedizione": "shipping"
            }
            translated = text.lower()
            for italian_word, english_word in basic_translations.items():
                translated = translated.replace(italian_word, english_word)
            return translated
        
        elif target_language == "hi":  # English to Hindi
            basic_translations = {
                "hello": "नमस्ते",
                "hi": "नमस्ते",
                "understand": "समझता हूं",
                "order": "ऑर्डर",
                "hasn't": "नहीं",
                "has not": "नहीं",
                "arrived": "आया है",
                "yet": "अभी तक",
                "happy": "खुशी",
                "look into": "जांच करना",
                "status": "स्थिति",
                "please": "कृपया",
                "provide": "देना",
                "order number": "ऑर्डर नंबर",
                "assist": "मदद",
                "help": "मदद",
                "better": "बेहतर",
                "sorry": "माफ़ करें",
                "apologize": "माफ़ी मांगता हूं",
                "check": "जांच",
                "track": "ट्रैक",
                "shipping": "शिपिंग",
                "delivery": "डिलीवरी"
            }
            translated = text.lower()
            for english_word, hindi_word in basic_translations.items():
                translated = translated.replace(english_word, hindi_word)
            return translated
        
        return text

    def _convert_to_azure_language_code(self, language_code: str) -> str:
        """
        Convert our language codes to Azure Translator format.
        """
        # Azure Translator uses slightly different codes for some languages
        azure_mapping = {
            "zh": "zh-Hans",  # Chinese Simplified
            "pt": "pt",       # Portuguese
            "ar": "ar",       # Arabic
            "he": "he",       # Hebrew
        }
        
        return azure_mapping.get(language_code, language_code)
    
    def get_supported_languages(self) -> Dict[str, str]:
        """
        Get list of supported languages with their display names.
        """
        return self.supported_languages
    
    def is_language_supported(self, language_code: str) -> bool:
        """
        Check if a language code is supported.
        """
        return language_code in self.supported_languages
    
    def get_language_display_name(self, language_code: str) -> str:
        """
        Get the display name for a language code.
        """
        return self.supported_languages.get(language_code, language_code.upper())
    
    def get_cultural_context(self, language_code: str) -> Dict[str, Any]:
        """
        Get cultural context information for a language.
        """
        cultural_contexts = {
            "en": {
                "greeting": "Hello",
                "farewell": "Goodbye",
                "polite": "Please",
                "thanks": "Thank you",
                "formal": False
            },
            "es": {
                "greeting": "Hola",
                "farewell": "Adiós",
                "polite": "Por favor",
                "thanks": "Gracias",
                "formal": True
            },
            "fr": {
                "greeting": "Bonjour",
                "farewell": "Au revoir",
                "polite": "S'il vous plaît",
                "thanks": "Merci",
                "formal": True
            },
            "de": {
                "greeting": "Hallo",
                "farewell": "Auf Wiedersehen",
                "polite": "Bitte",
                "thanks": "Danke",
                "formal": True
            },
            "pt": {
                "greeting": "Olá",
                "farewell": "Adeus",
                "polite": "Por favor",
                "thanks": "Obrigado",
                "formal": True
            },
            "zh": {
                "greeting": "你好",
                "farewell": "再见",
                "polite": "请",
                "thanks": "谢谢",
                "formal": True
            },
            "ar": {
                "greeting": "مرحبا",
                "farewell": "مع السلامة",
                "polite": "من فضلك",
                "thanks": "شكرا",
                "formal": True
            }
        }
        
        return cultural_contexts.get(language_code, cultural_contexts["en"])

# Global instance
language_service = LanguageService() 