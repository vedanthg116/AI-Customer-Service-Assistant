# server/monitoring_config.py
"""
Azure Monitoring Configuration for Customer Support System
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import json

# Azure Application Insights
try:
    from opencensus.ext.azure.log_exporter import AzureLogHandler
    from opencensus.ext.azure.trace_exporter import AzureExporter
    from opencensus.trace.tracer import Tracer
    from opencensus.trace.samplers import ProbabilitySampler
    from opencensus.stats import aggregation, measure, view
    from opencensus.ext.azure import metrics_exporter
    AZURE_MONITORING_AVAILABLE = True
except ImportError:
    AZURE_MONITORING_AVAILABLE = False
    print("⚠️ Azure monitoring packages not installed. Install with: pip install opencensus-ext-azure")

class MonitoringService:
    def __init__(self):
        self.connection_string = os.getenv('APPLICATIONINSIGHTS_CONNECTION_STRING')
        self.enabled = AZURE_MONITORING_AVAILABLE and self.connection_string
        
        if self.enabled:
            self._setup_monitoring()
        else:
            print("⚠️ Azure monitoring not configured. Set APPLICATIONINSIGHTS_CONNECTION_STRING environment variable.")
    
    def _setup_monitoring(self):
        """Setup Azure Application Insights monitoring"""
        try:
            # Setup logging
            self.logger = logging.getLogger(__name__)
            self.logger.addHandler(AzureLogHandler(connection_string=self.connection_string))
            
            # Setup tracing
            self.tracer = Tracer(
                exporter=AzureExporter(connection_string=self.connection_string),
                sampler=ProbabilitySampler(1.0)
            )
            
            # Setup metrics
            self.metrics_exporter = metrics_exporter.new_metrics_exporter(
                connection_string=self.connection_string
            )
            
            # Define custom metrics
            self._setup_custom_metrics()
            
            print("✅ Azure monitoring configured successfully")
            
        except Exception as e:
            print(f"❌ Failed to setup Azure monitoring: {e}")
            self.enabled = False
    
    def _setup_custom_metrics(self):
        """Setup custom metrics for the application"""
        try:
            # Conversation metrics
            self.conversation_measure = measure.MeasureFloat(
                "conversation_count", 
                "Number of conversations", 
                "conversations"
            )
            
            # Message metrics
            self.message_measure = measure.MeasureFloat(
                "message_count", 
                "Number of messages", 
                "messages"
            )
            
            # Translation metrics
            self.translation_measure = measure.MeasureFloat(
                "translation_count", 
                "Number of translations", 
                "translations"
            )
            
            # Response time metrics
            self.response_time_measure = measure.MeasureFloat(
                "response_time_ms", 
                "Response time in milliseconds", 
                "ms"
            )
            
            # Error metrics
            self.error_measure = measure.MeasureFloat(
                "error_count", 
                "Number of errors", 
                "errors"
            )
            
            # Create views for metrics
            self._create_metric_views()
            
        except Exception as e:
            print(f"❌ Failed to setup custom metrics: {e}")
    
    def _create_metric_views(self):
        """Create views for custom metrics"""
        try:
            # Conversation view
            conversation_view = view.View(
                "conversation_count",
                "Number of conversations",
                [],
                self.conversation_measure,
                aggregation.CountAggregation()
            )
            
            # Message view
            message_view = view.View(
                "message_count",
                "Number of messages",
                [],
                self.message_measure,
                aggregation.CountAggregation()
            )
            
            # Translation view
            translation_view = view.View(
                "translation_count",
                "Number of translations",
                [],
                self.translation_measure,
                aggregation.CountAggregation()
            )
            
            # Response time view
            response_time_view = view.View(
                "response_time_ms",
                "Response time in milliseconds",
                [],
                self.response_time_measure,
                aggregation.MeanAggregation()
            )
            
            # Error view
            error_view = view.View(
                "error_count",
                "Number of errors",
                [],
                self.error_measure,
                aggregation.CountAggregation()
            )
            
            # Register views
            view_manager = view.ViewManager()
            view_manager.register_view(conversation_view)
            view_manager.register_view(message_view)
            view_manager.register_view(translation_view)
            view_manager.register_view(response_time_view)
            view_manager.register_view(error_view)
            
        except Exception as e:
            print(f"❌ Failed to create metric views: {e}")
    
    def log_conversation_created(self, conversation_id: str, source: str, language: str):
        """Log when a new conversation is created"""
        if not self.enabled:
            return
            
        try:
            self.logger.info(
                "Conversation created",
                extra={
                    "conversation_id": conversation_id,
                    "source": source,
                    "language": language,
                    "event_type": "conversation_created"
                }
            )
            
            # Record metric
            self.metrics_exporter.export_metrics([{
                "name": "conversation_count",
                "value": 1,
                "tags": {
                    "source": source,
                    "language": language
                }
            }])
            
        except Exception as e:
            print(f"❌ Failed to log conversation: {e}")
    
    def log_message_sent(self, message_id: str, sender_type: str, language: str, has_translation: bool):
        """Log when a message is sent"""
        if not self.enabled:
            return
            
        try:
            self.logger.info(
                "Message sent",
                extra={
                    "message_id": message_id,
                    "sender_type": sender_type,
                    "language": language,
                    "has_translation": has_translation,
                    "event_type": "message_sent"
                }
            )
            
            # Record metric
            self.metrics_exporter.export_metrics([{
                "name": "message_count",
                "value": 1,
                "tags": {
                    "sender_type": sender_type,
                    "language": language,
                    "has_translation": str(has_translation)
                }
            }])
            
        except Exception as e:
            print(f"❌ Failed to log message: {e}")
    
    def log_translation(self, source_language: str, target_language: str, method: str, success: bool):
        """Log translation events"""
        if not self.enabled:
            return
            
        try:
            self.logger.info(
                "Translation performed",
                extra={
                    "source_language": source_language,
                    "target_language": target_language,
                    "method": method,
                    "success": success,
                    "event_type": "translation"
                }
            )
            
            # Record metric
            self.metrics_exporter.export_metrics([{
                "name": "translation_count",
                "value": 1,
                "tags": {
                    "source_language": source_language,
                    "target_language": target_language,
                    "method": method,
                    "success": str(success)
                }
            }])
            
        except Exception as e:
            print(f"❌ Failed to log translation: {e}")
    
    def log_response_time(self, endpoint: str, response_time_ms: float):
        """Log API response times"""
        if not self.enabled:
            return
            
        try:
            self.logger.info(
                "API response time",
                extra={
                    "endpoint": endpoint,
                    "response_time_ms": response_time_ms,
                    "event_type": "response_time"
                }
            )
            
            # Record metric
            self.metrics_exporter.export_metrics([{
                "name": "response_time_ms",
                "value": response_time_ms,
                "tags": {
                    "endpoint": endpoint
                }
            }])
            
        except Exception as e:
            print(f"❌ Failed to log response time: {e}")
    
    def log_error(self, error_type: str, error_message: str, context: Dict[str, Any] = None):
        """Log errors"""
        if not self.enabled:
            return
            
        try:
            self.logger.error(
                f"Error: {error_message}",
                extra={
                    "error_type": error_type,
                    "error_message": error_message,
                    "context": context or {},
                    "event_type": "error"
                }
            )
            
            # Record metric
            self.metrics_exporter.export_metrics([{
                "name": "error_count",
                "value": 1,
                "tags": {
                    "error_type": error_type
                }
            }])
            
        except Exception as e:
            print(f"❌ Failed to log error: {e}")
    
    def log_ai_analysis(self, analysis_type: str, language: str, processing_time_ms: float):
        """Log AI analysis events"""
        if not self.enabled:
            return
            
        try:
            self.logger.info(
                "AI analysis performed",
                extra={
                    "analysis_type": analysis_type,
                    "language": language,
                    "processing_time_ms": processing_time_ms,
                    "event_type": "ai_analysis"
                }
            )
            
        except Exception as e:
            print(f"❌ Failed to log AI analysis: {e}")
    
    def log_user_activity(self, user_id: str, activity_type: str, details: Dict[str, Any] = None):
        """Log user activity"""
        if not self.enabled:
            return
            
        try:
            self.logger.info(
                "User activity",
                extra={
                    "user_id": user_id,
                    "activity_type": activity_type,
                    "details": details or {},
                    "event_type": "user_activity"
                }
            )
            
        except Exception as e:
            print(f"❌ Failed to log user activity: {e}")

# Global monitoring instance
monitoring_service = MonitoringService() 