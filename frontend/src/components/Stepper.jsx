import React from 'react';
import { Camera, User, UtensilsCrossed, Check } from 'lucide-react';

export default function Stepper({ currentStep, setStep, canGoToStep2, canGoToStep3 }) {
  const steps = [
    { id: 1, title: 'Menu Scanner', icon: Camera, desc: 'Upload menu image' },
    { id: 2, title: 'Health Matrix', icon: User, desc: 'Biometrics & guardrails' },
    { id: 3, title: '3-Tier Matchmaker', icon: UtensilsCrossed, desc: 'Good, Medium & Bad' },
  ];

  return (
    <div className="w-full max-w-4xl mx-auto mb-10">
      <div className="relative flex items-center justify-between">
        {/* Connecting Line */}
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-slate-800 -translate-y-1/2 z-0" />
        <div 
          className="absolute top-1/2 left-0 h-0.5 bg-gradient-to-r from-emerald-500 to-blue-500 -translate-y-1/2 z-0 transition-all duration-500 ease-out"
          style={{ width: `${((currentStep - 1) / (steps.length - 1)) * 100}%` }}
        />

        {steps.map((step) => {
          const Icon = step.icon;
          const isActive = currentStep === step.id;
          const isPassed = currentStep > step.id;
          const isClickable = (step.id === 1) || (step.id === 2 && canGoToStep2) || (step.id === 3 && canGoToStep3);

          return (
            <button
              key={step.id}
              onClick={() => isClickable && setStep(step.id)}
              disabled={!isClickable}
              className={`relative z-10 flex flex-col items-center group focus:outline-none ${
                isClickable ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'
              }`}
            >
              <div
                className={`w-12 h-12 rounded-2xl flex items-center justify-center font-bold transition-all duration-300 ${
                  isActive
                    ? 'bg-emerald-500 text-white shadow-glow-green scale-110 ring-4 ring-emerald-500/20'
                    : isPassed
                    ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                    : 'bg-slate-900 border border-slate-700 text-slate-400'
                }`}
              >
                {isPassed ? <Check className="w-5 h-5 stroke-[2.5]" /> : <Icon className="w-5 h-5" />}
              </div>
              <div className="mt-3 text-center">
                <span className={`text-sm font-bold block ${isActive ? 'text-white' : isPassed ? 'text-emerald-400' : 'text-slate-400'}`}>
                  {step.title}
                </span>
                <span className="text-xs text-slate-500 hidden sm:block">
                  {step.desc}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
