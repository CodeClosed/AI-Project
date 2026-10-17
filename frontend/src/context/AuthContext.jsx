import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import {
  getStoredToken,
  getRefreshToken,
  getStoredUser,
  setStoredUser,
  clearStoredUser,
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
  const [user, setUser] = useState(() => getStoredUser());
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
      clearStoredUser();
      setIsLoading(false);
      return null;
    }

    try {
      const userData = await fetchCurrentUser();
      if (userData) {
        setUser(userData);
        setStoredUser(userData);
        setToken(getStoredToken());
        return userData;
      } else {
        const currentToken = getStoredToken();
        if (!currentToken) {
          setUser(null);
          setToken(null);
          clearStoredUser();
        }
      }
    } catch (err) {
      console.warn('Authentication token verification failed:', err);
      if (err?.message?.includes('401') || err?.message?.includes('Session expired')) {
        setUser(null);
        setToken(null);
        clearStoredTokens();
        clearStoredUser();
      }
    } finally {
      setIsLoading(false);
    }
    return null;
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  // Sync login/logout across browser tabs in real-time
  useEffect(() => {
    const handleStorageChange = (e) => {
      if (e.key === 'nutrimenu_refresh_token') {
        if (!e.newValue) {
          // Logged out in another tab
          setUser(null);
          setToken(null);
          clearStoredTokens();
          clearStoredUser();
        } else {
          // Logged in or rotated tokens in another tab
          setToken(getStoredToken());
          setUser(getStoredUser());
          refreshUser();
        }
      }
    };
    window.addEventListener('storage', handleStorageChange);
    return () => window.removeEventListener('storage', handleStorageChange);
  }, [refreshUser]);

  const login = async (email, password) => {
    setIsLoading(true);
    try {
      const res = await apiLogin(email, password);
      if (res.verification_required || res.mfa_required || res.deletion_pending) {
        return res;
      }
      setToken(res.access_token);
      setUser(res.user);
      if (res.user) setStoredUser(res.user);
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
      if (res.user) setStoredUser(res.user);
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
        setStoredUser(res.user);
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
        setStoredUser(res.user);
      }
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const resendVerification = async (email) => {
    return await resendEmailVerification(email);
  };

  const cancelDeletion = async (email, password) => {
    setIsLoading(true);
    try {
      const res = await cancelAccountDeletion(email, password);
      if (res.access_token) {
        setToken(res.access_token);
      }
      if (res.user) {
        setUser(res.user);
        setStoredUser(res.user);
      }
      return res;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    // 1. Instantly clear tokens and user from local storage and in-memory state
    clearStoredTokens();
    clearStoredUser();
    setToken(null);
    setUser(null);

    // Thoroughly purge all account-specific data from client storage to prevent cross-account data leakage
    try {
      localStorage.removeItem('nutrimenu_account_profile');
      localStorage.removeItem('nutrimenu_active_plate');
      localStorage.removeItem('nutrimenu_daily_logged_meals');
      localStorage.removeItem('nutrimenu_saved_menus');
      // Purge any user-scoped and guest-scoped storage keys
      Object.keys(localStorage).forEach((key) => {
        if (key.startsWith('nutrimenu_guest_') || key.startsWith('nutrimenu_user_')) {
          localStorage.removeItem(key);
        }
      });
    } catch {}

    // 2. Notify entire app to purge memory state
    window.dispatchEvent(new CustomEvent('auth:logout'));

    // 3. Notify backend server session revocation in background
    try {
      await logoutServerSession();
    } catch {}
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
