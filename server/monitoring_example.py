# server/monitoring_example.py
"""
Example of how to integrate Azure monitoring into your existing code
"""

import time
from monitoring_config import monitoring_service

# Example: Add monitoring to chat router endpoints
def example_chat_router_monitoring():
    """
    Example of how to add monitoring to your chat router endpoints
    """
    
    # Example: Monitor conversation creation
    def create_conversation_monitored(customer_id: str, source: str, language: str):
        start_time = time.time()
        
        try:
            # Your existing conversation creation code here
            conversation_id = "example-conversation-id"
            
            # Log successful conversation creation
            monitoring_service.log_conversation_created(
                conversation_id=conversation_id,
                source=source,
                language=language
            )
            
            # Log response time
            response_time = (time.time() - start_time) * 1000
            monitoring_service.log_response_time("/create-conversation", response_time)
            
            return conversation_id
            
        except Exception as e:
            # Log error
            monitoring_service.log_error(
                error_type="conversation_creation_error",
                error_message=str(e),
                context={"customer_id": customer_id, "source": source}
            )
            raise
    
    # Example: Monitor message sending
    def send_message_monitored(message_id: str, sender_type: str, language: str, has_translation: bool):
        start_time = time.time()
        
        try:
            # Your existing message sending code here
            
            # Log successful message
            monitoring_service.log_message_sent(
                message_id=message_id,
                sender_type=sender_type,
                language=language,
                has_translation=has_translation
            )
            
            # Log response time
            response_time = (time.time() - start_time) * 1000
            monitoring_service.log_response_time("/send-message", response_time)
            
        except Exception as e:
            # Log error
            monitoring_service.log_error(
                error_type="message_send_error",
                error_message=str(e),
                context={"message_id": message_id, "sender_type": sender_type}
            )
            raise
    
    # Example: Monitor translation
    def translate_message_monitored(text: str, source_language: str, target_language: str):
        start_time = time.time()
        
        try:
            # Your existing translation code here
            translation_result = {"translated_text": "Example translation", "method": "azure"}
            
            # Log successful translation
            monitoring_service.log_translation(
                source_language=source_language,
                target_language=target_language,
                method=translation_result["method"],
                success=True
            )
            
            # Log processing time
            processing_time = (time.time() - start_time) * 1000
            monitoring_service.log_ai_analysis(
                analysis_type="translation",
                language=source_language,
                processing_time_ms=processing_time
            )
            
            return translation_result
            
        except Exception as e:
            # Log translation error
            monitoring_service.log_translation(
                source_language=source_language,
                target_language=target_language,
                method="error",
                success=False
            )
            raise
    
    # Example: Monitor AI analysis
    def analyze_message_monitored(text: str, language: str):
        start_time = time.time()
        
        try:
            # Your existing AI analysis code here
            analysis_result = {"intent": "order_status", "sentiment": "neutral"}
            
            # Log AI analysis
            processing_time = (time.time() - start_time) * 1000
            monitoring_service.log_ai_analysis(
                analysis_type="message_analysis",
                language=language,
                processing_time_ms=processing_time
            )
            
            return analysis_result
            
        except Exception as e:
            # Log AI analysis error
            monitoring_service.log_error(
                error_type="ai_analysis_error",
                error_message=str(e),
                context={"text_length": len(text), "language": language}
            )
            raise
    
    # Example: Monitor user activity
    def log_user_activity_monitored(user_id: str, activity_type: str, details: dict = None):
        try:
            monitoring_service.log_user_activity(
                user_id=user_id,
                activity_type=activity_type,
                details=details or {}
            )
        except Exception as e:
            print(f"Failed to log user activity: {e}")

# Example usage
if __name__ == "__main__":
    print("🔍 Monitoring Example")
    print("====================")
    
    # Test monitoring functions
    try:
        # Test conversation creation monitoring
        conversation_id = example_chat_router_monitoring().create_conversation_monitored(
            customer_id="customer123",
            source="chat",
            language="hi"
        )
        print(f"✅ Created conversation: {conversation_id}")
        
        # Test message sending monitoring
        example_chat_router_monitoring().send_message_monitored(
            message_id="msg123",
            sender_type="customer",
            language="hi",
            has_translation=True
        )
        print("✅ Sent message with monitoring")
        
        # Test translation monitoring
        translation = example_chat_router_monitoring().translate_message_monitored(
            text="Hello, I need help with my order",
            source_language="en",
            target_language="hi"
        )
        print(f"✅ Translated message: {translation}")
        
        # Test AI analysis monitoring
        analysis = example_chat_router_monitoring().analyze_message_monitored(
            text="My order hasn't arrived yet",
            language="en"
        )
        print(f"✅ Analyzed message: {analysis}")
        
        # Test user activity monitoring
        example_chat_router_monitoring().log_user_activity_monitored(
            user_id="agent456",
            activity_type="login",
            details={"browser": "Chrome", "location": "US"}
        )
        print("✅ Logged user activity")
        
        print("\n🎉 All monitoring examples completed successfully!")
        print("📊 Check your Azure Application Insights dashboard to see the metrics")
        
    except Exception as e:
        print(f"❌ Error in monitoring example: {e}")
        print("💡 Make sure you have set the APPLICATIONINSIGHTS_CONNECTION_STRING environment variable") 