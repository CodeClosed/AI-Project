import React, { useState, useEffect, useCallback } from 'react';
import { Salad, ShieldCheck } from 'lucide-react';
import AccountSection from './components/AccountSection';
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

  // When profile is saved in Section 1, update matrix & re-run evaluation if dishes exist
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

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 flex flex-col justify-between selection:bg-emerald-500 selection:text-slate-950 font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/70 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-glow-green">
              <Salad className="w-5 h-5 text-slate-950 font-bold" />
            </div>
            <div>
              <span className="font-black text-lg text-white tracking-tight flex items-center gap-1.5">
                NutriMenu <span className="text-emerald-400">AI</span>
              </span>
              <span className="text-[10px] text-slate-500 block leading-none font-semibold">
                Clinical Menu Intelligence & Matchmaker
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Deterministic Clinical Safety Authority
            </span>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex-1 w-full space-y-8">
        {/* Section 1: User Account & Health Matrix Configuration */}
        <AccountSection
          profile={profile}
          setProfile={setProfile}
          userMatrix={userMatrix}
          onSaveProfile={handleSaveProfile}
          loadingMatrix={loadingMatrix}
        />

        {/* Section 2: Menu Upload (Image Left, Extracted Table Right) */}
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

        {/* Section 3: 3-Tier Recommendation Tables (Unified & Filterable Tables) */}
        <RecommendationTableSection
          dishes={dishes}
          userMatrix={userMatrix}
          evalResult={evalResult}
          evalLoading={evalLoading}
          onRunEvaluation={() => runEvaluation(userMatrix, dishes)}
        />
      </main>

      {/* Footer Disclaimer */}
      <footer className="border-t border-slate-800/60 bg-slate-950/60 py-6 text-center text-xs text-slate-500">
        <div className="max-w-4xl mx-auto px-4">
          <p className="flex items-center justify-center gap-1.5 mb-1 text-slate-400 font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-400" /> Medical & Nutritional Guidance Disclaimer
          </p>
          <p className="text-[11px] leading-relaxed">
            Recommendations are computational estimates based on user biometric inputs and published clinical nutritional literature. This application is not a medical device and does not substitute for clinical advice from a licensed medical professional or registered dietitian.
          </p>
        </div>
      </footer>
    </div>
  );
}
