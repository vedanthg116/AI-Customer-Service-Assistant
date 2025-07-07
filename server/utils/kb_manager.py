# server/utils/kb_manager.py

# This dictionary serves as a synthetic knowledge base for the AI assistant.
# Each key represents a detected customer intent, and the value is a list of
# factual or helpful pieces of information related to that intent.
# Gemini will use this information to inform its "pre_written_response" and
# "knowledge_base" suggestions to the agent.
knowledge_base = {
    "order_status_inquiry": [
        "Orders typically ship within 1-2 business days.",
        "Standard shipping delivers in 3-5 business days.",
        "Expedited shipping delivers in 1-2 business days.",
        "You can track your order using the tracking number provided in your shipping confirmation email.",
        "Login to your account and visit the 'My Orders' section for the latest status updates."
    ],
    "account_balance_inquiry": [
        "Your current account balance is updated daily.",
        "Detailed transaction history is available in your online portal under 'Statements'.",
        "Overdraft fees apply if your balance falls below zero.",
        "You can set up balance alerts in your account settings.",
        "For security reasons, we cannot disclose exact balance details over chat without full verification."
    ],
    "password_reset_request": [
        "To reset your password, please go to our login page and click 'Forgot Password'.",
        "A password reset link will be sent to the email address registered on your account.",
        "The reset link is valid for 1 hour.",
        "If you don't receive the email, please check your spam or junk folder.",
        "For additional security, ensure your security questions are up-to-date."
    ],
    "technical_support": [
        "Before contacting support, please try restarting your device/application.",
        "Ensure your internet connection is stable.",
        "Our technical support team is available Monday-Friday, 9:00 AM - 7:00 PM EST.",
        "For software issues, check our FAQ section for known bugs and workarounds.",
        "Provide specific error codes or screenshots for faster resolution."
    ],
    "refund_request": [
        "Refunds for eligible items are processed within 5-10 business days after the returned item is received and inspected.",
        "Items must be returned in their original condition within 30 days of purchase for a full refund.",
        "Shipping costs are non-refundable unless the return is due to our error.",
        "Digital products are generally non-refundable.",
        "Please provide your order number and reason for the refund request."
    ],
    "product_information": [
        "Detailed specifications for all products are available on their respective product pages.",
        "Product manuals and user guides can be downloaded from our 'Support' section.",
        "We offer a 1-year warranty on all electronic devices.",
        "Customer reviews provide insights into product performance and features.",
        "New product releases are announced on our website and through our newsletter."
    ],
    "billing_dispute": [
        "For billing discrepancies, please provide the invoice number and the disputed amount.",
        "All charges are detailed in your monthly statement.",
        "Billing disputes must be raised within 60 days of the statement date.",
        "We will investigate the charge and typically respond within 3 business days.",
        "Proof of payment or bank statements may be requested for verification."
    ],
    "change_address_request": [
        "You can update your shipping address in your account settings under 'Address Book'.",
        "Address changes for active orders must be requested within 24 hours of purchase.",
        "For billing address changes, please ensure your payment method is also updated.",
        "A confirmation email will be sent after the address change is processed.",
        "Changes to the primary account address may require security verification."
    ],
    "unclear_intent": [
        "This intent is used when the customer's message is too vague, ambiguous, or contains multiple possible intents.",
        "The system needs more information to accurately categorize the request.",
        "Agent should ask clarifying questions to narrow down the customer's need.",
        "Agent can offer a list of common services or direct to general help resources."
    ],
    "greeting": [
        "A customer's initial polite greeting.",
        "Agent should respond in kind and ask how they can help."
    ],
    "complaint": [
        "Customer expressing dissatisfaction or a problem with a product, service, or interaction.",
        "Agent needs to empathize, acknowledge the issue, and gather details.",
        "Offer resolution steps such as investigation, escalation, or compensation if applicable."
    ],
    "cancellation_request": [
        "Customer wishes to cancel an order, service, or subscription.",
        "Agent needs to confirm the item/service to be cancelled and provide cancellation terms.",
        "Inform about potential fees or deadlines for cancellation."
    ]
}

# These dictionaries are kept for consistency with previous structure,
# but the current Gemini integration directly generates 'pre_written_response' and 'next_actions'
# based on the prompt and the 'knowledge_base' content.
# You can remove them if you are certain they won't be used for static lookups anymore.
recommended_responses = {
    "order_status_inquiry": "Hello! I can certainly help with your order status. Could you please provide your order number?",
    "account_balance_inquiry": "Hi there! I can assist with your account balance. To ensure your privacy, could you please confirm your identity first?",
    "password_reset_request": "Of course! To reset your password, please visit our login page and click on the 'Forgot Password' link. A new link will be sent to your registered email.",
    "technical_support": "I understand you're experiencing a technical issue. To help you best, could you please describe the problem in more detail and let me know if you're seeing any error messages?",
    "refund_request": "I can help you with your refund request. Could you please provide your order number and the reason for the return?",
    "product_information": "I'd be happy to provide information about our products! Do you have a specific product in mind, or are you looking for general details?",
    "billing_dispute": "I can certainly look into this billing concern for you. Could you please provide the invoice number or relevant transaction details?",
    "change_address_request": "I can assist you with updating your address. Are you looking to change a shipping or billing address, and for which order or account?",
    "unclear_intent": "I'm having a bit of trouble understanding your request fully. Could you please rephrase or provide more details, or tell me in a few words what you need help with?",
    "greeting": "Hello! Thank you for contacting us. How may I assist you today?",
    "complaint": "I'm very sorry to hear that you're having this issue. Please tell me more about what happened so I can help address your concerns.",
    "cancellation_request": "I can help with cancellation requests. Please provide your order ID and the reason for cancellation."
}

next_best_actions = {
    "order_status_inquiry": ["Ask for Order ID.", "Direct to 'My Orders' page on website.", "Check internal order management system."],
    "account_balance_inquiry": ["Initiate identity verification (e.g., last 4 SSN, security questions).", "Direct to online banking portal.", "Offer to send account statement via secure email."],
    "password_reset_request": ["Direct to 'Forgot Password' link.", "Verify registered email address.", "Suggest checking spam folder if link isn't received.", "Escalate if user cannot access email."],
    "technical_support": ["Gather detailed description of the issue.", "Suggest basic troubleshooting (restart, clear cache).", "Offer to escalate to Tier 2 support or schedule a callback."],
    "refund_request": ["Request order number and specific reason for refund.", "Explain refund policy and eligibility criteria.", "Initiate return merchandise authorization (RMA) process."],
    "product_information": ["Ask for specific product name or category.", "Direct to product's detailed specifications page.", "Provide comparison details if multiple products are mentioned."],
    "billing_dispute": ["Request invoice number and details of the dispute.", "Review customer's billing history.", "Initiate an investigation with the billing department."],
    "change_address_request": ["Confirm type of address (shipping/billing) and associated order/account.", "Verify current address on file.", "Guide customer to update via portal or manually update if authorized."],
    "unclear_intent": ["Ask clarifying questions ('Could you tell me more about...?').", "Offer a menu of common inquiry types.", "Suggest searching the general FAQ section."],
    "greeting": ["Acknowledge greeting and ask open-ended question for assistance.", "Prompt for initial query."],
    "complaint": ["Apologize sincerely and validate customer's feelings.", "Collect all relevant details of the complaint.", "Outline next steps for resolution or escalation."],
    "cancellation_request": ["Ask for Order ID/Service details and reason for cancellation.", "Inform about any cancellation fees or deadlines.", "Confirm cancellation process and timeline."]
}