// client/src/components/AgentDashboard.jsx
import React, { useState, useEffect, useRef } from 'react';

const AgentDashboard = () => {
  // State for conversation history (customer messages via WS, agent replies local)
  const [conversation, setConversation] = useState([]);
  // State for the AI analysis of the LATEST customer message
  const [latestAnalysis, setLatestAnalysis] = useState(null);

  // State for agent's input message
  const [agentMessage, setAgentMessage] = useState('');

  // Time metrics
  const [convoStartTime, setConvoStartTime] = useState(null); // Timestamp when first message received
  const [convoDuration, setConvoDuration] = useState('00:00:00');
  const [timeSinceLastCustomerMessage, setTimeSinceLastCustomerMessage] = useState('00:00:00');
  const lastCustomerMessageTimestamp = useRef(null); // Ref to hold the timestamp for accurate calculation

  // WebSocket setup for Agent Dashboard
  const ws = useRef(null);
  const WS_URL = 'ws://127.0.0.1:8000/ws/agent'; // Matches FastAPI WS endpoint for agents

  useEffect(() => {
    // Establish WebSocket connection
    ws.current = new WebSocket(WS_URL);

    ws.current.onopen = () => {
      console.log('Agent WebSocket connected.');
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // Listen for both customer messages and agent messages (broadcast back to agent dashboard too)
      if (data.type === 'customer_message_analysis') {
        const { original_message, analysis } = data;

        // Add original message to conversation history
        setConversation((prevConv) => [
          ...prevConv,
          { text: original_message, sender: 'customer', timestamp: analysis.timestamp }
        ]);

        // Update latest AI analysis
        setLatestAnalysis(analysis);

        // Update time metrics
        if (!convoStartTime) {
          setConvoStartTime(new Date(analysis.timestamp));
        }
        lastCustomerMessageTimestamp.current = new Date(analysis.timestamp);

      } else if (data.type === 'agent_chat_message') { // NEW: Handle agent messages broadcast from backend
        setConversation((prevConv) => [
          ...prevConv,
          { text: data.text, sender: 'agent', timestamp: data.timestamp }
        ]);
      }
    };

    ws.current.onclose = () => {
      console.log('Agent WebSocket disconnected.');
      // Optional: Implement reconnect logic here
    };

    ws.current.onerror = (error) => {
      console.error('Agent WebSocket error:', error);
    };

    // Cleanup function: Close WebSocket when component unmounts
    return () => {
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [convoStartTime]); // Dependency on convoStartTime ensures WS connects once per conversation start


  // Timer for conversation duration and time since last message
  useEffect(() => {
    const interval = setInterval(() => {
      // Update Conversation Duration
      if (convoStartTime) {
        const durationSeconds = Math.floor((new Date() - convoStartTime) / 1000);
        const hours = String(Math.floor(durationSeconds / 3600)).padStart(2, '0');
        const minutes = String(Math.floor((durationSeconds % 3600) / 60)).padStart(2, '0');
        const seconds = String(durationSeconds % 60).padStart(2, '0');
        setConvoDuration(`${hours}:${minutes}:${seconds}`);
      }

      // Update Time Since Last Customer Message
      if (lastCustomerMessageTimestamp.current) {
        const timeSinceSeconds = Math.floor((new Date() - lastCustomerMessageTimestamp.current) / 1000);
        const hours = String(Math.floor(timeSinceSeconds / 3600)).padStart(2, '0');
        const minutes = String(Math.floor((timeSinceSeconds % 3600) / 60)).padStart(2, '0');
        const seconds = String(timeSinceSeconds % 60).padStart(2, '0');
        setTimeSinceLastCustomerMessage(`${hours}:${minutes}:${seconds}`);
      }
    }, 1000); // Update every second

    return () => clearInterval(interval); // Clean up interval on unmount
  }, [convoStartTime]); // Re-run effect if convoStartTime changes (e.g., new conversation)


  // Function to handle agent sending a message - NOW SENDS TO BACKEND VIA HTTP POST
  const handleAgentSend = async () => {
    if (agentMessage.trim() === '') return;

    try {
      const response = await fetch('http://127.0.0.1:8000/send-agent-message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ message: agentMessage, agent_id: "Agent123" }), // You can make agent_id dynamic
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Agent message sent to backend:', data);
      
      // The message will be broadcast back via WebSocket, so no need to locally add it here.
      // This ensures the conversation history is consistent with what's broadcast.

    } catch (error) {
      console.error('Error sending agent message to backend:', error);
      // Fallback: Add locally if sending fails
      setConversation((prevHistory) => [
        ...prevHistory,
        { text: agentMessage + " (Failed to send!)", sender: 'agent-error', timestamp: new Date().toISOString() }
      ]);
    }
    
    setAgentMessage(''); // Clear the input field after attempting to send
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter') {
      handleAgentSend();
    }
  };

  const renderSentiment = (sentiment) => {
    if (!sentiment) return <span className="sentiment-unknown">N/A</span>;
    const label = String(sentiment.label).toLowerCase(); // Ensure label is string
    let className = 'sentiment-unknown';
    if (label === 'positive') className = 'sentiment-positive';
    else if (label === 'negative') className = 'sentiment-negative';
    else if (label === 'neutral') className = 'sentiment-neutral';
    return <span className={className}>{sentiment.label} ({Math.round(sentiment.score * 100)}%)</span>;
  };

  const renderConfidence = (confidence) => {
    if (confidence === undefined || confidence === null) return <span className="confidence-unknown">N/A</span>;
    const className = confidence < 0.6 ? 'confidence-low' : 'confidence-high'; // Adjusted threshold for LLM's 'estimate'
    return <span className={className}>{Math.round(confidence * 100)}%</span>;
  };

  const copyToClipboard = (text) => {
    if (!navigator.clipboard) {
      alert("Clipboard API not available in this browser/context.");
      return;
    }
    navigator.clipboard.writeText(text)
      .then(() => alert('Copied to clipboard!'))
      .catch((err) => console.error('Failed to copy: ', err));
  };

  return (
    <div className="panel agent-panel">
      <h2>Agent Dashboard</h2>
      <div className="agent-dashboard-content"> {/* Main flex container for agent dashboard content */}
        <div className="agent-chat-column"> {/* Left column: Conversation */}
          <h3>Customer Conversation</h3>
          <div className="chat-box">
            <div className="chat-messages">
              {conversation.length === 0 ? (
                <p>Waiting for customer messages...</p>
              ) : (
                conversation.map((msg, index) => (
                  <div key={index} className={`chat-message ${msg.sender}`}>
                    <p>{msg.text}</p>
                    <small>{new Date(msg.timestamp).toLocaleTimeString()}</small>
                  </div>
                ))
              )}
            </div>
          </div>
          <div className="message-input-area">
            <input
              type="text"
              value={agentMessage}
              onChange={(e) => setAgentMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your reply to customer..."
            />
            <button onClick={handleAgentSend}>Send Reply</button>
          </div>
        </div>

        <div className="ai-suggestions-column"> {/* Right column: AI Suggestions & Metrics */}
          <h3>AI Suggestions (for last customer message)</h3>
          {latestAnalysis ? (
            <>
              <p><strong>Customer's Message:</strong> "{latestAnalysis.user_message}"</p>

              <div className="time-metrics">
                  {convoStartTime && (
                      <p>Conversation Start: <span>{new Date(convoStartTime).toLocaleTimeString()}</span></p>
                  )}
                  <p>Conversation Duration: <span>{convoDuration}</span></p>
                  {/* Highlight warning/critical based on time since last customer message */}
                  <p className={timeSinceLastCustomerMessage > '00:00:30' ? 'warning' : ''}>
                      Time since last customer msg: <span className={timeSinceLastCustomerMessage > '00:01:00' ? 'critical' : ''}>
                          {timeSinceLastCustomerMessage}
                      </span>
                  </p>
              </div>

              <p><strong>Sentiment:</strong> {renderSentiment(latestAnalysis.sentiment)}</p>
              <p>
                <strong>Predicted Intent:</strong> {latestAnalysis.predicted_intent.replace(/_/g, ' ').toUpperCase()} ({renderConfidence(latestAnalysis.intent_confidence)})
              </p>

              <h3>Extracted Entities:</h3>
              {latestAnalysis.detected_entities && latestAnalysis.detected_entities.length > 0 ? (
                <ul>
                  {latestAnalysis.detected_entities.map((entity, index) => (
                    <li key={index}>
                      <strong>{entity.label}:</strong> {entity.text}
                    </li>
                  ))}
                </ul>
              ) : (
                <p>No entities detected.</p>
              )}

              <h3>Knowledge Base Information:</h3>
              <div className="suggestion-card">
                  <ul>
                  {latestAnalysis.suggestions.knowledge_base && latestAnalysis.suggestions.knowledge_base.length > 0 ? (
                      latestAnalysis.suggestions.knowledge_base.map((info, index) => (
                      <li key={index}>{info}</li>
                      ))
                  ) : (
                      <li>No specific knowledge base info found.</li>
                  )}
                  </ul>
              </div>

              <h3>Recommended Response:</h3>
              <div className="suggestion-card">
                  <p>{latestAnalysis.suggestions.pre_written_response}</p>
                  <button onClick={() => copyToClipboard(latestAnalysis.suggestions.pre_written_response)}>
                      Copy Response
                  </button>
              </div>

              <h3>Next Best Actions:</h3>
              <div className="suggestion-card">
                  <ul>
                  {latestAnalysis.suggestions.next_actions && latestAnalysis.suggestions.next_actions.length > 0 ? (
                      latestAnalysis.suggestions.next_actions.map((action, index) => (
                      <li key={index}>{action}</li>
                      ))
                  ) : (
                      <li>No specific next actions defined.</li>
                  )}
                  </ul>
              </div>
            </>
          ) : (
            <p>Waiting for the first customer message to provide AI suggestions...</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentDashboard;