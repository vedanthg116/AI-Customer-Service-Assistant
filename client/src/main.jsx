// client/src/main.jsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import CustomerChat from './components/CustomerChat';
import AgentDashboard from './components/AgentDashboard';
import { AuthProvider } from './context/AuthContext'; // Import AuthProvider
import './index.css'; // Import global styles

const Home = () => (
  <div className="home-container">
    <h1>Welcome to AI Customer Service Assistant</h1>
    <p>Choose your role to begin:</p>
    <div className="home-buttons">
      <Link to="/customer" className="home-button">Start Customer Chat</Link>
      <Link to="/agent" className="home-button">Go to Agent Dashboard</Link>
    </div>
  </div>
);

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AuthProvider> {/* Wrap the entire application with AuthProvider */}
      <Router>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/customer" element={<CustomerChat />} />
          <Route path="/agent" element={<AgentDashboard />} />
          {/* Add a catch-all route for 404 if needed */}
          <Route path="*" element={<div>404 Not Found</div>} />
        </Routes>
      </Router>
    </AuthProvider>
  </React.StrictMode>,
);

