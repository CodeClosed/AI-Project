import React from 'react';
import { Link } from 'react-router-dom';
import { Salad, Home, ArrowLeft } from 'lucide-react';

export default function NotFoundPage() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
      <div className="w-16 h-16 rounded-3xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center mb-6 border border-emerald-100 dark:border-emerald-800">
        <Salad className="w-8 h-8" />
      </div>
      <h1 className="text-4xl font-black text-slate-900 dark:text-slate-100 tracking-tight">404 - Page Not Found</h1>
      <p className="mt-2 text-sm text-slate-500 dark:text-slate-400 max-w-sm">
        The page you are looking for doesn't exist or has been moved.
      </p>
      <div className="mt-6 flex items-center gap-3">
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md transition"
        >
          <Home className="w-4 h-4" />
          <span>Back to Dashboard</span>
        </Link>
      </div>
    </div>
  );
}
