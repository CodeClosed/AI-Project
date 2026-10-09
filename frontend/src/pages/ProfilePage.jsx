import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Heart,
  ShieldAlert,
  Sparkles,
  Flame,
  Scale,
  Check,
  BrainCircuit,
  Cloud,
  Save,
  User,
  ShieldCheck,
  AlertTriangle,
  FileText,
  Stethoscope,
  Sliders,
} from 'lucide-react';
import { useNutrition } from '../context/NutritionContext';
import { useAuth } from '../context/AuthContext';
import { openClinicalDoctorReport } from '../utils/exportUtils';

export default function ProfilePage() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const {
    profile,
    setProfile,
    userMatrix,
    handleSaveProfile,
    loadingMatrix,
    loggedMeals,
  } = useNutrition();

  const [saveSuccess, setSaveSuccess] = useState(false);

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

  const onSave = async () => {
    await handleSaveProfile();
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const targets = userMatrix?.metabolic_targets || {};
  const guardrails = userMatrix?.nutritional_guardrails || {};

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <Heart className="w-7 h-7 text-emerald-600 dark:text-emerald-400" />
            <span>Clinical Health & Biometric Profile</span>
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 mt-1">
            Configure your biometrics, clinical conditions, and allergies to fine-tune the recommendation engine.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => openClinicalDoctorReport({ profile, userMatrix, loggedMeals })}
            className="flex items-center gap-2 px-3.5 sm:px-4 py-2.5 rounded-xl border border-slate-300 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-200 font-bold text-xs shadow-xs transition-all cursor-pointer"
            title="Generate printable physician consultation dossier and clinical log"
          >
            <FileText className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Physician Report (PDF/Print)</span>
          </button>

          <button
            onClick={onSave}
            disabled={loadingMatrix}
            className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-md transition-all cursor-pointer"
          >
            {saveSuccess ? (
              <>
                <Check className="w-4 h-4 text-emerald-200" />
                <span>Saved & Synchronized!</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>{loadingMatrix ? 'Recalculating...' : 'Save Profile'}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Sync Status Alert */}
      {!isAuthenticated ? (
        <div className="rounded-2xl bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 p-4 text-xs text-amber-900 dark:text-amber-200 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" />
            <span>
              You are currently in <strong>Guest Mode</strong>. Profile changes are saved locally in your browser.
              Sign in to automatically sync your profile across devices.
            </span>
          </div>
          <button
            onClick={() => navigate('/login')}
            className="ml-4 px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-700 text-white font-bold text-xs shrink-0 cursor-pointer"
          >
            Sign In / Register
          </button>
        </div>
      ) : (
        <div className="rounded-2xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 p-4 text-xs text-emerald-900 dark:text-emerald-200 flex items-center gap-3">
          <Cloud className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" />
          <span>
            Connected to <strong>{user?.email}</strong>. Your clinical parameters and encrypted API preferences are safely saved.
          </span>
        </div>
      )}

      {/* Main Grid: Biometrics + Clinical Conditions + Derived Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Left Column (2 Cols): Input Parameters */}
        <div className="lg:col-span-2 space-y-6">
          {/* Card 1: Physical Biometrics */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-xs space-y-4">
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Scale className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
              <span>Biometric Fundamentals</span>
            </h2>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div>
                <label className="text-xs font-bold text-slate-600 dark:text-slate-400 block mb-1">Age</label>
                <input
                  type="number"
                  min="16"
                  max="120"
                  value={profile.age || ''}
                  onChange={(e) => handleFieldChange('age', Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm font-semibold focus:outline-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600 dark:text-slate-400 block mb-1">Gender</label>
                <select
                  value={profile.gender || 'male'}
                  onChange={(e) => handleFieldChange('gender', e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm font-semibold focus:outline-emerald-500"
                >
                  <option value="male">Male</option>
                  <option value="female">Female</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600 dark:text-slate-400 block mb-1">Height (cm)</label>
                <input
                  type="number"
                  min="100"
                  max="250"
                  value={profile.height_cm || ''}
                  onChange={(e) => handleFieldChange('height_cm', Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm font-semibold focus:outline-emerald-500"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600 dark:text-slate-400 block mb-1">Weight (kg)</label>
                <input
                  type="number"
                  min="30"
                  max="300"
                  value={profile.weight_kg || ''}
                  onChange={(e) => handleFieldChange('weight_kg', Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm font-semibold focus:outline-emerald-500"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
              <div>
                <label className="text-xs font-bold text-slate-600 dark:text-slate-400 block mb-1">Physical Activity Level</label>
                <select
                  value={profile.activity_level || 'sedentary'}
                  onChange={(e) => handleFieldChange('activity_level', e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm font-semibold focus:outline-emerald-500"
                >
                  <option value="sedentary">Sedentary (Desk Job, minimal movement)</option>
                  <option value="light">Light Activity (1–3 days/week)</option>
                  <option value="moderate">Moderate Activity (3–5 days/week)</option>
                  <option value="heavy">Heavy / Intense (6–7 days/week)</option>
                  <option value="athlete">Athlete / Very Heavy</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-bold text-slate-600 dark:text-slate-400 block mb-1">Primary Nutritional Goal</label>
                <select
                  value={profile.primary_goal || 'fat_loss'}
                  onChange={(e) => handleFieldChange('primary_goal', e.target.value)}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-sm font-semibold focus:outline-emerald-500"
                >
                  <option value="fat_loss">Fat Loss (-20% caloric deficit)</option>
                  <option value="maintenance">Maintenance (Energy equilibrium)</option>
                  <option value="muscle_gain">Muscle Hypertrophy (+10% surplus)</option>
                </select>
              </div>
            </div>
          </div>

          {/* Card 2: Clinical Health Conditions */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-xs space-y-4">
            <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-rose-600 dark:text-rose-400" />
              <span>Diagnosed Clinical Conditions</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              The engine applies specialized nutritional ceilings (such as sodium caps for hypertension and glycemic sensitivity for diabetes).
            </p>

            <div className="flex flex-wrap gap-2 pt-1">
              {conditionsList.map((cond) => {
                const active = (profile.health_conditions || []).includes(cond.id);
                return (
                  <button
                    key={cond.id}
                    type="button"
                    onClick={() => toggleArrayItem('health_conditions', cond.id)}
                    className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                      active
                        ? 'bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-200 border-rose-300 dark:border-rose-800 shadow-xs'
                        : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
                    }`}
                  >
                    <span>{cond.icon}</span>
                    <span>{cond.label}</span>
                    {active && <Check className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400 ml-1" />}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Card 3: Allergies & Dietary Restrictions */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-xs space-y-6">
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2 mb-1">
                <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                <span>Strict Food Allergies (Automatic Exclusion)</span>
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mb-3">
                Dishes containing these ingredients are placed in the red "Avoid / High Risk" tier.
              </p>
              <div className="flex flex-wrap gap-2">
                {allergiesList.map((allergy) => {
                  const active = (profile.allergies || []).includes(allergy.id);
                  return (
                    <button
                      key={allergy.id}
                      type="button"
                      onClick={() => toggleArrayItem('allergies', allergy.id)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                        active
                          ? 'bg-amber-50 dark:bg-amber-950/60 text-amber-900 dark:text-amber-200 border-amber-300 dark:border-amber-800 shadow-xs'
                          : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      <span>{allergy.icon}</span>
                      <span>{allergy.label}</span>
                      {active && <Check className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 ml-1" />}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="border-t border-slate-100 dark:border-slate-800 pt-5">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-2">Dietary Preferences</h3>
              <div className="flex flex-wrap gap-2">
                {dietsList.map((diet) => {
                  const active = (profile.dietary_preferences || []).includes(diet.id);
                  return (
                    <button
                      key={diet.id}
                      type="button"
                      onClick={() => toggleArrayItem('dietary_preferences', diet.id)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-bold transition-all cursor-pointer border ${
                        active
                          ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-900 dark:text-emerald-200 border-emerald-300 dark:border-emerald-800 shadow-xs'
                          : 'bg-slate-50 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      <span>{diet.icon}</span>
                      <span>{diet.label}</span>
                      {active && <Check className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 ml-1" />}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Right Column (1 Col): Clinician Override & Real-Time Calculated Matrix */}
        <div className="space-y-6">
          {/* Card: Clinician Prescription Override */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 sm:p-6 shadow-xs space-y-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Stethoscope className="w-5 h-5 text-indigo-600 dark:text-indigo-400 shrink-0" />
                <h2 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
                  Clinician Target Override
                </h2>
              </div>
              <label className="relative inline-flex items-center cursor-pointer shrink-0">
                <input
                  type="checkbox"
                  checked={Boolean(profile.custom_targets_override?.enabled)}
                  onChange={(e) => {
                    const isEnabled = e.target.checked;
                    const currentOv = profile.custom_targets_override || {};
                    setProfile({
                      ...profile,
                      custom_targets_override: {
                        ...currentOv,
                        enabled: isEnabled,
                        target_calories_kcal: Number(currentOv.target_calories_kcal || targets.target_calories_kcal || 2000),
                        target_protein_g: Number(currentOv.target_protein_g || targets.target_protein_g || 130),
                        target_carbs_g: Number(currentOv.target_carbs_g || targets.target_carbs_g || 220),
                        target_fats_g: Number(currentOv.target_fats_g || targets.target_fats_g || 65),
                        sodium_ceiling_mg: Number(currentOv.sodium_ceiling_mg || guardrails.sodium_ceiling_mg || 2000),
                      },
                    });
                  }}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-200 rounded-full peer dark:bg-slate-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-slate-600 peer-checked:bg-indigo-600"></div>
              </label>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              {profile.custom_targets_override?.enabled ? (
                <span className="text-indigo-600 dark:text-indigo-300 font-semibold">
                  Prescription override active. Standard automated Mifflin-St Jeor algorithms are bypassed in favor of clinician-specified targets.
                </span>
              ) : (
                <span>
                  Using automated Mifflin-St Jeor metabolic formulas. Toggle on to define customized nutritionist or physician prescription targets.
                </span>
              )}
            </p>

            {profile.custom_targets_override?.enabled && (
              <div className="pt-2 space-y-4 animate-in fade-in duration-150">
                <div className="p-3 rounded-xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800/60 text-[11px] text-indigo-900 dark:text-indigo-200 flex items-start gap-2.5">
                  <Sliders className="w-4 h-4 text-indigo-600 dark:text-indigo-400 shrink-0 mt-0.5" />
                  <span>
                    Directly overrides caloric targets, macro ratios, and sodium ceiling across recommendations and plate guardrails.
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-[11px] font-bold text-slate-600 dark:text-slate-400 block mb-1">
                      Target Calories (kcal)
                    </label>
                    <input
                      type="number"
                      min="800"
                      max="5000"
                      value={profile.custom_targets_override?.target_calories_kcal || ''}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          custom_targets_override: {
                            ...profile.custom_targets_override,
                            target_calories_kcal: Number(e.target.value),
                          },
                        })
                      }
                      className="w-full px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-bold focus:outline-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-600 dark:text-slate-400 block mb-1">
                      Sodium Ceiling (mg)
                    </label>
                    <input
                      type="number"
                      min="500"
                      max="4000"
                      value={profile.custom_targets_override?.sodium_ceiling_mg || ''}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          custom_targets_override: {
                            ...profile.custom_targets_override,
                            sodium_ceiling_mg: Number(e.target.value),
                          },
                        })
                      }
                      className="w-full px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-bold focus:outline-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-600 dark:text-slate-400 block mb-1">
                      Target Protein (g)
                    </label>
                    <input
                      type="number"
                      min="20"
                      max="350"
                      value={profile.custom_targets_override?.target_protein_g || ''}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          custom_targets_override: {
                            ...profile.custom_targets_override,
                            target_protein_g: Number(e.target.value),
                          },
                        })
                      }
                      className="w-full px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-bold focus:outline-indigo-500"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-slate-600 dark:text-slate-400 block mb-1">
                      Target Carbs (g)
                    </label>
                    <input
                      type="number"
                      min="10"
                      max="600"
                      value={profile.custom_targets_override?.target_carbs_g || ''}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          custom_targets_override: {
                            ...profile.custom_targets_override,
                            target_carbs_g: Number(e.target.value),
                          },
                        })
                      }
                      className="w-full px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-bold focus:outline-indigo-500"
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="text-[11px] font-bold text-slate-600 dark:text-slate-400 block mb-1">
                      Target Fats (g)
                    </label>
                    <input
                      type="number"
                      min="10"
                      max="250"
                      value={profile.custom_targets_override?.target_fats_g || ''}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          custom_targets_override: {
                            ...profile.custom_targets_override,
                            target_fats_g: Number(e.target.value),
                          },
                        })
                      }
                      className="w-full px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-bold focus:outline-indigo-500"
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="text-[11px] font-bold text-slate-600 dark:text-slate-400 block mb-1">
                      Prescribed By / Clinician Name
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. Dr. Sarah Jenkins, MD / John Doe, RD"
                      value={profile.custom_targets_override?.prescribed_by || ''}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          custom_targets_override: {
                            ...profile.custom_targets_override,
                            prescribed_by: e.target.value,
                          },
                        })
                      }
                      className="w-full px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-medium focus:outline-indigo-500"
                    />
                  </div>

                  <div className="col-span-2">
                    <label className="text-[11px] font-bold text-slate-600 dark:text-slate-400 block mb-1">
                      Clinical Notes / Prescription Directives
                    </label>
                    <textarea
                      rows={2}
                      placeholder="e.g. Strict <2000mg sodium ceiling for Stage 2 hypertension management."
                      value={profile.custom_targets_override?.clinical_notes || ''}
                      onChange={(e) =>
                        setProfile({
                          ...profile,
                          custom_targets_override: {
                            ...profile.custom_targets_override,
                            clinical_notes: e.target.value,
                          },
                        })
                      }
                      className="w-full px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-medium focus:outline-indigo-500"
                    />
                  </div>
                </div>

                <button
                  type="button"
                  onClick={() => {
                    setProfile({
                      ...profile,
                      custom_targets_override: {
                        ...profile.custom_targets_override,
                        enabled: false,
                      },
                    });
                  }}
                  className="w-full py-1.5 rounded-xl text-xs font-bold text-slate-600 dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/30 border border-slate-200 dark:border-slate-700 transition-all cursor-pointer"
                >
                  Reset to Automated Formula
                </button>
              </div>
            )}
          </div>

          {/* Card: Derived Metabolic Matrix Breakdown */}
          <div className="rounded-2xl bg-gradient-to-br from-slate-900 to-slate-800 text-white p-6 shadow-lg space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                <BrainCircuit className="w-4 h-4" /> Computed Matrix
              </span>
              <span
                className={`text-[10px] px-2 py-0.5 rounded-full font-bold ${
                  profile.custom_targets_override?.enabled
                    ? 'bg-indigo-500/30 text-indigo-300 border border-indigo-400/40'
                    : 'bg-white/10 text-slate-300'
                }`}
              >
                {profile.custom_targets_override?.enabled ? '🩺 Clinician Rx Override' : 'Mifflin-St Jeor'}
              </span>
            </div>

            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between pb-2 border-b border-white/10 text-xs">
                <span className="text-slate-400">Basal Metabolic Rate (BMR)</span>
                <span className="font-bold">{targets.bmr_kcal ? `${targets.bmr_kcal} kcal` : '—'}</span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-white/10 text-xs">
                <span className="text-slate-400">Total Daily Expenditure (TDEE)</span>
                <span className="font-bold">{targets.tdee_kcal ? `${targets.tdee_kcal} kcal` : '—'}</span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-white/10 text-xs">
                <span className="text-emerald-400 font-bold">Target Calories / Day</span>
                <span className="font-black text-emerald-400 text-sm">
                  {targets.target_calories_kcal ? `${targets.target_calories_kcal} kcal` : '—'}
                </span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-white/10 text-xs">
                <span className="text-slate-400">Daily Protein Target</span>
                <span className="font-bold">{targets.target_protein_g ? `${targets.target_protein_g}g (${targets.target_protein_pct || 25}%)` : '—'}</span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-white/10 text-xs">
                <span className="text-slate-400">Daily Carbs Target</span>
                <span className="font-bold">{targets.target_carbs_g ? `${targets.target_carbs_g}g (${targets.target_carbs_pct || 50}%)` : '—'}</span>
              </div>

              <div className="flex items-center justify-between pb-2 border-b border-white/10 text-xs">
                <span className="text-slate-400">Daily Fats Target</span>
                <span className="font-bold">{targets.target_fats_g ? `${targets.target_fats_g}g (${targets.target_fats_pct || 25}%)` : '—'}</span>
              </div>

              <div className="flex items-center justify-between text-xs pt-1">
                <span className="text-amber-400 font-bold">Sodium Ceiling</span>
                <span className="font-black text-amber-400">
                  {guardrails.sodium_ceiling_mg ? `${guardrails.sodium_ceiling_mg} mg` : '2300 mg'}
                </span>
              </div>
            </div>

            <div className="p-3 bg-white/5 rounded-xl border border-white/10 text-[11px] text-slate-300 leading-relaxed">
              {targets.strategy_summary || 'Targeting optimal macro ratios.'}
            </div>

            {profile.custom_targets_override?.enabled && profile.custom_targets_override?.prescribed_by && (
              <div className="p-2.5 rounded-lg bg-indigo-950/40 border border-indigo-500/30 text-[10px] text-indigo-200">
                <span className="font-bold">Prescribing Clinician: </span>
                {profile.custom_targets_override.prescribed_by}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

