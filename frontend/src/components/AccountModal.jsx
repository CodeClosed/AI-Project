import React, { useState } from 'react';
import { X, User, Heart, ShieldAlert, Sparkles, Flame, Check, Scale } from 'lucide-react';

export default function AccountModal({ isOpen, onClose, profile, setProfile, userMatrix }) {
  if (!isOpen) return null;

  const conditionsList = [
    { id: 'hypertension', label: 'Hypertension', icon: '🫀' },
    { id: 'type_2_diabetes', label: 'Type 2 Diabetes', icon: '🩸' },
    { id: 'pre_diabetes', label: 'Pre-Diabetes', icon: '📈' },
    { id: 'gerd', label: 'Acid Reflux / GERD', icon: '🔥' },
    { id: 'hyperlipidemia', label: 'Hyperlipidemia', icon: '🫀' },
    { id: 'pcos', label: 'PCOS', icon: '🧬' },
    { id: 'fatty_liver', label: 'Fatty Liver', icon: '🩺' },
  ];

  const allergiesList = [
    { id: 'peanuts', label: 'Peanuts', icon: '🥜' },
    { id: 'tree_nuts', label: 'Tree Nuts', icon: '🌰' },
    { id: 'dairy', label: 'Dairy / Milk', icon: '🥛' },
    { id: 'gluten', label: 'Gluten / Wheat', icon: '🌾' },
    { id: 'shellfish', label: 'Shellfish', icon: '🦐' },
    { id: 'eggs', label: 'Eggs', icon: '🥚' },
    { id: 'soy', label: 'Soy', icon: '🌱' },
  ];

  const dietsList = [
    { id: 'vegetarian', label: 'Vegetarian', icon: '🥦' },
    { id: 'vegan', label: 'Vegan', icon: '🌱' },
    { id: 'pescatarian', label: 'Pescatarian', icon: '🐟' },
    { id: 'halal', label: 'Halal', icon: '🌙' },
    { id: 'keto', label: 'Keto / Low-Carb', icon: '🥑' },
  ];

  const toggleArrayItem = (field, itemId) => {
    const list = profile[field] || [];
    const updated = list.includes(itemId)
      ? list.filter((i) => i !== itemId)
      : [...list, itemId];
    setProfile({ ...profile, [field]: updated });
  };

  const handleFieldChange = (field, value) => {
    setProfile({ ...profile, [field]: value });
  };

  const m = userMatrix?.metabolic_targets;
  const g = userMatrix?.nutritional_guardrails;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/60 backdrop-blur-md transition-opacity"
        onClick={onClose}
      />

      {/* Modal Card (Apple HIG Sheet Style) */}
      <div className="relative w-full max-w-3xl max-h-[90vh] bg-slate-900 border border-slate-700/60 rounded-[28px] shadow-2xl flex flex-col overflow-hidden z-10">
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-800 flex items-center justify-between bg-slate-900/90 backdrop-blur-xl">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center justify-center">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white leading-tight">My Health Profile & Nutritional Matrix</h2>
              <p className="text-xs text-slate-400">Configures your metabolic baseline and strict clinical guardrails</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-slate-800 transition-colors active:scale-[0.96]"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6 overflow-y-auto space-y-6">
          {/* Live Metabolic Summary Bar */}
          {m && (
            <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-950/30 via-slate-800/40 to-blue-950/30 border border-emerald-500/30 flex flex-wrap items-center justify-between gap-4">
              <div>
                <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">Target Energy</span>
                <span className="text-2xl font-extrabold text-emerald-400 tabular-nums">{Math.round(m.target_calories_kcal)}</span>
                <span className="text-xs text-slate-400 ml-1">kcal/day</span>
              </div>
              <div className="text-xs font-semibold text-slate-300 flex items-center gap-3">
                <span className="px-2.5 py-1 rounded-lg bg-emerald-500/10 text-emerald-300 border border-emerald-500/20">
                  🥩 {Math.round(m.target_protein_g)}g Protein
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-blue-500/10 text-blue-300 border border-blue-500/20">
                  🌾 {Math.round(m.target_carbs_g)}g Carbs
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-amber-500/10 text-amber-300 border border-amber-500/20">
                  🥑 {Math.round(m.target_fats_g)}g Fat
                </span>
              </div>
            </div>
          )}

          {/* Biometrics */}
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-blue-400" /> Biometrics & Body Composition
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Age</label>
                <input
                  type="number"
                  value={profile.age}
                  onChange={(e) => handleFieldChange('age', parseInt(e.target.value) || 30)}
                  className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Gender</label>
                <select
                  value={profile.gender}
                  onChange={(e) => handleFieldChange('gender', e.target.value)}
                  className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                >
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Height (cm)</label>
                <input
                  type="number"
                  value={profile.height_cm}
                  onChange={(e) => handleFieldChange('height_cm', parseFloat(e.target.value) || 170)}
                  className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1">Weight (kg)</label>
                <input
                  type="number"
                  value={profile.weight_kg}
                  onChange={(e) => handleFieldChange('weight_kg', parseFloat(e.target.value) || 70)}
                  className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                />
              </div>
            </div>
          </div>

          {/* Activity Level & Goal */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Activity Level</label>
              <select
                value={profile.activity_level}
                onChange={(e) => handleFieldChange('activity_level', e.target.value)}
                className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
              >
                <option value="sedentary">Sedentary (Desk Job)</option>
                <option value="light">Light (1-2x/wk)</option>
                <option value="moderate">Moderate (3-5x/wk)</option>
                <option value="heavy">Heavy (Daily Workout)</option>
                <option value="athlete">Athlete / Intense</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Primary Metabolic Goal</label>
              <select
                value={profile.primary_goal}
                onChange={(e) => handleFieldChange('primary_goal', e.target.value)}
                className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
              >
                <option value="fat_loss">Fat Loss (-20% deficit)</option>
                <option value="muscle_gain">Muscle Gain (+10% surplus)</option>
                <option value="maintenance">Weight Maintenance</option>
                <option value="healthy_aging">Healthy Aging & Longevity</option>
              </select>
            </div>
          </div>

          {/* Clinical Conditions */}
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
              <Heart className="w-3.5 h-3.5 text-rose-400" /> Medical Conditions (Triggers Clinical Guardrails)
            </h3>
            <div className="flex flex-wrap gap-2">
              {conditionsList.map((cond) => {
                const isSelected = (profile.health_conditions || []).includes(cond.id);
                return (
                  <button
                    key={cond.id}
                    type="button"
                    onClick={() => toggleArrayItem('health_conditions', cond.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-[0.96] ${
                      isSelected
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/50 shadow-sm'
                        : 'bg-slate-800/80 text-slate-400 border border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <span>{cond.icon}</span> {cond.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Allergies & Diets */}
          <div>
            <h3 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2.5 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-400" /> Strict Allergens (Fit Score = 0 Override)
            </h3>
            <div className="flex flex-wrap gap-2 mb-4">
              {allergiesList.map((all) => {
                const isSelected = (profile.allergies || []).includes(all.id);
                return (
                  <button
                    key={all.id}
                    type="button"
                    onClick={() => toggleArrayItem('allergies', all.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all active:scale-[0.96] ${
                      isSelected
                        ? 'bg-amber-500 text-slate-950 shadow-glow-amber'
                        : 'bg-slate-800/80 text-slate-400 border border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <span>{all.icon}</span> {all.label}
                  </button>
                );
              })}
            </div>

            <label className="block text-xs font-semibold text-slate-400 mb-2">Dietary Pattern</label>
            <div className="flex flex-wrap gap-2">
              {dietsList.map((diet) => {
                const isSelected = (profile.dietary_preferences || []).includes(diet.id);
                return (
                  <button
                    key={diet.id}
                    type="button"
                    onClick={() => toggleArrayItem('dietary_preferences', diet.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-[0.96] ${
                      isSelected
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 shadow-sm'
                        : 'bg-slate-800/80 text-slate-400 border border-slate-700 hover:border-slate-600'
                    }`}
                  >
                    <span>{diet.icon}</span> {diet.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 bg-slate-900/90 border-t border-slate-800 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 font-bold text-xs shadow-lg transition-all active:scale-[0.96] flex items-center gap-1.5"
          >
            <Check className="w-4 h-4 stroke-[2.5]" /> Save & Sync Matrix
          </button>
        </div>
      </div>
    </div>
  );
}
