import React, { createContext, useState, useEffect, useContext } from 'react';
import { authService, userService } from '../services/api';
import { useNavigate } from 'react-router-dom';

// Create the authentication context
export const AuthContext = createContext(null);

// Custom hook to use the auth context
export const useAuth = () => {
  return useContext(AuthContext);
};

// Auth Provider component
export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // Check if the user is authenticated on component mount
  useEffect(() => {
    const loadUserProfile = async () => {
      try {
        if (authService.isAuthenticated()) {
          const profile = await userService.getProfile();
          setUser(profile);
          localStorage.setItem('userId', profile.google_id);
        }
      } catch (err) {
        if (err.response && (err.response.status === 401 || err.response.status === 403)) {
          // Token might be expired or invalid, force logout
          authService.logout();
        } else {
          setError('Failed to load user profile. Please try again later.');
        }
      } finally {
        setLoading(false);
      }
    };

    loadUserProfile();
  }, []);

  // Handle login with Google
  const login = () => {
    authService.loginWithGoogle();
  };

  // Handle logout
  const logout = async () => {
    try {
      await authService.logout();
      setUser(null);
      navigate('/login');
    } catch (err) {
      // Even if the logout API fails, we still clear local storage
      localStorage.removeItem('token');
      localStorage.removeItem('userId');
      setUser(null);
      navigate('/login');
    }
  };

  // Handle OAuth callback
  const handleCallback = (token) => {
    authService.handleCallback(token);
    navigate('/dashboard');
  };

  // Context value
  const value = {
    user,
    loading,
    error,
    login,
    logout,
    handleCallback,
    isAuthenticated: authService.isAuthenticated()
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
