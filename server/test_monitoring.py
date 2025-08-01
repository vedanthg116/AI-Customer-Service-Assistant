# server/test_monitoring.py
"""
Simple test script for Azure monitoring setup
"""

import time
from monitoring_config import monitoring_service

def test_monitoring():
    """Test basic monitoring functionality"""
    
    print("🔍 Testing Azure Monitoring Setup")
    print("=================================")
    
    # Test 1: Check if monitoring is enabled
    print(f"📊 Monitoring enabled: {monitoring_service.enabled}")
    
    if not monitoring_service.enabled:
        print("⚠️ Monitoring not enabled. Set APPLICATIONINSIGHTS_CONNECTION_STRING environment variable.")
        print("💡 Example: export APPLICATIONINSIGHTS_CONNECTION_STRING='InstrumentationKey=your-key;...'")
        return
    
    # Test 2: Test conversation logging
    print("\n📝 Testing conversation logging...")
    try:
        monitoring_service.log_conversation_created(
            conversation_id="test-conv-123",
            source="test",
            language="en"
        )
        print("✅ Conversation logging successful")
    except Exception as e:
        print(f"❌ Conversation logging failed: {e}")
    
    # Test 3: Test message logging
    print("\n💬 Testing message logging...")
    try:
        monitoring_service.log_message_sent(
            message_id="test-msg-123",
            sender_type="customer",
            language="hi",
            has_translation=True
        )
        print("✅ Message logging successful")
    except Exception as e:
        print(f"❌ Message logging failed: {e}")
    
    # Test 4: Test translation logging
    print("\n🌍 Testing translation logging...")
    try:
        monitoring_service.log_translation(
            source_language="en",
            target_language="hi",
            method="azure",
            success=True
        )
        print("✅ Translation logging successful")
    except Exception as e:
        print(f"❌ Translation logging failed: {e}")
    
    # Test 5: Test response time logging
    print("\n⏱️ Testing response time logging...")
    try:
        monitoring_service.log_response_time("/test-endpoint", 150.5)
        print("✅ Response time logging successful")
    except Exception as e:
        print(f"❌ Response time logging failed: {e}")
    
    # Test 6: Test error logging
    print("\n🚨 Testing error logging...")
    try:
        monitoring_service.log_error(
            error_type="test_error",
            error_message="This is a test error",
            context={"test": True}
        )
        print("✅ Error logging successful")
    except Exception as e:
        print(f"❌ Error logging failed: {e}")
    
    # Test 7: Test AI analysis logging
    print("\n🤖 Testing AI analysis logging...")
    try:
        monitoring_service.log_ai_analysis(
            analysis_type="test_analysis",
            language="en",
            processing_time_ms=250.0
        )
        print("✅ AI analysis logging successful")
    except Exception as e:
        print(f"❌ AI analysis logging failed: {e}")
    
    # Test 8: Test user activity logging
    print("\n👤 Testing user activity logging...")
    try:
        monitoring_service.log_user_activity(
            user_id="test-user-123",
            activity_type="test_activity",
            details={"test": True, "timestamp": time.time()}
        )
        print("✅ User activity logging successful")
    except Exception as e:
        print(f"❌ User activity logging failed: {e}")
    
    print("\n🎉 Monitoring test completed!")
    print("📊 Check your Azure Application Insights dashboard to see the test metrics")
    print("🔗 Dashboard URL: https://portal.azure.com/#@your-tenant/resource/subscriptions/...")

if __name__ == "__main__":
    test_monitoring() 