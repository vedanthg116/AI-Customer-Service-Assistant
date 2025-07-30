// client/src/components/CustomerChat.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useAuth } from '../context/AuthContext'; // Correct import for useAuth
import { v4 as uuidv4 } from 'uuid'; // For generating temporary IDs

const CustomerChat = () => {
  const { userId, userName, isAuthenticated, isLoadingAuth, setCustomerIdentity, clearCustomerIdentity } = useAuth(); // Use the custom hook and new functions
  const [message, setMessage] = useState('');
  const [chatHistory, setChatHistory] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [imageFile, setImageFile] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [isSending, setIsSending] = useState(false); // To prevent multiple sends
  const [isUploadingImage, setIsUploadingImage] = useState(false); // For image upload state

  // New state for name input
  const [customerNameInput, setCustomerNameInput] = useState('');
  const [showNameInputScreen, setShowNameInputScreen] = useState(true);
  const [isSearchingCustomer, setIsSearchingCustomer] = useState(false);

  // New function to search for existing customer by name
  const handleSearchExistingCustomer = async () => {
    if (customerNameInput.trim() === '') {
      alert("Please enter a name to search.");
      return;
    }

    setIsSearchingCustomer(true);
    try {
      const response = await fetch(`${API_BASE_URL}/search-customer/${encodeURIComponent(customerNameInput.trim())}`);
      if (response.ok) {
        const data = await response.json();
        if (data.customer_id) {
          // Customer found, set their identity and continue
          setCustomerIdentity(customerNameInput.trim(), data.customer_id);
          setShowNameInputScreen(false);
          console.log(`CustomerChat: Found existing customer ${customerNameInput.trim()} with ID ${data.customer_id}`);
        } else {
          alert(`No existing customer found with name "${customerNameInput.trim()}". Starting new chat.`);
          setCustomerIdentity(customerNameInput.trim());
          setShowNameInputScreen(false);
        }
      } else {
        // Customer not found, start new chat
        alert(`No existing customer found with name "${customerNameInput.trim()}". Starting new chat.`);
        setCustomerIdentity(customerNameInput.trim());
        setShowNameInputScreen(false);
      }
    } catch (error) {
      console.error('CustomerChat: Error searching for customer:', error);
      alert("Error searching for customer. Starting new chat.");
      setCustomerIdentity(customerNameInput.trim());
      setShowNameInputScreen(false);
    } finally {
      setIsSearchingCustomer(false);
    }
  };


  const ws = useRef(null);
  const reconnectTimeout = useRef(null);
  const chatBoxRef = useRef(null); // Ref for auto-scrolling chat

  const API_BASE_URL = import.meta.env.VITE_API_URL;
  const WS_BASE_URL = import.meta.env.VITE_WS_URL;

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [chatHistory]);

  // Effect to manage the name input screen visibility
  useEffect(() => {
    if (!isLoadingAuth) {
      // If auth is loaded and user is authenticated, hide the name input screen
      if (isAuthenticated && userId && userName) {
        setShowNameInputScreen(false);
      } else {
        // If auth is loaded but no user, show the name input screen
        setShowNameInputScreen(true);
        // Pre-fill input if a name was previously stored but ID wasn't (edge case)
        setCustomerNameInput(localStorage.getItem('customer_user_name') || '');
      }
    }
  }, [isLoadingAuth, isAuthenticated, userId, userName]);


  // Fetch initial chat history when authenticated
  useEffect(() => {
    const fetchChatHistory = async () => {
      if (!isAuthenticated || !userId || showNameInputScreen) return; // Only fetch if authenticated and name screen is hidden

      try {
        const response = await fetch(`${API_BASE_URL}/chat-history/user/${userId}`);
        if (response.ok) {
          const data = await response.json();
          setChatHistory(Array.isArray(data) ? data : []);
          console.log(`CustomerChat: Fetched chat history for user ${userId}:`, data);
        } else {
          console.error('CustomerChat: Failed to fetch chat history:', response.statusText);
          setChatHistory([]);
        }
      } catch (error) {
          // Check if the error is due to a 404 for chat history (e.g., brand new user with no history yet)
          // For now, just log and set empty. A 404 is valid for no history.
          console.error('CustomerChat: Error fetching chat history (possibly none yet):', error);
          setChatHistory([]);
      }
    };

    fetchChatHistory();
  }, [isAuthenticated, userId, API_BASE_URL, showNameInputScreen]); // Add showNameInputScreen to dependencies


  // WebSocket connection logic wrapped in useCallback
  const connectWebSocket = useCallback(() => {
    // Clear any existing reconnect attempts
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    if (!isAuthenticated || !userId || showNameInputScreen) { // Don't connect if not authenticated or name screen is visible
      console.log("CustomerChat: Not authenticated, User ID not available, or Name Input Screen is visible. Not connecting WebSocket.");
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
      return;
    }

    const currentWsUrl = `${WS_BASE_URL}/ws/customer/${userId}`;
    if (!ws.current || ws.current.readyState === WebSocket.CLOSED || ws.current.readyState === WebSocket.CLOSING) {
      console.log('CustomerChat: Attempting to connect Customer WebSocket to:', currentWsUrl);
      ws.current = new WebSocket(currentWsUrl);

      ws.current.onopen = () => {
        console.log('CustomerChat: Customer WebSocket connected successfully.');
        setIsTyping(false); // Reset typing status on connect
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('CustomerChat: Received WebSocket data:', data);

          setChatHistory((prev) => {
            const currentMessages = Array.isArray(prev) ? prev : [];
            const incomingMessageId = data.message_id; 
            const incomingTimestamp = data.timestamp;

            // 1. If the message already exists by its final server-assigned ID, ignore it.
            // This is the primary deduplication for confirmed messages.
            if (incomingMessageId && currentMessages.some(msg => msg.id === incomingMessageId)) {
              console.log(`CustomerChat: Ignoring duplicate message with server ID: ${incomingMessageId}.`);
              return currentMessages;
            }

            if (data.type === 'agent_chat_message') {
              setIsTyping(false); 
              return [
                ...currentMessages,
                {
                  id: incomingMessageId,
                  text: data.text,
                  sender: data.sender,
                  timestamp: incomingTimestamp,
                },
              ];
            } 
            
            else if (data.type === 'customer_chat_message') {
                // 2. For customer messages, first try to find and update the *optimistic* message.
                // An optimistic message is marked with `id: null` and has its `tempId` (though `tempId` is not used for lookup here).
                const optimisticMessageIndex = currentMessages.findIndex(msg => 
                    msg.sender === 'customer' && 
                    msg.text === data.text && // Match by text (heuristic)
                    msg.id === null // Crucial: This identifies the optimistic message awaiting server ID
                );

                if (optimisticMessageIndex > -1) {
                    // Found the optimistic message, update it with the server's details
                    const updatedMessages = [...currentMessages];
                    updatedMessages[optimisticMessageIndex] = { 
                        ...updatedMessages[optimisticMessageIndex], 
                        id: incomingMessageId, // Assign the server's ID
                        timestamp: incomingTimestamp, // Use server's timestamp
                        image_url: data.image_url,
                        ocr_text: data.ocr_text
                    };
                    return updatedMessages;
                } else {
                    // If no matching optimistic message (id === null) was found, 
                    // this is either a message from another source (e.g., recorded call)
                    // or an optimistic message that somehow wasn't marked correctly,
                    // or a re-broadcast that needs to be added as new.
                    // (The top-level duplicate check for `incomingMessageId` handles strict duplicates).
                    return [...currentMessages, {
                        id: incomingMessageId,
                        text: data.text,
                        sender: data.sender,
                        timestamp: incomingTimestamp,
                        image_url: data.image_url,
                        ocr_text: data.ocr_text
                    }];
                }
            }
            return currentMessages; // Fallback for unknown message types
          });
        } catch (error) {
          console.error("CustomerChat: Error parsing WebSocket message:", error, "Raw data:", event.data);
        }
      };

      ws.current.onclose = (event) => {
        console.log('CustomerChat: Customer WebSocket disconnected.', event.code, event.reason);
        if (event.code !== 1000 && !reconnectTimeout.current) { // 1000 is normal closure
          console.log('CustomerChat: Attempting to reconnect WebSocket in 3 seconds...');
          reconnectTimeout.current = setTimeout(connectWebSocket, 3000);
        }
      };

      ws.current.onerror = (error) => {
        console.error('CustomerChat: Customer WebSocket error:', error);
      };
    }
  }, [isAuthenticated, userId, WS_BASE_URL, showNameInputScreen]); // Added showNameInputScreen to dependencies


  // Effect to manage WebSocket connection lifecycle
  useEffect(() => {
    connectWebSocket();
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
  }, [connectWebSocket]); // Re-run effect only if connectWebSocket changes

  // Handle customer name submission
  const handleCustomerNameSubmit = () => {
    if (customerNameInput.trim() === '') {
      alert("Please enter your name to start the chat.");
      return;
    }
    setCustomerIdentity(customerNameInput.trim()); // Use the AuthContext function
    setShowNameInputScreen(false); // Hide the name input screen
  };

  // Function to handle starting a completely new chat
  const handleStartNewChat = () => {
    clearCustomerIdentity(); // Clear identity using AuthContext function
    setCustomerNameInput(''); // Clear input field
    setChatHistory([]); // Clear chat history
    setShowNameInputScreen(true); // Show the name input screen again
    // No need for window.location.reload() as state update will re-render
  };


  const handleSendMessage = async () => {
    if (isSending || (!message.trim() && !imageFile)) {
      return;
    }

    setIsSending(true);
    setIsTyping(true); // Indicate that a message is being processed

    const currentTimestamp = new Date().toISOString();
    const tempClientSideId = uuidv4(); // Generate a temporary client-side ID for optimistic display

    // Optimistically add customer message to chat history
    const newCustomerMessage = {
      tempClientSideId: tempClientSideId, // Store this for potential future advanced deduplication
      id: null, // Critical: Set initial ID to null, it will be updated by server's message_id
      text: message.trim() || (imageFile ? "Image shared." : ""),
      sender: 'customer',
      timestamp: currentTimestamp, // Use client's current time for optimistic display
      image_url: imagePreview, 
      ocr_text: null 
    };
    setChatHistory((prev) => [...(Array.isArray(prev) ? prev : []), newCustomerMessage]);
    setMessage(''); // Clear input field
    setImagePreview(null); // Clear image preview
    const fileToSend = imageFile; // Store file before clearing state
    setImageFile(null); // Clear image file state

    try {
      if (fileToSend) {
        setIsUploadingImage(true);
        const formData = new FormData();
        formData.append('file', fileToSend);
        formData.append('customer_id', userId);
        formData.append('customer_name', userName);
        formData.append('text', newCustomerMessage.text);
        formData.append('chat_history_json', JSON.stringify(chatHistory)); // Send current history for context

        const response = await fetch(`${API_BASE_URL}/analyze-image-message`, {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          const errorData = await response.json();
          console.error('CustomerChat: Failed to send image message:', errorData);
          alert(`Failed to send image: ${errorData.detail || response.statusText}`);
          // TODO: Implement logic to revert optimistic update or mark as failed
        }
      } else {
        const response = await fetch(`${API_BASE_URL}/analyze-message`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            customer_id: userId,
            customer_name: userName,
            text: newCustomerMessage.text,
            chat_history: chatHistory, // Send current history for context
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          console.error('CustomerChat: Failed to send text message:', errorData);
          alert(`Failed to send message: ${errorData.detail || response.statusText}`);
          // TODO: Implement logic to revert optimistic update or mark as failed
        }
      }
    } catch (error) {
      console.error('CustomerChat: Network error sending message:', error);
      alert("Network error or server unreachable.");
      // TODO: Implement logic to revert optimistic update or mark as failed
    } finally {
      setIsSending(false);
      setIsUploadingImage(false);
      // setIsTyping(false); // Agent will handle setting this to false when they reply
    }
  };

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      const reader = new FileReader();
      reader.onloadend = () => {
        setImagePreview(reader.result);
      };
      reader.readAsDataURL(file);
    } else {
      setImageFile(null);
      setImagePreview(null);
    }
  };

  // Display loading state for auth
  if (isLoadingAuth) {
    return <div className="panel customer-panel" style={{ textAlign: 'center', padding: '50px' }}>Loading customer identity...</div>;
  }

  // Render name input form if needed
  if (showNameInputScreen) {
    return (
      <div className="panel customer-panel" style={{ textAlign: 'center', padding: '50px' }}>
        <h2>Customer Chat</h2>
        <p>Enter your name to continue an existing chat or start a new one:</p>
        <input
          type="text"
          value={customerNameInput}
          onChange={(e) => setCustomerNameInput(e.target.value)}
          placeholder="Your Name"
          style={{ padding: '10px', fontSize: '1em', width: '80%', maxWidth: '300px', marginBottom: '15px' }}
          onKeyPress={(e) => e.key === 'Enter' && handleSearchExistingCustomer()}
        />
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'center' }}>
          <button 
            onClick={handleSearchExistingCustomer} 
            className="home-button" 
            style={{ padding: '10px 20px', fontSize: '1em', backgroundColor: '#28a745' }}
            disabled={isSearchingCustomer}
          >
            {isSearchingCustomer ? 'Searching...' : 'Continue Existing Chat'}
          </button>
          <button 
            onClick={handleCustomerNameSubmit} 
            className="home-button" 
            style={{ padding: '10px 20px', fontSize: '1em', backgroundColor: '#007bff' }}
          >
            Start New Chat
          </button>
          {userName && ( // Show "Continue as" only if a name was previously stored
            <button 
              onClick={() => { setCustomerIdentity(userName); setShowNameInputScreen(false); }} 
              className="home-button" 
              style={{ marginTop: '10px', padding: '10px 20px', fontSize: '1em', backgroundColor: '#6c757d' }}
            >
              Continue as {userName}
            </button>
          )}
        </div>
      </div>
    );
  }

  // Main Customer Chat UI
  return (
    <div className="panel customer-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
        <h2>Customer Chat ({userName})</h2>
        <button onClick={handleStartNewChat} className="home-button logout-button">Start New Chat</button> {/* Updated onClick */}
      </div>
      <div className="chat-box" ref={chatBoxRef}>
        <div className="chat-messages">
          {chatHistory.length === 0 ? (
            <p className="no-messages-placeholder">Start a conversation!</p>
          ) : (
            chatHistory.map((msg, index) => (
              // Use msg.id as key if available, otherwise fallback to index. tempClientSideId could also be used for optimistic.
              <div key={msg.id || msg.tempClientSideId || index} className={`chat-message ${msg.sender}`}>
                {msg.image_url && (
                  <img src={msg.image_url} alt="User Upload" style={{ maxWidth: '100%', borderRadius: '8px', marginBottom: '8px' }} />
                )}
                <p>{msg.text}</p>
                {msg.ocr_text && (
                  <small style={{ color: '#888' }}>OCR: "{msg.ocr_text.substring(0, Math.min(msg.ocr_text.length, 50))}..."</small>
                )}
                <small>{new Date(msg.timestamp).toLocaleTimeString()}</small>
              </div>
            ))
          )}
          {isTyping && (
            <div className="chat-message agent">
              <p>Agent is typing...</p>
            </div>
          )}
        </div>
      </div>
      <div className="message-input-area">
        {imagePreview && (
          <div style={{ marginBottom: '10px', position: 'relative' }}>
            <img src={imagePreview} alt="Preview" style={{ maxWidth: '100px', maxHeight: '100px', borderRadius: '8px' }} />
            <button
              onClick={() => { setImagePreview(null); setImageFile(null); }}
              style={{ position: 'absolute', top: '-5px', right: '-5px', background: 'red', color: 'white', border: 'none', borderRadius: '50%', width: '20px', height: '20px', cursor: 'pointer', fontSize: '0.8em', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
            >
              X
            </button>
          </div>
        )}
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
          placeholder="Type your message..."
          disabled={isSending || isUploadingImage}
        />
        <input
          type="file"
          accept="image/*"
          onChange={handleImageChange}
          style={{ display: 'none' }}
          id="image-upload-input"
          disabled={isSending || isUploadingImage}
        />
        <label htmlFor="image-upload-input" className="upload-button" style={{ cursor: 'pointer', padding: '10px', borderRadius: '5px', background: '#007bff', color: 'white', whiteSpace: 'nowrap' }}>
          {isUploadingImage ? 'Uploading...' : 'Upload Image'}
        </label>
        <button onClick={handleSendMessage} disabled={isSending || isUploadingImage || (!message.trim() && !imageFile)}>
          {isSending ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
};

export default CustomerChat;
