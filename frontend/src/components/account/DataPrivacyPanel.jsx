import React, { useState } from 'react';
import {
  Download,
  Trash2,
  Lock,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  FileCode,
  ShieldAlert,
  Clock,
} from 'lucide-react';
import { exportAccountData, scheduleAccountDeletion } from '../../api';
import { useAuth } from '../../context/AuthContext';

export default function DataPrivacyPanel() {
  const { user, logout } = useAuth();

  // Export State
  const [exportPassword, setExportPassword] = useState('');
  const [exportLoading, setExportLoading] = useState(false);
  const [exportError, setExportError] = useState(null);
  const [exportSuccess, setExportSuccess] = useState(false);

  // Deletion State
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteLoading, setDeleteLoading] = useState(false);
  const [deleteError, setDeleteError] = useState(null);

  const handleExportData = async (e) => {
    e.preventDefault();
    if (!exportPassword) {
      setExportError('Please enter your password to authorize personal data export.');
      return;
    }

    setExportError(null);
    setExportLoading(true);

    try {
      const data = await exportAccountData(exportPassword);
      // Trigger download
      const jsonStr = JSON.stringify(data, null, 2);
      const blob = new Blob([jsonStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `nutrimenu_gdpr_export_${new Date().toISOString().split('T')[0]}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);

      setExportSuccess(true);
      setExportPassword('');
      setTimeout(() => setExportSuccess(false), 4000);
    } catch (err) {
      setExportError(err.message || 'Failed to export account data. Please check your password.');
    } finally {
      setExportLoading(false);
    }
  };

  const handleScheduleDeletion = async (e) => {
    e.preventDefault();
    if (!deletePassword) {
      setDeleteError('Please enter your password to confirm account deletion.');
      return;
    }

    setDeleteError(null);
    setDeleteLoading(true);

    try {
      const res = await scheduleAccountDeletion(deletePassword);
      alert(res?.message || 'Your account has been scheduled for deletion with a 14-day grace period.');
      logout();
    } catch (err) {
      setDeleteError(err.message || 'Failed to schedule account deletion.');
      setDeleteLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Card 1: GDPR Personal Data Export */}
      <div className="p-5 rounded-2xl bg-white dark:bg-slate-800/40 border border-slate-200 dark:border-slate-700 space-y-4">
        <div className="flex items-center gap-2">
          <FileCode className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
          <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider">
            GDPR / CCPA Full Data Archive
          </h3>
        </div>

        <p className="text-xs text-slate-500 dark:text-slate-400">
          Under privacy regulations (GDPR Article 20 / CCPA), you have the right to receive a machine-readable JSON archive of all your personal data, biometrics, saved menus, logged meals, and security audit logs.
        </p>

        {exportSuccess && (
          <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300 text-xs font-semibold flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>GDPR export downloaded successfully.</span>
          </div>
        )}

        {exportError && (
          <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-800 text-rose-700 dark:text-rose-300 text-xs font-semibold flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{exportError}</span>
          </div>
        )}

        <form onSubmit={handleExportData} className="space-y-3 pt-1">
          <div>
            <label className="text-xs font-bold text-slate-700 dark:text-slate-300 block mb-1">
              Confirm Account Password
            </label>
            <div className="relative">
              <Lock className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
              <input
                type="password"
                required
                value={exportPassword}
                onChange={(e) => setExportPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full pl-9 pr-3 py-2 rounded-xl text-xs bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 text-slate-900 dark:text-white focus:outline-emerald-500"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={exportLoading}
            className="w-full py-2.5 px-4 rounded-xl bg-slate-900 dark:bg-slate-700 hover:bg-slate-800 text-white font-bold text-xs shadow-xs transition cursor-pointer disabled:opacity-50 flex items-center justify-center gap-2"
          >
            <Download className="w-4 h-4" />
            <span>{exportLoading ? 'Compiling Archive...' : 'Download JSON Personal Data Archive'}</span>
          </button>
        </form>
      </div>

      {/* Card 2: Account Deletion (14-day Grace Period) */}
      <div className="p-5 rounded-2xl bg-rose-50/50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/60 space-y-4">
        <div className="flex items-center gap-2">
          <Trash2 className="w-4 h-4 text-rose-600 dark:text-rose-400" />
          <h3 className="text-xs font-bold text-rose-900 dark:text-rose-300 uppercase tracking-wider">
            Delete Account (14-Day Grace Period)
          </h3>
        </div>

        <p className="text-xs text-rose-700 dark:text-rose-400">
          Scheduling account deletion initiates a <strong>14-day grace window</strong>. Your sessions will be signed out immediately. You can cancel this deletion anytime within 14 days by signing back in. After 14 days, all personal data, clinical profiles, meals, and menus will be permanently wiped.
        </p>

        {deleteError && (
          <div className="p-3 rounded-xl bg-rose-100 dark:bg-rose-950 border border-rose-300 dark:border-rose-800 text-rose-800 dark:text-rose-200 text-xs font-semibold flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{deleteError}</span>
          </div>
        )}

        {!showDeleteModal ? (
          <button
            type="button"
            onClick={() => setShowDeleteModal(true)}
            className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs shadow-xs transition cursor-pointer"
          >
            Request Account Deletion
          </button>
        ) : (
          <form onSubmit={handleScheduleDeletion} className="space-y-3 pt-2">
            <div>
              <label className="text-xs font-bold text-rose-900 dark:text-rose-300 block mb-1">
                Enter Password to Confirm Deletion Request
              </label>
              <div className="relative">
                <Lock className="w-4 h-4 text-rose-400 absolute left-3 top-2.5 pointer-events-none" />
                <input
                  type="password"
                  required
                  autoFocus
                  value={deletePassword}
                  onChange={(e) => setDeletePassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full pl-9 pr-3 py-2 rounded-xl text-xs bg-white dark:bg-slate-900 border border-rose-300 dark:border-rose-800 text-slate-900 dark:text-white focus:outline-rose-500"
                />
              </div>
            </div>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => {
                  setShowDeleteModal(false);
                  setDeletePassword('');
                  setDeleteError(null);
                }}
                className="px-4 py-2 rounded-xl text-xs font-bold border border-slate-300 dark:border-slate-700 text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 transition cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={deleteLoading}
                className="flex-1 py-2 px-4 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-bold text-xs shadow-xs transition cursor-pointer disabled:opacity-50"
              >
                {deleteLoading ? 'Scheduling...' : 'Schedule 14-Day Deletion & Sign Out'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
