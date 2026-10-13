import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  ShieldAlert,
  Key,
  UserCheck,
  LogOut,
  Clock,
  Globe,
  RefreshCw,
  AlertCircle,
  FileText,
} from 'lucide-react';
import { fetchAccountActivity } from '../../api';

export default function ActivityPanel() {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadActivity = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchAccountActivity();
      setLogs(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load security activity.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadActivity();
  }, []);

  const getEventBadge = (event_type, status) => {
    const isSuccess = status === 'success';
    const isFailure = status === 'failure' || status === 'blocked';

    if (isFailure) {
      return (
        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 border border-rose-300 dark:border-rose-800">
          {status}
        </span>
      );
    }
    return (
      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-300 dark:border-emerald-800">
        {status}
      </span>
    );
  };

  const getEventTitle = (event_type) => {
    const map = {
      'auth.login_success': 'Successful Sign-in',
      'auth.login_failed': 'Failed Login Attempt',
      'auth.logout_success': 'Session Signed Out',
      'auth.logout_all_success': 'All Sessions Revoked',
      'auth.session_revoked': 'Remote Device Disconnected',
      'auth.token_refreshed': 'Session Token Rotated',
      'auth.token_reuse_blocked': 'Token Reuse Intercepted',
      'auth.password_changed': 'Password Changed',
      'auth.password_reset': 'Password Reset via OTP',
      'auth.email_verified': 'Email Verified',
      'auth.email_change_requested': 'Email Change Requested',
      'auth.email_changed': 'Email Address Updated',
      'auth.mfa_enabled': 'Two-Factor Auth Enabled',
      'auth.mfa_disabled': 'Two-Factor Auth Disabled',
      'account.gdpr_export': 'GDPR Personal Data Exported',
      'account.deletion_requested': 'Account Deletion Scheduled',
      'account.deletion_cancelled': 'Account Deletion Cancelled',
    };
    return map[event_type] || event_type;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Recently';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
            Security Audit Trail
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Cryptographic ledger of authentication and account security events.
          </p>
        </div>

        <button
          type="button"
          onClick={loadActivity}
          disabled={loading}
          className="p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
          title="Refresh activity logs"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading && logs.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-400">Loading security audit events...</div>
      ) : logs.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-400">No security events recorded yet.</div>
      ) : (
        <div className="space-y-2 max-h-[350px] overflow-y-auto pr-1">
          {logs.map((log) => (
            <div
              key={log.id}
              className="p-3.5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-800/40 text-xs flex items-center justify-between gap-3"
            >
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-slate-900 dark:text-white">
                    {getEventTitle(log.event_type)}
                  </span>
                  {getEventBadge(log.event_type, log.status)}
                </div>
                <div className="flex items-center gap-3 text-[11px] text-slate-500 dark:text-slate-400">
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDate(log.created_at)}
                  </span>
                  <span>•</span>
                  <span className="flex items-center gap-1">
                    <Globe className="w-3 h-3" />
                    {log.ip_address || '127.0.0.1'}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
