import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  getStoredToken,
  setStoredToken,
  clearStoredToken,
  loginUser as apiLogin,
  registerUser as apiRegister,
  verifyMfaLogin,
  fetchCurrentUser,
  fetchUserProfile,
} from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => getStoredToken());
  const [isLoading, setIsLoading] = useState(true);

  // Re-check authentication and fetch profile on app start
  const refreshUser = useCallback(async () => {
    const savedToken = getStoredToken();
    if (!savedToken) {
      setUser(null);
      setToken(null);
      setIsLoading(false);
      return null;
    }

    try {
      const userData = await fetchCurrentUser();
      if (userData) {
        setUser(userData);
        setToken(savedToken);
        return userData;
      } else {
        setUser(null);
        setToken(null);
      }
    } catch (err) {
      console.warn('Authentication token verification failed:', err);
      setUser(null);
      setToken(null);
      clearStoredToken();
    } finally {
      setIsLoading(false);
    }
    return null;
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = async (email, password) => {
    setIsLoading(true);
    try {
      const res = await apiLogin(email, password);
      if (res.mfa_required) {
        return res;
      }
      setToken(res.access_token);
      setUser(res.user);
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const completeMfaLogin = async (tempToken, code) => {
    setIsLoading(true);
    try {
      const res = await verifyMfaLogin(tempToken, code);
      setToken(res.access_token);
      setUser(res.user);
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (email, password, profile = null) => {
    setIsLoading(true);
    try {
      const res = await apiRegister(email, password, profile);
      setToken(res.access_token);
      setUser(res.user);
      return res.user;
    } finally {
      setIsLoading(false);
    }
  };

  const [sessionExpiredNotice, setSessionExpiredNotice] = useState(false);

  const logout = () => {
    clearStoredToken();
    setToken(null);
    setUser(null);

    // Thoroughly purge all account-specific data from client storage to prevent cross-account data leakage
    try {
      localStorage.removeItem('nutrimenu_account_profile');
      localStorage.removeItem('nutrimenu_active_plate');
      localStorage.removeItem('nutrimenu_daily_logged_meals');
      localStorage.removeItem('nutrimenu_saved_menus');
      // Purge any user-scoped storage keys
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith('nutrimenu_user_') || key.startsWith('nutrimenu_guest_')) {
          localStorage.removeItem(key);
        }
      });
    } catch {}

    window.dispatchEvent(new CustomEvent('auth:logout'));
  };

  useEffect(() => {
    const handleExpired = () => {
      logout();
      setSessionExpiredNotice(true);
    };
    window.addEventListener('auth:session_expired', handleExpired);
    return () => window.removeEventListener('auth:session_expired', handleExpired);
  }, []);

  const value = {
    user,
    token,
    isAuthenticated: Boolean(user && token),
    isLoading,
    login,
    completeMfaLogin,
    register,
    logout,
    refreshUser,
    sessionExpiredNotice,
    setSessionExpiredNotice,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
