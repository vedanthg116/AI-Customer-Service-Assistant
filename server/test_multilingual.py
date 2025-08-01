#!/usr/bin/env python3
"""
Test script for multilingual functionality
"""

import asyncio
import sys
import os

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api.services.language_service import language_service

async def test_language_detection():
    """Test language detection functionality"""
    print("🧪 Testing Language Detection...")
    
    test_cases = [
        ("Hello, how can I help you?", "en"),
        ("Hola, ¿cómo puedo ayudarte?", "es"),
        ("Bonjour, comment puis-je vous aider?", "fr"),
        ("Hallo, wie kann ich Ihnen helfen?", "de"),
        ("Olá, como posso ajudá-lo?", "pt"),
        ("你好，我能为您做些什么？", "zh"),
        ("مرحبا، كيف يمكنني مساعدتك؟", "ar"),
    ]
    
    for text, expected_lang in test_cases:
        result = language_service.detect_language(text)
        detected_lang = result["language"]
        confidence = result["confidence"]
        method = result["method"]
        
        status = "✅" if detected_lang == expected_lang else "❌"
        print(f"{status} Text: '{text[:30]}...'")
        print(f"   Expected: {expected_lang}, Detected: {detected_lang}")
        print(f"   Confidence: {confidence:.2f}, Method: {method}")
        print()

async def test_translation():
    """Test translation functionality"""
    print("🌐 Testing Translation...")
    
    test_cases = [
        ("Hello, how can I help you?", "es"),
        ("Thank you for your patience", "fr"),
        ("Your order has been shipped", "de"),
        ("We apologize for the inconvenience", "pt"),
    ]
    
    for text, target_lang in test_cases:
        result = language_service.translate_text(text, target_lang, "en")
        translated_text = result["translated_text"]
        method = result["method"]
        
        print(f"📝 Original: '{text}'")
        print(f"🔄 Translated ({target_lang}): '{translated_text}'")
        print(f"   Method: {method}")
        print()

async def test_supported_languages():
    """Test supported languages functionality"""
    print("📚 Testing Supported Languages...")
    
    languages = language_service.get_supported_languages()
    print(f"Total supported languages: {len(languages)}")
    
    # Show first 10 languages
    print("First 10 languages:")
    for i, (code, name) in enumerate(list(languages.items())[:10]):
        print(f"  {i+1}. {code} - {name}")
    
    print()

async def test_cultural_context():
    """Test cultural context functionality"""
    print("🎭 Testing Cultural Context...")
    
    test_languages = ["en", "es", "fr", "de", "zh", "ar"]
    
    for lang_code in test_languages:
        context = language_service.get_cultural_context(lang_code)
        print(f"🌍 {lang_code.upper()} - {language_service.get_language_display_name(lang_code)}")
        print(f"   Greeting: {context['greeting']}")
        print(f"   Polite: {context['polite']}")
        print(f"   Formal: {context['formal']}")
        print()

async def main():
    """Run all tests"""
    print("🚀 Starting Multilingual Functionality Tests\n")
    
    await test_supported_languages()
    await test_language_detection()
    await test_translation()
    await test_cultural_context()
    
    print("✅ All tests completed!")

if __name__ == "__main__":
    asyncio.run(main()) 