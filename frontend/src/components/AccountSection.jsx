import React, { useState } from 'react';
import { User, Heart, ShieldAlert, Sparkles, Flame, Scale, Check, ChevronDown, ChevronUp } from 'lucide-react';

export default function AccountSection({
  profile,
  setProfile,
  userMatrix,
  onSaveProfile,
  loadingMatrix,
}) {
  const [isExpanded, setIsExpanded] = useState(true);

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
    <section className="bg-white border border-slate-200/90 rounded-3xl p-6 shadow-sm">
      {/* Section Header */}
      <div
        className="flex items-center justify-between cursor-pointer select-none"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-600 flex items-center justify-center shadow-xs">
            <User className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
              1. User Account & Health Matrix Configuration
              {profile.allergies?.length > 0 && (
                <span className="px-2.5 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 text-xs font-bold">
                  Allergen: {profile.allergies.join(', ')}
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-500">
              Personalized biometric targets, Mifflin-St Jeor metabolic baseline, and clinical guardrails.
            </p>
          </div>
        </div>

        <button
          type="button"
          className="p-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-600 transition-colors active:scale-[0.96]"
        >
          {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {/* Profile Configuration Body */}
      {isExpanded && (
        <div className="mt-6 pt-6 border-t border-slate-100 space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Biometric Controls (7 cols) */}
            <div className="lg:col-span-7 space-y-4">
              {/* Row 1: Biometrics */}
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

              {/* Row 2: Activity & Goal */}
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
                  <label className="block text-xs font-semibold text-slate-600 mb-1">Primary Goal</label>
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
                  <Heart className="w-3.5 h-3.5 text-rose-500" /> Medical Conditions (Clinical Guardrails)
                </label>
                <div className="flex flex-wrap gap-1.5">
                  {conditionsList.map((cond) => {
                    const isSelected = (profile.health_conditions || []).includes(cond.id);
                    return (
                      <button
                        key={cond.id}
                        type="button"
                        onClick={() => toggleArrayItem('health_conditions', cond.id)}
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-[0.96] ${
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
                        className={`px-3 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all active:scale-[0.96] ${
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
                        className={`px-3 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all active:scale-[0.96] ${
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

            {/* Live Computed Matrix Card (5 cols) */}
            <div className="lg:col-span-5 bg-slate-50 border border-slate-200 rounded-2xl p-5 flex flex-col justify-between">
              <div>
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                    <Flame className="w-4 h-4 text-emerald-600" /> Active Nutritional Matrix
                  </span>
                  {loadingMatrix && (
                    <span className="text-[11px] text-emerald-600 font-semibold animate-pulse">Syncing...</span>
                  )}
                </div>

                {m ? (
                  <div className="space-y-4">
                    {/* Calories & Split */}
                    <div className="p-4 rounded-xl bg-white border border-slate-200 shadow-xs">
                      <div className="flex items-center justify-between">
                        <div>
                          <span className="text-[11px] text-slate-500 font-semibold block">Target Calories</span>
                          <span className="text-2xl font-black text-emerald-600 tabular-nums">
                            {Math.round(m.target_calories_kcal)}
                          </span>
                          <span className="text-xs text-slate-500 ml-1">kcal/day</span>
                        </div>
                        <div className="text-right">
                          <span className="px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs font-bold">
                            {m.caloric_adjustment_ratio > 0 ? `+${Math.round(m.caloric_adjustment_ratio * 100)}%` : `${Math.round(m.caloric_adjustment_ratio * 100)}% Deficit`}
                          </span>
                          <div className="text-[10px] text-slate-400 mt-1">BMR: {Math.round(m.bmr_kcal)} | TDEE: {Math.round(m.tdee_kcal)}</div>
                        </div>
                      </div>

                      {/* Split Bar */}
                      <div className="mt-3">
                        <div className="h-2.5 w-full bg-slate-100 rounded-full flex overflow-hidden">
                          <div style={{ width: `${m.target_protein_pct}%` }} className="bg-emerald-500" />
                          <div style={{ width: `${m.target_carbs_pct}%` }} className="bg-blue-500" />
                          <div style={{ width: `${m.target_fats_pct}%` }} className="bg-amber-500" />
                        </div>
                        <div className="flex justify-between text-[11px] font-semibold mt-2 text-slate-700 tabular-nums">
                          <span>🥩 Protein: {Math.round(m.target_protein_g)}g ({Math.round(m.target_protein_pct)}%)</span>
                          <span>🌾 Carbs: {Math.round(m.target_carbs_g)}g</span>
                          <span>🥑 Fats: {Math.round(m.target_fats_g)}g</span>
                        </div>
                      </div>
                    </div>

                    {/* Guardrails Summary */}
                    <div className="grid grid-cols-2 gap-2 text-[11px]">
                      <div className="p-2.5 rounded-lg bg-white border border-slate-200 shadow-xs">
                        <span className="text-slate-500 block">Sodium Ceiling</span>
                        <span className="font-bold text-sky-700 tabular-nums">&lt; {g?.sodium_ceiling_mg} mg</span>
                      </div>
                      <div className="p-2.5 rounded-lg bg-white border border-slate-200 shadow-xs">
                        <span className="text-slate-500 block">Sat. Fat Cap</span>
                        <span className="font-bold text-rose-700 tabular-nums">&lt; {Math.round(g?.saturated_fat_max_pct * 100)}% kcal</span>
                      </div>
                    </div>

                    {userMatrix.exclusion_mask?.length > 0 && (
                      <div className="p-2.5 rounded-xl bg-rose-50 border border-rose-200 text-[11px]">
                        <span className="font-bold text-rose-800 block mb-0.5">Strict Exclusion Mask:</span>
                        <span className="font-mono text-rose-700 font-semibold">{userMatrix.exclusion_mask.join(', ')}</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="text-xs text-slate-400 p-6 text-center">Loading matrix...</div>
                )}
              </div>

              {/* Action Button */}
              <div className="mt-4 pt-3 border-t border-slate-200 flex justify-end">
                <button
                  type="button"
                  onClick={onSaveProfile}
                  className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs shadow-md transition-all active:scale-[0.96] flex items-center gap-1.5 cursor-pointer"
                >
                  <Check className="w-4 h-4 stroke-[2.5]" /> Update Account Matrix
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}
