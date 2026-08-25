import React, { useState, useMemo } from 'react';
import { X, User, Heart, ShieldAlert, Sparkles, Flame, Scale, Check, Key, Eye, EyeOff, BrainCircuit } from 'lucide-react';

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

  const [savedFeedback, setSavedFeedback] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);

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

  // Instant reactive real-time metabolic target calculation (Mifflin-St Jeor & WHO equation)
  const dynamicMetabolic = useMemo(() => {
    const age = Number(profile.age) || 30;
    const gender = String(profile.gender || 'male').toLowerCase();
    const height = Number(profile.height_cm) || 170;
    const weight = Number(profile.weight_kg) || 70;
    const activity = String(profile.activity_level || 'sedentary').toLowerCase();
    const goal = String(profile.primary_goal || 'maintenance').toLowerCase();

    // 1. BMR
    const s = gender === 'male' ? 5.0 : -161.0;
    const bmr = 10.0 * weight + 6.25 * height - 5.0 * age + s;

    // 2. PAL & TDEE
    const palMap = {
      sedentary: 1.2,
      light: 1.375,
      moderate: 1.55,
      heavy: 1.725,
      athlete: 1.9,
    };
    const pal = palMap[activity] || 1.2;
    const tdee = bmr * pal;

    // 3. Caloric Target
    let adj = 0.0;
    if (goal.includes('fat_loss') || goal.includes('deficit') || goal.includes('weight_loss')) {
      adj = -0.20;
    } else if (goal.includes('muscle') || goal.includes('gain') || goal.includes('surplus')) {
      adj = 0.10;
    }
    const targetCalories = Math.max(1000, tdee * (1.0 + adj));

    // 4. Macro Splits
    const pPerKg = adj !== 0.0 ? 1.8 : 1.2;
    const pG = weight * pPerKg;
    const pKcal = pG * 4.0;
    const pPct = Math.min(60, (pKcal / targetCalories) * 100.0);

    const fPct = 25.0;
    const fKcal = targetCalories * (fPct / 100.0);
    const fG = fKcal / 9.0;

    const cKcal = Math.max(0, targetCalories - pKcal - fKcal);
    const cG = Math.max(30.0, cKcal / 4.0);
    const cPct = Math.max(15, 100.0 - pPct - fPct);

    return {
      bmr_kcal: Math.round(bmr),
      tdee_kcal: Math.round(tdee),
      target_calories_kcal: Math.round(targetCalories),
      caloric_adjustment_ratio: adj,
      target_protein_g: Math.round(pG),
      target_protein_pct: Math.round(pPct),
      target_carbs_g: Math.round(cG),
      target_carbs_pct: Math.round(cPct),
      target_fats_g: Math.round(fG),
      target_fats_pct: Math.round(fPct),
    };
  }, [profile]);

  const handleSave = async () => {
    await onSaveProfile();
    setSavedFeedback(true);
    setTimeout(() => setSavedFeedback(false), 3000);
  };

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
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900 leading-tight">My Health Profile & Matrix</h2>
                <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 text-[10px] font-black uppercase tracking-wider flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-emerald-600" /> Gemini AI
                </span>
              </div>
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
          {/* Live Reactive Metabolic Target Banner */}
          <div className="p-4 rounded-2xl bg-gradient-to-r from-emerald-50 via-teal-50/50 to-slate-50 border border-emerald-200 shadow-xs transition-all duration-300">
            <div className="flex items-center justify-between mb-2">
              <div>
                <span className="text-[11px] font-bold text-slate-500 uppercase tracking-wider block">
                  Daily Energy Target
                </span>
                <span className="text-2xl font-black text-emerald-700 tabular-nums">
                  {dynamicMetabolic.target_calories_kcal}
                </span>
                <span className="text-xs text-slate-500 ml-1">kcal/day</span>
              </div>
              <div className="text-right">
                <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-bold transition-all">
                  {dynamicMetabolic.caloric_adjustment_ratio > 0
                    ? `+${Math.round(dynamicMetabolic.caloric_adjustment_ratio * 100)}% Surplus`
                    : dynamicMetabolic.caloric_adjustment_ratio < 0
                    ? `${Math.round(dynamicMetabolic.caloric_adjustment_ratio * 100)}% Deficit`
                    : 'Maintenance'}
                </span>
                <div className="text-[10px] text-slate-400 mt-1">
                  BMR: {dynamicMetabolic.bmr_kcal} | TDEE: {dynamicMetabolic.tdee_kcal}
                </div>
              </div>
            </div>

            {/* Dynamic Macro Bar */}
            <div className="h-2.5 w-full bg-slate-200 rounded-full flex overflow-hidden transition-all duration-300">
              <div
                style={{ width: `${dynamicMetabolic.target_protein_pct}%` }}
                className="bg-emerald-500 transition-all duration-300"
              />
              <div
                style={{ width: `${dynamicMetabolic.target_carbs_pct}%` }}
                className="bg-blue-500 transition-all duration-300"
              />
              <div
                style={{ width: `${dynamicMetabolic.target_fats_pct}%` }}
                className="bg-amber-500 transition-all duration-300"
              />
            </div>
            <div className="flex justify-between text-[11px] font-semibold mt-1.5 text-slate-700 tabular-nums">
              <span>🥩 {dynamicMetabolic.target_protein_g}g Protein ({dynamicMetabolic.target_protein_pct}%)</span>
              <span>🌾 {dynamicMetabolic.target_carbs_g}g Carbs</span>
              <span>🥑 {dynamicMetabolic.target_fats_g}g Fat</span>
            </div>
          </div>

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
                <option value="sedentary">Sedentary (Desk Job, Little Exercise)</option>
                <option value="light">Light Activity (Exercise 1-2x/week)</option>
                <option value="moderate">Moderate Activity (Exercise 3-5x/week)</option>
                <option value="heavy">Heavy (Hard Exercise 6-7x/week)</option>
                <option value="athlete">Athlete / Very Intense Training</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-600 mb-1">Primary Metabolic Goal</label>
              <select
                value={profile.primary_goal}
                onChange={(e) => handleFieldChange('primary_goal', e.target.value)}
                className="w-full bg-slate-50 border border-slate-300 rounded-xl px-3 py-2 text-xs font-semibold text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
              >
                <option value="fat_loss">Fat Loss (-20% caloric deficit)</option>
                <option value="muscle_gain">Muscle Gain (+10% caloric surplus)</option>
                <option value="maintenance">Weight Maintenance (Balanced)</option>
                <option value="healthy_aging">Healthy Aging & Longevity</option>
              </select>
            </div>
          </div>

          {/* Conditions */}
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Heart className="w-3.5 h-3.5 text-rose-500" /> Medical Conditions (Triggers Clinical Guardrails)
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

          {/* Gemini API Key Configuration (Optional) */}
          <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
            <div className="flex items-center justify-between">
              <label className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                <Key className="w-3.5 h-3.5 text-emerald-600" /> Google Gemini API Key
                <span className="text-[10px] font-normal text-slate-400">(Optional)</span>
              </label>
              <button
                type="button"
                onClick={() => setShowApiKey(!showApiKey)}
                className="text-[11px] text-emerald-700 font-semibold flex items-center gap-1 hover:underline cursor-pointer"
              >
                {showApiKey ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                {showApiKey ? 'Hide' : 'Show'}
              </button>
            </div>
            <input
              type={showApiKey ? 'text' : 'password'}
              placeholder="AIzaSy... (leave blank to use server environment key)"
              value={profile.api_key || ''}
              onChange={(e) => handleFieldChange('api_key', e.target.value)}
              className="w-full bg-white border border-slate-300 rounded-xl px-3 py-2 text-xs font-mono text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
            />
            <p className="text-[11px] text-slate-500 leading-tight">
              Directly integrates with Gemini 2.5/1.5 Flash for deep clinical matrix reasoning and multimodal OCR parsing.
            </p>
          </div>
        </div>

        {/* Footer (Does NOT close the modal upon save) */}
        <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
          <div className="flex items-center gap-2">
            {savedFeedback ? (
              <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-lg border border-emerald-200 flex items-center gap-1">
                <Check className="w-3.5 h-3.5 stroke-[2.5]" /> Matrix Synced with Gemini!
              </span>
            ) : (
              <span className="text-xs text-slate-500 flex items-center gap-1">
                <BrainCircuit className="w-3.5 h-3.5 text-emerald-600" />
                {loadingMatrix ? 'Synthesizing with Gemini API...' : 'Live metric preview active'}
              </span>
            )}
          </div>

          <button
            type="button"
            onClick={handleSave}
            disabled={loadingMatrix}
            className="px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white font-extrabold text-xs shadow-sm transition-all active:scale-[0.96] flex items-center gap-1.5 cursor-pointer"
          >
            <Check className="w-4 h-4 stroke-[2.5]" /> Save & Sync Matrix
          </button>
        </div>
      </div>
    </div>
  );
}
