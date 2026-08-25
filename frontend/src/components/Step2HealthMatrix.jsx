import React, { useState, useEffect } from 'react';
import { User, Activity, ShieldAlert, Sparkles, Flame, Heart, AlertTriangle, ArrowRight, ArrowLeft, Loader2 } from 'lucide-react';
import { generateHealthMatrix } from '../api';

export default function Step2HealthMatrix({
  profile,
  setProfile,
  userMatrix,
  setUserMatrix,
  onBack,
  onNext,
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Available clinical options
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

  // Fetch or update matrix whenever profile changes
  const fetchMatrix = async (currentProfile) => {
    setLoading(true);
    setError(null);
    try {
      const data = await generateHealthMatrix(currentProfile);
      setUserMatrix(data.matrix);
    } catch (err) {
      setError(err.message || 'Failed to synthesize health matrix.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMatrix(profile);
  }, []);

  const toggleArrayItem = (field, itemId) => {
    const list = profile[field] || [];
    const updated = list.includes(itemId)
      ? list.filter((i) => i !== itemId)
      : [...list, itemId];
    const newProfile = { ...profile, [field]: updated };
    setProfile(newProfile);
    fetchMatrix(newProfile);
  };

  const handleFieldChange = (field, value) => {
    const newProfile = { ...profile, [field]: value };
    setProfile(newProfile);
    fetchMatrix(newProfile);
  };

  const m = userMatrix?.metabolic_targets;
  const w = userMatrix?.clinical_risk_weights;
  const g = userMatrix?.nutritional_guardrails;

  return (
    <div className="max-w-5xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-3">
          <Sparkles className="w-3.5 h-3.5" /> Model 2: Personalized Health Matrix Studio
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-teal-300 to-emerald-400">
          Biometrics & Clinical Guardrails
        </h1>
        <p className="text-slate-400 text-sm sm:text-base mt-2 max-w-xl mx-auto">
          Your profile generates a deterministic metabolic baseline (Mifflin-St Jeor) combined with clinical risk weights for safe food matchmaking.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Col: Biometric Inputs (5 cols) */}
        <div className="lg:col-span-6 space-y-6">
          {/* Biometrics Card */}
          <div className="glass-panel rounded-3xl p-6 border border-slate-800">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
              <User className="w-4 h-4 text-blue-400" /> Biometrics & Body Composition
            </h3>
            <div className="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Age</label>
                <input
                  type="number"
                  value={profile.age}
                  onChange={(e) => handleFieldChange('age', parseInt(e.target.value) || 30)}
                  className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:ring-2 focus:ring-blue-500/40"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Gender</label>
                <select
                  value={profile.gender}
                  onChange={(e) => handleFieldChange('gender', e.target.value)}
                  className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:ring-2 focus:ring-blue-500/40"
                >
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                  <option value="other">Other</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Height (cm)</label>
                <input
                  type="number"
                  value={profile.height_cm}
                  onChange={(e) => handleFieldChange('height_cm', parseFloat(e.target.value) || 170)}
                  className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:ring-2 focus:ring-blue-500/40"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Weight (kg)</label>
                <input
                  type="number"
                  value={profile.weight_kg}
                  onChange={(e) => handleFieldChange('weight_kg', parseFloat(e.target.value) || 70)}
                  className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:ring-2 focus:ring-blue-500/40"
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Activity Level</label>
                <select
                  value={profile.activity_level}
                  onChange={(e) => handleFieldChange('activity_level', e.target.value)}
                  className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:ring-2 focus:ring-blue-500/40"
                >
                  <option value="sedentary">Sedentary (desk job)</option>
                  <option value="light">Light Activity (1-2x/wk)</option>
                  <option value="moderate">Moderate (3-5x/wk)</option>
                  <option value="heavy">Heavy Active (daily)</option>
                  <option value="athlete">Athlete / Intense</option>
                </select>
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-400 mb-1.5">Metabolic Goal</label>
                <select
                  value={profile.primary_goal}
                  onChange={(e) => handleFieldChange('primary_goal', e.target.value)}
                  className="w-full glass-input rounded-xl px-3 py-2 text-sm font-semibold text-white focus:ring-2 focus:ring-blue-500/40"
                >
                  <option value="fat_loss">Fat Loss (-20% deficit)</option>
                  <option value="muscle_gain">Muscle Gain (+10% surplus)</option>
                  <option value="maintenance">Maintenance</option>
                  <option value="healthy_aging">Healthy Aging</option>
                </select>
              </div>
            </div>
          </div>

          {/* Clinical Conditions */}
          <div className="glass-panel rounded-3xl p-6 border border-slate-800">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3 flex items-center gap-2">
              <Heart className="w-4 h-4 text-rose-400" /> Clinical Conditions
            </h3>
            <div className="flex flex-wrap gap-2">
              {conditionsList.map((cond) => {
                const isSelected = (profile.health_conditions || []).includes(cond.id);
                return (
                  <button
                    key={cond.id}
                    type="button"
                    onClick={() => toggleArrayItem('health_conditions', cond.id)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      isSelected
                        ? 'bg-rose-500/20 text-rose-300 border border-rose-500/50 shadow-sm'
                        : 'bg-slate-900/60 text-slate-400 border border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <span>{cond.icon}</span> {cond.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Allergens & Dietary Exclusions */}
          <div className="glass-panel rounded-3xl p-6 border border-slate-800">
            <h3 className="text-sm font-bold text-white uppercase tracking-wider mb-3 flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber-400" /> Zero-Tolerance Allergens & Diet
            </h3>
            
            <label className="block text-xs font-semibold text-slate-400 mb-2">Strict Allergens (Fit Score = 0 Override)</label>
            <div className="flex flex-wrap gap-2 mb-4">
              {allergiesList.map((all) => {
                const isSelected = (profile.allergies || []).includes(all.id);
                return (
                  <button
                    key={all.id}
                    type="button"
                    onClick={() => toggleArrayItem('allergies', all.id)}
                    className={`px-3.5 py-1.5 rounded-xl text-xs font-bold flex items-center gap-1.5 transition-all ${
                      isSelected
                        ? 'bg-amber-500 text-slate-950 font-extrabold shadow-glow-amber'
                        : 'bg-slate-900/60 text-slate-400 border border-slate-800 hover:border-slate-700'
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
                    className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                      isSelected
                        ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/50 shadow-sm'
                        : 'bg-slate-900/60 text-slate-400 border border-slate-800 hover:border-slate-700'
                    }`}
                  >
                    <span>{diet.icon}</span> {diet.label}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Col: Live Synthesized Matrix (6 cols) */}
        <div className="lg:col-span-6 space-y-6">
          <div className="glass-panel rounded-3xl p-6 border border-slate-800 sticky top-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-bold text-white uppercase tracking-wider flex items-center gap-2">
                <Flame className="w-4 h-4 text-emerald-400" /> Live Computational Health Matrix
              </h3>
              {loading && (
                <span className="flex items-center gap-1 text-xs text-blue-400 font-medium">
                  <Loader2 className="w-3.5 h-3.5 animate-spin" /> Synthesizing...
                </span>
              )}
            </div>

            {error && (
              <div className="p-3 mb-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-400 text-xs">
                {error}
              </div>
            )}

            {userMatrix && m && (
              <div className="space-y-5">
                {/* Calories Card */}
                <div className="p-5 rounded-2xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-blue-950/40 border border-emerald-500/30">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-xs text-slate-400 font-semibold block">Target Daily Energy</span>
                      <div className="text-3xl font-extrabold text-white flex items-baseline gap-1.5">
                        <span className="text-emerald-400">{Math.round(m.target_calories_kcal)}</span>
                        <span className="text-xs text-slate-400 font-normal">kcal/day</span>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className="px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
                        {m.caloric_adjustment_ratio > 0 ? `+${Math.round(m.caloric_adjustment_ratio * 100)}% Surplus` : `${Math.round(m.caloric_adjustment_ratio * 100)}% Deficit`}
                      </span>
                      <div className="text-[11px] text-slate-500 mt-1">BMR {Math.round(m.bmr_kcal)} | TDEE {Math.round(m.tdee_kcal)}</div>
                    </div>
                  </div>

                  {/* Macro Progress Split */}
                  <div className="mt-4">
                    <div className="h-2.5 w-full bg-slate-800 rounded-full flex overflow-hidden">
                      <div style={{ width: `${m.target_protein_pct}%` }} className="bg-emerald-500" />
                      <div style={{ width: `${m.target_carbs_pct}%` }} className="bg-blue-500" />
                      <div style={{ width: `${m.target_fats_pct}%` }} className="bg-amber-500" />
                    </div>
                    <div className="flex justify-between text-xs font-semibold mt-2 text-slate-300">
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /> Protein: {Math.round(m.target_protein_g)}g ({Math.round(m.target_protein_pct)}%)</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-blue-500" /> Carbs: {Math.round(m.target_carbs_g)}g ({Math.round(m.target_carbs_pct)}%)</span>
                      <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-amber-500" /> Fat: {Math.round(m.target_fats_g)}g ({Math.round(m.target_fats_pct)}%)</span>
                    </div>
                  </div>
                </div>

                {/* Clinical Summary */}
                <div className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 text-xs text-slate-300 italic">
                  <b>🩺 Clinical Summary:</b> "{userMatrix.user_summary}"
                </div>

                {/* Guardrails Grid */}
                <div className="grid grid-cols-2 gap-3 text-xs">
                  <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800/80">
                    <span className="text-slate-500 block mb-0.5">Sodium Ceiling</span>
                    <span className="font-bold text-sky-400">&lt; {g?.sodium_ceiling_mg} mg/day</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800/80">
                    <span className="text-slate-500 block mb-0.5">Glycemic Sensitivity</span>
                    <span className="font-bold text-amber-400">{w?.glycemic_sensitivity >= 0.7 ? 'High (Strict Low-GI)' : 'Standard'}</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800/80">
                    <span className="text-slate-500 block mb-0.5">Saturated Fat Cap</span>
                    <span className="font-bold text-rose-400">&lt; {Math.round(g?.saturated_fat_max_pct * 100)}% kcal</span>
                  </div>
                  <div className="p-3 rounded-xl bg-slate-900/40 border border-slate-800/80">
                    <span className="text-slate-500 block mb-0.5">Min Dietary Fiber</span>
                    <span className="font-bold text-emerald-400">&gt; {Math.round(g?.dietary_fiber_min_g)} g/day</span>
                  </div>
                </div>

                {/* Hard Exclusion Mask */}
                {userMatrix.exclusion_mask && userMatrix.exclusion_mask.length > 0 && (
                  <div className="p-3.5 rounded-2xl bg-rose-950/20 border border-rose-500/30">
                    <div className="text-xs font-bold text-rose-400 flex items-center gap-1.5 mb-1.5">
                      <AlertTriangle className="w-3.5 h-3.5" /> Hard Exclusion Mask:
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {userMatrix.exclusion_mask.map((ex, i) => (
                        <span key={i} className="px-2 py-0.5 rounded-md bg-rose-500/20 text-rose-300 text-[11px] font-mono font-semibold">
                          {ex}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="mt-10 flex justify-between items-center">
        <button
          onClick={onBack}
          className="flex items-center gap-2 px-6 py-3 rounded-2xl font-bold text-sm text-slate-300 hover:text-white bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all cursor-pointer"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Menu
        </button>

        <button
          onClick={onNext}
          disabled={!userMatrix}
          className="flex items-center gap-2 px-8 py-3.5 rounded-2xl font-bold text-sm bg-gradient-to-r from-emerald-500 to-blue-500 text-white shadow-xl hover:scale-[1.02] shadow-glow-green transition-all cursor-pointer"
        >
          Run 3-Tier Matchmaker ➔
        </button>
      </div>
    </div>
  );
}
