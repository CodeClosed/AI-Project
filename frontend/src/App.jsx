import React, { useState, useEffect, useCallback } from 'react';
import { Salad, ShieldCheck, User, Settings, Heart, ShieldAlert, Sparkles } from 'lucide-react';
import MenuWorkspace from './components/MenuWorkspace';
import RecommendationFeed from './components/RecommendationFeed';
import AccountModal from './components/AccountModal';
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
  // Load stored profile or fallback
  const [profile, setProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('nutrimenu_user_profile');
      return saved ? JSON.parse(saved) : DEFAULT_PROFILE;
    } catch {
      return DEFAULT_PROFILE;
    }
  });

  const [userMatrix, setUserMatrix] = useState(null);
  const [dishes, setDishes] = useState([]);
  const [evalResult, setEvalResult] = useState(null);
  const [evalLoading, setEvalLoading] = useState(false);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);

  // Save profile changes to localStorage
  useEffect(() => {
    try {
      localStorage.setItem('nutrimenu_user_profile', JSON.stringify(profile));
    } catch {}
  }, [profile]);

  // Sync health matrix whenever profile changes
  const syncMatrix = useCallback(async (currentProfile) => {
    try {
      const data = await generateHealthMatrix(currentProfile);
      setUserMatrix(data.matrix);
      return data.matrix;
    } catch (err) {
      console.error('Failed to sync matrix:', err);
      return null;
    }
  }, []);

  // Initial matrix generation
  useEffect(() => {
    syncMatrix(profile);
  }, []);

  // Reactive matchmaker trigger: runs whenever dishes or userMatrix update
  useEffect(() => {
    const runMatchmaker = async () => {
      if (!userMatrix || dishes.length === 0) {
        setEvalResult(null);
        return;
      }
      setEvalLoading(true);
      try {
        const data = await evaluateRecommendations(userMatrix, dishes);
        setEvalResult(data.result);
      } catch (err) {
        console.error('Matchmaker error:', err);
      } finally {
        setEvalLoading(false);
      }
    };

    runMatchmaker();
  }, [dishes, userMatrix]);

  // Handle profile update from modal and trigger matrix sync
  const handleUpdateProfile = async (newProfile) => {
    setProfile(newProfile);
    await syncMatrix(newProfile);
  };

  const dietLabels = (profile.dietary_preferences || []).join(', ');
  const allergyLabels = (profile.allergies || []).join(', ');

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 flex flex-col justify-between selection:bg-emerald-500 selection:text-slate-950 font-sans">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/60 backdrop-blur-xl sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          {/* Logo & Brand */}
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-glow-green">
              <Salad className="w-5 h-5 text-slate-950 font-bold" />
            </div>
            <div>
              <span className="font-black text-lg text-white tracking-tight flex items-center gap-1">
                NutriMenu <span className="text-emerald-400">AI</span>
              </span>
              <span className="text-[10px] text-slate-500 block leading-none font-semibold">
                Clinical Menu Intelligence & Matchmaker
              </span>
            </div>
          </div>

          {/* Persistent User Profile & Account Capsule */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setIsAccountModalOpen(true)}
              className="px-3.5 py-1.5 rounded-2xl bg-slate-900 border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-800/60 transition-all flex items-center gap-2.5 shadow-sm active:scale-[0.96] cursor-pointer group"
            >
              <div className="w-6 h-6 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-xs font-bold">
                <User className="w-3.5 h-3.5" />
              </div>
              <div className="text-left hidden sm:block">
                <div className="text-xs font-bold text-slate-200 group-hover:text-emerald-400 transition-colors flex items-center gap-1.5">
                  <span>My Health Profile</span>
                  {profile.allergies?.length > 0 && (
                    <span className="px-1.5 py-0.2 rounded-md bg-amber-500/20 text-amber-400 text-[10px] font-extrabold">
                      {profile.allergies.join(', ')}
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 truncate max-w-[200px]">
                  {dietLabels || 'Standard'} • {profile.health_conditions?.join(', ') || 'Healthy'}
                </div>
              </div>
              <Settings className="w-4 h-4 text-slate-500 group-hover:text-slate-300" />
            </button>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex-1 w-full space-y-8">
        {/* Step-less Workspace: Upload Menu Image */}
        <MenuWorkspace
          dishes={dishes}
          setDishes={setDishes}
          ocrLoading={ocrLoading}
          setOcrLoading={setOcrLoading}
          ocrError={ocrError}
          setOcrError={setOcrError}
          imagePreview={imagePreview}
          setImagePreview={setImagePreview}
        />

        {/* Live Recommendation Results (Updates Automatically) */}
        <RecommendationFeed
          evalResult={evalResult}
          evalLoading={evalLoading}
          onOpenProfile={() => setIsAccountModalOpen(true)}
        />
      </main>

      {/* Account Profile Modal Sheet */}
      <AccountModal
        isOpen={isAccountModalOpen}
        onClose={() => setIsAccountModalOpen(false)}
        profile={profile}
        setProfile={handleUpdateProfile}
        userMatrix={userMatrix}
      />

      {/* Footer */}
      <footer className="border-t border-slate-800/60 bg-slate-950/60 py-6 text-center text-xs text-slate-500">
        <div className="max-w-4xl mx-auto px-4">
          <p className="flex items-center justify-center gap-1.5 mb-1 text-slate-400 font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-400" /> Deterministic Clinical Safety & Exclusions Authority
          </p>
          <p className="text-[11px] leading-relaxed">
            Recommendations are computational estimates based on personal biometric inputs and published clinical nutritional literature. This application does not substitute for clinical advice from a licensed medical professional or registered dietitian.
          </p>
        </div>
      </footer>
    </div>
  );
}
