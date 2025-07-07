// client/src/App.jsx
import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import CustomerChat from './components/CustomerChat';
import AgentDashboard from './components/AgentDashboard';
import './App.css'; // Import the main CSS

// This component will be displayed when no specific route matches
const NotFound = () => (
  <div style={{ padding: '20px', textAlign: 'center' }}>
    <h2>404 - Page Not Found</h2>
    <p>The page you are looking for does not exist.</p>
    <Link to="/">Go to Home</Link>
  </div>
);

// This is a simple Home component that will guide the user to the demo pages
const Home = () => {
  return (
    <div style={{ padding: '20px', textAlign: 'center' }}>
      <h1>AI Customer Service Assistant Demo</h1>
      <p>Please select a demo view:</p>
      <div style={{ display: 'flex', justifyContent: 'center', gap: '20px', marginTop: '30px' }}>
        <Link to="/customer" style={{ padding: '15px 30px', backgroundColor: '#007bff', color: 'white', textDecoration: 'none', borderRadius: '8px', fontSize: '1.2em' }}>
          Customer View
        </Link>
        <Link to="/agent" style={{ padding: '15px 30px', backgroundColor: '#28a745', color: 'white', textDecoration: 'none', borderRadius: '8px', fontSize: '1.2em' }}>
          Agent View
        </Link>
      </div>
    </div>
  );
};


function App() {
  // Modified: handleCustomerSendMessage now accepts the full chat history
  const handleCustomerSendMessage = async (latestMessage, chatHistory) => {
    try {
      const response = await fetch('http://127.0.0.1:8000/analyze-message', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        // Send both the latest message and the full history
        body: JSON.stringify({ text: latestMessage, chat_history: chatHistory }),
      });
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      console.log('Message sent and analyzed by backend:', data);
    } catch (error) {
      console.error('Error sending message to backend:', error);
    }
  };

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        {/* Pass handleCustomerSendMessage to CustomerChat */}
        <Route path="/customer" element={<CustomerChat onSendMessage={handleCustomerSendMessage} />} />
        <Route path="/agent" element={<AgentDashboard />} />
        <Route path="*" element={<NotFound />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;