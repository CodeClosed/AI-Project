import React, { useState, useEffect, useCallback } from 'react';
import { Salad, ShieldCheck, User, Settings, Sparkles } from 'lucide-react';
import AccountDrawerModal from './components/AccountDrawerModal';
import MenuUploadSection from './components/MenuUploadSection';
import RecommendationTableSection from './components/RecommendationTableSection';
import { generateHealthMatrix, evaluateRecommendations } from './api';

const DEFAULT_PROFILE = {
  age: 45,
  gender: 'male',
  height_cm: 176,
  weight_kg: 86,
  activity_level: 'sedentary',
  primary_goal: 'fat_loss',
  health_conditions: ['hypertension', 'type_2_diabetes', 'gerd'],
  allergies: ['peanuts'],
  dietary_preferences: ['vegetarian'],
  raw_bio_text: '',
};

export default function App() {
  // 1. Persistent User Account Profile
  const [profile, setProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('nutrimenu_account_profile');
      return saved ? JSON.parse(saved) : DEFAULT_PROFILE;
    } catch {
      return DEFAULT_PROFILE;
    }
  });

  const [userMatrix, setUserMatrix] = useState(null);
  const [loadingMatrix, setLoadingMatrix] = useState(false);
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);

  // 2. Extracted Menu Dishes & OCR
  const [dishes, setDishes] = useState([]);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  // 3. Recommendation Evaluation
  const [evalResult, setEvalResult] = useState(null);
  const [evalLoading, setEvalLoading] = useState(false);

  // Sync profile to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('nutrimenu_account_profile', JSON.stringify(profile));
    } catch {}
  }, [profile]);

  // Sync health matrix with backend
  const syncMatrix = useCallback(async (currentProfile) => {
    setLoadingMatrix(true);
    try {
      const data = await generateHealthMatrix(currentProfile);
      setUserMatrix(data.matrix);
      return data.matrix;
    } catch (err) {
      console.error('Matrix generation failed:', err);
      return null;
    } finally {
      setLoadingMatrix(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    syncMatrix(profile);
  }, []);

  // Run Recommendation Matchmaker
  const runEvaluation = async (activeMatrix = userMatrix, activeDishes = dishes) => {
    if (!activeMatrix || activeDishes.length === 0) return;
    setEvalLoading(true);
    try {
      const data = await evaluateRecommendations(activeMatrix, activeDishes);
      setEvalResult(data.result);
    } catch (err) {
      console.error('Recommendation evaluation failed:', err);
    } finally {
      setEvalLoading(false);
    }
  };

  // When profile is saved in Modal, update matrix & re-run evaluation if dishes exist
  const handleSaveProfile = async () => {
    const updatedMatrix = await syncMatrix(profile);
    if (updatedMatrix && dishes.length > 0) {
      runEvaluation(updatedMatrix, dishes);
    }
  };

  // Auto-run evaluation when new dishes are extracted from image
  useEffect(() => {
    if (userMatrix && dishes.length > 0) {
      runEvaluation(userMatrix, dishes);
    } else {
      setEvalResult(null);
    }
  }, [dishes]);

  const dietLabels = (profile.dietary_preferences || []).join(', ');
  const allergyLabels = (profile.allergies || []).join(', ');

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 flex flex-col justify-between selection:bg-emerald-500 selection:text-white font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-200/90 bg-white/95 backdrop-blur-md sticky top-0 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Logo */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center shadow-sm">
              <Salad className="w-5 h-5 text-white font-bold" />
            </div>
            <div>
              <span className="font-black text-lg text-slate-900 tracking-tight flex items-center gap-1.5">
                NutriMenu <span className="text-emerald-600">AI</span>
              </span>
              <span className="text-[10px] text-slate-500 block leading-none font-semibold">
                Clinical Menu Intelligence & Matchmaker
              </span>
            </div>
          </div>

          {/* Account Profile Avatar Circle & Status Chip */}
          <div className="flex items-center gap-3">
            {/* Quick Profile Summary Badge */}
            <button
              onClick={() => setIsAccountModalOpen(true)}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200 hover:border-emerald-300 hover:bg-slate-100 transition-all text-xs font-semibold text-slate-700 cursor-pointer active:scale-[0.96]"
            >
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span>{dietLabels || 'Standard'}</span>
              {allergyLabels && (
                <span className="px-1.5 py-0.5 rounded-md bg-amber-100 text-amber-800 text-[10px] font-bold">
                  {allergyLabels}
                </span>
              )}
            </button>

            {/* Account Avatar Circle Button */}
            <button
              onClick={() => setIsAccountModalOpen(true)}
              title="Open Account & Health Matrix Settings"
              className="relative w-10 h-10 rounded-full bg-slate-900 text-white font-bold flex items-center justify-center shadow-sm hover:ring-2 hover:ring-emerald-500 hover:ring-offset-2 transition-all active:scale-[0.96] cursor-pointer"
            >
              <User className="w-5 h-5" />
              <span className="absolute bottom-0 right-0 w-3 h-3 bg-emerald-500 border-2 border-white rounded-full" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace (Uncramped & Spacious) */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex-1 w-full space-y-8">
        {/* Section 1: Menu Upload (Left Image / Right Extracted Items Table) */}
        <MenuUploadSection
          dishes={dishes}
          setDishes={setDishes}
          ocrLoading={ocrLoading}
          setOcrLoading={setOcrLoading}
          ocrError={ocrError}
          setOcrError={setOcrError}
          imagePreview={imagePreview}
          setImagePreview={setImagePreview}
        />

        {/* Section 2: 3-Tier Recommendation Tables (Unified Combined Table & Filter Tabs) */}
        <RecommendationTableSection
          dishes={dishes}
          userMatrix={userMatrix}
          evalResult={evalResult}
          evalLoading={evalLoading}
          onRunEvaluation={() => runEvaluation(userMatrix, dishes)}
        />
      </main>

      {/* Slide-over / Floating Account Drawer Modal */}
      <AccountDrawerModal
        isOpen={isAccountModalOpen}
        onClose={() => setIsAccountModalOpen(false)}
        profile={profile}
        setProfile={setProfile}
        userMatrix={userMatrix}
        onSaveProfile={handleSaveProfile}
        loadingMatrix={loadingMatrix}
      />

      {/* Footer Disclaimer */}
      <footer className="border-t border-slate-200/80 bg-white py-6 text-center text-xs text-slate-500">
        <div className="max-w-4xl mx-auto px-4">
          <p className="flex items-center justify-center gap-1.5 mb-1 text-slate-700 font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-600" /> Medical & Nutritional Guidance Disclaimer
          </p>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Recommendations are computational estimates based on user biometric inputs and published clinical nutritional literature. This application is not a medical device and does not substitute for clinical advice from a licensed medical professional or registered dietitian.
          </p>
        </div>
      </footer>
    </div>
  );
}
