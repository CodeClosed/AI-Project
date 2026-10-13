import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  getStoredToken,
  getRefreshToken,
  setStoredTokens,
  clearStoredTokens,
  loginUser as apiLogin,
  registerUser as apiRegister,
  verifyMfaLogin,
  fetchCurrentUser,
  verifyEmailAddress,
  resendEmailVerification,
  cancelAccountDeletion,
  logoutServerSession,
} from '../api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => getStoredToken());
  const [isLoading, setIsLoading] = useState(true);
  const [sessionExpiredNotice, setSessionExpiredNotice] = useState(false);

  // Re-check authentication and fetch profile on app start
  const refreshUser = useCallback(async () => {
    const savedToken = getStoredToken();
    const savedRefreshToken = getRefreshToken();

    if (!savedToken && !savedRefreshToken) {
      setUser(null);
      setToken(null);
      setIsLoading(false);
      return null;
    }

    try {
      const userData = await fetchCurrentUser();
      if (userData) {
        setUser(userData);
        setToken(getStoredToken());
        return userData;
      } else {
        setUser(null);
        setToken(null);
      }
    } catch (err) {
      console.warn('Authentication token verification failed:', err);
      setUser(null);
      setToken(null);
      clearStoredTokens();
    } finally {
      setIsLoading(false);
    }
    return null;
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  // Sync logout across browser tabs
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'nutrimenu_refresh_token' && !e.newValue) {
        setUser(null);
        setToken(null);
        clearStoredTokens();
      }
    };
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, []);

  const login = async (email, password) => {
    setIsLoading(true);
    try {
      const res = await apiLogin(email, password);
      if (res.verification_required || res.mfa_required) {
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
      if (res.verification_required) {
        return res;
      }
      if (res.access_token) {
        setToken(res.access_token);
      }
      if (res.user) {
        setUser(res.user);
      }
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const verifyEmail = async (email, code) => {
    setIsLoading(true);
    try {
      const res = await verifyEmailAddress(email, code);
      if (res.access_token) {
        setToken(res.access_token);
      }
      if (res.user) {
        setUser(res.user);
      }
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const resendVerification = async (email) => {
    return await resendEmailVerification(email);
  };

  const cancelDeletion = async (password) => {
    setIsLoading(true);
    try {
      const res = await cancelAccountDeletion(password);
      if (res.access_token) {
        setToken(res.access_token);
      }
      if (res.user) {
        setUser(res.user);
      }
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      await logoutServerSession();
    } catch {}

    clearStoredTokens();
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
    verifyEmail,
    resendVerification,
    cancelDeletion,
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
