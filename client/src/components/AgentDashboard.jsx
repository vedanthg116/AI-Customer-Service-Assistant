// client/src/components/AgentDashboard.jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid'; // Import uuidv4 for generating unique IDs

const AgentDashboard = () => {
  const [activeConversations, setActiveConversations] = useState([]);
  const [selectedConversationId, setSelectedConversationId] = useState(null);
  const [selectedConversationMessages, setSelectedConversationMessages] = useState([]);
  const [replyMessage, setReplyMessage] = useState('');
  const [loadingConversations, setLoadingConversations] = useState(true);
  const [loadingMessages, setLoadingMessages] = useState(false);
  const [aiSuggestions, setAiSuggestions] = useState(null); // This holds the full analysis object for the selected message
  const [copyStatus, setCopyStatus] = useState(''); // State for copy button feedback

  // Agent identity state
  const [agentId, setAgentId] = useState(null);
  const [agentName, setAgentName] = useState('');
  const [agentNameInput, setAgentNameInput] = useState('');
  const [showAgentNameInput, setShowAgentNameInput] = useState(true);
  const [filter, setFilter] = useState('all'); // 'all', 'unassigned', 'my_assigned'

  // Ticket Management States
  const [showRaiseTicketModal, setShowRaiseTicketModal] = useState(false);
  const [ticketIssueDescription, setTicketIssueDescription] = useState('');
  const [ticketPriority, setTicketPriority] = useState('Medium');
  const [conversationTickets, setConversationTickets] = useState([]); // To store tickets for the selected conversation

  // NEW: Customer Overview State
  const [showCustomerOverview, setShowCustomerOverview] = useState(false); // Toggle between chat and overview
  const [customerOverviewData, setCustomerOverviewData] = useState([]);
  const [loadingCustomerOverview, setLoadingCustomerOverview] = useState(false);


  const ws = useRef(null);
  const reconnectTimeout = useRef(null);
  const chatBoxRef = useRef(null); // Ref for auto-scrolling chat

  // Use environment variables for API and WebSocket URLs
  const API_BASE_URL = import.meta.env.VITE_API_URL;
  const WS_BASE_URL = import.meta.env.VITE_WS_URL;

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (chatBoxRef.current) {
      chatBoxRef.current.scrollTop = chatBoxRef.current.scrollHeight;
    }
  }, [selectedConversationMessages]);


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
    // Clear any existing reconnect attempts
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }

    if (!agentId) {
      console.log("AgentDashboard: Agent ID not available for WebSocket. Not connecting.");
      // Ensure any existing WebSocket is closed if agentId becomes null
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
          console.log('AgentDashboard: WebSocket data.type:', data.type); // NEW LOG
          console.log('AgentDashboard: WebSocket data.analysis (full object):', data.analysis); // NEW LOG

          if (data.type === 'customer_message_analysis') {
            const convId = data.conversation_id;
            const userId = data.user_id;
            const userName = data.user_name;

            // Update the list of active conversations
            setActiveConversations((prev) => {
              const currentConversations = Array.isArray(prev) ? prev : [];
              const existingConv = currentConversations.find(conv => conv.id === convId);
              if (existingConv) {
                // Update existing conversation with latest message summary
                return prev.map(conv =>
                  conv.id === convId
                    ? { ...conv, last_message_summary: data.original_message }
                    : conv
                );
              } else {
                // Add new conversation to the list
                return [...currentConversations, {
                  id: convId,
                  user_id: userId,
                  user_name: userName,
                  start_time: new Date().toISOString(),
                  status: 'open',
                  last_message_summary: data.original_message,
                  assigned_agent_id: null, // Initially unassigned
                  assigned_agent_name: null // Initially unassigned
                }];
              }
            });

            // If the message is for the currently selected conversation, update its messages and AI suggestions
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
                    analysis: data.analysis // <--- This is where the full analysis object is stored
                  }
                ];
                console.log('AgentDashboard: Updating selected conversation messages to:', newMessages);
                return newMessages;
              });
              // CRITICAL: Set AI suggestions directly from the incoming message's analysis
              console.log('AgentDashboard: Setting AI suggestions from WebSocket (data.analysis):', data.analysis); // NEW LOG
              setAiSuggestions(data.analysis || null); // Set the entire analysis object
            }

          } else if (data.type === 'agent_chat_message') {
              const convId = data.conversation_id;
              const incomingAgentId = data.agent_id; // Get the ID of the agent who sent the message

              // NEW LOGIC: Prevent re-rendering if this message originated from the current agent
              if (incomingAgentId === agentId) {
                  console.log(`AgentDashboard: Ignoring own agent message received via WS broadcast (Agent ID: ${incomingAgentId}).`);
                  return; // Exit early, as we've already optimistically rendered this message
              }

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
          } else if (data.type === 'conversation_assigned') { // Handle assignment broadcast
              setActiveConversations(prev => prev.map(conv =>
                  conv.id === data.conversation_id
                      ? { ...conv, assigned_agent_id: data.assigned_agent_id, assigned_agent_name: data.assigned_agent_name }
                      : conv
              ));
              console.log(`AgentDashboard: Conversation ${data.conversation_id} assigned to ${data.assigned_agent_name}`);
          } else if (data.type === 'conversation_unassigned') { // Handle unassignment broadcast
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
        // Attempt to reconnect after a delay if not a clean close (e.g., 1000 for normal closure)
        if (event.code !== 1000 && !reconnectTimeout.current) {
          console.log('AgentDashboard: Attempting to reconnect WebSocket in 3 seconds...');
          reconnectTimeout.current = setTimeout(connectWebSocket, 3000);
        }
      };

      ws.current.onerror = (error) => {
        console.error('AgentDashboard: Agent WebSocket error:', error);
        // Error often precedes close, so reconnection logic is primarily in onclose
      };
    }
  }, [agentId, WS_BASE_URL, selectedConversationId]); // Dependencies for WebSocket effect

  // Effect to manage WebSocket connection lifecycle
  useEffect(() => {
    if (!showAgentNameInput && agentId) { // Only connect if agentId is set and name input is hidden
      connectWebSocket();
    }

    // Cleanup function: close WebSocket and clear timeout when component unmounts or dependencies change
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

  // Fetch active conversations when component mounts or agentId changes
  const fetchActiveConversations = async () => {
    setLoadingConversations(true);
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/active`);
      if (response.ok) {
        const data = await response.json();
        // The backend now sends user_name directly, no need for extra fetch
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
    if (!showAgentNameInput && agentId) { // Fetch conversations only if agent is identified
      fetchActiveConversations();
    }
  }, [API_BASE_URL, showAgentNameInput, agentId]);

  // Function to fetch tickets for the selected conversation
  const fetchConversationTickets = async (convId) => {
    if (!convId) {
      setConversationTickets([]);
      return;
    }
    try {
      const response = await fetch(`${API_BASE_URL}/conversations/${convId}/tickets`);
      if (response.ok) {
        const data = await response.json();
        setConversationTickets(Array.isArray(data) ? data : []);
        console.log(`AgentDashboard: Fetched ${data.length} tickets for conversation ${convId}.`);
      } else {
        console.error('AgentDashboard: Failed to fetch conversation tickets:', response.statusText);
        setConversationTickets([]);
      }
    } catch (error) {
      console.error('AgentDashboard: Error fetching conversation tickets:', error);
      setConversationTickets([]);
    }
  };


  // Handle selecting a conversation from the list
  const selectConversation = async (conversationId) => {
    setSelectedConversationId(conversationId);
    setLoadingMessages(true);
    setAiSuggestions(null); // Clear previous suggestions when new conversation is selected
    setConversationTickets([]); // Clear tickets when new conversation is selected

    try {
      const response = await fetch(`${API_BASE_URL}/chat-history/conversation/${conversationId}`);
      if (response.ok) {
        const data = await response.json(); // This 'data' is the array of messages for the conversation
        setSelectedConversationMessages(Array.isArray(data) ? data : []);
        
        // After loading history, find the last customer message that has 'analysis' data
        // We reverse to find the most recent customer message with analysis efficiently
        const lastCustomerMessageWithAnalysis = data.slice().reverse().find(msg => msg.sender === 'customer' && msg.analysis);
        
        console.log('AgentDashboard: Found last customer message with analysis from history:', lastCustomerMessageWithAnalysis); // NEW LOG
        
        if (lastCustomerMessageWithAnalysis) {
          // CRITICAL: Set AI suggestions from the analysis found in the fetched history
          console.log('AgentDashboard: Setting AI suggestions from fetched history (lastCustomerMessageWithAnalysis.analysis):', lastCustomerMessageWithAnalysis.analysis); // NEW LOG
          setAiSuggestions(lastCustomerMessageWithAnalysis.analysis); // Set the entire analysis object
        } else {
          console.log('AgentDashboard: No analysis found in fetched history for selected conversation.');
          setAiSuggestions(null);
        }
        
        // Fetch tickets for the newly selected conversation
        fetchConversationTickets(conversationId);

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

  // Handle sending a reply from the agent
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
          agent_id: agentId, // Send agentId
          agent_name: agentName, // Send agentName
          message: replyMessage,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('AgentDashboard: Agent message sent:', data);
        setReplyMessage('');

        // Optimistically update the agent's own chat view
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
      console.error('AgentDashboard: Network error sending message:', error);
      alert("Network error or server unreachable.");
    }
  };

  // Handle agent name submission (when first entering dashboard or switching)
  const handleAgentNameSubmit = () => {
    if (agentNameInput.trim() === '') {
      alert("Please enter your name to access the dashboard.");
      return;
    }
    const newAgentId = uuidv4(); // Generate a new UUID for the agent
    localStorage.setItem('agent_id', newAgentId);
    localStorage.setItem('agent_name', agentNameInput.trim());
    setAgentId(newAgentId);
    setAgentName(agentNameInput.trim());
    setShowAgentNameInput(false);
    setLoadingConversations(true); // Re-trigger conversation load and WS connection
  };

  // Function to handle switching agents (clears local storage and resets state)
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
    setAiSuggestions(null); // Clear AI suggestions
    setConversationTickets([]); // Clear tickets
    setLoadingConversations(false); // So the name input shows immediately
    setLoadingMessages(false);
    setShowCustomerOverview(false); // Hide overview if switching agent

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

  // Handle claiming a conversation
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
        // UI update will happen via WebSocket broadcast from backend
      }
    } catch (error) {
      console.error('Network error claiming conversation:', error);
      alert("Network error or server unreachable.");
    }
  };

  // Handle releasing a conversation
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
        // UI update will happen via WebSocket broadcast from backend
      }
    } catch (error) {
      console.error('Network error releasing conversation:', error);
      alert("Network error or server unreachable.");
    }
  };

  // Filter conversations based on selected filter (All, Unassigned, My Assigned)
  const filteredConversations = activeConversations.filter(conv => {
    if (filter === 'unassigned') {
      return !conv.assigned_agent_id;
    } else if (filter === 'my_assigned') {
      return conv.assigned_agent_id === agentId;
    }
    return true; // 'all' filter
  });

  // Function to send the pre-written response
  const handleSendPrewrittenResponse = async () => {
    if (aiSuggestions?.suggestions?.pre_written_response && selectedConversationId) {
      setReplyMessage(aiSuggestions.suggestions.pre_written_response);
      // Automatically send after setting the message
      setTimeout(() => {
        handleReplySend();
      }, 50); // Small delay to allow state update to render
    } else {
      alert("No pre-written response available to send.");
    }
  };

  // Function to copy the pre-written response to clipboard
  const handleCopyPrewrittenResponse = () => {
    const responseText = aiSuggestions?.suggestions?.pre_written_response;
    if (responseText) {
      // document.execCommand('copy') is used for clipboard operations in iframes
      const textarea = document.createElement('textarea');
      textarea.value = responseText;
      document.body.appendChild(textarea);
      textarea.select();
      try {
        document.execCommand('copy');
        setCopyStatus('Copied!');
        setTimeout(() => setCopyStatus(''), 2000); // Clear status after 2 seconds
      } catch (err) {
        console.error('Failed to copy text: ', err);
        setCopyStatus('Failed to copy.');
        setTimeout(() => setCopyStatus(''), 2000);
      } finally {
        document.body.removeChild(textarea);
      }
    } else {
      setCopyStatus('No text to copy.');
      setTimeout(() => setCopyStatus(''), 2000);
    }
  };

  // Handle raising a new ticket
  const handleRaiseTicket = async () => {
    if (!selectedConversationId || !agentId || !agentName) {
      alert("Please select a conversation and ensure agent identity is set.");
      return;
    }
    setShowRaiseTicketModal(true); // Show the modal
  };

  // Handle submitting the new ticket form
  const handleSubmitTicket = async () => {
    if (ticketIssueDescription.trim() === '') {
      alert("Please provide an issue description for the ticket.");
      return;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/tickets/raise`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          conversation_id: selectedConversationId,
          raised_by_agent_id: agentId,
          raised_by_agent_name: agentName,
          issue_description: ticketIssueDescription,
          priority: ticketPriority,
        }),
      });

      if (response.ok) {
        const newTicket = await response.json();
        console.log('AgentDashboard: Ticket raised successfully:', newTicket);
        alert('Ticket raised successfully!');
        setTicketIssueDescription(''); // Clear form
        setTicketPriority('Medium'); // Reset priority
        setShowRaiseTicketModal(false); // Close modal
        fetchConversationTickets(selectedConversationId); // Refresh tickets for this conversation
      } else {
        const errorData = await response.json();
        console.error('AgentDashboard: Failed to raise ticket:', errorData.detail);
        alert(`Failed to raise ticket: ${errorData.detail}`);
      }
    } catch (error) {
      console.error('AgentDashboard: Network error raising ticket:', error);
      alert("Network error or server unreachable while raising ticket.");
    }
  };

  // NEW: Fetch Customer Overview Data
  const fetchCustomerOverview = async () => {
    setLoadingCustomerOverview(true);
    try {
      const response = await fetch(`${API_BASE_URL}/customer-overview`);
      if (response.ok) {
        const data = await response.json();
        setCustomerOverviewData(Array.isArray(data) ? data : []);
        console.log(`AgentDashboard: Fetched customer overview data:`, data);
      } else {
        console.error('AgentDashboard: Failed to fetch customer overview:', response.statusText);
        setCustomerOverviewData([]);
      }
    } catch (error) {
      console.error('AgentDashboard: Error fetching customer overview:', error);
      setCustomerOverviewData([]);
    } finally {
      setLoadingCustomerOverview(false);
    }
  };

  // Handle toggling between chat and customer overview
  const toggleCustomerOverview = () => {
    if (!showCustomerOverview) {
      fetchCustomerOverview(); // Fetch data when switching to overview
    }
    setShowCustomerOverview(prev => !prev);
    // When switching to overview, unselect conversation and clear chat/suggestions
    setSelectedConversationId(null);
    setSelectedConversationMessages([]);
    setAiSuggestions(null);
    setConversationTickets([]);
  };


  // Render agent name input form if needed
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

  // Display loading state for conversations
  if (loadingConversations) {
    return <div style={{ textAlign: 'center', padding: '50px' }}>Loading conversations...</div>;
  }

  // Main Agent Dashboard UI
  return (
    <div className="panel agent-panel">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <h2>Agent Dashboard ({agentName})</h2> {/* Display agent's name */}
        <div>
          <button onClick={toggleCustomerOverview} className="home-button" style={{ marginRight: '10px' }}>
            {showCustomerOverview ? 'Back to Chat' : 'Customer Overview'}
          </button>
          <button onClick={handleSwitchAgent} className="home-button logout-button">Switch Agent</button>
        </div>
      </div>
      <div className="agent-content">
        {showCustomerOverview ? (
          // NEW: Customer Overview Table View
          <div className="customer-overview-table" style={{ width: '100%', overflowX: 'auto' }}>
            <h3>All Customers Overview</h3>
            {loadingCustomerOverview ? (
              <p>Loading customer data...</p>
            ) : customerOverviewData.length === 0 ? (
              <p>No customer data available.</p>
            ) : (
              <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '15px' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f2f2f2' }}>
                    <th style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>Customer Name</th>
                    <th style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>Latest Conversation</th>
                    <th style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>Status</th>
                    <th style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>Assigned Agent</th>
                    <th style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>Open Tickets</th>
                    <th style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>Latest Ticket Issue</th>
                    <th style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'left' }}>Latest Ticket Status</th>
                  </tr>
                </thead>
                <tbody>
                  {customerOverviewData.map((customer) => (
                    <tr key={customer.user_id} style={{ borderBottom: '1px solid #eee' }}>
                      <td style={{ padding: '8px', border: '1px solid #ddd' }}>{customer.user_name}</td>
                      <td style={{ padding: '8px', border: '1px solid #ddd' }}>
                        {customer.latest_message_summary ? (
                          <>
                            "{customer.latest_message_summary.substring(0, Math.min(customer.latest_message_summary.length, 50))}..."
                            <br/>
                            <small>({new Date(customer.latest_conversation_start_time).toLocaleString()})</small>
                          </>
                        ) : 'N/A'}
                      </td>
                      <td style={{ padding: '8px', border: '1px solid #ddd' }}>{customer.latest_conversation_status || 'N/A'}</td>
                      <td style={{ padding: '8px', border: '1px solid #ddd' }}>{customer.assigned_agent_name || 'Unassigned'}</td>
                      <td style={{ padding: '8px', border: '1px solid #ddd' }}>{customer.open_tickets_count}</td>
                      <td style={{ padding: '8px', border: '1px solid #ddd' }}>
                        {customer.latest_ticket_issue ? (
                          `${customer.latest_ticket_issue.substring(0, Math.min(customer.latest_ticket_issue.length, 50))}...`
                        ) : 'N/A'}
                      </td>
                      <td style={{ padding: '8px', border: '1px solid #ddd' }}>{customer.latest_ticket_status || 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        ) : (
          // Existing Chat and Conversation List View
          <>
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
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                    <h3>Conversation ID: {selectedConversationId.substring(0, 8)}...</h3>
                    <button onClick={handleRaiseTicket} className="raise-ticket-button" disabled={!selectedConversationId}>Raise Ticket</button>
                  </div>

                  {/* Ticket Display Section */}
                  {conversationTickets.length > 0 && (
                    <div className="tickets-display" style={{ marginBottom: '15px', padding: '10px', border: '1px solid #ccc', borderRadius: '8px', backgroundColor: '#f9f9f9' }}>
                      <h4>Associated Tickets:</h4>
                      <ul style={{ listStyle: 'none', padding: 0 }}>
                        {conversationTickets.map(ticket => (
                          <li key={ticket.id} style={{ marginBottom: '5px', paddingBottom: '5px', borderBottom: '1px dotted #eee' }}>
                            <strong>Ticket ID:</strong> {ticket.id.substring(0, 8)}...<br/>
                            <strong>Issue:</strong> {ticket.issue_description}<br/>
                            <strong>Status:</strong> <span style={{ fontWeight: 'bold', color: ticket.status === 'Open' ? 'orange' : ticket.status === 'Closed' ? 'green' : 'blue' }}>{ticket.status}</span>, <strong>Priority:</strong> {ticket.priority}<br/>
                            <small>Raised by {ticket.raised_by_agent_name} on {new Date(ticket.created_at).toLocaleString()}</small>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  <div className="chat-box" ref={chatBoxRef}> {/* Add ref here */}
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
                  <h4>Predicted Intent:</h4>
                  <p>{aiSuggestions.predicted_intent || 'N/A'} ({aiSuggestions.intent_confidence?.toFixed(2) || 'N/A'})</p>
                  
                  <h4>Sentiment:</h4>
                  <p>{aiSuggestions.sentiment?.label || 'N/A'} ({aiSuggestions.sentiment?.score?.toFixed(2) || 'N/A'})</p>

                  {aiSuggestions.detected_entities && aiSuggestions.detected_entities.length > 0 && (
                    <>
                      <h4>Detected Entities:</h4>
                      <ul>
                        {aiSuggestions.detected_entities.map((entity, entIdx) => (
                          <li key={entIdx}><strong>{entity.label}:</strong> {entity.text}</li>
                        ))}
                      </ul>
                    </>
                  )}

                  <h4>Pre-written Response:</h4>
                  <p>{aiSuggestions.suggestions?.pre_written_response || 'N/A'}</p>
                  {aiSuggestions.suggestions?.pre_written_response && (
                    <div style={{ display: 'flex', gap: '8px', marginTop: '10px' }}>
                      <button onClick={handleSendPrewrittenResponse} className="send-suggestion-button">Send</button>
                      <button onClick={handleCopyPrewrittenResponse} className="copy-suggestion-button">Copy</button>
                      {copyStatus && <span style={{ marginLeft: '10px', color: copyStatus.includes('Failed') ? 'red' : 'green' }}>{copyStatus}</span>}
                    </div>
                  )}
                  
                  <h4>Knowledge Base:</h4>
                  {aiSuggestions.suggestions?.knowledge_base && aiSuggestions.suggestions.knowledge_base.length > 0 ? (
                    <ul>
                      {aiSuggestions.suggestions.knowledge_base.map((kb, index) => (
                        <li key={index}>{kb}</li>
                      ))}
                    </ul>
                  ) : (
                    <p>No specific knowledge base suggestions.</p>
                  )}

                  <h4>Next Actions:</h4>
                  {aiSuggestions.suggestions?.next_actions && aiSuggestions.suggestions.next_actions.length > 0 ? (
                    <ul>
                      {aiSuggestions.suggestions.next_actions.map((action, index) => (
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
          </>
        )}
      </div>

      {/* Raise Ticket Modal */}
      {showRaiseTicketModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h3>Raise New Ticket for Conversation {selectedConversationId?.substring(0, 8)}...</h3>
            <div className="modal-body">
              <label>
                Issue Description:
                <textarea
                  value={ticketIssueDescription}
                  onChange={(e) => setTicketIssueDescription(e.target.value)}
                  placeholder="Describe the issue for the ticket..."
                  rows="4"
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
                />
              </label>
              <label style={{ marginTop: '10px', display: 'block' }}>
                Priority:
                <select
                  value={ticketPriority}
                  onChange={(e) => setTicketPriority(e.target.value)}
                  style={{ width: '100%', padding: '8px', borderRadius: '4px', border: '1px solid #ccc' }}
                >
                  <option value="Low">Low</option>
                  <option value="Medium">Medium</option>
                  <option value="High">High</option>
                  <option value="Urgent">Urgent</option>
                </select>
              </label>
            </div>
            <div className="modal-footer" style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
              <button onClick={() => setShowRaiseTicketModal(false)} className="cancel-button">Cancel</button>
              <button onClick={handleSubmitTicket} className="submit-button">Submit Ticket</button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default AgentDashboard;