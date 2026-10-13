import React, { useState, useEffect } from 'react';
import {
  Laptop,
  Smartphone,
  Globe,
  Trash2,
  ShieldAlert,
  ShieldCheck,
  RefreshCw,
  Clock,
  MapPin,
  CheckCircle2,
  AlertCircle,
} from 'lucide-react';
import { fetchActiveSessions, revokeSingleSession, revokeAllOtherSessions } from '../../api';

export default function SessionsPanel() {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionSuccess, setActionSuccess] = useState('');
  const [revokingId, setRevokingId] = useState(null);
  const [revokingAll, setRevokingAll] = useState(false);

  const loadSessions = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchActiveSessions();
      setSessions(data || []);
    } catch (err) {
      setError(err.message || 'Failed to load active sessions.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadSessions();
  }, []);

  const handleRevokeSingle = async (sessionId) => {
    setRevokingId(sessionId);
    setError(null);
    setActionSuccess('');
    try {
      await revokeSingleSession(sessionId);
      setActionSuccess('Session revoked successfully.');
      await loadSessions();
      setTimeout(() => setActionSuccess(''), 3000);
    } catch (err) {
      setError(err.message || 'Failed to revoke session.');
    } finally {
      setRevokingId(null);
    }
  };

  const handleRevokeAllOther = async () => {
    if (!window.confirm('Are you sure you want to log out of all other devices?')) return;
    setRevokingAll(true);
    setError(null);
    setActionSuccess('');
    try {
      const res = await revokeAllOtherSessions();
      setActionSuccess(res?.message || 'All other sessions have been terminated.');
      await loadSessions();
      setTimeout(() => setActionSuccess(''), 3500);
    } catch (err) {
      setError(err.message || 'Failed to revoke other sessions.');
    } finally {
      setRevokingAll(false);
    }
  };

  const getDeviceIcon = (ua) => {
    const uaLower = (ua || '').toLowerCase();
    if (uaLower.includes('mobile') || uaLower.includes('android') || uaLower.includes('iphone')) {
      return <Smartphone className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />;
    }
    return <Laptop className="w-4 h-4 text-indigo-600 dark:text-indigo-400" />;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return 'Just now';
    try {
      const d = new Date(dateStr);
      return d.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
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
            Active Logged-in Devices
          </h3>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Manage browser sessions across your desktop and mobile devices.
          </p>
        </div>

        <button
          type="button"
          onClick={loadSessions}
          disabled={loading}
          className="p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
          title="Refresh active sessions"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {actionSuccess && (
        <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-semibold flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span>{actionSuccess}</span>
        </div>
      )}

      {error && (
        <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold flex items-center gap-2">
          <AlertCircle className="w-4 h-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading && sessions.length === 0 ? (
        <div className="py-8 text-center text-xs text-slate-400">Loading active sessions...</div>
      ) : (
        <div className="space-y-2.5">
          {sessions.map((sess) => (
            <div
              key={sess.id}
              className={`p-4 rounded-2xl border transition flex items-center justify-between gap-4 ${
                sess.is_current
                  ? 'border-emerald-500/60 bg-emerald-50/50 dark:bg-emerald-950/20'
                  : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800/40'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center shrink-0 mt-0.5">
                  {getDeviceIcon(sess.user_agent)}
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-bold text-slate-900 dark:text-white truncate max-w-[220px] sm:max-w-xs">
                      {sess.device_name || 'Web Browser'}
                    </span>
                    {sess.is_current && (
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider bg-emerald-600 text-white shadow-xs">
                        Current Device
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 mt-1 text-[11px] text-slate-500 dark:text-slate-400">
                    <span className="flex items-center gap-1">
                      <Globe className="w-3 h-3" />
                      {sess.ip_address || '127.0.0.1'}
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      Active {formatDate(sess.last_active_at)}
                    </span>
                  </div>
                </div>
              </div>

              {!sess.is_current && (
                <button
                  type="button"
                  onClick={() => handleRevokeSingle(sess.id)}
                  disabled={revokingId === sess.id}
                  className="px-3 py-1.5 rounded-xl text-xs font-bold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 border border-rose-200 dark:border-rose-900 transition cursor-pointer disabled:opacity-50 shrink-0"
                >
                  {revokingId === sess.id ? 'Terminating...' : 'Sign Out'}
                </button>
              )}
            </div>
          ))}

          {sessions.filter((s) => !s.is_current).length > 0 && (
            <div className="pt-2">
              <button
                type="button"
                onClick={handleRevokeAllOther}
                disabled={revokingAll}
                className="w-full py-2.5 px-4 rounded-xl text-xs font-bold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 border border-dashed border-rose-300 dark:border-rose-800 transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2"
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span>{revokingAll ? 'Terminating sessions...' : 'Sign Out of All Other Devices'}</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
