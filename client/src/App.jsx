// client/src/App.jsx
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import CustomerChat from './components/CustomerChat';
import AgentDashboard from './components/AgentDashboard';
import { AuthProvider, useAuth } from './context/AuthContext'; // Keep AuthProvider for API_BASE_URL

import './App.css'; // Ensure App.css is imported for styling

// Home component (simplified, no login/register links)
const Home = () => {
  return (
    <div className="auth-container"> {/* Re-using auth-container for centering */}
      <div className="auth-card" style={{ textAlign: 'center' }}>
        <h2>Welcome to the Chat Support Demo</h2>
        <p>Choose your role to begin:</p>
        <div style={{ marginTop: '20px' }}>
          <Link to="/customer" className="home-button customer-button">
            Start Customer Chat
          </Link>
          <Link to="/agent" className="home-button agent-button">
            Go to Agent Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
};

// Main App component
function App() {
  return (
    <AuthProvider> {/* AuthProvider is still needed for API_BASE_URL */}
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/customer" element={<CustomerChat />} />
          <Route path="/agent" element={<AgentDashboard />} />
          {/* Removed: /login, /register routes */}
        </Routes>
      </Router>
    </AuthProvider>
  );
}

export default App;