// client/src/components/CustomerChat.jsx
import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { v4 as uuidv4 } from 'uuid';

const CustomerChat = () => {
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [selectedImage, setSelectedImage] = useState(null);
  const [loadingHistory, setLoadingHistory] = useState(true);

  const [customerId, setCustomerId] = useState(null);
  const [customerName, setCustomerName] = useState('');
  const [nameInput, setNameInput] = useState('');
  const [showNameInput, setShowNameInput] = useState(true);
  // NEW: State to hold previous customer details for "Continue" option
  const [previousCustomerDetails, setPreviousCustomerDetails] = useState(null); 

  const chatBoxRef = useRef(null);
  const fileInputRef = useRef(null);
  const ws = useRef(null);
  const reconnectTimeout = useRef(null);

  const { API_BASE_URL } = useAuth();

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [chatHistory]);

  // Manage customer ID and name from local storage and present options
  useEffect(() => {
    const storedCustomerId = localStorage.getItem('customer_id');
    const storedCustomerName = localStorage.getItem('customer_name');

    if (storedCustomerId && storedCustomerName) {
      // If previous details exist, offer to continue or start new
      setPreviousCustomerDetails({ id: storedCustomerId, name: storedCustomerName });
      setShowNameInput(true); // Still show name input, but with options
      console.log(`CustomerChat: Found previous customer: ${storedCustomerName} (ID: ${storedCustomerId}). Offering options.`);
    } else {
      // No previous details, just ask for a new name
      setShowNameInput(true);
      setLoadingHistory(false); // No history to load yet
      console.log("CustomerChat: No customer ID/name found in local storage. Prompting for new name.");
    }
  }, []);

  // Function to initialize chat after name is set (either new or continued)
  const initializeChat = async (id, name) => {
    setCustomerId(id);
    setCustomerName(name);
    setShowNameInput(false);
    setLoadingHistory(true); // Start loading history
    console.log(`CustomerChat: Initializing chat for ${name} (ID: ${id}).`);
  };

  // Fetch chat history once customerId is available
  useEffect(() => {
    const fetchChatHistory = async (currentCustomerId) => {
      if (!currentCustomerId) {
        console.log("CustomerChat: Customer ID not available for history fetch.");
        setLoadingHistory(false);
        return;
      }
      console.log("CustomerChat: Fetching history for customer ID:", currentCustomerId);

      try {
        const response = await fetch(`${API_BASE_URL}/chat-history/user/${currentCustomerId}`);

        if (response.ok) {
          const history = await response.json();
          setChatHistory(history);
          console.log("CustomerChat: Fetched chat history successfully.");
        } else {
          console.error("CustomerChat: Failed to fetch chat history:", response.status, response.statusText);
          setChatHistory([]);
        }
      } catch (error) {
        console.error("CustomerChat: Error fetching chat history:", error);
        setChatHistory([]);
      } finally {
        setLoadingHistory(false);
      }
    };

    if (customerId && !showNameInput) { // Only fetch if customerId is set and name input is hidden
      fetchChatHistory(customerId);
    }
  }, [customerId, API_BASE_URL, showNameInput]);

  // WebSocket connection
  useEffect(() => {
    const connectWebSocket = () => {
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
        reconnectTimeout.current = null;
      }

      if (!customerId) {
        console.log("CustomerChat: Customer ID not available for WebSocket. Not connecting.");
        if (ws.current) {
          ws.current.close();
          ws.current = null;
        }
        return;
      }

      // NEW: Pass customerId in WebSocket URL
      const currentWsUrl = `${WS_URL}/${customerId}`; 
      if (!ws.current || ws.current.readyState === WebSocket.CLOSED || ws.current.readyState === WebSocket.CLOSING) {
        console.log('CustomerChat: Attempting to connect Customer WebSocket to:', currentWsUrl);
        ws.current = new WebSocket(currentWsUrl);

        ws.current.onopen = () => {
          console.log('CustomerChat: Customer WebSocket connected successfully.');
        };

        ws.current.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            console.log('CustomerChat: Received WebSocket data:', data); 
            if (data.type === 'agent_chat_message' || data.type === 'customer_chat_message') {
              setChatHistory((prevHistory) => {
                const newHistory = [
                  ...prevHistory,
                  {
                    text: data.text,
                    sender: data.sender,
                    timestamp: data.timestamp,
                    image_url: data.image_url,
                    ocr_text: data.ocr_text
                  }
                ];
                console.log('CustomerChat: Updating chat history to:', newHistory);
                return newHistory;
              });
            }
          } catch (error) {
            console.error("CustomerChat: Error parsing WebSocket message:", error, "Raw data:", event.data);
          }
        };

        ws.current.onclose = (event) => {
          console.log('CustomerChat: Customer WebSocket disconnected.', event.code, event.reason);
          if (event.code !== 1000 && !reconnectTimeout.current) {
            console.log('CustomerChat: Attempting to reconnect WebSocket in 3 seconds...');
            reconnectTimeout.current = setTimeout(connectWebSocket, 3000);
          }
        };

        ws.current.onerror = (error) => {
          console.error('CustomerChat: Customer WebSocket error:', error);
        };
      }
    };

    if (customerId && !showNameInput) { // Connect only if customerId is set and name input is hidden
      connectWebSocket();
    }

    return () => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.close();
      }
      if (reconnectTimeout.current) {
        clearTimeout(reconnectTimeout.current);
      }
      ws.current = null;
      reconnectTimeout.current = null;
    };
  }, [customerId, WS_URL, showNameInput]);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setSelectedImage(file);
    } else {
      setSelectedImage(null);
    }
  };

  const handleSend = async () => {
    if (message.trim() === '' && !selectedImage) {
      alert("Please enter a message or select an image to send.");
      return;
    }
    if (!customerId) {
        alert("Customer ID not set. Please refresh and enter your name.");
        return;
    }

    try {
      let response;
      if (selectedImage) {
        const formData = new FormData();
        formData.append('file', selectedImage);
        formData.append('customer_id', customerId);
        formData.append('customer_name', customerName);
        if (message.trim() !== '') {
          formData.append('text', message.trim());
        }
        formData.append('chat_history_json', JSON.stringify(chatHistory));

        response = await fetch(`${API_BASE_URL}/analyze-image-message`, {
          method: 'POST',
          body: formData,
        });
      } else {
        response = await fetch(`${API_BASE_URL}/analyze-message`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ 
            customer_id: customerId,
            customer_name: customerName,
            text: message, 
            chat_history: chatHistory 
          }),
        });
      }

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('CustomerChat: Message sent and analyzed by backend (HTTP response data):', data);
    } catch (error) {
      console.error('CustomerChat: Error sending message to backend:', error);
      alert(`Error sending message: ${error.message}. Please try again.`);
    }
    
    setMessage('');
    setSelectedImage(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !selectedImage) {
      handleSend();
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current.click();
  };

  // NEW: Handle name submission for new chat
  const handleStartNewChatSubmit = () => {
    if (nameInput.trim() === '') {
      alert("Please enter your name to start a new chat.");
      return;
    }
    const newCustomerId = uuidv4();
    localStorage.setItem('customer_id', newCustomerId);
    localStorage.setItem('customer_name', nameInput.trim());
    initializeChat(newCustomerId, nameInput.trim());
  };

  // NEW: Handle continuing previous chat
  const handleContinuePreviousChat = () => {
    if (previousCustomerDetails) {
      localStorage.setItem('customer_id', previousCustomerDetails.id); // Ensure it's explicitly set
      localStorage.setItem('customer_name', previousCustomerDetails.name); // Ensure it's explicitly set
      initializeChat(previousCustomerDetails.id, previousCustomerDetails.name);
    }
  };

  // Render name input form with options
  if (showNameInput) {
    return (
      <div className="panel customer-panel" style={{ textAlign: 'center', padding: '50px' }}>
        <h2>Welcome to Customer Support!</h2>
        {previousCustomerDetails ? (
          <>
            <p>You were previously chatting as **{previousCustomerDetails.name}**.</p>
            <button 
              onClick={handleContinuePreviousChat} 
              style={{ padding: '10px 20px', fontSize: '1em', marginRight: '10px' }}
            >
              Continue as {previousCustomerDetails.name}
            </button>
            <p style={{ marginTop: '20px', marginBottom: '10px' }}>Or start a new chat:</p>
          </>
        ) : (
          <p>Please enter your name to begin:</p>
        )}
        <input
          type="text"
          value={nameInput}
          onChange={(e) => setNameInput(e.target.value)}
          placeholder="Your Name (for new chat)"
          style={{ padding: '10px', fontSize: '1em', width: '80%', maxWidth: '300px', marginBottom: '15px' }}
          onKeyPress={(e) => e.key === 'Enter' && handleStartNewChatSubmit()}
        />
        <button onClick={handleStartNewChatSubmit} style={{ padding: '10px 20px', fontSize: '1em' }}>Start New Chat</button>
      </div>
    );
  }

  if (loadingHistory) {
    return <div style={{ textAlign: 'center', padding: '50px' }}>Loading chat history...</div>;
  }

  return (
    <div className="panel customer-panel">
      <h2>Customer Chat ({customerName})</h2>
      <div className="chat-box" ref={chatBoxRef}>
        <div className="chat-messages">
          {chatHistory.length === 0 ? (
            <p className="no-messages-placeholder">Start a new conversation!</p>
          ) : (
            chatHistory.map((msg, index) => (
              <div key={index} className={`chat-message ${msg.sender}`}>
                {msg.image_url && (
                  <img src={msg.image_url} alt="Customer Upload" style={{ maxWidth: '100%', borderRadius: '8px', marginBottom: '8px' }} />
                )}
                <p>{msg.text}</p>
                {msg.ocr_text && (
                  <small style={{ color: '#888' }}>OCR: "{msg.ocr_text.substring(0, Math.min(msg.ocr_text.length, 50))}..."</small>
                )}
                <small>{new Date(msg.timestamp).toLocaleTimeString()}</small>
              </div>
            ))
          )}
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
        <input
          type="file"
          accept="image/*"
          ref={fileInputRef}
          onChange={handleImageChange}
          style={{ display: 'none' }}
        />
        <button onClick={triggerFileInput} className="attach-button" title="Attach Screenshot">📎</button>
        <button onClick={handleSend} disabled={message.trim() === '' && !selectedImage}>Send</button>
      </div>
      {selectedImage && (
        <p style={{ fontSize: '0.8em', color: '#666', marginTop: '5px' }}>Selected: {selectedImage.name}</p>
      )}
    </div>
  );
};

export default CustomerChat;