// client/src/context/AuthContext.jsx
import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';

// Create the Auth Context
const AuthContext = createContext(null);

// Create a custom hook to use the Auth Context
export const useAuth = () => {
  return useContext(AuthContext);
};

// Auth Provider Component
export const AuthProvider = ({ children }) => {
  const [userId, setUserId] = useState(null);
  const [userName, setUserName] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false); // Simple authentication state
  const [isLoadingAuth, setIsLoadingAuth] = useState(true); // New state to indicate auth loading

  useEffect(() => {
    // Attempt to load user from localStorage
    let storedUserId = localStorage.getItem('customer_user_id');
    let storedUserName = localStorage.getItem('customer_user_name');

    if (storedUserId && storedUserName) {
      setUserId(storedUserId);
      setUserName(storedUserName);
      setIsAuthenticated(true);
      console.log(`AuthContext: Loaded existing customer: ${storedUserName} (ID: ${storedUserId})`);
    } else {
      console.log("AuthContext: No customer ID/name found in local storage. Awaiting user input.");
      // Do NOT auto-generate here. Wait for user input.
    }
    setIsLoadingAuth(false); // Auth loading is complete
  }, []);

  // New function to set customer identity from an external component
  const setCustomerIdentity = useCallback((name, existingUserId = null) => {
    const newUserId = existingUserId || uuidv4();
    const newUserName = name.trim();
    
    localStorage.setItem('customer_user_id', newUserId);
    localStorage.setItem('customer_user_name', newUserName);
    
    setUserId(newUserId);
    setUserName(newUserName);
    setIsAuthenticated(true);
    console.log(`AuthContext: Set customer: ${newUserName} (ID: ${newUserId})${existingUserId ? ' - existing customer' : ' - new customer'}`);
  }, []);

  // New function to clear customer identity
  const clearCustomerIdentity = useCallback(() => {
    localStorage.removeItem('customer_user_id');
    localStorage.removeItem('customer_user_name');
    setUserId(null);
    setUserName(null);
    setIsAuthenticated(false);
    console.log("AuthContext: Cleared customer identity.");
  }, []);


  const value = {
    userId,
    userName,
    isAuthenticated,
    isLoadingAuth, // Provide loading state
    setCustomerIdentity, // Provide function to set identity
    clearCustomerIdentity // Provide function to clear identity
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

