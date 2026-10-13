import React, { useState } from 'react';
import { Mail, Lock, KeyRound, CheckCircle2, AlertCircle, ArrowRight, ShieldCheck } from 'lucide-react';
import { requestEmailChange, confirmEmailChange } from '../../api';
import { useAuth } from '../../context/AuthContext';

export default function ChangeEmailPanel() {
  const { user, refreshUser } = useAuth();
  const [step, setStep] = useState(1); // 1: request change, 2: enter confirmation code
  const [newEmail, setNewEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState('');

  const handleRequest = async (e) => {
    e.preventDefault();
    if (!newEmail.trim() || !password) {
      setError('Please fill in both your new email address and current password.');
      return;
    }

    if (newEmail.trim().toLowerCase() === user?.email?.toLowerCase()) {
      setError('The new email address must be different from your current email.');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      await requestEmailChange(newEmail.trim(), password);
      setStep(2);
      setSuccess(`A 6-digit confirmation code has been dispatched to ${newEmail.trim()}.`);
    } catch (err) {
      setError(err.message || 'Failed to request email change.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (e) => {
    e.preventDefault();
    if (!code.trim() || code.trim().length !== 6) {
      setError('Please enter the full 6-digit confirmation code.');
      return;
    }

    setError(null);
    setLoading(true);

    try {
      const res = await confirmEmailChange(code.trim());
      setSuccess(res?.message || 'Email address successfully updated!');
      await refreshUser();
      setTimeout(() => {
        setStep(1);
        setNewEmail('');
        setPassword('');
        setCode('');
        setSuccess('');
      }, 4000);
    } catch (err) {
      setError(err.message || 'Failed to confirm email change. Please check your code.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-5 rounded-2xl bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 space-y-4">
      <div className="flex items-center gap-2">
        <Mail className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
        <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
          Primary Email Address
        </h3>
      </div>

      <p className="text-xs text-slate-500 dark:text-slate-400">
        Current email: <strong className="text-slate-800 dark:text-slate-200">{user?.email}</strong>.
        Updating your email requires verifying your new address with a secure 6-digit code.
      </p>

      {success && (
        <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-semibold flex items-center gap-2 animate-in fade-in">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{success}</span>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {step === 1 ? (
        <form onSubmit={handleRequest} className="space-y-3 pt-1">
          <div>
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">
              New Email Address
            </label>
            <div className="relative">
              <Mail className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type="email"
                required
                value={newEmail}
                onChange={(e) => setNewEmail(e.target.value)}
                placeholder="new-address@example.com"
                className="w-full pl-9 pr-3 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-emerald-500"
              />
            </div>
          </div>

          <div>
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">
              Current Password (for authorization)
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-emerald-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-xs transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2 mt-2"
          >
            <span>{loading ? 'Sending Code...' : 'Request Email Update Code'}</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </form>
      ) : (
        <form onSubmit={handleConfirm} className="space-y-3 pt-1">
          <div>
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">
              6-Digit Confirmation Code
            </label>
            <div className="relative">
              <KeyRound className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type="text"
                maxLength={6}
                required
                autoFocus
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                placeholder="123456"
                className="w-full pl-9 pr-3 py-2 rounded-xl text-xs font-mono font-bold tracking-widest bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-emerald-500"
              />
            </div>
          </div>

          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => {
                setStep(1);
                setError(null);
              }}
              className="px-4 py-2 rounded-xl text-xs font-bold border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading || code.length !== 6}
              className="flex-1 py-2 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-xs transition cursor-pointer disabled:opacity-50"
            >
              {loading ? 'Confirming...' : 'Confirm & Apply Email Change'}
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
