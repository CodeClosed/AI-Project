import React, { useState, useEffect } from 'react';
import { 
  X, Trash2, Plus, Minus, Sparkles, Utensils, Zap, ShieldAlert, 
  CheckCircle2, Flame, Heart, Loader2, ArrowRight, RefreshCw, BookmarkCheck,
  Clock, Calendar, History, Check, ChevronDown, ChevronUp
} from 'lucide-react';
import { evaluatePlate, completePlate } from '../api';

const MEAL_SLOTS = ['Breakfast', 'Lunch', 'Snacks', 'Dinner'];

export default function MealPlateDrawer({
  isOpen,
  onClose,
  plate,
  onUpdatePortion,
  onRemoveItem,
  onClearPlate,
  onAddItem,
  allDishes,
  userMatrix,
  profile,
  loggedMeals = [],
  onSaveMealToLog,
  onRemoveLoggedMeal,
}) {
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

  // Filter logged meals for today
  const todayLoggedMeals = loggedMeals.filter((m) => m.date === todayStr);

  // Sum nutritional values from previously logged meals today
  const previousTotals = todayLoggedMeals.reduce(
    (acc, meal) => {
      const nut = meal.nutrients || {};
      return {
        calories: acc.calories + (Number(nut.calories) || 0),
        protein: acc.protein + (Number(nut.protein) || 0),
        carbs: acc.carbs + (Number(nut.carbs) || 0),
        fat: acc.fat + (Number(nut.fat) || 0),
        sodium: acc.sodium + (Number(nut.sodium) || 0),
        fiber: acc.fiber + (Number(nut.fiber) || 0),
      };
    },
    { calories: 0, protein: 0, carbs: 0, fat: 0, sodium: 0, fiber: 0 }
  );

  // Re-evaluate plate whenever plate items change
  useEffect(() => {
    if (!isOpen || plate.length === 0) {
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
    return () => { isMounted = false; };
  }, [plate, isOpen, userMatrix, profile]);

  const handleCompletePlate = async () => {
    if (plate.length === 0) return;
    setLoadingSuggestions(true);
    try {
      const payload = {
        plate: plate.map((p) => ({ name: p.name, portion: p.portion || 1.0 })),
        menu_dishes: allDishes.map((d) => d.name || d),
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

  const handleLogAndSaveMeal = () => {
    if (plate.length === 0 || !onSaveMealToLog) return;
    const now = new Date();
    const mealEntry = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      date: todayStr,
      mealSlot: selectedSlot,
      timestamp: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      items: plate.map((p) => ({
        name: p.name,
        portion: p.portion || 1.0,
        price: p.price || '',
      })),
      nutrients: evalData?.total_nutrients || { calories: 0, protein: 0, carbs: 0, fat: 0, sodium: 0, fiber: 0 },
    };

    onSaveMealToLog(mealEntry);
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  if (!isOpen) return null;

  const currentPlateNutrients = evalData?.total_nutrients || { calories: 0, protein: 0, carbs: 0, fat: 0, sodium: 0, fiber: 0 };
  const dailyTargets = {
    calories: Number(userMatrix?.metabolic_targets?.target_calories_kcal || userMatrix?.metabolic_targets?.target_calories || evalData?.daily_targets?.calories || 2000),
    protein: Number(userMatrix?.metabolic_targets?.target_protein_g || userMatrix?.metabolic_targets?.protein_g || evalData?.daily_targets?.protein || 120),
    carbs: Number(userMatrix?.metabolic_targets?.target_carbs_g || userMatrix?.metabolic_targets?.carb_g || evalData?.daily_targets?.carbs || 225),
    fat: Number(userMatrix?.metabolic_targets?.target_fats_g || userMatrix?.metabolic_targets?.fat_g || evalData?.daily_targets?.fat || 65),
    sodium_ceiling: Number(userMatrix?.nutritional_guardrails?.sodium_ceiling_mg || userMatrix?.clinical_guardrails?.sodium_mg_ceiling || evalData?.daily_targets?.sodium_ceiling || 2000),
  };

  // Combined daily totals = Previous meals logged today + Current active plate
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

  return (
    <div className="fixed inset-0 z-50 overflow-hidden flex justify-end bg-slate-900/60 backdrop-blur-xs transition-opacity duration-300">
      <div 
        className="w-full max-w-xl bg-white h-full shadow-2xl flex flex-col border-l border-slate-200 animate-in slide-in-from-right duration-300"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 py-5 border-b border-slate-200 bg-slate-50/80 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-600 text-white flex items-center justify-center shadow-md shadow-emerald-500/20">
              <Utensils className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-900 leading-tight">My Active Meal Plate</h2>
                <span className="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-black uppercase tracking-wider">
                  {plate.length} {plate.length === 1 ? 'Dish on Plate' : 'Dishes on Plate'}
                </span>
              </div>
              <p className="text-xs text-slate-500">Track current plate + previous logged meals against daily targets</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-200/60 transition cursor-pointer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Section 1: Active Plate Dishes */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold text-slate-700 uppercase tracking-wider flex items-center gap-1.5">
                <Utensils className="w-3.5 h-3.5 text-emerald-600" />
                <span>Current Plate Items ({plate.length})</span>
              </h3>
              {plate.length > 0 && (
                <button
                  onClick={onClearPlate}
                  className="text-xs font-semibold text-rose-600 hover:text-rose-700 transition cursor-pointer flex items-center gap-1"
                >
                  <Trash2 className="w-3.5 h-3.5" /> Clear Plate
                </button>
              )}
            </div>

            {plate.length === 0 ? (
              <div className="text-center py-8 px-4 bg-slate-50 border border-dashed border-slate-200 rounded-2xl">
                <p className="text-xs text-slate-500">
                  Your current plate is empty. Click <b>"+ Add to Plate"</b> on any dish card to add items.
                </p>
              </div>
            ) : (
              <div className="space-y-2">
                {plate.map((item, idx) => (
                  <div
                    key={idx}
                    className="p-3.5 rounded-2xl bg-white border border-slate-200 hover:border-slate-300 transition shadow-xs flex items-center justify-between gap-3"
                  >
                    <div className="flex-1 min-w-0">
                      <h4 className="text-xs font-bold text-slate-900 truncate">{item.name}</h4>
                      <div className="flex items-center gap-2 mt-0.5 text-[11px] text-slate-500 font-medium">
                        <span>Portion: {item.portion || 1.0}x</span>
                        {item.price && <span>• {item.price}</span>}
                      </div>
                    </div>

                    {/* Portion Controls */}
                    <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl border border-slate-200">
                      <button
                        onClick={() => onUpdatePortion(item.name, Math.max(0.5, (item.portion || 1.0) - 0.5))}
                        disabled={(item.portion || 1.0) <= 0.5}
                        className="w-6 h-6 rounded-lg bg-white flex items-center justify-center text-slate-600 hover:text-slate-900 disabled:opacity-40 transition cursor-pointer shadow-2xs"
                      >
                        <Minus className="w-3 h-3" />
                      </button>
                      <span className="w-8 text-center text-xs font-bold text-slate-800">{item.portion || 1.0}x</span>
                      <button
                        onClick={() => onUpdatePortion(item.name, Math.min(3.0, (item.portion || 1.0) + 0.5))}
                        disabled={(item.portion || 1.0) >= 3.0}
                        className="w-6 h-6 rounded-lg bg-white flex items-center justify-center text-slate-600 hover:text-slate-900 disabled:opacity-40 transition cursor-pointer shadow-2xs"
                      >
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>

                    {/* Remove Button */}
                    <button
                      onClick={() => onRemoveItem(item.name)}
                      className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition cursor-pointer"
                      title="Remove dish"
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ))}

                {/* Log & Save Plate Action */}
                <div className="p-3.5 rounded-2xl bg-emerald-50/70 border border-emerald-200 space-y-2 mt-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-emerald-950 flex items-center gap-1.5">
                      <BookmarkCheck className="w-4 h-4 text-emerald-700" /> Save as Logged Meal
                    </span>
                    <select
                      value={selectedSlot}
                      onChange={(e) => setSelectedSlot(e.target.value)}
                      className="text-xs font-bold bg-white border border-emerald-300 text-emerald-900 rounded-lg px-2.5 py-1 focus:outline-none cursor-pointer"
                    >
                      {MEAL_SLOTS.map((s) => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>

                  <button
                    onClick={handleLogAndSaveMeal}
                    className="w-full py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold rounded-xl transition flex items-center justify-center gap-1.5 cursor-pointer shadow-xs"
                  >
                    {saveSuccess ? (
                      <>
                        <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                        <span>Saved to Today's Meals!</span>
                      </>
                    ) : (
                      <>
                        <Plus className="w-3.5 h-3.5" />
                        <span>Log {selectedSlot} & Clear for Next Meal</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Section 2: Combined Daily Macro Budget Burn-Down Card */}
          <div className="p-5 rounded-3xl bg-slate-900 text-white shadow-lg space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <Flame className="w-4 h-4 text-amber-400" />
                <span className="text-xs font-bold uppercase tracking-wider text-slate-300">
                  Daily Cumulative Intake
                </span>
              </div>
              <span className="text-xs font-bold text-emerald-400 bg-emerald-950/80 px-2.5 py-0.5 rounded-full border border-emerald-800">
                {combinedCals.toFixed(0)} / {dailyTargets.calories.toFixed(0)} kcal ({totalCalsPct.toFixed(0)}%)
              </span>
            </div>

            {/* Split Breakdown Tags */}
            <div className="flex items-center justify-between text-[11px] bg-slate-800/80 p-2.5 rounded-xl border border-slate-700/60">
              <span className="text-slate-400">
                Earlier Today: <b className="text-slate-200">{previousTotals.calories.toFixed(0)} kcal</b> ({previousTotals.protein.toFixed(1)}g P)
              </span>
              <span className="text-emerald-400">
                This Plate: <b>{currentPlateNutrients.calories.toFixed(0)} kcal</b> ({currentPlateNutrients.protein.toFixed(1)}g P)
              </span>
            </div>

            {/* Progress Bars */}
            <div className="space-y-3">
              {/* Calories Bar (Two-tone: Earlier + Current) */}
              <div>
                <div className="flex justify-between text-[11px] font-semibold mb-1 text-slate-300">
                  <span>Calories ({remDailyCals.toFixed(0)} kcal remaining)</span>
                  <span>{combinedCals.toFixed(0)} / {dailyTargets.calories.toFixed(0)} kcal</span>
                </div>
                <div className="w-full h-2.5 rounded-full bg-slate-800 flex overflow-hidden">
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

              {/* Protein Bar */}
              <div>
                <div className="flex justify-between text-[11px] font-semibold mb-1 text-slate-300">
                  <span>Protein ({remDailyProtein.toFixed(1)}g to goal)</span>
                  <span className="text-emerald-400">{combinedProtein.toFixed(1)}g / {dailyTargets.protein.toFixed(0)}g</span>
                </div>
                <div className="w-full h-2.5 rounded-full bg-slate-800 flex overflow-hidden">
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
                <div className="p-2.5 rounded-2xl bg-slate-800/80 border border-slate-700/60 text-center">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Carbs Today</span>
                  <span className="text-sm font-black text-slate-200">{combinedCarbs.toFixed(1)}g</span>
                </div>
                <div className="p-2.5 rounded-2xl bg-slate-800/80 border border-slate-700/60 text-center">
                  <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Fats Today</span>
                  <span className="text-sm font-black text-slate-200">{combinedFat.toFixed(1)}g</span>
                </div>
              </div>

              {/* Sodium Alert Bar */}
              <div className="pt-1">
                <div className="flex justify-between text-[11px] font-semibold mb-1">
                  <span className="flex items-center gap-1 text-slate-300">
                    <ShieldAlert className="w-3 h-3 text-amber-400" /> Sodium Ceiling ({remDailySodium.toFixed(0)} mg safe remaining)
                  </span>
                  <span>
                    {combinedSodium.toFixed(0)} / {dailyTargets.sodium_ceiling.toFixed(0)} mg
                  </span>
                </div>
                <div className="w-full h-1.5 rounded-full bg-slate-800 overflow-hidden">
                  <div 
                    className={`h-full transition-all duration-500 rounded-full ${
                      (combinedSodium / dailyTargets.sodium_ceiling) > 0.8 ? 'bg-rose-500' : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, (combinedSodium / dailyTargets.sodium_ceiling) * 100)}%` }}
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Section 3: Today's Previously Logged Meals History */}
          <div className="space-y-3 bg-slate-50/70 border border-slate-200 rounded-3xl p-4">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setShowHistory(!showHistory)}
                className="flex items-center gap-2 text-xs font-bold text-slate-800 uppercase tracking-wider hover:text-emerald-700 transition cursor-pointer"
              >
                <History className="w-3.5 h-3.5 text-emerald-600" />
                <span>Today's Logged Meals ({todayLoggedMeals.length})</span>
                {showHistory ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
              </button>
              <span className="text-[11px] font-semibold text-slate-500">
                {previousTotals.calories.toFixed(0)} kcal logged
              </span>
            </div>

            {showHistory && (
              <div className="space-y-2 pt-1">
                {todayLoggedMeals.length === 0 ? (
                  <div className="text-center py-4 text-xs text-slate-400 italic">
                    No previous meals logged today. When you finish a plate, click "Log Meal & Clear for Next Meal" above.
                  </div>
                ) : (
                  todayLoggedMeals.map((meal) => (
                    <div
                      key={meal.id}
                      className="p-3 rounded-2xl bg-white border border-slate-200 space-y-1.5 shadow-2xs"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold text-slate-900 flex items-center gap-1.5">
                          <span>🍳 {meal.mealSlot}</span>
                          <span className="text-[10px] text-slate-400 font-normal">({meal.timestamp})</span>
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200">
                            {meal.nutrients?.calories?.toFixed(0) || 0} kcal • {meal.nutrients?.protein?.toFixed(1) || 0}g P
                          </span>
                          {onRemoveLoggedMeal && (
                            <button
                              onClick={() => onRemoveLoggedMeal(meal.id)}
                              className="text-slate-400 hover:text-rose-600 p-1 transition cursor-pointer"
                              title="Delete logged meal"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>

                      {/* Dishes on this previous plate */}
                      <div className="text-xs text-slate-600 pl-2 space-y-0.5 border-l-2 border-slate-100">
                        {meal.items?.map((it, dIdx) => (
                          <div key={dIdx} className="flex justify-between">
                            <span className="truncate">{it.name}</span>
                            <span className="text-slate-400 text-[11px] shrink-0 ml-2">{it.portion || 1}x</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>

          {/* Section 4: "Complete My Plate" AI Companion Suggester */}
          <div className="p-5 rounded-3xl bg-white border border-slate-200 shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Zap className="w-4 h-4 text-amber-500" />
                <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                  ✨ Complete My Plate
                </h3>
              </div>
              <button
                onClick={handleCompletePlate}
                disabled={loadingSuggestions || plate.length === 0}
                className="text-xs font-bold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-3 py-1.5 rounded-xl transition cursor-pointer flex items-center gap-1.5 disabled:opacity-40"
              >
                {loadingSuggestions ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <RefreshCw className="w-3.5 h-3.5" />}
                <span>Auto-Suggest Companions</span>
              </button>
            </div>

            <p className="text-xs text-slate-500">
              Scans remaining dishes on the menu matching your health matrix to fill nutritional gaps.
            </p>

            {/* Suggestions List */}
            {suggestions.length > 0 && (
              <div className="space-y-2 pt-2">
                {suggestions.map((sug, i) => (
                  <div
                    key={i}
                    className="p-3.5 rounded-2xl bg-amber-50/50 border border-amber-200/80 flex items-center justify-between gap-3"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <h4 className="text-xs font-bold text-slate-900 truncate">{sug.dish_name}</h4>
                        {sug.synergy_benefit && (
                          <span className="text-[10px] font-black text-amber-800 bg-amber-200/60 px-2 py-0.5 rounded-md">
                            {sug.synergy_benefit}
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-slate-600 mt-0.5">{sug.why_recommended}</p>
                    </div>

                    <button
                      onClick={() => {
                        onAddItem({ name: sug.dish_name, portion: 1.0 });
                        setSuggestions(suggestions.filter((_, idx) => idx !== i));
                      }}
                      className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold transition flex items-center gap-1 shrink-0 cursor-pointer shadow-xs"
                    >
                      <Plus className="w-3.5 h-3.5" /> Add
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Drawer Footer */}
        <div className="p-5 border-t border-slate-200 bg-slate-50 flex items-center justify-between gap-3">
          <div>
            <span className="text-[10px] uppercase font-bold text-slate-400 block">Total Daily Intake</span>
            <span className="text-base font-black text-slate-900">{combinedCals.toFixed(0)} kcal</span>
          </div>
          <button
            onClick={onClose}
            className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold px-6 py-2.5 rounded-xl transition cursor-pointer shadow-md shadow-emerald-500/20 flex items-center gap-2"
          >
            <span>Done Tracking</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
