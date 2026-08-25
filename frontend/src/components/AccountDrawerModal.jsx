import React, { useState } from 'react';
import { X, User, Heart, ShieldAlert, Sparkles, Flame, Scale, Check, Activity, Target } from 'lucide-react';

export default function AccountDrawerModal({
  isOpen,
  onClose,
  profile,
  setProfile,
  userMatrix,
  onSaveProfile,
  loadingMatrix,
}) {
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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-slate-900/40 backdrop-blur-sm transition-opacity"
        onClick={onClose}
      />

      {/* Modal Container */}
      <div className="relative w-full max-w-2xl bg-white rounded-3xl shadow-2xl border border-slate-200 overflow-hidden z-10 flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 flex items-center justify-center font-bold text-sm shadow-xs">
              <User className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 leading-tight">My Health Profile & Matrix</h2>
              <p className="text-xs text-slate-500">Configure your biometrics, conditions, and strict allergens</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors active:scale-[0.96] cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Scrollable Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-slate-800">
          {/* Live Metabolic Target Banner */}
          {m && (
            <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-50 via-teal-50/50 to-slate-50 border border-emerald-200 shadow-xs">
              <div className="flex items-center justify-between mb-2">
                <div>
                  <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">Daily Energy Target</span>
                  <span className="text-2xl font-black text-emerald-700 tabular-nums">{Math.round(m.target_calories_kcal)}</span>
                  <span className="text-xs text-slate-500 ml-1">kcal/day</span>
                </div>
                <div className="text-right">
                  <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-bold">
                    {m.caloric_adjustment_ratio > 0 ? `+${Math.round(m.caloric_adjustment_ratio * 100)}%` : `${Math.round(m.caloric_adjustment_ratio * 100)}% Deficit`}
                  </span>
                  <div className="text-[10px] text-slate-400 mt-1">BMR: {Math.round(m.bmr_kcal)} | TDEE: {Math.round(m.tdee_kcal)}</div>
                </div>
              </div>

              {/* Macro Bar */}
              <div className="h-2 w-full bg-slate-200 rounded-full flex overflow-hidden">
                <div style={{ width: `${m.target_protein_pct}%` }} className="bg-emerald-500" />
                <div style={{ width: `${m.target_carbs_pct}%` }} className="bg-blue-500" />
                <div style={{ width: `${m.target_fats_pct}%` }} className="bg-amber-500" />
              </div>
              <div className="flex justify-between text-[11px] font-semibold mt-1.5 text-slate-700 tabular-nums">
                <span>🥩 {Math.round(m.target_protein_g)}g Protein</span>
                <span>🌾 {Math.round(m.target_carbs_g)}g Carbs</span>
                <span>🥑 {Math.round(m.target_fats_g)}g Fat</span>
              </div>
            </div>
          )}

          {/* Biometrics */}
          <div>
            <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider mb-3 flex items-center gap-1.5">
              <Scale className="w-3.5 h-3.5 text-slate-600" /> Biometrics & Body Parameters
            </h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Age</label>
                <input
                  type="number"
                  value={profile.age}
                  onChange={(e) => handleFieldChange('age', parseInt(e.target.value) || 30)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-sm font-bold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30 tabular-nums"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Gender</label>
                <select
                  value={profile.gender}
                  onChange={(e) => handleFieldChange('gender', e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-sm font-bold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
                >
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Height (cm)</label>
                <input
                  type="number"
                  value={profile.height_cm}
                  onChange={(e) => handleFieldChange('height_cm', parseFloat(e.target.value) || 170)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-sm font-bold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30 tabular-nums"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1">Weight (kg)</label>
                <input
                  type="number"
                  value={profile.weight_kg}
                  onChange={(e) => handleFieldChange('weight_kg', parseFloat(e.target.value) || 70)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-sm font-bold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30 tabular-nums"
                />
              </div>
            </div>
          </div>

          {/* Activity & Goal */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Activity Level</label>
              <select
                value={profile.activity_level}
                onChange={(e) => handleFieldChange('activity_level', e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              >
                <option value="sedentary">Sedentary (Desk Job)</option>
                <option value="light">Light Activity (1-2x/wk)</option>
                <option value="moderate">Moderate Activity (3-5x/wk)</option>
                <option value="heavy">Heavy (Daily Training)</option>
                <option value="athlete">Athlete / Intense</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Primary Metabolic Goal</label>
              <select
                value={profile.primary_goal}
                onChange={(e) => handleFieldChange('primary_goal', e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              >
                <option value="fat_loss">Fat Loss (-20% deficit)</option>
                <option value="muscle_gain">Muscle Gain (+10% surplus)</option>
                <option value="maintenance">Weight Maintenance</option>
                <option value="healthy_aging">Healthy Aging & Longevity</option>
              </select>
            </div>
          </div>

          {/* Conditions */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Heart className="w-3.5 h-3.5 text-rose-500" /> Medical Conditions (Triggers Guardrails)
            </label>
            <div className="flex flex-wrap gap-1.5">
              {conditionsList.map((cond) => {
                const isSelected = (profile.health_conditions || []).includes(cond.id);
                return (
                  <button
                    key={cond.id}
                    type="button"
                    onClick={() => toggleArrayItem('health_conditions', cond.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-[0.96] cursor-pointer ${
                      isSelected
                        ? 'bg-rose-50 text-rose-700 border border-rose-300 font-bold shadow-xs'
                        : 'bg-slate-50 text-slate-600 border border-slate-200 hover:border-slate-300 hover:bg-slate-100'
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
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-amber-600" /> Strict Allergens (Fit Score = 0 Override)
            </label>
            <div className="flex flex-wrap gap-1.5 mb-3">
              {allergiesList.map((all) => {
                const isSelected = (profile.allergies || []).includes(all.id);
                return (
                  <button
                    key={all.id}
                    type="button"
                    onClick={() => toggleArrayItem('allergies', all.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all active:scale-[0.96] cursor-pointer ${
                      isSelected
                        ? 'bg-amber-500 text-white font-extrabold shadow-sm'
                        : 'bg-slate-50 text-slate-600 border border-slate-200 hover:border-slate-300 hover:bg-slate-100'
                    }`}
                  >
                    <span>{all.icon}</span> {all.label}
                  </button>
                );
              })}
            </div>

            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Dietary Pattern
            </label>
            <div className="flex flex-wrap gap-1.5">
              {dietsList.map((diet) => {
                const isSelected = (profile.dietary_preferences || []).includes(diet.id);
                return (
                  <button
                    key={diet.id}
                    type="button"
                    onClick={() => toggleArrayItem('dietary_preferences', diet.id)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-[0.96] cursor-pointer ${
                      isSelected
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300 font-bold shadow-xs'
                        : 'bg-slate-50 text-slate-600 border border-slate-200 hover:border-slate-300 hover:bg-slate-100'
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
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <span className="text-xs text-slate-500">
            {loadingMatrix ? 'Recalculating metabolic matrix...' : 'Matrix automatically syncs on update'}
          </span>
          <button
            type="button"
            onClick={() => {
              onSaveProfile();
              onClose();
            }}
            className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-sm transition-all active:scale-[0.96] flex items-center gap-1.5 cursor-pointer"
          >
            <Check className="w-4 h-4 stroke-[2.5]" /> Save & Close
          </button>
        </div>
      </div>
    </div>
  );
}
