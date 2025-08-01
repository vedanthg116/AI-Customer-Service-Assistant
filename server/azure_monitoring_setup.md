# Azure Monitoring Setup Guide

## 📊 **Monitoring Overview**

This guide helps you set up comprehensive monitoring for your customer support system using Azure services.

## 🎯 **What We'll Monitor**

### **Application Performance:**
- ✅ API response times
- ✅ Error rates and types
- ✅ Database query performance
- ✅ Memory and CPU usage

### **Business Metrics:**
- ✅ Conversations created per day
- ✅ Messages sent per hour
- ✅ Translation usage by language
- ✅ Agent response times
- ✅ Customer satisfaction metrics

### **User Experience:**
- ✅ Page load times
- ✅ User interactions
- ✅ Geographic distribution
- ✅ Device and browser usage

### **Infrastructure:**
- ✅ Server health
- ✅ Database performance
- ✅ Storage usage
- ✅ Cost tracking

## 🚀 **Setup Steps**

### **Step 1: Create Azure Application Insights**

```bash
# Create Application Insights resource
az monitor app-insights component create \
  --app your-app-insights-name \
  --location eastus \
  --resource-group your-resource-group \
  --application-type web \
  --kind web

# Get the connection string
az monitor app-insights component show \
  --app your-app-insights-name \
  --resource-group your-resource-group \
  --query connectionString
```

### **Step 2: Install Monitoring Packages**

```bash
# Install Azure monitoring packages
pip install opencensus-ext-azure
pip install opencensus-ext-logging
pip install opencensus-ext-requests
```

### **Step 3: Configure Environment Variables**

```bash
# Add to your .env file
APPLICATIONINSIGHTS_CONNECTION_STRING="InstrumentationKey=your-key;IngestionEndpoint=https://eastus-0.in.applicationinsights.azure.com/;LiveEndpoint=https://eastus.livediagnostics.monitor.azure.com/"
```

### **Step 4: Update requirements.txt**

```txt
# Add to requirements.txt
opencensus-ext-azure==1.1.8
opencensus-ext-logging==0.1.0
opencensus-ext-requests==0.1.0
```

## 📈 **Custom Metrics Dashboard**

### **Conversation Metrics:**
```json
{
  "name": "conversation_count",
  "description": "Number of conversations created",
  "tags": ["source", "language"],
  "aggregation": "count"
}
```

### **Message Metrics:**
```json
{
  "name": "message_count", 
  "description": "Number of messages sent",
  "tags": ["sender_type", "language", "has_translation"],
  "aggregation": "count"
}
```

### **Translation Metrics:**
```json
{
  "name": "translation_count",
  "description": "Number of translations performed",
  "tags": ["source_language", "target_language", "method", "success"],
  "aggregation": "count"
}
```

### **Response Time Metrics:**
```json
{
  "name": "response_time_ms",
  "description": "API response times",
  "tags": ["endpoint"],
  "aggregation": "average"
}
```

### **Error Metrics:**
```json
{
  "name": "error_count",
  "description": "Number of errors",
  "tags": ["error_type"],
  "aggregation": "count"
}
```

## 📊 **Azure Dashboard Queries**

### **Daily Conversation Count:**
```kusto
customEvents
| where name == "conversation_created"
| summarize count() by bin(timestamp, 1d)
| render timechart
```

### **Message Volume by Language:**
```kusto
customEvents
| where name == "message_sent"
| summarize count() by customDimensions.language, bin(timestamp, 1h)
| render timechart
```

### **Translation Success Rate:**
```kusto
customEvents
| where name == "translation"
| summarize 
    total = count(),
    success = countif(customDimensions.success == "true")
| extend success_rate = success * 100.0 / total
```

### **API Response Times:**
```kusto
customEvents
| where name == "response_time"
| summarize avg(customDimensions.response_time_ms) by customDimensions.endpoint
| render barchart
```

### **Error Analysis:**
```kusto
exceptions
| summarize count() by type, bin(timestamp, 1h)
| render timechart
```

## 🔔 **Alert Rules**

### **High Error Rate Alert:**
```json
{
  "name": "High Error Rate",
  "condition": {
    "metricName": "exceptions/count",
    "operator": "GreaterThan",
    "threshold": 10,
    "timeAggregation": "Count",
    "windowSize": "PT5M"
  },
  "actions": [
    {
      "actionGroupId": "your-action-group-id",
      "webhookProperties": {}
    }
  ]
}
```

### **Slow Response Time Alert:**
```json
{
  "name": "Slow API Response",
  "condition": {
    "metricName": "response_time_ms",
    "operator": "GreaterThan",
    "threshold": 5000,
    "timeAggregation": "Average",
    "windowSize": "PT5M"
  }
}
```

### **Cost Budget Alert:**
```json
{
  "name": "Budget Alert",
  "condition": {
    "metricName": "cost",
    "operator": "GreaterThan",
    "threshold": 50,
    "timeAggregation": "Total",
    "windowSize": "P1M"
  }
}
```

## 📱 **Real-time Monitoring**

### **Live Metrics Stream:**
- Real-time application performance
- Live user sessions
- Instant error detection
- Performance counters

### **Application Map:**
- Service dependencies
- Performance bottlenecks
- Error propagation
- Database connections

### **User Flows:**
- User journey tracking
- Conversion funnels
- Drop-off analysis
- Feature usage patterns

## 🎯 **Business Intelligence**

### **Customer Support KPIs:**
```kusto
// Average response time
customEvents
| where name == "response_time"
| summarize avg(customDimensions.response_time_ms)

// Customer satisfaction
customEvents
| where name == "customer_satisfaction"
| summarize avg(customDimensions.rating)

// Language distribution
customEvents
| where name == "translation"
| summarize count() by customDimensions.source_language
```

### **Agent Performance:**
```kusto
// Agent response times
customEvents
| where name == "agent_response"
| summarize avg(customDimensions.response_time_ms) by customDimensions.agent_id

// Agent workload
customEvents
| where name == "conversation_assigned"
| summarize count() by customDimensions.agent_id, bin(timestamp, 1d)
```

## 🔧 **Integration with Existing Code**

### **Add Monitoring to Chat Router:**
```python
from monitoring_config import monitoring_service
import time

@app.post("/send-message")
async def send_message(request: SendMessageRequest):
    start_time = time.time()
    
    try:
        # Your existing code...
        
        # Log successful message
        monitoring_service.log_message_sent(
            message_id=str(saved_message.id),
            sender_type="customer",
            language=detected_language,
            has_translation=detected_language != "en"
        )
        
        # Log response time
        response_time = (time.time() - start_time) * 1000
        monitoring_service.log_response_time("/send-message", response_time)
        
    except Exception as e:
        monitoring_service.log_error("message_send_error", str(e))
        raise
```

### **Add Monitoring to Translation:**
```python
def translate_text(self, text: str, target_language: str, source_language: str = None):
    start_time = time.time()
    
    try:
        # Your existing translation code...
        
        # Log translation
        monitoring_service.log_translation(
            source_language=source_language,
            target_language=target_language,
            method=result["method"],
            success=True
        )
        
    except Exception as e:
        monitoring_service.log_translation(
            source_language=source_language,
            target_language=target_language,
            method="error",
            success=False
        )
        raise
```

## 📊 **Dashboard Templates**

### **Executive Dashboard:**
- Total conversations today
- Average response time
- Customer satisfaction score
- Cost per conversation
- Language distribution

### **Operations Dashboard:**
- Active conversations
- Agent workload
- Error rates
- System performance
- Translation accuracy

### **Technical Dashboard:**
- API response times
- Database performance
- Memory usage
- Error logs
- Service health

## 💰 **Cost Optimization**

### **Free Tier Limits:**
- 5GB data ingestion per month
- 1GB data retention
- Basic alerting
- Standard metrics

### **Cost Control:**
- Set daily data caps
- Use sampling for high-volume events
- Archive old data
- Monitor usage regularly

### **Budget Alerts:**
- Set spending limits
- Configure alerts at 80% usage
- Review costs weekly
- Optimize data collection

## 🎯 **Next Steps**

1. **Deploy Application Insights**
2. **Configure monitoring in your code**
3. **Set up custom dashboards**
4. **Create alert rules**
5. **Monitor and optimize**

This monitoring setup will give you complete visibility into your customer support system's performance, user experience, and business metrics! 🚀 