// client/src/components/AgentDashboard.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react'; // Import useCallback
import { useAuth } from '../context/AuthContext';
import { v4 as uuidv4 } from 'uuid';

const AgentDashboard = () => {
  const [activeConversations, setActiveConversations] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [selectedConversationMessages, setSelectedConversationMessages] = useState([]);
  const [replyMessage, setReplyMessage] = useState('');
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState(null);

  // Agent identity state
  const [agentId, setAgentId] = useState(null);
  const [agentName, setAgentName] = useState('');
  const [agentNameInput, setAgentNameInput] = useState('');
  const [showAgentNameInput, setShowAgentNameInput] = useState(true);
  const [filter, setFilter] = useState('all');

  const ws = useRef(null);
  const reconnectTimeout = useRef(null);

  // Use environment variables for API and WebSocket URLs
  const API_BASE_URL = import.meta.env.VITE_API_URL;
  const WS_BASE_URL = import.meta.env.VITE_WS_URL;

  // Agent ID and Name from local storage
  useEffect(() => {
    const storedAgentId = localStorage.getItem('agent_id');
    const storedAgentName = localStorage.getItem('agent_name');

    if (storedAgentId && storedAgentName) {
      setAgentId(storedAgentId);
      setAgentName(storedAgentName);
      setShowAgentNameInput(false);
      console.log(`AgentDashboard: Loaded agent: ${storedAgentName} (ID: ${storedAgentId}) from local storage.`);
    } else {
      console.log("AgentDashboard: No agent ID/name found in local storage. Prompting for name.");
      setShowAgentNameInput(true);
    }
  }, []);

  // WebSocket connection logic wrapped in useCallback
  const connectWebSocket = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    if (!agentId) {
      console.log("AgentDashboard: Agent ID not available for WebSocket. Not connecting.");
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
      return;
    }

    // Construct WebSocket URL with agentId as a path parameter
    const currentWsUrl = `${WS_BASE_URL}/ws/agent/${agentId}`;
    if (!ws.current || ws.current.readyState === WebSocket.CLOSED || ws.current.readyState === WebSocket.CLOSING) {
      console.log('AgentDashboard: Attempting to connect Agent WebSocket to:', currentWsUrl);
      ws.current = new WebSocket(currentWsUrl);

      ws.current.onopen = () => {
        console.log('AgentDashboard: Agent WebSocket connected successfully.');
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('AgentDashboard: Received WebSocket data:', data);
          console.log('AgentDashboard: WebSocket data.analysis:', data.analysis);

          if (data.type === 'customer_message_analysis') {
            const convId = data.conversation_id;
            const userId = data.user_id;
            const userName = data.user_name;

            setActiveConversations((prev) => {
              const currentConversations = Array.isArray(prev) ? prev : [];
              const existingConv = currentConversations.find(conv => conv.id === convId);
              if (existingConv) {
                return prev.map(conv =>
                  conv.id === convId
                    ? { ...conv, last_message_summary: data.original_message }
                    : conv
                );
              } else {
                return [...currentConversations, {
                  id: convId,
                  user_id: userId,
                  user_name: userName,
                  start_time: new Date().toISOString(),
                  status: 'open',
                  last_message_summary: data.original_message,
                  assigned_agent_id: null,
                  assigned_agent_name: null
                }];
              }
            });

            if (convId === selectedConversationId) {
              setSelectedConversationMessages((prevMessages) => {
                const currentMessages = Array.isArray(prevMessages) ? prevMessages : [];
                const newMessages = [
                  ...currentMessages,
                  {
                    text: data.original_message,
                    sender: 'customer',
                    timestamp: new Date().toISOString(),
                    image_url: data.image_url,
                    ocr_text: data.ocr_text,
                    analysis: data.analysis
                  }
                ];
                console.log('AgentDashboard: Updating selected conversation messages to:', newMessages);
                return newMessages;
              });
              console.log('AgentDashboard: Setting AI suggestions from WebSocket:', data.analysis?.suggestions);
              setAiSuggestions(data.analysis?.suggestions || null);
            }

          } else if (data.type === 'agent_chat_message') {
              const convId = data.conversation_id;
              if (convId === selectedConversationId) {
                  setSelectedConversationMessages((prevMessages) => {
                    const currentMessages = Array.isArray(prevMessages) ? prevMessages : [];
                    const newMessages = [
                        ...currentMessages,
                        {
                            text: data.text,
                            sender: data.sender,
                            timestamp: data.timestamp,
                        }
                    ];
                    console.log('AgentDashboard: Updating selected conversation messages to:', newMessages);
                    return newMessages;
                  });
              }
          } else if (data.type === 'conversation_assigned') {
              setActiveConversations(prev => prev.map(conv =>
                  conv.id === data.conversation_id
                      ? { ...conv, assigned_agent_id: data.assigned_agent_id, assigned_agent_name: data.assigned_agent_name }
                      : conv
              ));
              console.log(`AgentDashboard: Conversation ${data.conversation_id} assigned to ${data.assigned_agent_name}`);
          } else if (data.type === 'conversation_unassigned') {
              setActiveConversations(prev => prev.map(conv =>
                  conv.id === data.conversation_id
                      ? { ...conv, assigned_agent_id: null, assigned_agent_name: null }
                      : conv
              ));
              console.log(`AgentDashboard: Conversation ${data.conversation_id} unassigned from ${data.unassigned_agent_name}`);
          }

        } catch (error) {
          console.error("AgentDashboard: Error parsing WebSocket message:", error, "Raw data:", event.data);
        }
      };

      ws.current.onclose = (event) => {
        console.log('AgentDashboard: Agent WebSocket disconnected.', event.code, event.reason);
        if (event.code !== 1000 && !reconnectTimeout.current) {
          console.log('AgentDashboard: Attempting to reconnect WebSocket in 3 seconds...');
          reconnectTimeout.current = setTimeout(connectWebSocket, 3000);
        }
      };

      ws.current.onerror = (error) => {
        console.error('AgentDashboard: Agent WebSocket error:', error);
      };
    }
  }, [agentId, WS_BASE_URL, selectedConversationId]); // Added selectedConversationId to dependencies for onmessage updates

  useEffect(() => {
    if (!showAgentNameInput && agentId) {
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
  }, [agentId, WS_BASE_URL, showAgentNameInput, connectWebSocket]); // Added connectWebSocket to dependencies

  const fetchActiveConversations = async () => {
    setLoadingConversations(true);
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/active`);
      if (response.ok) {
        const data = await response.json();
        setActiveConversations(Array.isArray(data) ? data : []);
      } else {
        console.error('AgentDashboard: Failed to fetch active conversations:', response.statusText);
        setActiveConversations([]);
      }
    } catch (error) {
      console.error('AgentDashboard: Error fetching active conversations:', error);
      setActiveConversations([]);
    } finally {
      setLoadingConversations(false);
    }
  };

  useEffect(() => {
    if (!showAgentNameInput && agentId) {
      fetchActiveConversations();
    }
  }, [API_BASE_URL, showAgentNameInput, agentId]);

  const selectConversation = async (conversationId) => {
    setSelectedConversationId(conversationId);
    setLoadingMessages(true);
    setAiSuggestions(null);
    try {
      const response = await fetch(`${API_BASE_URL}/chat-history/conversation/${conversationId}`);
      if (response.ok) {
        const data = await response.json();
        setSelectedConversationMessages(Array.isArray(data) ? data : []);
        const lastCustomerMessageWithAnalysis = data.slice().reverse().find(msg => msg.sender === 'customer' && msg.analysis);
        console.log('AgentDashboard: Found last customer message with analysis:', lastCustomerMessageWithAnalysis);
        if (lastCustomerMessageWithAnalysis) {
          console.log('AgentDashboard: Setting AI suggestions from fetched history:', lastCustomerMessageWithAnalysis.analysis.suggestions);
          setAiSuggestions(lastCustomerMessageWithAnalysis.analysis.suggestions);
        } else {
          console.log('AgentDashboard: No analysis found in fetched history for selected conversation.');
          setAiSuggestions(null);
        }
      } else {
        console.error('AgentDashboard: Failed to fetch conversation history:', response.statusText);
        setSelectedConversationMessages([]);
      }
    } catch (error) {
      console.error('AgentDashboard: Error fetching conversation history:', error);
      setSelectedConversationMessages([]);
    } finally {
      setLoadingMessages(false);
    }
  };

  const handleReplySend = async () => {
    if (replyMessage.trim() === '' || !selectedConversationId) {
      alert("Please type a message and select a conversation.");
      return;
    }
    if (!agentId || !agentName) {
      alert("Agent identity not set. Please refresh and enter your name.");
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/send-agent-message`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: selectedConversationId,
          agent_id: agentId,
          agent_name: agentName,
          message: replyMessage,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('AgentDashboard: Agent message sent:', data);
        setReplyMessage('');

        setSelectedConversationMessages((prevMessages) => {
          const currentMessages = Array.isArray(prevMessages) ? prevMessages : [];
          return [
            ...currentMessages,
            {
                text: replyMessage,
                sender: 'agent',
                timestamp: new Date().toISOString(),
            }
          ];
        });

      } else {
        const errorData = await response.json();
        console.error('AgentDashboard: Failed to send agent message:', errorData.detail);
        alert(`Failed to send message: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('AgentDashboard: Network error sending agent message:', error);
      alert("Network error or server unreachable.");
    }
  };

  const handleAgentNameSubmit = () => {
    if (agentNameInput.trim() === '') {
      alert("Please enter your name to access the dashboard.");
      return;
    }
    const newAgentId = uuidv4();
    localStorage.setItem('agent_id', newAgentId);
    localStorage.setItem('agent_name', agentNameInput.trim());
    setAgentId(newAgentId);
    setAgentName(agentNameInput.trim());
    setShowAgentNameInput(false);
    setLoadingConversations(true);
  };

  // Function to handle switching agents
  const handleSwitchAgent = () => {
    console.log("AgentDashboard: Switching agent...");
    // Clear local storage for current agent
    localStorage.removeItem('agent_id');
    localStorage.removeItem('agent_name');

    // Reset component state to show name input form
    setAgentId(null);
    setAgentName('');
    setAgentNameInput('');
    setShowAgentNameInput(true);

    // Clear all conversation and chat states for a clean slate
    setActiveConversations([]);
    setSelectedConversationId(null);
    setSelectedConversationMessages([]);
    setReplyMessage('');
    setAiSuggestions(null);
    setLoadingConversations(false); // So the name input shows immediately
    setLoadingMessages(false);

    // Close existing WebSocket connection if open
    if (ws.current && ws.current.readyState === WebSocket.OPEN) {
      ws.current.close();
      ws.current = null;
    }
    // Clear any pending reconnect timeouts
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
  };

  const handleClaimConversation = async (convId) => {
    if (!agentId || !agentName) {
      alert("Agent identity not set. Please refresh and enter your name.");
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/assign-conversation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: convId,
          agent_id: agentId,
          agent_name: agentName
        })
      });
      if (!response.ok) {
        const errorData = await response.json();
        alert(`Failed to claim conversation: ${errorData.detail}`);
        console.error('Failed to claim conversation:', errorData);
      } else {
        console.log(`Conversation ${convId} claimed successfully.`);
      }
    } catch (error) {
      console.error('Network error claiming conversation:', error);
      alert("Network error or server unreachable.");
    }
  };

  const handleReleaseConversation = async (convId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/unassign-conversation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          conversation_id: convId
        })
      });
      if (!response.ok) {
        const errorData = await response.json();
        alert(`Failed to release conversation: ${errorData.detail}`);
        console.error('Failed to release conversation:', errorData);
      } else {
        console.log(`Conversation ${convId} released successfully.`);
      }
    } catch (error) {
      console.error('Network error releasing conversation:', error);
      alert("Network error or server unreachable.");
    }
  };

  const filteredConversations = activeConversations.filter(conv => {
    if (filter === 'unassigned') {
      return !conv.assigned_agent_id;
    } else if (filter === 'my_assigned') {
      return conv.assigned_agent_id === agentId;
    }
    return true;
  });

  if (showAgentNameInput) {
    return (
      <div className="panel agent-panel" style={{ textAlign: 'center', padding: '50px' }}>
        <h2>Agent Dashboard Access</h2>
        <p>Please enter your name to access the dashboard:</p>
        <input
          type="text"
          value={agentNameInput}
          onChange={(e) => setAgentNameInput(e.target.value)}
          placeholder="Your Agent Name"
          style={{ padding: '10px', fontSize: '1em', width: '80%', maxWidth: '300px', marginBottom: '15px' }}
          onKeyPress={(e) => e.key === 'Enter' && handleAgentNameSubmit()}
        />
        <button onClick={handleAgentNameSubmit} style={{ padding: '10px 20px', fontSize: '1em' }}>Enter Dashboard</button>
      </div>
    );
  }

  if (loadingConversations) {
    return <div style={{ textAlign: 'center', padding: '50px' }}>Loading conversations...</div>;
  }

  return (
    <div className="panel agent-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Agent Dashboard ({agentName})</h2>
        <button onClick={handleSwitchAgent} className="home-button logout-button">Switch Agent</button>
      </div>
      <div className="agent-content">
        <div className="conversation-list">
          <h3>Active Conversations</h3>
          <div className="filter-buttons">
            <button onClick={() => setFilter('all')} className={filter === 'all' ? 'active' : ''}>All</button>
            <button onClick={() => setFilter('unassigned')} className={filter === 'unassigned' ? 'active' : ''}>Unassigned</button>
            <button onClick={() => setFilter('my_assigned')} className={filter === 'my_assigned' ? 'active' : ''}>My Assigned</button>
          </div>
          {filteredConversations.length === 0 ? (
            <p>No active conversations matching filter.</p>
          ) : (
            <ul>
              {filteredConversations.map((conv) => (
                <li
                  key={conv.id}
                  className={conv.id === selectedConversationId ? 'selected' : ''}
                  onClick={() => selectConversation(conv.id)}
                >
                  <strong>Customer: {conv.user_name || conv.user_id.substring(0, 8)}...</strong>
                  {conv.assigned_agent_name && (
                    <span className="assigned-agent-tag">
                      {conv.assigned_agent_id === agentId ? ` (Assigned to YOU)` : ` (Assigned to ${conv.assigned_agent_name})`}
                    </span>
                  )}
                  <p className="last-message-summary">{conv.last_message_summary}</p>
                  <div className="conversation-actions">
                    {!conv.assigned_agent_id ? (
                      <button onClick={(e) => { e.stopPropagation(); handleClaimConversation(conv.id); }} className="claim-button">Claim</button>
                    ) : (
                      conv.assigned_agent_id === agentId && (
                        <button onClick={(e) => { e.stopPropagation(); handleReleaseConversation(conv.id); }} className="release-button">Release</button>
                      )
                    )}
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="chat-view">
          {selectedConversationId ? (
            <>
              <h3>Conversation ID: {selectedConversationId.substring(0, 8)}...</h3>
              <div className="chat-box">
                <div className="chat-messages">
                  {loadingMessages ? (
                    <p>Loading messages...</p>
                  ) : (
                    Array.isArray(selectedConversationMessages) && selectedConversationMessages.length === 0 ? (
                      <p className="no-messages-placeholder">No messages in this conversation yet.</p>
                    ) : (
                      Array.isArray(selectedConversationMessages) && selectedConversationMessages.map((msg, index) => (
                        <div key={index} className={`chat-message ${msg.sender}`}>
                          {msg.image_url && (
                            <img src={msg.image_url} alt="Customer Upload" style={{ maxWidth: '100%', borderRadius: '8px', marginBottom: '8px' }} />
                          )}
                          <p>{msg.text}</p>
                          {msg.ocr_text && (
                             <small style={{ color: '#888' }}>OCR: "{msg.ocr_text.substring(0, Math.min(msg.ocr_text.length, 50))}..."</small>
                          )}
                          {msg.analysis && (
                            <div className="message-analysis">
                              <strong>Intent:</strong> {msg.analysis.predicted_intent} ({msg.analysis.intent_confidence.toFixed(2)})<br/>
                              <strong>Sentiment:</strong> {msg.analysis.sentiment.label} ({msg.analysis.sentiment.score.toFixed(2)})<br/>
                              {msg.analysis.detected_entities && msg.analysis.detected_entities.length > 0 && (
                                <>
                                  <strong>Entities:</strong>
                                  <ul>
                                    {msg.analysis.detected_entities.map((entity, entIdx) => (
                                      <li key={entIdx}>{entity.label}: {entity.text}</li>
                                    ))}
                                  </ul>
                                </>
                              )}
                              {msg.analysis.suggestions?.pre_written_response && (
                                  <small>Suggestion: "{msg.analysis.suggestions.pre_written_response}"</small>
                              )}
                            </div>
                          )}
                          <small>{new Date(msg.timestamp).toLocaleTimeString()}</small>
                        </div>
                      ))
                    )
                  )}
                </div>
              </div>
              <div className="message-input-area">
                <input
                  type="text"
                  value={replyMessage}
                  onChange={(e) => setReplyMessage(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && handleReplySend()}
                  placeholder="Type your reply..."
                />
                <button onClick={handleReplySend} disabled={replyMessage.trim() === ''}>Send Reply</button>
              </div>
            </>
          ) : (
            <p className="select-conversation-placeholder">Select a conversation to view messages.</p>
          )}
        </div>

        <div className="ai-suggestions-column">
          <h3>AI Suggestions</h3>
          {aiSuggestions ? (
            <div className="suggestion-card">
              <h4>Pre-written Response:</h4>
              <p>{aiSuggestions.pre_written_response || 'N/A'}</p>
              
              <h4>Knowledge Base:</h4>
              {aiSuggestions.knowledge_base && aiSuggestions.knowledge_base.length > 0 ? (
                <ul>
                  {aiSuggestions.knowledge_base.map((kb, index) => (
                    <li key={index}>{kb}</li>
                  ))}
                </ul>
              ) : (
                <p>No specific knowledge base suggestions.</p>
              )}

              <h4>Next Actions:</h4>
              {aiSuggestions.next_actions && aiSuggestions.next_actions.length > 0 ? (
                <ul>
                  {aiSuggestions.next_actions.map((action, index) => (
                    <li key={index}>{action}</li>
                  ))}
                </ul>
              ) : (
                <p>No suggested next actions.</p>
              )}
            </div>
          ) : (
            <p>AI suggestions will appear here after a customer message is analyzed for the selected conversation.</p>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentDashboard;