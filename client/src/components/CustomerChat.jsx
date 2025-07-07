// client/src/components/CustomerChat.jsx
import React, { useState, useEffect, useRef } from 'react';

const CustomerChat = ({ onSendMessage }) => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);

  const chatBoxRef = useRef(null);
  const ws = useRef(null);
  const WS_URL = 'ws://127.0.0.1:8000/ws/customer'; 

  // Effect to scroll to the bottom whenever chatHistory updates
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [chatHistory]);

  // Effect to establish and manage the WebSocket connection for incoming messages
  useEffect(() => {
    ws.current = new WebSocket(WS_URL);

    ws.current.onopen = () => {
      console.log('Customer WebSocket connected.');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Listen for agent chat messages broadcast from the backend
      // and also the echo of customer's own message from backend
      if (data.type === 'agent_chat_message' || data.type === 'customer_chat_message') {
        setChatHistory((prevHistory) => [
          ...prevHistory,
          { text: data.text, sender: data.sender, timestamp: data.timestamp }
        ]);
      }
    };

    ws.current.onclose = () => {
      console.log('Customer WebSocket disconnected.');
    };

    ws.current.onerror = (error) => {
      console.error('Customer WebSocket error:', error);
    };

    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, []); // Empty dependency array means this effect runs only once on mount

  // Modified handleSend: now only sends the message, does NOT optimistically update local chat history
  const handleSend = async () => {
    if (message.trim() === '') return;

    // Create the new customer message object first (but don't add to state yet)
    const newCustomerMessage = { text: message, sender: 'customer', timestamp: new Date().toISOString() };
    
    // IMPORTANT: Send the latest message and the *current* chat history to the backend.
    // The backend will then broadcast the new message back to this client via WS,
    // which will then be added to chatHistory by the onmessage handler.
    // This prevents duplicates.
    onSendMessage(message, [...chatHistory, newCustomerMessage]); // Pass the history *including* the new message for backend processing

    setMessage(''); // Clear the input field
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleSend();
    }
  };

  return (
    <div className="panel customer-panel">
      <h2>Customer Chat</h2>
      <div className="chat-box" ref={chatBoxRef}>
        <div className="chat-messages">
          {chatHistory.map((msg, index) => (
            <div key={index} className={`chat-message ${msg.sender}`}>
              <p>{msg.text}</p>
              <small>{new Date(msg.timestamp).toLocaleTimeString()}</small>
            </div>
          ))}
        </div>
      </div>
      <div className="message-input-area">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message..."
        />
        <button onClick={handleSend}>Send</button>
      </div>
    </div>
  );
};

export default CustomerChat;