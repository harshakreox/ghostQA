/**
 * Authentication Context
 * Manages user authentication state with 30-minute session timeout
 * Note: Axios interceptors are set up in main.jsx to ensure they run first
 */
import { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

// Session timeout in milliseconds (30 minutes)
const SESSION_TIMEOUT = 30 * 60 * 1000;

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sessionExpiry, setSessionExpiry] = useState(null);
  const [mustChangePassword, setMustChangePassword] = useState(false);

  // Initialize auth state from localStorage
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');
    const storedExpiry = localStorage.getItem('auth_expiry');

    console.log('[AUTH] Initializing from localStorage, token exists:', !!storedToken);

    if (storedToken && storedUser && storedExpiry) {
      // Ensure expiry is parsed as UTC
      const expiryString = storedExpiry.endsWith('Z') ? storedExpiry : storedExpiry + 'Z';
      const expiryTime = new Date(expiryString);
      const now = new Date();

      console.log('[AUTH] Expiry:', expiryTime.toISOString(), 'Now:', now.toISOString(), 'Valid:', expiryTime > now);

      // Check if session is still valid
      if (expiryTime > now) {
        setToken(storedToken);
        setUser(JSON.parse(storedUser));
        setSessionExpiry(expiryTime);
      } else {
        // Session expired, clear storage
        console.log('[AUTH] Session expired, clearing...');
        clearAuthData();
      }
    }
    setLoading(false);
  }, []);

  // Session timeout checker
  useEffect(() => {
    if (!sessionExpiry) return;

    const checkSession = () => {
      if (new Date() >= sessionExpiry) {
        logout();
      }
    };

    // Check every minute
    const interval = setInterval(checkSession, 60000);

    // Also check immediately
    checkSession();

    return () => clearInterval(interval);
  }, [sessionExpiry]);

  const clearAuthData = () => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    localStorage.removeItem('auth_expiry');
    // Note: axios interceptor reads from localStorage, so clearing it is enough
    setToken(null);
    setUser(null);
    setSessionExpiry(null);
  };

  const login = async (username, password) => {
    try {
      console.log('[AUTH] Attempting login for:', username);
      const response = await axios.post('/api/auth/login', { username, password });
      console.log('[AUTH] Login response:', response.data);
      const { access_token, expires_at, user: userData } = response.data;

      // Parse expiry - append Z if no timezone to treat as UTC
      const expiryString = expires_at.endsWith('Z') ? expires_at : expires_at + 'Z';
      const expiryDate = new Date(expiryString);
      console.log('[AUTH] Expiry parsed:', expiryDate.toISOString(), 'Now:', new Date().toISOString());

      // Store auth data - axios interceptor will pick up the token automatically
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('auth_user', JSON.stringify(userData));
      localStorage.setItem('auth_expiry', expiryDate.toISOString());

      setToken(access_token);
      setUser(userData);
      setSessionExpiry(expiryDate);

      // Check if user must change password
      console.log('[AUTH] User data:', userData);
      console.log('[AUTH] must_change_password:', userData.must_change_password);
      if (userData.must_change_password) {
        console.log('[AUTH] Setting mustChangePassword to true');
        setMustChangePassword(true);
      }

      return { success: true, user: userData };
    } catch (error) {
      const message = error.response?.data?.detail || 'Login failed';
      return { success: false, error: message };
    }
  };

  const register = async (username, email, password) => {
    try {
      const response = await axios.post('/api/auth/register', {
        username,
        email,
        password,
        role: 'user'
      });
      const { access_token, expires_at, user: userData } = response.data;

      // Parse expiry - append Z if no timezone to treat as UTC
      const expiryString = expires_at.endsWith('Z') ? expires_at : expires_at + 'Z';
      const expiryDate = new Date(expiryString);

      // Store auth data - axios interceptor will pick up the token automatically
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('auth_user', JSON.stringify(userData));
      localStorage.setItem('auth_expiry', expiryDate.toISOString());

      setToken(access_token);
      setUser(userData);
      setSessionExpiry(expiryDate);

      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Registration failed';
      return { success: false, error: message };
    }
  };

  const logout = useCallback(() => {
    clearAuthData();
    setMustChangePassword(false);
  }, []);

  const forceChangePassword = async (newPassword) => {
    try {
      const response = await axios.post('/api/auth/force-change-password', {
        new_password: newPassword
      });
      const { access_token, expires_at, user: userData } = response.data;

      // Parse expiry - append Z if no timezone to treat as UTC
      const expiryString = expires_at.endsWith('Z') ? expires_at : expires_at + 'Z';
      const expiryDate = new Date(expiryString);

      // Update stored auth data
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('auth_user', JSON.stringify(userData));
      localStorage.setItem('auth_expiry', expiryDate.toISOString());

      setToken(access_token);
      setUser(userData);
      setSessionExpiry(expiryDate);
      setMustChangePassword(false);

      return { success: true };
    } catch (error) {
      const message = error.response?.data?.detail || 'Password change failed';
      return { success: false, error: message };
    }
  };

  const refreshSession = async () => {
    try {
      const response = await axios.post('/api/auth/refresh');
      const { access_token, expires_at, user: userData } = response.data;

      // Parse expiry - append Z if no timezone to treat as UTC
      const expiryString = expires_at.endsWith('Z') ? expires_at : expires_at + 'Z';
      const expiryDate = new Date(expiryString);

      // Update stored auth data - axios interceptor will pick up the token automatically
      localStorage.setItem('auth_token', access_token);
      localStorage.setItem('auth_user', JSON.stringify(userData));
      localStorage.setItem('auth_expiry', expiryDate.toISOString());

      setToken(access_token);
      setUser(userData);
      setSessionExpiry(expiryDate);

      return true;
    } catch (error) {
      logout();
      return false;
    }
  };

  // Computed properties
  const isAuthenticated = !!token && !!user;
  const isAdmin = user?.role === 'admin';
  const isUser = user?.role === 'user';

  // Time until session expires
  const getTimeUntilExpiry = () => {
    if (!sessionExpiry) return 0;
    return Math.max(0, sessionExpiry - new Date());
  };

  const value = {
    user,
    token,
    loading,
    isAuthenticated,
    isAdmin,
    isUser,
    sessionExpiry,
    mustChangePassword,
    login,
    register,
    logout,
    forceChangePassword,
    refreshSession,
    getTimeUntilExpiry,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

export default AuthContext;
