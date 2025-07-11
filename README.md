AI Customer Service Assistant:


This project is a real-time AI-powered customer service chat application with a dedicated agent dashboard for managing customer interactions. It demonstrates how to integrate large language models (like Google Gemini) for automated responses and sentiment analysis, alongside human agent intervention for complex queries.

✨ Features
Simplified Customer Onboarding: Customers can start a chat simply by providing a name, no explicit login required. Their session is persisted locally.

Real-time Chat: Instant messaging between customers and AI/agents using WebSockets.

AI-Powered Analysis (Google Gemini - using this for will use faster llm api later on):

Intent Prediction: Automatically identifies the customer's intent (e.g., "order status", "returns").

Sentiment Analysis: Determines the emotional tone of customer messages.

Entity Detection: Extracts key information from messages.

Suggested Responses & Next Actions: Provides agents with AI-generated pre-written replies and recommended steps based on the analysis.

Image Analysis (OCR): Customers can upload screenshots, and OCR (Optical Character Recognition) extracts text for AI analysis.

Agent Dashboard:

Active Conversations List: View all ongoing customer chats.

Conversation Assignment: Agents can "claim" unassigned conversations to avoid multiple agents responding to the same customer.

Agent Visibility: Other agents can see who a conversation is assigned to.

Real-time Updates: Conversation list and chat view update dynamically via WebSockets.

Conversation Filters: Filter conversations by "All", "Unassigned", or "My Assigned".

Agent Identity Switching: Easily switch between different agent identities for demonstration purposes.

Knowledge Base Integration: AI analysis leverages a simple knowledge base (though not directly editable from the UI in this demo).

Persistent Data: Conversations, messages, and customer profiles are stored in a SQLite database.

🚀 Technologies Used
Backend (FastAPI - Python):

FastAPI: Modern, fast (high-performance) web framework for building APIs.

SQLAlchemy: SQL toolkit and Object Relational Mapper (ORM) for database interactions.

AioSQLite: Asynchronous SQLite driver for SQLAlchemy.

Uvicorn: ASGI server for running FastAPI applications.

Google Gemini API: For AI text and image analysis.

EasyOCR: For Optical Character Recognition from images.

WebSockets: For real-time communication between backend and frontend.

python-dotenv: For managing environment variables.

Frontend (React - JavaScript):

React: A JavaScript library for building user interfaces.

Vite: Next-generation frontend tooling for fast development.

React Router DOM: For declarative routing in React applications.

UUID: For generating unique identifiers (UUIDs) for customers and agents.

Local Storage: For persisting customer and agent identities across browser sessions.

CSS: For styling.

🛠️ Setup Instructions
1. Clone the Repository
git clone <your-repository-url>
cd capstone # Or whatever your project's root folder is named

2. Backend Setup
Navigate into the server directory:

cd server

a. Create a Python Virtual Environment (Recommended)

python3 -m venv venv
source venv/bin/activate # On Windows: .\venv\Scripts\activate

b. Install Python Dependencies


# pip install fastapi uvicorn sqlalchemy aiosqlite python-dotenv google-generativeai easyocr python-multipart

c. Configure Environment Variables

Create a .env file in the server directory:

# .env
GEMINI_API_KEY="YOUR_GEMINI_API_KEY"
# Get your API key from https://ai.google.dev/

d. Delete Old Database (Crucial for Schema Updates)

If you've run the project before, delete the old SQLite database file to ensure the new schema is applied:

rm sql_app.db # On Windows: del sql_app.db

e. Run the Backend Server

uvicorn main:app --reload --port 8000

The server should start on http://127.0.0.1:8000. You should see logs indicating database tables are created.

3. Frontend Setup
Open a new terminal and navigate into the client directory:

cd ../client # From the server directory, or cd capstone/client from project root

a. Install Node.js Dependencies

npm install

b. Run the Frontend Development Server

npm run dev

The frontend should start on http://localhost:5173.

🚀 Usage
1. Access the Application
Open your web browser and go to http://localhost:5173/. You will see a simple home page.

2. Customer Chat
Click on "Start Customer Chat".

If it's your first time, you'll be prompted to "Please enter your name to begin:". Enter a name (e.g., "Alice") and click "Start New Chat".

If you've chatted before on this browser, you'll see an option to "Continue as [Your Previous Name]" or "Start New Chat".

Type your message in the input field and press Enter or click "Send".

Verify: Your messages should appear in the chat. The AI will process them (there might be a slight delay as Gemini responds).

Test multiple customer chats: Open an incognito window or a different browser, go to http://localhost:5173/customer, and enter a different name (e.g., "Bob"). Send messages. Verify that Alice's chat does not show Bob's messages, and vice-versa.

3. Agent Dashboard
Open a new browser tab and go to http://localhost:5173/agent.

If it's your first time, you'll be prompted to "Please enter your name to access the dashboard:". Enter an agent name (e.g., "Agent Charlie") and click "Enter Dashboard".

Switch Agents: To simulate another agent, click the "Switch Agent" button at the top right. This will clear your current agent's session and allow you to enter a new agent name (e.g., "Agent David").

View Conversations: You should see the active conversations from your customers (e.g., "Alice" and "Bob").

Select a Conversation: Click on a conversation in the left panel to view its chat history and AI suggestions.

Claim/Release Conversations:

Click the "Claim" button next to an unassigned conversation. It should then show (Assigned to YOU).

If you switch to another agent (e.g., "Agent David"), that agent will see (Assigned to Agent Charlie) next to the claimed conversation, preventing them from claiming it.

Click "Release" to unassign a conversation.

Reply to Customers: Type a message in the chat input and click "Send Reply".

Verify: The agent's reply should appear in the customer's chat in real-time.

🧹 Cleanup
To reset the database and start fresh (e.g., for a new demo):

Stop the backend server (Ctrl + C in the backend terminal).

Delete the sql_app.db file in the server directory.

rm server/sql_app.db

Restart the backend server.
