import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  X,
  Settings,
  Shield,
  Key,
  Trash2,
  Download,
  FileSpreadsheet,
  FileCode,
  Moon,
  Sun,
  UtensilsCrossed,
  AlertTriangle,
  Check,
  Loader2,
  Cloud,
  HardDrive,
  User,
  LogIn,
  ShieldCheck,
  Smartphone,
  Copy,
  CheckCircle2,
  QrCode,
  KeyRound,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useNutrition } from '../context/NutritionContext';
import { changeUserPassword, deleteUserAccount, setupMfa, enableMfa, disableMfa, getApiBaseUrl, setCustomApiUrl } from '../api';
import { exportMealsToCsv, exportMealsToJson } from '../utils/exportUtils';

export default function SettingsModal({ isOpen, onClose }) {
  const navigate = useNavigate();
  const { user, isAuthenticated, logout, refreshUser } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const { loggedMeals, savedMenus, plate, handleClearAllLoggedMeals, handleClearPlate } = useNutrition();

  const [activeTab, setActiveTab] = useState('security'); // 'security' | 'data' | 'preferences'

  // Change Password State
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState('');
  const [passwordError, setPasswordError] = useState('');

  // 2FA / MFA State
  const [mfaSetupData, setMfaSetupData] = useState(null); // { secret, otpauth_uri, backup_codes }
  const [mfaVerifyCode, setMfaVerifyCode] = useState('');
  const [mfaLoading, setMfaLoading] = useState(false);
  const [mfaError, setMfaError] = useState('');
  const [mfaSuccess, setMfaSuccess] = useState('');
  const [showDisableMfa, setShowDisableMfa] = useState(false);
  const [disableMfaPassword, setDisableMfaPassword] = useState('');
  const [copiedKey, setCopiedKey] = useState(false);
  const [copiedBackupCodes, setCopiedBackupCodes] = useState(false);

  // Delete Account State
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  // Dining Mode State (persisted in localStorage)
  const [diningMode, setDiningMode] = useState(() => {
    try {
      return localStorage.getItem('nutrimenu_dining_mode') || 'strict';
    } catch {
      return 'strict';
    }
  });

  const handleSelectDiningMode = (mode) => {
    setDiningMode(mode);
    try {
      localStorage.setItem('nutrimenu_dining_mode', mode);
    } catch {}
  };

  // Custom API URL State
  const [apiUrl, setApiUrl] = useState(() => {
    try {
      return localStorage.getItem('nutrimenu_custom_api_url') || '';
    } catch {
      return '';
    }
  });
  const [savedApiSuccess, setSavedApiSuccess] = useState(false);

  // Close on Escape key
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  // Change Password Submit
  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordError('');
    setPasswordSuccess('');

    if (!oldPassword) {
      setPasswordError('Please enter your current password.');
      return;
    }
    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match.');
      return;
    }

    setPasswordLoading(true);
    try {
      const res = await changeUserPassword(oldPassword, newPassword);
      setPasswordSuccess(res?.message || 'Password changed successfully!');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordSuccess(''), 4000);
    } catch (err) {
      setPasswordError(err.message || 'Failed to change password.');
    } finally {
      setPasswordLoading(false);
    }
  };

  // 2FA Handlers
  const handleStartMfaSetup = async () => {
    setMfaError('');
    setMfaSuccess('');
    setMfaLoading(true);
    try {
      const data = await setupMfa();
      setMfaSetupData(data);
    } catch (err) {
      setMfaError(err.message || 'Failed to initialize 2FA setup.');
    } finally {
      setMfaLoading(false);
    }
  };

  const handleConfirmEnableMfa = async (e) => {
    e.preventDefault();
    if (!mfaVerifyCode || mfaVerifyCode.trim().length !== 6) {
      setMfaError('Please enter the 6-digit code from your authenticator app.');
      return;
    }
    setMfaError('');
    setMfaLoading(true);
    try {
      await enableMfa(mfaVerifyCode.trim());
      await refreshUser();
      setMfaSuccess('Two-factor authentication successfully enabled!');
      setMfaSetupData(null);
      setMfaVerifyCode('');
      setTimeout(() => setMfaSuccess(''), 5000);
    } catch (err) {
      setMfaError(err.message || 'Failed to verify code. Please try again.');
    } finally {
      setMfaLoading(false);
    }
  };

  const handleDisableMfa = async (e) => {
    e.preventDefault();
    if (!disableMfaPassword) {
      setMfaError('Please enter your password to disable 2FA.');
      return;
    }
    setMfaError('');
    setMfaLoading(true);
    try {
      await disableMfa(disableMfaPassword);
      await refreshUser();
      setShowDisableMfa(false);
      setDisableMfaPassword('');
      setMfaSuccess('Two-factor authentication has been disabled.');
      setTimeout(() => setMfaSuccess(''), 5000);
    } catch (err) {
      setMfaError(err.message || 'Failed to disable 2FA. Verify your password.');
    } finally {
      setMfaLoading(false);
    }
  };

  const handleCopySecret = () => {
    if (mfaSetupData?.secret) {
      navigator.clipboard.writeText(mfaSetupData.secret);
      setCopiedKey(true);
      setTimeout(() => setCopiedKey(false), 2000);
    }
  };

  const handleCopyBackupCodes = () => {
    if (mfaSetupData?.backup_codes) {
      navigator.clipboard.writeText(mfaSetupData.backup_codes.join('\n'));
      setCopiedBackupCodes(true);
      setTimeout(() => setCopiedBackupCodes(false), 2000);
    }
  };

  const handleDownloadBackupCodes = () => {
    if (mfaSetupData?.backup_codes) {
      const element = document.createElement('a');
      const file = new Blob([
        `NutriMenu AI Two-Factor Authentication Backup Codes\nAccount: ${user?.email || 'user'}\nDate: ${new Date().toISOString()}\n\nKeep these codes in a safe place. Each code can only be used once.\n\n` +
        mfaSetupData.backup_codes.map((code, idx) => `${idx + 1}. ${code}`).join('\n')
      ], { type: 'text/plain' });
      element.href = URL.createObjectURL(file);
      element.download = 'nutrimenu-backup-codes.txt';
      document.body.appendChild(element);
      element.click();
      document.body.removeChild(element);
    }
  };

  // Delete Account Submit
  const handleDeleteAccount = async (e) => {
    e.preventDefault();
    setDeleteError('');
    if (!deletePassword) {
      setDeleteError('Please enter your password to confirm account deletion.');
      return;
    }

    setDeleteLoading(true);
    try {
      await deleteUserAccount(deletePassword);
      logout();
      onClose();
      navigate('/');
    } catch (err) {
      setDeleteError(err.message || 'Incorrect password. Deletion aborted.');
    } finally {
      setDeleteLoading(false);
    }
  };

  // Clear Local Data
  const handleClearCache = () => {
    if (window.confirm('Clear local meals and current plate? (If logged in, your cloud account remains safe).')) {
      handleClearAllLoggedMeals();
      handleClearPlate();
    }
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-200">
      <div
        className="w-full max-w-2xl bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 overflow-hidden flex flex-col max-h-[90vh] animate-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="px-6 py-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/70 dark:bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-600 text-white flex items-center justify-center shadow-md shadow-emerald-600/20">
              <Settings className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-black text-slate-900 dark:text-white leading-tight">Settings & Preferences</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Manage your credentials, data backups, and dining modes
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition cursor-pointer"
            title="Close Settings"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tab Navigation */}
        <div className="flex border-b border-slate-200 dark:border-slate-800 px-6 bg-white dark:bg-slate-900">
          <button
            onClick={() => setActiveTab('security')}
            className={`py-3 px-4 text-xs font-bold border-b-2 transition flex items-center gap-2 cursor-pointer ${
              activeTab === 'security'
                ? 'border-emerald-600 text-emerald-600 dark:text-emerald-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Shield className="w-4 h-4" />
            <span>Account & Security</span>
          </button>

          <button
            onClick={() => setActiveTab('data')}
            className={`py-3 px-4 text-xs font-bold border-b-2 transition flex items-center gap-2 cursor-pointer ${
              activeTab === 'data'
                ? 'border-emerald-600 text-emerald-600 dark:text-emerald-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <Download className="w-4 h-4" />
            <span>Data & Export</span>
          </button>

          <button
            onClick={() => setActiveTab('preferences')}
            className={`py-3 px-4 text-xs font-bold border-b-2 transition flex items-center gap-2 cursor-pointer ${
              activeTab === 'preferences'
                ? 'border-emerald-600 text-emerald-600 dark:text-emerald-400'
                : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
            }`}
          >
            <UtensilsCrossed className="w-4 h-4" />
            <span>Preferences</span>
          </button>
        </div>

        {/* Tab Content Body */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* TAB 1: ACCOUNT & SECURITY */}
          {activeTab === 'security' && (
            <div className="space-y-6">
              {/* Account Status Pill */}
              <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-9 h-9 rounded-xl bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-slate-700 dark:text-slate-200">
                    <User className="w-5 h-5" />
                  </div>
                  <div>
                    <span className="text-xs font-bold text-slate-900 dark:text-white block">
                      {isAuthenticated ? user?.email : 'Guest Session (Unauthenticated)'}
                    </span>
                    <span className="text-[11px] text-slate-500 dark:text-slate-400">
                      {isAuthenticated
                        ? 'Authenticated account with cloud database synchronization'
                        : 'Your data is currently stored only in this browser'}
                    </span>
                  </div>
                </div>
                {isAuthenticated ? (
                  <span className="px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 text-[11px] font-black flex items-center gap-1 border border-emerald-200 dark:border-emerald-800">
                    <Cloud className="w-3 h-3" /> Synced
                  </span>
                ) : (
                  <button
                    onClick={() => {
                      onClose();
                      navigate('/login');
                    }}
                    className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition flex items-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    <LogIn className="w-3.5 h-3.5" /> Sign In
                  </button>
                )}
              </div>

              {/* Change Password Section */}
              {isAuthenticated ? (
                <div className="p-5 rounded-2xl bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 space-y-4">
                  <div className="flex items-center gap-2">
                    <Key className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                    <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                      Change Account Password
                    </h3>
                  </div>

                  {passwordSuccess && (
                    <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs font-semibold flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-600" />
                      <span>{passwordSuccess}</span>
                    </div>
                  )}

                  {passwordError && (
                    <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs font-semibold flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-rose-600" />
                      <span>{passwordError}</span>
                    </div>
                  )}

                  <form onSubmit={handleChangePassword} className="space-y-3">
                    <div>
                      <label className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block mb-1">
                        Current Password
                      </label>
                      <input
                        type="password"
                        value={oldPassword}
                        onChange={(e) => setOldPassword(e.target.value)}
                        placeholder="••••••••"
                        className="w-full px-3.5 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:border-emerald-500"
                        required
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <div>
                        <label className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block mb-1">
                          New Password (min 8 chars)
                        </label>
                        <input
                          type="password"
                          value={newPassword}
                          onChange={(e) => setNewPassword(e.target.value)}
                          placeholder="••••••••"
                          className="w-full px-3.5 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:border-emerald-500"
                          required
                        />
                      </div>
                      <div>
                        <label className="text-[11px] font-bold text-slate-700 dark:text-slate-300 block mb-1">
                          Confirm New Password
                        </label>
                        <input
                          type="password"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder="••••••••"
                          className="w-full px-3.5 py-2 text-xs rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:border-emerald-500"
                          required
                        />
                      </div>
                    </div>

                    <div className="pt-1 flex justify-end">
                      <button
                        type="submit"
                        disabled={passwordLoading}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition flex items-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                      >
                        {passwordLoading ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            <span>Updating Password...</span>
                          </>
                        ) : (
                          <span>Update Password</span>
                        )}
                      </button>
                    </div>
                  </form>
                </div>
              ) : null}

              {/* Two-Factor Authentication (2FA) Section */}
              {isAuthenticated ? (
                <div className="p-5 rounded-2xl bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 space-y-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                      <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                        Two-Factor Authentication (2FA)
                      </h3>
                    </div>
                    {user?.two_factor_enabled ? (
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/80 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800 flex items-center gap-1">
                        <Check className="w-3 h-3" />
                        Active
                      </span>
                    ) : (
                      <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                        Inactive
                      </span>
                    )}
                  </div>

                  {mfaSuccess && (
                    <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200 text-xs font-semibold flex items-center gap-2">
                      <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                      <span>{mfaSuccess}</span>
                    </div>
                  )}

                  {mfaError && (
                    <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/60 border border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs font-semibold flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-rose-600 shrink-0" />
                      <span>{mfaError}</span>
                    </div>
                  )}

                  {user?.two_factor_enabled ? (
                    <div className="space-y-3 pt-1">
                      <p className="text-xs text-slate-600 dark:text-slate-400">
                        Your account is secured with RFC 6238 time-based one-time passwords (TOTP). Signing in requires your password and an authenticator app code.
                      </p>

                      {!showDisableMfa ? (
                        <div>
                          <button
                            type="button"
                            onClick={() => {
                              setShowDisableMfa(true);
                              setMfaError('');
                            }}
                            className="px-3.5 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold transition cursor-pointer"
                          >
                            Disable Two-Factor Authentication
                          </button>
                        </div>
                      ) : (
                        <form onSubmit={handleDisableMfa} className="p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 space-y-3">
                          <p className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                            Enter your account password to confirm disabling 2FA:
                          </p>
                          <input
                            type="password"
                            required
                            value={disableMfaPassword}
                            onChange={(e) => setDisableMfaPassword(e.target.value)}
                            placeholder="Current account password"
                            className="w-full px-3.5 py-2 text-xs rounded-xl bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:border-emerald-500"
                          />
                          <div className="flex items-center gap-2 pt-1">
                            <button
                              type="submit"
                              disabled={mfaLoading}
                              className="px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl transition cursor-pointer disabled:opacity-50"
                            >
                              {mfaLoading ? 'Disabling...' : 'Confirm Disable'}
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                setShowDisableMfa(false);
                                setDisableMfaPassword('');
                                setMfaError('');
                              }}
                              className="px-3.5 py-1.5 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 text-xs font-bold rounded-xl transition cursor-pointer"
                            >
                              Cancel
                            </button>
                          </div>
                        </form>
                      )}
                    </div>
                  ) : !mfaSetupData ? (
                    <div className="space-y-3 pt-1">
                      <p className="text-xs text-slate-600 dark:text-slate-400">
                        Add an extra layer of defense against unauthorized access. Signing in will require an authenticator app code (Google Authenticator, Authy, 1Password) or single-use recovery code.
                      </p>
                      <button
                        type="button"
                        onClick={handleStartMfaSetup}
                        disabled={mfaLoading}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition flex items-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                      >
                        {mfaLoading ? (
                          <>
                            <Loader2 className="w-3.5 h-3.5 animate-spin" />
                            <span>Setting up...</span>
                          </>
                        ) : (
                          <>
                            <Smartphone className="w-3.5 h-3.5" />
                            <span>Set Up Authenticator App (2FA)</span>
                          </>
                        )}
                      </button>
                    </div>
                  ) : (
                    <div className="space-y-4 pt-1 border-t border-slate-100 dark:border-slate-800">
                      {/* Step 1: Scan QR or copy key */}
                      <div className="space-y-2">
                        <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                          Step 1: Link Authenticator App
                        </span>
                        <div className="flex flex-col sm:flex-row items-center gap-4 p-4 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                          <div className="bg-white p-2 rounded-xl shadow-xs shrink-0">
                            <img
                              src={`https://api.qrserver.com/v1/create-qr-code/?size=140x140&data=${encodeURIComponent(mfaSetupData.otpauth_uri)}`}
                              alt="2FA QR Code"
                              className="w-32 h-32"
                            />
                          </div>
                          <div className="space-y-2 text-center sm:text-left">
                            <p className="text-xs text-slate-600 dark:text-slate-300">
                              Scan this QR code in Google Authenticator, Authy, or 1Password. Or enter the secret key manually:
                            </p>
                            <div className="flex items-center gap-2">
                              <code className="px-2.5 py-1.5 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400 select-all break-all">
                                {mfaSetupData.secret}
                              </code>
                              <button
                                type="button"
                                onClick={handleCopySecret}
                                className="p-2 rounded-lg bg-slate-200 dark:bg-slate-700 hover:bg-slate-300 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 transition cursor-pointer shrink-0"
                                title="Copy Secret Key"
                              >
                                {copiedKey ? <Check className="w-3.5 h-3.5 text-emerald-500" /> : <Copy className="w-3.5 h-3.5" />}
                              </button>
                            </div>
                          </div>
                        </div>
                      </div>

                      {/* Step 2: Save Emergency Recovery Codes */}
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                            Step 2: Save Emergency Recovery Codes
                          </span>
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              onClick={handleCopyBackupCodes}
                              className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400 hover:underline cursor-pointer"
                            >
                              <Copy className="w-3 h-3" />
                              <span>{copiedBackupCodes ? 'Copied' : 'Copy'}</span>
                            </button>
                            <span className="text-slate-300 dark:text-slate-600">•</span>
                            <button
                              type="button"
                              onClick={handleDownloadBackupCodes}
                              className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600 dark:text-emerald-400 hover:underline cursor-pointer"
                            >
                              <Download className="w-3 h-3" />
                              <span>Download .txt</span>
                            </button>
                          </div>
                        </div>
                        <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-800">
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                            {mfaSetupData.backup_codes?.map((code, idx) => (
                              <div
                                key={idx}
                                className="px-2 py-1 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-center font-mono text-[11px] font-bold text-slate-700 dark:text-slate-300"
                              >
                                {code}
                              </div>
                            ))}
                          </div>
                          <p className="mt-2 text-[10px] text-slate-500 dark:text-slate-400">
                            Each backup recovery code can only be used once if you ever lose your authenticator device.
                          </p>
                        </div>
                      </div>

                      {/* Step 3: Enter verification code */}
                      <form onSubmit={handleConfirmEnableMfa} className="space-y-3">
                        <span className="text-[11px] font-extrabold uppercase tracking-wider text-slate-500 dark:text-slate-400 block">
                          Step 3: Confirm 6-Digit Code
                        </span>
                        <div className="flex gap-2">
                          <input
                            type="text"
                            maxLength={6}
                            required
                            value={mfaVerifyCode}
                            onChange={(e) => setMfaVerifyCode(e.target.value.replace(/\D/g, ''))}
                            placeholder="123456"
                            className="flex-1 text-center font-mono tracking-widest text-sm font-bold px-3.5 py-2 rounded-xl bg-slate-50 dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:border-emerald-500"
                          />
                          <button
                            type="submit"
                            disabled={mfaLoading || mfaVerifyCode.length !== 6}
                            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition cursor-pointer shadow-xs disabled:opacity-50"
                          >
                            {mfaLoading ? 'Verifying...' : 'Verify & Activate'}
                          </button>
                          <button
                            type="button"
                            onClick={() => {
                              setMfaSetupData(null);
                              setMfaVerifyCode('');
                              setMfaError('');
                            }}
                            className="px-3.5 py-2 bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 text-xs font-bold rounded-xl transition cursor-pointer"
                          >
                            Cancel
                          </button>
                        </div>
                      </form>
                    </div>
                  )}
                </div>
              ) : null}

              {/* Danger Zone: Delete Account */}
              {isAuthenticated ? (
                <div className="p-5 rounded-2xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/60 space-y-3">
                  <div className="flex items-center gap-2 text-rose-700 dark:text-rose-400">
                    <Trash2 className="w-4 h-4" />
                    <h3 className="text-xs font-bold uppercase tracking-wider">Danger Zone</h3>
                  </div>
                  <p className="text-xs text-slate-600 dark:text-slate-400">
                    Permanently delete your NutriMenu account, saved health biometrics, and cloud meal logs. This action cannot be undone.
                  </p>

                  {!showDeleteConfirm ? (
                    <button
                      onClick={() => setShowDeleteConfirm(true)}
                      className="px-3.5 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold transition cursor-pointer shadow-xs"
                    >
                      Delete Account Permanently
                    </button>
                  ) : (
                    <form onSubmit={handleDeleteAccount} className="space-y-3 pt-2">
                      {deleteError && (
                        <div className="p-2.5 rounded-xl bg-rose-100 dark:bg-rose-900/40 text-rose-800 dark:text-rose-200 text-xs font-semibold">
                          {deleteError}
                        </div>
                      )}
                      <div>
                        <label className="text-xs font-bold text-rose-700 dark:text-rose-400 block mb-1">
                          Confirm with your password to delete:
                        </label>
                        <input
                          type="password"
                          value={deletePassword}
                          onChange={(e) => setDeletePassword(e.target.value)}
                          placeholder="Your current password"
                          className="w-full px-3.5 py-2 text-xs rounded-xl bg-white dark:bg-slate-900 border border-rose-300 dark:border-rose-700 text-slate-900 dark:text-white focus:outline-none"
                          required
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="submit"
                          disabled={deleteLoading}
                          className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl transition flex items-center gap-2 cursor-pointer shadow-xs disabled:opacity-50"
                        >
                          {deleteLoading ? (
                            <>
                              <Loader2 className="w-3.5 h-3.5 animate-spin" />
                              <span>Deleting...</span>
                            </>
                          ) : (
                            <span>Confirm & Delete Permanently</span>
                          )}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            setShowDeleteConfirm(false);
                            setDeletePassword('');
                            setDeleteError('');
                          }}
                          className="px-3 py-2 text-xs font-semibold text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white cursor-pointer"
                        >
                          Cancel
                        </button>
                      </div>
                    </form>
                  )}
                </div>
              ) : null}
            </div>
          )}

          {/* TAB 2: DATA & EXPORT */}
          {activeTab === 'data' && (
            <div className="space-y-6">
              {/* Export Actions Card */}
              <div className="p-5 rounded-2xl bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 space-y-4">
                <div className="flex items-center gap-2">
                  <Download className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Export Nutrition Data
                  </h3>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Take your logged meals and macro data with you to share with your personal healthcare provider, dietitian, or coach.
                </p>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
                  <button
                    onClick={() => exportMealsToCsv(loggedMeals)}
                    className="p-4 rounded-2xl bg-emerald-50/80 dark:bg-emerald-950/40 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 border border-emerald-200 dark:border-emerald-800/80 text-left transition cursor-pointer group flex items-start gap-3"
                  >
                    <div className="p-2.5 rounded-xl bg-emerald-600 text-white shrink-0 shadow-xs">
                      <FileSpreadsheet className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-emerald-700 dark:group-hover:text-emerald-300">
                        Export as CSV
                      </h4>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        Structured spreadsheet format for Excel or Google Sheets ({loggedMeals.length} records)
                      </p>
                    </div>
                  </button>

                  <button
                    onClick={() => exportMealsToJson(loggedMeals)}
                    className="p-4 rounded-2xl bg-indigo-50/80 dark:bg-indigo-950/40 hover:bg-indigo-100 dark:hover:bg-indigo-900/40 border border-indigo-200 dark:border-indigo-800/80 text-left transition cursor-pointer group flex items-start gap-3"
                  >
                    <div className="p-2.5 rounded-xl bg-indigo-600 text-white shrink-0 shadow-xs">
                      <FileCode className="w-5 h-5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white group-hover:text-indigo-700 dark:group-hover:text-indigo-300">
                        Export as JSON
                      </h4>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        Raw portable data backup for complete personal nutrition archiving
                      </p>
                    </div>
                  </button>
                </div>
              </div>

              {/* Local Storage & Cache Card */}
              <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <HardDrive className="w-4 h-4 text-slate-600 dark:text-slate-400" />
                    <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                      Local Storage Cache
                    </h3>
                  </div>
                  <button
                    onClick={handleClearCache}
                    className="text-xs font-bold text-rose-600 dark:text-rose-400 hover:text-rose-700 dark:hover:text-rose-300 transition cursor-pointer"
                  >
                    Clear Local Cache
                  </button>
                </div>

                <div className="grid grid-cols-3 gap-2 pt-1 text-center">
                  <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                    <span className="text-[10px] text-slate-400 font-bold uppercase block">Logged Meals</span>
                    <span className="text-base font-black text-slate-900 dark:text-white">{loggedMeals.length}</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                    <span className="text-[10px] text-slate-400 font-bold uppercase block">Saved Menus</span>
                    <span className="text-base font-black text-slate-900 dark:text-white">{savedMenus.length}</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700">
                    <span className="text-[10px] text-slate-400 font-bold uppercase block">Staged Plate</span>
                    <span className="text-base font-black text-slate-900 dark:text-white">{plate.length}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: PREFERENCES & DINING MODE */}
          {activeTab === 'preferences' && (
            <div className="space-y-6">
              {/* Theme Preference */}
              <div className="p-5 rounded-2xl bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 space-y-3">
                <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                  Interface Appearance
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    onClick={() => {
                      if (isDark) toggleTheme();
                    }}
                    className={`p-3.5 rounded-2xl border text-xs font-bold flex items-center justify-center gap-2.5 transition cursor-pointer ${
                      !isDark
                        ? 'border-emerald-600 bg-emerald-50/80 text-emerald-900 shadow-xs'
                        : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    <Sun className="w-4 h-4 text-amber-500" />
                    <span>Light Theme</span>
                  </button>

                  <button
                    onClick={() => {
                      if (!isDark) toggleTheme();
                    }}
                    className={`p-3.5 rounded-2xl border text-xs font-bold flex items-center justify-center gap-2.5 transition cursor-pointer ${
                      isDark
                        ? 'border-emerald-500 bg-emerald-950/60 text-emerald-300 shadow-xs'
                        : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-600 dark:text-slate-400'
                    }`}
                  >
                    <Moon className="w-4 h-4 text-indigo-400" />
                    <span>Dark Theme</span>
                  </button>
                </div>
              </div>

              {/* Dining Mode Strategy */}
              <div className="p-5 rounded-2xl bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 space-y-3">
                <div className="flex items-center gap-2">
                  <UtensilsCrossed className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Dining Strategy Mode
                  </h3>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Select how strictly the 3-tier recommendation algorithm weights caloric deficits during restaurant visits.
                </p>

                <div className="space-y-2.5 pt-1">
                  <button
                    onClick={() => handleSelectDiningMode('strict')}
                    className={`w-full p-4 rounded-2xl border text-left transition cursor-pointer flex items-start gap-3 ${
                      diningMode === 'strict'
                        ? 'border-emerald-600 bg-emerald-50/70 dark:bg-emerald-950/40 text-emerald-950 dark:text-emerald-200 shadow-xs'
                        : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded-full mt-0.5 border flex items-center justify-center shrink-0 ${
                        diningMode === 'strict'
                          ? 'border-emerald-600 bg-emerald-600 text-white'
                          : 'border-slate-400 dark:border-slate-600'
                      }`}
                    >
                      {diningMode === 'strict' && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                    </div>
                    <div>
                      <div className="text-xs font-bold flex items-center gap-2">
                        <span>Strict Clinical Target (Recommended)</span>
                        <span className="px-1.5 py-0.2 rounded text-[10px] bg-emerald-200/60 dark:bg-emerald-800/60 text-emerald-800 dark:text-emerald-200 font-extrabold">
                          Default
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        Strictly adheres to exact calculated TDEE caloric deficits, sodium ceilings, and glycemic guardrails.
                      </p>
                    </div>
                  </button>

                  <button
                    onClick={() => handleSelectDiningMode('flexible')}
                    className={`w-full p-4 rounded-2xl border text-left transition cursor-pointer flex items-start gap-3 ${
                      diningMode === 'flexible'
                        ? 'border-emerald-600 bg-emerald-50/70 dark:bg-emerald-950/40 text-emerald-950 dark:text-emerald-200 shadow-xs'
                        : 'border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 text-slate-700 dark:text-slate-300'
                    }`}
                  >
                    <div
                      className={`w-4 h-4 rounded-full mt-0.5 border flex items-center justify-center shrink-0 ${
                        diningMode === 'flexible'
                          ? 'border-emerald-600 bg-emerald-600 text-white'
                          : 'border-slate-400 dark:border-slate-600'
                      }`}
                    >
                      {diningMode === 'flexible' && <Check className="w-2.5 h-2.5 stroke-[3]" />}
                    </div>
                    <div>
                      <div className="text-xs font-bold">Flexible Social Dining Mode</div>
                      <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                        Relaxes caloric deficit by 15% to offer more restaurant dish options while retaining 100% allergen & sodium ceiling safety.
                      </p>
                    </div>
                  </button>
                </div>
              </div>

              {/* Backend API Endpoint */}
              <div className="p-5 rounded-2xl bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 space-y-3">
                <div className="flex items-center gap-2">
                  <Cloud className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                  <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    Backend API Endpoint
                  </h3>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Configure the FastAPI server endpoint (e.g. for GitHub Pages, remote hosting, or local network dev).
                </p>
                <div className="flex gap-2 pt-1">
                  <input
                    type="url"
                    value={apiUrl}
                    onChange={(e) => {
                      setApiUrl(e.target.value);
                      setSavedApiSuccess(false);
                    }}
                    placeholder="http://127.0.0.1:8000"
                    className="flex-1 px-3.5 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  />
                  <button
                    onClick={() => {
                      setCustomApiUrl(apiUrl);
                      setSavedApiSuccess(true);
                      setTimeout(() => setSavedApiSuccess(false), 2500);
                    }}
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition cursor-pointer"
                  >
                    {savedApiSuccess ? 'Saved!' : 'Save'}
                  </button>
                  {apiUrl && (
                    <button
                      onClick={() => {
                        setApiUrl('');
                        setCustomApiUrl('');
                        setSavedApiSuccess(true);
                        setTimeout(() => setSavedApiSuccess(false), 2500);
                      }}
                      className="px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-semibold transition cursor-pointer"
                    >
                      Reset
                    </button>
                  )}
                </div>
                <p className="text-[11px] text-slate-400">
                  Active endpoint: <code className="text-emerald-600 dark:text-emerald-400 font-mono">{getApiBaseUrl() || 'Default (127.0.0.1:8000)'}</code>
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-900/90 flex justify-end">
          <button
            onClick={onClose}
            className="px-5 py-2 rounded-xl bg-slate-900 dark:bg-slate-800 hover:bg-slate-800 dark:hover:bg-slate-700 text-white text-xs font-bold transition cursor-pointer shadow-xs"
          >
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
