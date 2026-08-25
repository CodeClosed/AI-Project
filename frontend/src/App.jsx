import React, { useState } from 'react';
import { Salad, ShieldCheck, HeartHandshake } from 'lucide-react';
import Stepper from './components/Stepper';
import Step1MenuUpload from './components/Step1MenuUpload';
import Step2HealthMatrix from './components/Step2HealthMatrix';
import Step3Recommendations from './components/Step3Recommendations';

export default function App() {
  const [currentStep, setCurrentStep] = useState(1);
  const [dishes, setDishes] = useState([]);
  const [profile, setProfile] = useState({
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
  });
  const [userMatrix, setUserMatrix] = useState(null);

  const canGoToStep2 = dishes.length > 0;
  const canGoToStep3 = dishes.length > 0 && userMatrix !== null;

  return (
    <div className="min-h-screen bg-[#090D16] text-slate-100 flex flex-col justify-between">
      {/* Top Navbar */}
      <header className="border-b border-slate-800/80 bg-slate-950/40 backdrop-blur-xl sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-glow-green">
              <Salad className="w-5 h-5 text-slate-950 font-bold" />
            </div>
            <div>
              <span className="font-extrabold text-lg text-white tracking-tight flex items-center gap-1.5">
                NutriMenu <span className="text-emerald-400">AI</span>
              </span>
              <span className="text-[10px] text-slate-500 block leading-none font-semibold">
                Clinical 3-Tier Recommender
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <span className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-400">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" /> Deterministic Safety Authority
            </span>
          </div>
        </div>
      </header>

      {/* Main Content Body */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex-1 w-full">
        {/* Stepper Navigation */}
        <Stepper
          currentStep={currentStep}
          setStep={setCurrentStep}
          canGoToStep2={canGoToStep2}
          canGoToStep3={canGoToStep3}
        />

        {/* Step Views */}
        {currentStep === 1 && (
          <Step1MenuUpload
            dishes={dishes}
            setDishes={setDishes}
            onNext={() => setCurrentStep(2)}
          />
        )}

        {currentStep === 2 && (
          <Step2HealthMatrix
            profile={profile}
            setProfile={setProfile}
            userMatrix={userMatrix}
            setUserMatrix={setUserMatrix}
            onBack={() => setCurrentStep(1)}
            onNext={() => setCurrentStep(3)}
          />
        )}

        {currentStep === 3 && (
          <Step3Recommendations
            userMatrix={userMatrix}
            dishes={dishes}
            onBackToMatrix={() => setCurrentStep(2)}
            onRestart={() => {
              setDishes([]);
              setCurrentStep(1);
            }}
          />
        )}
      </main>

      {/* Global Medical Disclaimer Footer */}
      <footer className="border-t border-slate-800/60 bg-slate-950/60 py-6 text-center text-xs text-slate-500">
        <div className="max-w-4xl mx-auto px-4">
          <p className="flex items-center justify-center gap-1.5 mb-1 text-slate-400 font-semibold">
            <HeartHandshake className="w-4 h-4 text-emerald-400" /> Medical & Nutritional Disclaimer
          </p>
          <p className="text-[11px] leading-relaxed">
            Recommendations are computational estimates based on personal biometric inputs and published clinical nutritional literature. This application is not a medical device and does not substitute for clinical advice from a licensed medical professional or registered dietitian.
          </p>
        </div>
      </footer>
    </div>
  );
}
