import React, { useState, useEffect, useMemo } from 'react';
import { Link } from 'react-router-dom';
import {
  Utensils,
  Trash2,
  Plus,
  Minus,
  Sparkles,
  Flame,
  Zap,
  ShieldAlert,
  History,
  BookmarkCheck,
  Check,
  ArrowRight,
  RefreshCw,
  Loader2,
  X,
  ChevronDown,
  ChevronUp,
  Salad,
  Info,
} from 'lucide-react';
import { useNutrition } from '../context/NutritionContext';
import { evaluatePlate, completePlate } from '../api';

const MEAL_SLOTS = ['Breakfast', 'Lunch', 'Snacks', 'Dinner'];

export default function PlatePage() {
  const {
    plate,
    handleUpdatePortion,
    handleRemoveFromPlate,
    handleClearPlate,
    handleAddToPlate,
    dishes,
    userMatrix,
    profile,
    loggedMeals,
    handleSaveMealToLog,
    handleRemoveLoggedMeal,
  } = useNutrition();

  const [evalData, setEvalData] = useState(null);
  const [loadingEval, setLoadingEval] = useState(false);
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [selectedSlot, setSelectedSlot] = useState('Lunch');
  const [showHistory, setShowHistory] = useState(true);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const todayStr = (() => {
    const d = new Date();
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  })();
  const todayUtcStr = new Date().toISOString().split('T')[0];

  // Filter logged meals for today (supporting both local and UTC date strings)
  const todayLoggedMeals = (loggedMeals || []).filter((m) => {
    const mealDate = m.date || (m.timestamp && String(m.timestamp).split('T')[0]);
    return mealDate === todayStr || mealDate === todayUtcStr;
  });

  // Calculate cumulative nutrition from previously logged meals today
  const previousTotals = todayLoggedMeals.reduce(
    (acc, meal) => {
      const cals = Number(meal.total_calories ?? meal.nutrients?.calories ?? 0);
      const prot = Number(meal.total_protein ?? meal.nutrients?.protein ?? 0);
      const carbs = Number(meal.total_carbs ?? meal.nutrients?.carbs ?? 0);
      const fat = Number(meal.total_fats ?? meal.nutrients?.fat ?? meal.nutrients?.fats ?? 0);
      const sod = Number(meal.total_sodium ?? meal.nutrients?.sodium ?? 0);
      const fib = Number(meal.nutrients?.fiber ?? 0);
      return {
        calories: acc.calories + cals,
        protein: acc.protein + prot,
        carbs: acc.carbs + carbs,
        fat: acc.fat + fat,
        sodium: acc.sodium + sod,
        fiber: acc.fiber + fib,
      };
    },
    { calories: 0, protein: 0, carbs: 0, fat: 0, sodium: 0, fiber: 0 }
  );

  // Evaluate current plate with backend clinical rules whenever dishes change
  useEffect(() => {
    if (!plate || plate.length === 0) {
      setEvalData(null);
      return;
    }

    let isMounted = true;
    async function fetchPlateEval() {
      setLoadingEval(true);
      try {
        const payload = {
          plate: plate.map((p) => ({ name: p.name, portion: p.portion || 1.0 })),
          matrix: userMatrix,
          profile: profile,
          api_key: profile?.api_key,
        };
        const res = await evaluatePlate(payload);
        if (isMounted && res?.success) {
          setEvalData(res.plate_evaluation);
        }
      } catch (err) {
        console.error('Error evaluating plate:', err);
      } finally {
        if (isMounted) setLoadingEval(false);
      }
    }

    fetchPlateEval();
    return () => {
      isMounted = false;
    };
  }, [plate, userMatrix, profile]);

  // AI Suggester: Auto-suggest companions
  const handleCompletePlate = async () => {
    if (!plate || plate.length === 0) return;
    setLoadingSuggestions(true);
    try {
      const payload = {
        plate: plate.map((p) => ({ name: p.name, portion: p.portion || 1.0 })),
        menu_dishes: (dishes || []).map((d) => d.name || d),
        matrix: userMatrix,
        profile: profile,
        api_key: profile?.api_key,
      };
      const res = await completePlate(payload);
      if (res?.success) {
        setSuggestions(res.suggestions || []);
      }
    } catch (err) {
      console.error('Error completing plate:', err);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  // Log active plate to today's meal history
  const handleLogAndSaveMeal = () => {
    if (!plate || plate.length === 0 || !handleSaveMealToLog) return;
    const now = new Date();
    const nut = evalData?.total_nutrients || { calories: 0, protein: 0, carbs: 0, fat: 0, sodium: 0, fiber: 0 };
    const mealEntry = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      name: `${selectedSlot} Plate`,
      meal_type: selectedSlot,
      mealSlot: selectedSlot,
      date: todayStr,
      timestamp: now.toISOString(),
      dishes: plate.map((p) => ({
        name: p.name,
        portion: p.portion || 1.0,
        price: p.price || '',
      })),
      items: plate.map((p) => ({
        name: p.name,
        portion: p.portion || 1.0,
        price: p.price || '',
      })),
      nutrients: nut,
      total_calories: Number(nut.calories) || 0,
      total_protein: Number(nut.protein) || 0,
      total_carbs: Number(nut.carbs) || 0,
      total_fats: Number(nut.fat) || 0,
      total_sodium: Number(nut.sodium) || 0,
    };

    handleSaveMealToLog(mealEntry);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3500);
  };

  const currentPlateNutrients = evalData?.total_nutrients || {
    calories: 0,
    protein: 0,
    carbs: 0,
    fat: 0,
    sodium: 0,
    fiber: 0,
  };

  const dailyTargets = {
    calories: Number(
      userMatrix?.metabolic_targets?.target_calories_kcal ||
        userMatrix?.metabolic_targets?.target_calories ||
        evalData?.daily_targets?.calories ||
        2000
    ),
    protein: Number(
      userMatrix?.metabolic_targets?.target_protein_g ||
        userMatrix?.metabolic_targets?.protein_g ||
        evalData?.daily_targets?.protein ||
        120
    ),
    carbs: Number(
      userMatrix?.metabolic_targets?.target_carbs_g ||
        userMatrix?.metabolic_targets?.carb_g ||
        evalData?.daily_targets?.carbs ||
        225
    ),
    fat: Number(
      userMatrix?.metabolic_targets?.target_fats_g ||
        userMatrix?.metabolic_targets?.fat_g ||
        evalData?.daily_targets?.fat ||
        65
    ),
    sodium_ceiling: Number(
      userMatrix?.nutritional_guardrails?.sodium_ceiling_mg ||
        userMatrix?.clinical_guardrails?.sodium_mg_ceiling ||
        evalData?.daily_targets?.sodium_ceiling ||
        2000
    ),
  };

  // Combined daily totals = Earlier logged meals + Currently staged plate
  const combinedCals = previousTotals.calories + currentPlateNutrients.calories;
  const combinedProtein = previousTotals.protein + currentPlateNutrients.protein;
  const combinedCarbs = previousTotals.carbs + currentPlateNutrients.carbs;
  const combinedFat = previousTotals.fat + currentPlateNutrients.fat;
  const combinedSodium = previousTotals.sodium + currentPlateNutrients.sodium;

  const remDailyCals = Math.max(0, dailyTargets.calories - combinedCals);
  const remDailyProtein = Math.max(0, dailyTargets.protein - combinedProtein);
  const remDailySodium = Math.max(0, dailyTargets.sodium_ceiling - combinedSodium);

  const prevCalsPct = Math.min(100, (previousTotals.calories / (dailyTargets.calories || 2000)) * 100);
  const currCalsPct = Math.min(100 - prevCalsPct, (currentPlateNutrients.calories / (dailyTargets.calories || 2000)) * 100);
  const totalCalsPct = Math.min(100, prevCalsPct + currCalsPct);

  const prevProtPct = Math.min(100, (previousTotals.protein / (dailyTargets.protein || 120)) * 100);
  const currProtPct = Math.min(100 - prevProtPct, (currentPlateNutrients.protein / (dailyTargets.protein || 120)) * 100);
  const totalProtPct = Math.min(100, prevProtPct + currProtPct);

  // Clinical Decision Support: Proactive Guardrail Threshold Breaches
  const clinicalAlerts = useMemo(() => {
    if (!plate || plate.length === 0) return [];
    const alerts = [];

    // 1. Sodium Ceiling Alert (Hypertension / Cardiovascular)
    if (combinedSodium > dailyTargets.sodium_ceiling) {
      const overage = Math.round(combinedSodium - dailyTargets.sodium_ceiling);
      alerts.push({
        id: 'sodium_excess',
        type: 'danger',
        title: 'Hypertension Safety Breach: Sodium Ceiling Exceeded',
        message: `Combined daily sodium (${Math.round(combinedSodium)} mg) exceeds your clinical ceiling (${Math.round(dailyTargets.sodium_ceiling)} mg) by +${overage} mg.`,
        action: 'Dial down portions (e.g. 0.5x portion) or substitute high-sodium items with steamed/grilled dishes to prevent blood pressure elevation.',
      });
    } else if (combinedSodium > dailyTargets.sodium_ceiling * 0.85) {
      alerts.push({
        id: 'sodium_warning',
        type: 'warning',
        title: 'Sodium Safety Warning: Approaching Daily Guardrail',
        message: `Staged plate brings today's sodium to ${Math.round((combinedSodium / dailyTargets.sodium_ceiling) * 100)}% of your ceiling. Only ${Math.round(remDailySodium)} mg safe allowance remaining.`,
        action: 'Maintain strict portion control and select low-sodium sides for any remaining meals today.',
      });
    }

    // 2. Caloric Over-Consumption Alert
    if (combinedCals > dailyTargets.calories * 1.15) {
      const overage = Math.round(combinedCals - dailyTargets.calories);
      alerts.push({
        id: 'calories_excess',
        type: 'warning',
        title: 'Caloric Surplus Alert: Target Exceeded',
        message: `Staged intake reaches ${Math.round(combinedCals)} kcal (${overage} kcal over your Mifflin-St Jeor target of ${Math.round(dailyTargets.calories)} kcal).`,
        action: 'Tune dish portion multipliers (e.g. 0.5x or 0.75x) to stay aligned with your daily metabolic deficit/budget.',
      });
    }

    // 3. Allergen Conflict Alert on Staged Dishes
    const userAllergies = (profile?.allergies || []).map((a) => a.toLowerCase());
    if (userAllergies.length > 0) {
      plate.forEach((dish) => {
        const dishObj = (dishes || []).find(
          (d) => (typeof d === 'string' ? d : d.name || '').toLowerCase() === (dish.name || '').toLowerCase()
        );
        const tags = (dishObj?.tags || []).map((t) => t.toLowerCase());
        const dishDesc = ((dishObj?.description || '') + ' ' + (dish.name || '')).toLowerCase();

        userAllergies.forEach((allergen) => {
          if (tags.includes(allergen) || dishDesc.includes(allergen)) {
            alerts.push({
              id: `allergen_${dish.name}_${allergen}`,
              type: 'danger',
              title: `Critical Allergen Warning: "${dish.name}"`,
              message: `May contain "${allergen}", which is declared as an active allergen in your medical profile.`,
              action: `Strict avoidance or staff verification advised. Inquire with chef regarding separate cookware.`,
            });
          }
        });
      });
    }

    return alerts;
  }, [plate, combinedSodium, combinedCals, dailyTargets, remDailySodium, profile, dishes]);

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-6 sm:p-8 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs">
        <div className="flex items-center gap-4">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Utensils className="w-7 h-7" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-black text-slate-900 dark:text-white tracking-tight">My Meal Plate</h1>
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-300 text-xs font-black uppercase tracking-wider border border-emerald-200 dark:border-emerald-800">
                {plate.length} {plate.length === 1 ? 'Dish Staged' : 'Dishes Staged'}
              </span>
            </div>
            <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
              Live meal staging, portion tuning, and real-time clinical calorie & macro burn-down.
            </p>
          </div>
        </div>

        {/* Header Actions */}
        <div className="flex items-center gap-3">
          <Link
            to="/menu"
            className="px-4 py-2.5 rounded-2xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold transition flex items-center gap-2"
          >
            <Salad className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Browse Menu Scanner</span>
          </Link>
          {plate.length > 0 && (
            <button
              onClick={handleClearPlate}
              className="px-4 py-2.5 rounded-2xl bg-rose-50 dark:bg-rose-950/40 hover:bg-rose-100 dark:hover:bg-rose-900/40 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-800 text-xs font-bold transition flex items-center gap-1.5 cursor-pointer"
            >
              <Trash2 className="w-4 h-4" />
              <span>Clear Plate</span>
            </button>
          )}
        </div>
      </div>

      {/* Real-Time Clinical Decision Support Alerts */}
      {clinicalAlerts.length > 0 && (
        <div className="space-y-3">
          {clinicalAlerts.map((alert) => (
            <div
              key={alert.id}
              className={`p-4 sm:p-5 rounded-2xl border flex flex-col sm:flex-row sm:items-start justify-between gap-3 shadow-xs animate-in slide-in-from-top-2 duration-200 ${
                alert.type === 'danger'
                  ? 'bg-rose-50 dark:bg-rose-950/40 border-rose-200 dark:border-rose-900/60 text-rose-950 dark:text-rose-100'
                  : 'bg-amber-50 dark:bg-amber-950/40 border-amber-200 dark:border-amber-800 text-amber-950 dark:text-amber-100'
              }`}
            >
              <div className="flex items-start gap-3">
                <div
                  className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-2xs mt-0.5 ${
                    alert.type === 'danger' ? 'bg-rose-600 text-white' : 'bg-amber-600 text-white'
                  }`}
                >
                  <ShieldAlert className="w-5 h-5 stroke-[2.5]" />
                </div>
                <div>
                  <h4 className="font-black text-sm flex items-center gap-2">
                    <span>{alert.title}</span>
                  </h4>
                  <p className="text-xs mt-1 leading-relaxed opacity-90 font-medium">{alert.message}</p>
                  <div className="mt-2 text-[11px] font-semibold opacity-95 flex items-center gap-1.5 bg-white/70 dark:bg-slate-900/60 px-3 py-1.5 rounded-xl border border-current/10 w-fit">
                    <span>💡 Clinical Recommendation:</span>
                    <span>{alert.action}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Main Grid: Left (Plate & Suggester) | Right (Intake Burn-Down & History) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Active Staged Dishes + Meal Logging + AI Companion */}
        <div className="lg:col-span-7 xl:col-span-7 space-y-6">
          {/* Active Plate Staging Section */}
          <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h2 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider flex items-center gap-2">
                <Utensils className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span>Currently Staged Dishes ({plate.length})</span>
              </h2>
              {loadingEval && (
                <span className="flex items-center gap-1 text-xs text-slate-400">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-500" /> Computing macros...
                </span>
              )}
            </div>

            {plate.length === 0 ? (
              <div className="text-center py-12 px-6 bg-slate-50 dark:bg-slate-800/40 border border-dashed border-slate-200 dark:border-slate-700 rounded-2xl space-y-3">
                <div className="w-12 h-12 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 flex items-center justify-center mx-auto">
                  <Utensils className="w-6 h-6" />
                </div>
                <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">Your Plate is Empty</h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                  Add dishes from the Menu Scanner to calculate instant portion adjustments, calories, protein, and health matrix compliance.
                </p>
                <Link
                  to="/menu"
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition shadow-sm mt-2"
                >
                  <Plus className="w-4 h-4" />
                  <span>Go to Menu Scanner</span>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                {plate.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/70 border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 transition shadow-xs flex items-center justify-between gap-4"
                  >
                    <div className="flex-1 min-w-0">
                      <h4 className="text-sm font-bold text-slate-900 dark:text-slate-100 truncate">{item.name}</h4>
                      <div className="flex items-center gap-2.5 mt-1 text-xs text-slate-500 dark:text-slate-400 font-medium">
                        <span className="font-semibold text-emerald-700 dark:text-emerald-400">
                          Portion: {item.portion || 1.0}x
                        </span>
                        {item.price && <span>• {item.price}</span>}
                      </div>
                      {item.customization && (
                        <div className="mt-1.5 px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-950/60 border border-amber-200 dark:border-amber-800 text-[10px] text-amber-800 dark:text-amber-300 font-bold flex items-center gap-1.5 w-fit">
                          <Sparkles className="w-3 h-3 text-amber-600 dark:text-amber-400 shrink-0" />
                          <span>Customized: {item.customization}</span>
                        </div>
                      )}
                    </div>

                    {/* Portion Controls */}
                    <div className="flex items-center gap-1.5 bg-white dark:bg-slate-900 p-1 rounded-xl border border-slate-200 dark:border-slate-700">
                      <button
                        onClick={() => handleUpdatePortion(item.name, Math.max(0.5, (item.portion || 1.0) - 0.5))}
                        disabled={(item.portion || 1.0) <= 0.5}
                        className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white disabled:opacity-30 transition cursor-pointer"
                        title="Decrease portion"
                      >
                        <Minus className="w-3.5 h-3.5" />
                      </button>
                      <span className="w-10 text-center text-xs font-black text-slate-800 dark:text-slate-200">
                        {item.portion || 1.0}x
                      </span>
                      <button
                        onClick={() => handleUpdatePortion(item.name, Math.min(3.0, (item.portion || 1.0) + 0.5))}
                        disabled={(item.portion || 1.0) >= 3.0}
                        className="w-7 h-7 rounded-lg bg-slate-100 dark:bg-slate-800 flex items-center justify-center text-slate-700 dark:text-slate-200 hover:text-slate-900 dark:hover:text-white disabled:opacity-30 transition cursor-pointer"
                        title="Increase portion"
                      >
                        <Plus className="w-3.5 h-3.5" />
                      </button>
                    </div>

                    {/* Delete Item */}
                    <button
                      onClick={() => handleRemoveFromPlate(item.name)}
                      className="p-2 text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-rose-50 dark:hover:bg-rose-950/40 rounded-xl transition cursor-pointer"
                      title="Remove from plate"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}

                {/* Staged Plate Immediate Macro Totals Bar */}
                <div className="p-4 rounded-2xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/80 mt-4 flex flex-wrap items-center justify-between gap-3 text-xs">
                  <div>
                    <span className="text-[11px] font-bold text-emerald-800 dark:text-emerald-300 block uppercase">
                      Current Plate Macros
                    </span>
                    <span className="text-base font-black text-emerald-950 dark:text-emerald-100">
                      {currentPlateNutrients.calories.toFixed(0)} kcal
                    </span>
                  </div>
                  <div className="flex items-center gap-4 text-xs font-semibold text-emerald-900 dark:text-emerald-200">
                    <span><b>{currentPlateNutrients.protein.toFixed(1)}g</b> Protein</span>
                    <span><b>{currentPlateNutrients.carbs.toFixed(1)}g</b> Carbs</span>
                    <span><b>{currentPlateNutrients.fat.toFixed(1)}g</b> Fats</span>
                    <span><b>{currentPlateNutrients.sodium.toFixed(0)}mg</b> Sodium</span>
                  </div>
                </div>

                {/* Meal Slot Logger Form */}
                <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-3 mt-4">
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <span className="text-xs font-bold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                      <BookmarkCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                      <span>Commit Staged Plate to Daily Calendar</span>
                    </span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">Meal Slot:</span>
                      <select
                        value={selectedSlot}
                        onChange={(e) => setSelectedSlot(e.target.value)}
                        className="text-xs font-bold bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 text-slate-900 dark:text-slate-100 rounded-xl px-3 py-1.5 focus:outline-none cursor-pointer"
                      >
                        {MEAL_SLOTS.map((s) => (
                          <option key={s} value={s}>
                            {s}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <button
                    onClick={handleLogAndSaveMeal}
                    className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition flex items-center justify-center gap-2 cursor-pointer shadow-md shadow-emerald-600/20"
                  >
                    {saveSuccess ? (
                      <>
                        <Check className="w-4 h-4 stroke-[3]" />
                        <span>Successfully Saved to Today's Meals!</span>
                      </>
                    ) : (
                      <>
                        <Plus className="w-4 h-4" />
                        <span>Log {selectedSlot} to Calendar & Reset Plate</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Section: "Complete My Plate" AI Companion Suggester */}
          <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 flex items-center justify-center">
                  <Zap className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white uppercase tracking-wider">
                    ✨ Complete My Plate (AI Suggester)
                  </h3>
                  <p className="text-xs text-slate-500 dark:text-slate-400">
                    Analyzes your current plate against your clinical matrix to find gap-filling side dishes.
                  </p>
                </div>
              </div>

              <button
                onClick={handleCompletePlate}
                disabled={loadingSuggestions || plate.length === 0}
                className="text-xs font-bold text-emerald-800 dark:text-emerald-200 bg-emerald-50 dark:bg-emerald-950/60 hover:bg-emerald-100 dark:hover:bg-emerald-900/60 border border-emerald-200 dark:border-emerald-800 px-3.5 py-2 rounded-xl transition cursor-pointer flex items-center gap-1.5 disabled:opacity-40"
              >
                {loadingSuggestions ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                <span>Auto-Suggest</span>
              </button>
            </div>

            {/* Suggestions Display */}
            {suggestions.length > 0 && (
              <div className="space-y-2.5 pt-2">
                {suggestions.map((sug, i) => (
                  <div
                    key={i}
                    className="p-4 rounded-2xl bg-amber-50/50 dark:bg-amber-950/30 border border-amber-200/80 dark:border-amber-800/60 flex items-center justify-between gap-4"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-slate-900 dark:text-slate-100 truncate">{sug.dish_name}</h4>
                        {sug.synergy_benefit && (
                          <span className="text-[10px] font-black text-amber-800 dark:text-amber-300 bg-amber-200/60 dark:bg-amber-900/50 px-2 py-0.5 rounded-md">
                            {sug.synergy_benefit}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-slate-600 dark:text-slate-300 mt-1">{sug.why_recommended}</p>
                    </div>

                    <button
                      onClick={() => {
                        handleAddToPlate({ name: sug.dish_name, portion: 1.0 });
                        setSuggestions(suggestions.filter((_, idx) => idx !== i));
                      }}
                      className="px-3.5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition flex items-center gap-1 shrink-0 cursor-pointer shadow-xs"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add to Plate
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Column: Daily Cumulative Intake & Target Burn-Down + Previous Meals */}
        <div className="lg:col-span-5 xl:col-span-5 space-y-6 lg:sticky lg:top-24">
          {/* Cumulative Burn-Down Card */}
          <div className="p-6 rounded-3xl bg-slate-900 text-white shadow-xl space-y-5 border border-slate-800">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Flame className="w-5 h-5 text-amber-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Daily Cumulative Intake
                </span>
              </div>
              <span className="text-xs font-bold text-emerald-400 bg-emerald-950/80 px-3 py-1 rounded-full border border-emerald-800">
                {combinedCals.toFixed(0)} / {dailyTargets.calories.toFixed(0)} kcal ({totalCalsPct.toFixed(0)}%)
              </span>
            </div>

            {/* Earlier vs This Plate Legend */}
            <div className="flex items-center justify-between text-xs bg-slate-800/80 p-3 rounded-2xl border border-slate-700/60">
              <span className="text-slate-400">
                Earlier Today: <b className="text-slate-200">{previousTotals.calories.toFixed(0)} kcal</b>
              </span>
              <span className="text-emerald-400">
                This Plate: <b>{currentPlateNutrients.calories.toFixed(0)} kcal</b>
              </span>
            </div>

            {/* Progress Bars */}
            <div className="space-y-4">
              {/* Calories */}
              <div>
                <div className="flex justify-between text-xs font-semibold mb-1.5 text-slate-300">
                  <span>Calories ({remDailyCals.toFixed(0)} kcal remaining)</span>
                  <span>{combinedCals.toFixed(0)} / {dailyTargets.calories.toFixed(0)} kcal</span>
                </div>
                <div className="w-full h-3 rounded-full bg-slate-800 flex overflow-hidden">
                  <div
                    className="h-full bg-blue-500 transition-all duration-500"
                    style={{ width: `${prevCalsPct}%` }}
                    title={`Earlier meals: ${previousTotals.calories.toFixed(0)} kcal`}
                  />
                  <div
                    className="h-full bg-emerald-500 transition-all duration-500"
                    style={{ width: `${currCalsPct}%` }}
                    title={`Current plate: ${currentPlateNutrients.calories.toFixed(0)} kcal`}
                  />
                </div>
              </div>

              {/* Protein */}
              <div>
                <div className="flex justify-between text-xs font-semibold mb-1.5 text-slate-300">
                  <span>Protein ({remDailyProtein.toFixed(1)}g to goal)</span>
                  <span className="text-emerald-400">
                    {combinedProtein.toFixed(1)}g / {dailyTargets.protein.toFixed(0)}g
                  </span>
                </div>
                <div className="w-full h-3 rounded-full bg-slate-800 flex overflow-hidden">
                  <div
                    className="h-full bg-indigo-500 transition-all duration-500"
                    style={{ width: `${prevProtPct}%` }}
                    title={`Earlier protein: ${previousTotals.protein.toFixed(1)}g`}
                  />
                  <div
                    className="h-full bg-emerald-400 transition-all duration-500"
                    style={{ width: `${currProtPct}%` }}
                    title={`Current plate protein: ${currentPlateNutrients.protein.toFixed(1)}g`}
                  />
                </div>
              </div>

              {/* Carbs & Fats Grid */}
              <div className="grid grid-cols-2 gap-3 pt-1">
                <div className="p-3 rounded-2xl bg-slate-800/80 border border-slate-700/60 text-center">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Carbs Today</span>
                  <span className="text-sm font-black text-slate-200">{combinedCarbs.toFixed(1)}g</span>
                </div>
                <div className="p-3 rounded-2xl bg-slate-800/80 border border-slate-700/60 text-center">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Fats Today</span>
                  <span className="text-sm font-black text-slate-200">{combinedFat.toFixed(1)}g</span>
                </div>
              </div>

              {/* Sodium Ceiling Alert */}
              <div className="pt-1">
                <div className="flex justify-between text-xs font-semibold mb-1.5">
                  <span className="flex items-center gap-1.5 text-slate-300">
                    <ShieldAlert className="w-3.5 h-3.5 text-amber-400" /> Sodium Guardrail ({remDailySodium.toFixed(0)} mg safe)
                  </span>
                  <span>{combinedSodium.toFixed(0)} / {dailyTargets.sodium_ceiling.toFixed(0)} mg</span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-800 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 rounded-full ${
                      combinedSodium / dailyTargets.sodium_ceiling > 0.8 ? 'bg-rose-500' : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, (combinedSodium / dailyTargets.sodium_ceiling) * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Today's Logged Meals History */}
          <div className="p-6 rounded-3xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xs space-y-4">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="flex items-center gap-2 text-xs font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wider hover:text-emerald-700 dark:hover:text-emerald-400 transition cursor-pointer"
              >
                <History className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
                <span>Today's Logged Meals ({todayLoggedMeals.length})</span>
                {showHistory ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
              <span className="text-xs font-semibold text-slate-500 dark:text-slate-400">
                {previousTotals.calories.toFixed(0)} kcal
              </span>
            </div>

            {showHistory && (
              <div className="space-y-3 pt-1">
                {todayLoggedMeals.length === 0 ? (
                  <div className="text-center py-6 text-xs text-slate-400 dark:text-slate-500 italic">
                    No meals logged today yet. Log your active plate above to record it in today's history.
                  </div>
                ) : (
                  todayLoggedMeals.map((meal) => (
                    <div
                      key={meal.id}
                      className="p-3.5 rounded-2xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700 space-y-2 shadow-2xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                          <span>🍳 {meal.mealSlot || meal.meal_type || 'Meal'}</span>
                          <span className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">
                            ({(meal.timestamp || '').split('T')[1]?.slice(0, 5) || 'Logged'})
                          </span>
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 px-2.5 py-0.5 rounded-lg border border-emerald-200 dark:border-emerald-800">
                            {(meal.total_calories || meal.nutrients?.calories || 0).toFixed(0)} kcal
                          </span>
                          {handleRemoveLoggedMeal && (
                            <button
                              onClick={() => handleRemoveLoggedMeal(meal.id)}
                              className="text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 p-1 transition cursor-pointer"
                              title="Delete logged meal"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Dishes in this previous plate */}
                      <div className="text-xs text-slate-600 dark:text-slate-300 pl-2 space-y-0.5 border-l-2 border-slate-200 dark:border-slate-700">
                        {(meal.items || meal.dishes || []).map((it, dIdx) => (
                          <div key={dIdx} className="flex justify-between">
                            <span className="truncate">{it.name}</span>
                            <span className="text-slate-400 dark:text-slate-500 text-[11px] shrink-0 ml-2">
                              {it.portion || 1}x
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
