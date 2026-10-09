import React, { useState, useEffect } from 'react';
import { Mail, KeyRound, Lock, CheckCircle2, AlertCircle, ArrowRight, X, Clock, RefreshCw } from 'lucide-react';
import { requestForgotPassword, submitPasswordReset } from '../api';

export default function ForgotPasswordModal({ isOpen, onClose, initialEmail = '' }) {
  const [step, setStep] = useState(1); // 1: Request OTP, 2: Enter OTP & New Password, 3: Success
  const [email, setEmail] = useState(initialEmail);
  const [otpCode, setOtpCode] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [devCode, setDevCode] = useState('');
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [countdown, setCountdown] = useState(600); // 10 minutes in seconds
  const [resendCooldown, setResendCooldown] = useState(0);

  useEffect(() => {
    if (initialEmail) {
      setEmail(initialEmail);
    }
  }, [initialEmail]);

  useEffect(() => {
    if (!isOpen) {
      // Reset state on close
      setStep(1);
      setOtpCode('');
      setNewPassword('');
      setConfirmPassword('');
      setDevCode('');
      setError(null);
      setLoading(false);
      return;
    }
  }, [isOpen]);

  // 10-minute OTP countdown timer during Step 2
  useEffect(() => {
    let timer;
    if (isOpen && step === 2 && countdown > 0) {
      timer = setInterval(() => {
        setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [isOpen, step, countdown]);

  // Resend cooldown timer
  useEffect(() => {
    let timer;
    if (resendCooldown > 0) {
      timer = setInterval(() => {
        setResendCooldown((prev) => (prev > 0 ? prev - 1 : 0));
      }, 1000);
    }
    return () => clearInterval(timer);
  }, [resendCooldown]);

  if (!isOpen) return null;

  const handleRequestOtp = async (e) => {
    e?.preventDefault();
    if (!email.trim()) {
      setError('Please enter your email address.');
      return;
    }

    setError(null);
    setLoading(true);
    try {
      const res = await requestForgotPassword(email.trim());
      if (res?.dev_code) {
        setDevCode(res.dev_code);
      }
      setStep(2);
      setCountdown(600);
      setResendCooldown(30);
    } catch (err) {
      setError(err.message || 'Failed to dispatch reset code.');
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (resendCooldown > 0 || loading) return;
    setError(null);
    setLoading(true);
    try {
      const res = await requestForgotPassword(email.trim());
      if (res?.dev_code) {
        setDevCode(res.dev_code);
      }
      setCountdown(600);
      setResendCooldown(45);
    } catch (err) {
      setError(err.message || 'Failed to resend reset code.');
    } finally {
      setLoading(false);
    }
  };

  const handleResetPassword = async (e) => {
    e.preventDefault();
    setError(null);

    if (!otpCode.trim() || otpCode.trim().length !== 6) {
      setError('Please enter the full 6-digit verification code.');
      return;
    }

    if (newPassword.length < 8) {
      setError('New password must be at least 8 characters long.');
      return;
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      await submitPasswordReset(email.trim(), otpCode.trim(), newPassword);
      setStep(3);
    } catch (err) {
      setError(err.message || 'Failed to reset password. Please check your code or try again.');
    } finally {
      setLoading(false);
    }
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs < 10 ? '0' : ''}${secs}`;
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in duration-200">
      <div 
        className="relative w-full max-w-md bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-2xl p-6 sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-2 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition"
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>

        {step === 1 && (
          <div>
            <div className="w-12 h-12 rounded-2xl bg-amber-500/10 dark:bg-amber-500/20 text-amber-600 dark:text-amber-400 flex items-center justify-center mb-4">
              <KeyRound className="w-6 h-6" />
            </div>
            <h3 className="text-xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
              Reset Your Password
            </h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Enter your account's email address. We'll dispatch a cryptographic 6-digit verification code.
            </p>

            {error && (
              <div className="mt-4 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <form onSubmit={handleRequestOtp} className="mt-5 space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Account Email
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="name@example.com"
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-medium focus:outline-emerald-500 bg-slate-50/50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                <span>{loading ? 'Sending Code...' : 'Send Verification Code'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          </div>
        )}

        {step === 2 && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 rounded-2xl bg-emerald-500/10 dark:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
                <Lock className="w-6 h-6" />
              </div>
              <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-[11px] font-bold text-slate-600 dark:text-slate-300">
                <Clock className="w-3.5 h-3.5 text-amber-500" />
                <span>Expires in {formatTime(countdown)}</span>
              </div>
            </div>

            <h3 className="text-xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
              Enter 6-Digit Code
            </h3>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Code dispatched to <strong className="text-slate-800 dark:text-slate-200">{email}</strong>.
            </p>

            {error && (
              <div className="mt-4 p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold flex items-center gap-2">
                <AlertCircle className="w-4 h-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {devCode && (
              <div className="mt-4 p-3.5 rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 text-xs flex items-center justify-between gap-3 animate-in fade-in">
                <div>
                  <span className="font-bold text-amber-900 dark:text-amber-200 block">Development Reset Code</span>
                  <span className="text-[11px] text-amber-700 dark:text-amber-400">
                    Code: <strong className="font-mono text-xs tracking-widest text-amber-950 dark:text-amber-100">{devCode}</strong> (since SMTP email is not configured)
                  </span>
                </div>
                <button
                  type="button"
                  onClick={() => setOtpCode(devCode)}
                  className="px-3 py-1.5 rounded-xl bg-amber-600 hover:bg-amber-700 text-white font-bold text-[11px] transition cursor-pointer shadow-xs shrink-0"
                >
                  Auto-Fill
                </button>
              </div>
            )}

            <form onSubmit={handleResetPassword} className="mt-5 space-y-4">
              <div>
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  6-Digit OTP Code
                </label>
                <input
                  type="text"
                  maxLength={6}
                  required
                  autoFocus
                  value={otpCode}
                  onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ''))}
                  placeholder="123456"
                  className="w-full text-center tracking-[0.5em] text-lg font-mono font-black py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 focus:outline-emerald-500 bg-slate-50/50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:tracking-normal placeholder:font-sans placeholder:text-sm"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  New Password (min. 8 characters)
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="password"
                    required
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-medium focus:outline-emerald-500 bg-slate-50/50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">
                  Confirm New Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 text-slate-400 dark:text-slate-500 absolute left-3 top-3 pointer-events-none" />
                  <input
                    type="password"
                    required
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full pl-9 pr-3 py-2.5 rounded-xl border border-slate-200 dark:border-slate-700 text-xs font-medium focus:outline-emerald-500 bg-slate-50/50 dark:bg-slate-800 text-slate-900 dark:text-slate-100 placeholder:text-slate-400 dark:placeholder:text-slate-500"
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <button
                  type="button"
                  onClick={handleResendOtp}
                  disabled={resendCooldown > 0 || loading}
                  className="inline-flex items-center gap-1.5 font-bold text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 disabled:opacity-50 cursor-pointer disabled:cursor-not-allowed"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                  <span>{resendCooldown > 0 ? `Resend code (${resendCooldown}s)` : 'Resend code'}</span>
                </button>
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  className="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300 font-medium"
                >
                  Change email
                </button>
              </div>

              <button
                type="submit"
                disabled={loading || countdown === 0}
                className="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50 mt-2"
              >
                <span>{loading ? 'Updating Password...' : 'Reset Password'}</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          </div>
        )}

        {step === 3 && (
          <div className="text-center py-4">
            <div className="w-16 h-16 rounded-3xl bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 mx-auto flex items-center justify-center mb-4">
              <CheckCircle2 className="w-8 h-8" />
            </div>
            <h3 className="text-xl font-black text-slate-900 dark:text-slate-100 tracking-tight">
              Password Reset Successfully!
            </h3>
            <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              Your password has been securely updated and encrypted with industry-standard bcrypt. You can now log in to your account.
            </p>

            <button
              type="button"
              onClick={onClose}
              className="mt-6 w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md transition cursor-pointer"
            >
              Back to Sign In
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
