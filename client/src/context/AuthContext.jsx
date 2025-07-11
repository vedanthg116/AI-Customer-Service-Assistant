// client/src/context/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  // We no longer manage user authentication state (token, user, isAuthenticated)
  // directly in this context for the simplified demo.
  // It primarily provides the API_BASE_URL.
  
  const API_BASE_URL = "http://127.0.0.1:8000"; // Your backend URL

  // For the simplified model, user data (like ID and name) will be managed
  // directly within CustomerChat.jsx and AgentDashboard.jsx using local storage.
  // The 'user' object here will just hold a placeholder or be empty.
  const [user, setUser] = useState(null); // Placeholder for user data if needed for display
  const [isAuthenticated, setIsAuthenticated] = useState(false); // Will always be false or managed locally

  // The useEffect for checking token/user on load is no longer relevant
  // as we're removing explicit auth.

  // The login, register, logout functions are also removed.

  const contextValue = {
    API_BASE_URL,
    user, // This will mostly be null or a placeholder for this simplified demo
    isAuthenticated, // This will mostly be false for this simplified demo
    // Removed: login, register, logout functions
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};