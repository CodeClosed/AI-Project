import React, { useState, useRef, useEffect } from 'react';
import { Outlet, NavLink, Link, useNavigate } from 'react-router-dom';
import {
  Salad,
  Calendar,
  Utensils,
  User,
  LogIn,
  LogOut,
  Cloud,
  ShieldCheck,
  LayoutDashboard,
  HeartPulse,
  Sun,
  Moon,
  AlertCircle,
  X,
  ChevronDown,
  Sparkles,
  Settings,
  Scale,
  Download,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { useNutrition } from '../context/NutritionContext';
import SettingsModal from './SettingsModal';
import { exportMealsToCsv } from '../utils/exportUtils';

export default function Layout() {
  const { user, isAuthenticated, logout, sessionExpiredNotice, setSessionExpiredNotice } = useAuth();
  const { toggleTheme, isDark } = useTheme();
  const {
    profile,
    userMatrix,
    plate,
    dishes,
    loggedMeals,
  } = useNutrition();

  const navigate = useNavigate();
  const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const userMenuRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setIsUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const dietLabels = (profile.dietary_preferences || []).join(', ');
  const allergyLabels = (profile.allergies || []).join(', ');

  const navLinkClass = ({ isActive }) =>
    `flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
      isActive
        ? 'bg-white dark:bg-slate-900 text-slate-900 dark:text-white shadow-xs border border-slate-200/80 dark:border-slate-700'
        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-200/50 dark:hover:bg-slate-800'
    }`;

  return (
    <div className="min-h-screen bg-[#F8FAFC] dark:bg-slate-950 text-slate-900 dark:text-slate-100 flex flex-col justify-between selection:bg-emerald-500 selection:text-white font-sans transition-colors duration-200">
      <header className="border-b border-slate-200/90 dark:border-slate-800 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md sticky top-0 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Logo & Brand */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform">
              <Salad className="w-5 h-5 text-white font-bold" />
            </div>
            <div>
              <span className="font-black text-lg text-slate-900 dark:text-white tracking-tight flex items-center gap-1.5">
                NutriMenu <span className="text-emerald-600 dark:text-emerald-400">AI</span>
              </span>
              <span className="text-[10px] text-slate-500 dark:text-slate-400 block leading-none font-semibold">
                Clinical 3-Tier Food Recommendation Engine
              </span>
            </div>
          </Link>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1 p-1 bg-slate-100/90 dark:bg-slate-800/90 rounded-full border border-slate-200 dark:border-slate-700 shadow-2xs">
            <NavLink to="/" end className={navLinkClass}>
              <LayoutDashboard className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Dashboard</span>
            </NavLink>

            <NavLink to="/menu" className={navLinkClass}>
              <Salad className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Menu Scanner</span>
              {dishes.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-emerald-100 dark:bg-emerald-900/80 text-emerald-800 dark:text-emerald-200 text-[10px] font-black">
                  {dishes.length}
                </span>
              )}
            </NavLink>

            <NavLink to="/plate" className={navLinkClass}>
              <Utensils className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>My Plate</span>
              {plate.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-emerald-600 text-white text-[10px] font-black">
                  {plate.length}
                </span>
              )}
            </NavLink>

            <NavLink to="/calendar" className={navLinkClass}>
              <Calendar className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Meal Calendar</span>
              {loggedMeals.length > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-emerald-100 dark:bg-emerald-900/80 text-emerald-800 dark:text-emerald-200 text-[10px] font-black">
                  {loggedMeals.length}
                </span>
              )}
            </NavLink>

            <NavLink to="/profile" className={navLinkClass}>
              <HeartPulse className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span>Health Profile</span>
            </NavLink>
          </nav>

          {/* Right Action Bar */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Dark / Light Mode Switch */}
            <button
              onClick={toggleTheme}
              title={isDark ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
              className="p-2 rounded-full bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 transition cursor-pointer border border-slate-200 dark:border-slate-700 shadow-2xs"
            >
              {isDark ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-slate-600" />}
            </button>

            {/* User Profile Popover Dropdown (Eliminates Duplicate AccountDrawerModal) */}
            <div className="relative" ref={userMenuRef}>
              <button
                onClick={() => setIsUserMenuOpen(!isUserMenuOpen)}
                className="flex items-center gap-2 sm:gap-2.5 px-2 sm:px-3 py-1.5 rounded-full bg-slate-50 dark:bg-slate-800/90 border border-slate-200 dark:border-slate-700 hover:border-emerald-400 dark:hover:border-emerald-500 hover:bg-slate-100/80 dark:hover:bg-slate-800 transition-all text-xs font-semibold text-slate-800 dark:text-slate-200 shadow-xs cursor-pointer"
              >
                <div className="relative w-7 h-7 rounded-full bg-slate-900 dark:bg-slate-700 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                  <User className="w-3.5 h-3.5" />
                  <span
                    className={`absolute bottom-0 right-0 w-2 h-2 border-2 border-white dark:border-slate-900 rounded-full ${
                      isAuthenticated ? 'bg-emerald-500' : 'bg-amber-400'
                    }`}
                  />
                </div>
                <div className="text-left leading-tight hidden lg:block">
                  <div className="font-bold text-slate-900 dark:text-white flex items-center gap-1.5">
                    <span>{isAuthenticated ? (user?.email?.split('@')[0] || 'My Profile') : (dietLabels || 'Standard')}</span>
                  </div>
                  <div className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
                    {userMatrix?.metabolic_targets
                      ? `${Math.round(userMatrix.metabolic_targets.target_calories_kcal)} kcal`
                      : 'Clinical Matrix'}
                  </div>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform duration-200 ${isUserMenuOpen ? 'rotate-180' : ''}`} />
              </button>

              {/* Dropdown Menu */}
              {isUserMenuOpen && (
                <div className="absolute right-0 mt-2 w-72 bg-white dark:bg-slate-900 rounded-2xl shadow-xl border border-slate-200 dark:border-slate-800 py-2 z-50 animate-in fade-in zoom-in-95 duration-150">
                  {/* Account Header Info */}
                  <div className="px-4 py-3 border-b border-slate-100 dark:border-slate-800">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-bold text-xs text-slate-900 dark:text-white truncate">
                        {isAuthenticated ? user?.email : 'Guest Session'}
                      </span>
                      {isAuthenticated ? (
                        <span className="px-1.5 py-0.5 rounded-md bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-300 text-[10px] font-extrabold flex items-center gap-0.5">
                          <Cloud className="w-2.5 h-2.5" /> Synced
                        </span>
                      ) : (
                        <span className="px-1.5 py-0.5 rounded-md bg-amber-100 dark:bg-amber-900/60 text-amber-800 dark:text-amber-300 text-[10px] font-extrabold">
                          Local Only
                        </span>
                      )}
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400">
                      {userMatrix?.metabolic_targets
                        ? `Target: ${Math.round(userMatrix.metabolic_targets.target_calories_kcal)} kcal/day • ${userMatrix.metabolic_targets.target_protein_g}g protein`
                        : 'Biometric parameters configured'}
                    </p>
                  </div>

                  {/* User Utility Actions */}
                  <div className="py-1.5 text-xs text-slate-700 dark:text-slate-200">
                    <button
                      onClick={() => {
                        setIsUserMenuOpen(false);
                        setIsSettingsOpen(true);
                      }}
                      className="w-full text-left flex items-center gap-2.5 px-4 py-2 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer text-slate-800 dark:text-slate-200"
                    >
                      <div className="w-7 h-7 rounded-lg bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 flex items-center justify-center shrink-0">
                        <Settings className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="font-bold text-xs text-slate-900 dark:text-white">Settings & Preferences</div>
                        <div className="text-[10px] text-slate-400">Password, backups, dining mode</div>
                      </div>
                    </button>

                    <button
                      onClick={() => {
                        setIsUserMenuOpen(false);
                        exportMealsToCsv(loggedMeals);
                      }}
                      className="w-full text-left flex items-center gap-2.5 px-4 py-2 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors cursor-pointer text-slate-800 dark:text-slate-200"
                    >
                      <div className="w-7 h-7 rounded-lg bg-indigo-100 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-400 flex items-center justify-center shrink-0">
                        <Download className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="font-bold text-xs text-slate-900 dark:text-white">Export Meal History (CSV)</div>
                        <div className="text-[10px] text-slate-400">Download {loggedMeals.length} logged meals</div>
                      </div>
                    </button>

                    <Link
                      to="/profile"
                      onClick={() => setIsUserMenuOpen(false)}
                      className="flex items-center gap-2.5 px-4 py-2 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors text-slate-800 dark:text-slate-200"
                    >
                      <div className="w-7 h-7 rounded-lg bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-400 flex items-center justify-center shrink-0">
                        <HeartPulse className="w-3.5 h-3.5" />
                      </div>
                      <div>
                        <div className="font-bold text-xs text-slate-900 dark:text-white">Health Profile & Biometrics</div>
                        <div className="text-[10px] text-slate-400">TDEE calculator, conditions, allergies</div>
                      </div>
                    </Link>
                  </div>

                  {/* Auth Footer Action */}
                  <div className="pt-1 mt-1 border-t border-slate-100 dark:border-slate-800 px-2">
                    {isAuthenticated ? (
                      <button
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          logout();
                        }}
                        className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-xs font-bold text-rose-600 dark:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 transition cursor-pointer"
                      >
                        <LogOut className="w-4 h-4" />
                        <span>Sign Out ({user?.email?.split('@')[0]})</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => {
                          setIsUserMenuOpen(false);
                          navigate('/login');
                        }}
                        className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-xl text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-2xs cursor-pointer"
                      >
                        <LogIn className="w-4 h-4" />
                        <span>Sign In / Create Account</span>
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Mobile Navigation Sub-Bar (Slim, compact) */}
        <div className="md:hidden border-t border-slate-200 dark:border-slate-800 px-3 py-1.5 flex items-center justify-around bg-slate-50 dark:bg-slate-900 text-xs font-bold">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'text-emerald-700 dark:text-emerald-400 font-black' : 'text-slate-600 dark:text-slate-400')}>
            Dashboard
          </NavLink>
          <NavLink to="/menu" className={({ isActive }) => (isActive ? 'text-emerald-700 dark:text-emerald-400 font-black' : 'text-slate-600 dark:text-slate-400')}>
            Scanner {dishes.length > 0 && `(${dishes.length})`}
          </NavLink>
          <NavLink to="/plate" className={({ isActive }) => (isActive ? 'text-emerald-700 dark:text-emerald-400 font-black' : 'text-slate-600 dark:text-slate-400')}>
            Plate {plate.length > 0 && `(${plate.length})`}
          </NavLink>
          <NavLink to="/calendar" className={({ isActive }) => (isActive ? 'text-emerald-700 dark:text-emerald-400 font-black' : 'text-slate-600 dark:text-slate-400')}>
            Calendar {loggedMeals.length > 0 && `(${loggedMeals.length})`}
          </NavLink>
          <NavLink to="/profile" className={({ isActive }) => (isActive ? 'text-emerald-700 dark:text-emerald-400 font-black' : 'text-slate-600 dark:text-slate-400')}>
            Profile
          </NavLink>
        </div>
      </header>

      {/* Main Outlet for Routed Pages */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex-1 w-full space-y-8">
        <Outlet />
      </main>

      {/* Global Settings & Preferences Modal */}
      <SettingsModal isOpen={isSettingsOpen} onClose={() => setIsSettingsOpen(false)} />

      {/* Session Expired Toast (z-60 to avoid drawer collision) */}
      {sessionExpiredNotice && (
        <div className="fixed bottom-6 right-6 z-60 max-w-sm sm:max-w-md p-4 rounded-2xl bg-slate-900/95 dark:bg-slate-800/95 backdrop-blur-md text-white shadow-2xl border border-amber-500/40 flex items-start gap-3 animate-in slide-in-from-bottom-5 duration-300">
          <div className="p-2 rounded-xl bg-amber-500/20 text-amber-400 shrink-0">
            <AlertCircle className="w-5 h-5" />
          </div>
          <div className="flex-1 text-xs">
            <h4 className="font-bold text-sm text-white mb-0.5">Session Expired</h4>
            <p className="text-slate-300 mb-3 leading-relaxed">
              Your authentication session has expired. Please sign in again to continue synchronizing your profile and meal logs.
            </p>
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  setSessionExpiredNotice(false);
                  navigate('/login');
                }}
                className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs transition cursor-pointer shadow-xs"
              >
                Sign In Now
              </button>
              <button
                onClick={() => setSessionExpiredNotice(false)}
                className="px-3 py-1.5 rounded-lg bg-slate-800 dark:bg-slate-700 hover:bg-slate-700 dark:hover:bg-slate-600 text-slate-300 font-semibold text-xs transition cursor-pointer"
              >
                Dismiss
              </button>
            </div>
          </div>
          <button
            onClick={() => setSessionExpiredNotice(false)}
            className="text-slate-400 hover:text-white p-1 rounded-lg transition cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Global Footer */}
      <footer className="border-t border-slate-200/80 dark:border-slate-800 bg-white dark:bg-slate-900 py-6 text-center text-xs text-slate-500 dark:text-slate-400 transition-colors">
        <div className="max-w-4xl mx-auto px-4">
          <p className="flex items-center justify-center gap-1.5 mb-1 text-slate-700 dark:text-slate-300 font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" /> Medical & Nutritional Guidance Disclaimer
          </p>
          <p className="text-[11px] text-slate-500 dark:text-slate-400 leading-relaxed">
            Recommendations are computational estimates based on user biometric inputs and published clinical nutritional literature. Always verify allergen information directly with restaurant staff.
          </p>
        </div>
      </footer>
    </div>
  );
}
