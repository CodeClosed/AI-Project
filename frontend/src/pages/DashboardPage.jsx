import React, { useMemo } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  Salad,
  Calendar,
  Utensils,
  HeartPulse,
  Flame,
  Dumbbell,
  Wheat,
  Droplet,
  ShieldAlert,
  ArrowRight,
  Sparkles,
  CheckCircle2,
  Clock,
  Plus,
  ShieldCheck,
  Zap,
  Trash2,
} from 'lucide-react';
import { useNutrition } from '../context/NutritionContext';
import { useAuth } from '../context/AuthContext';

export default function DashboardPage() {
  const { user, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const {
    profile,
    userMatrix,
    loggedMeals,
    dishes,
    plate,
    handleSaveMealToLog,
    handleRemoveLoggedMeal,
  } = useNutrition();

  const targets = userMatrix?.metabolic_targets || {
    target_calories_kcal: 2000,
    target_protein_g: 130,
    target_carbs_g: 220,
    target_fats_g: 65,
    sodium_ceiling_mg: 2300,
  };

  const guardrails = userMatrix?.nutritional_guardrails || {
    sodium_ceiling_mg: 2300,
  };

  const getLocalDateStr = (d = new Date()) => {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  };
  const todayLocal = getLocalDateStr();
  const todayUtc = new Date().toISOString().split('T')[0];

  // Match meals logged on today (local date or UTC date fallback)
  const todaysMeals = (loggedMeals || []).filter((m) => {
    const mealDate = m.date || (m.timestamp && String(m.timestamp).split('T')[0]);
    return mealDate === todayLocal || mealDate === todayUtc;
  });

  const consumedToday = todaysMeals.reduce(
    (acc, m) => {
      const nut = m.nutrients || {};
      const cals = Number(m.total_calories) || Number(nut.calories) || 0;
      const prot = Number(m.total_protein) || Number(nut.protein) || 0;
      const carbs = Number(m.total_carbs) || Number(nut.carbs) || 0;
      const fats = Number(m.total_fats) || Number(nut.fat) || Number(nut.fats) || 0;
      const sod = Number(m.total_sodium) || Number(nut.sodium) || 0;
      return {
        calories: acc.calories + cals,
        protein: acc.protein + prot,
        carbs: acc.carbs + carbs,
        fats: acc.fats + fats,
        sodium: acc.sodium + sod,
      };
    },
    { calories: 0, protein: 0, carbs: 0, fats: 0, sodium: 0 }
  );

  // Estimate staged active plate nutrients
  const stagedPlateNutrients = useMemo(() => {
    if (!plate || plate.length === 0) {
      return { calories: 0, protein: 0, carbs: 0, fats: 0, sodium: 0 };
    }
    let cals = 0, prot = 0, carbs = 0, fats = 0, sod = 0;
    plate.forEach((p) => {
      const portion = Number(p.portion) || 1.0;
      const matched = dishes.find(
        (d) => (typeof d === 'string' ? d : d.name || '').toLowerCase() === (p.name || '').toLowerCase()
      );
      const dishNut = p.nutrients || (matched && typeof matched === 'object' ? matched.nutrients || matched : {}) || {};
      cals += (Number(dishNut.calories || matched?.calories) || 380) * portion;
      prot += (Number(dishNut.protein || matched?.protein) || 20) * portion;
      carbs += (Number(dishNut.carbs || matched?.carbs) || 45) * portion;
      fats += (Number(dishNut.fat || matched?.fat || dishNut.fats) || 14) * portion;
      sod += (Number(dishNut.sodium || matched?.sodium) || 420) * portion;
    });
    return {
      calories: Math.round(cals),
      protein: Math.round(prot),
      carbs: Math.round(carbs),
      fats: Math.round(fats),
      sodium: Math.round(sod),
    };
  }, [plate, dishes]);

  const handleQuickLogPlate = () => {
    if (plate.length === 0 || !handleSaveMealToLog) return;
    const now = new Date();
    const mealEntry = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      name: `Plate (${plate.length} dishes)`,
      meal_type: 'Lunch',
      date: todayLocal,
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
      nutrients: {
        calories: stagedPlateNutrients.calories,
        protein: stagedPlateNutrients.protein,
        carbs: stagedPlateNutrients.carbs,
        fat: stagedPlateNutrients.fats,
        sodium: stagedPlateNutrients.sodium,
        fiber: 5,
      },
      total_calories: stagedPlateNutrients.calories,
      total_protein: stagedPlateNutrients.protein,
      total_carbs: stagedPlateNutrients.carbs,
      total_fats: stagedPlateNutrients.fats,
      total_sodium: stagedPlateNutrients.sodium,
    };
    handleSaveMealToLog(mealEntry);
  };

  const handleQuickLogSampleMeal = (slot = 'Lunch') => {
    if (!handleSaveMealToLog) return;
    const now = new Date();
    const sample = slot === 'Breakfast'
      ? { name: 'Oatmeal & Boiled Eggs', cals: 420, p: 24, c: 52, f: 12, s: 280 }
      : slot === 'Lunch'
      ? { name: 'Grilled Chicken & Quinoa Salad', cals: 580, p: 44, c: 55, f: 18, s: 490 }
      : { name: 'Baked Salmon & Greens', cals: 510, p: 38, c: 22, f: 28, s: 390 };

    const mealEntry = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      name: sample.name,
      meal_type: slot,
      date: todayLocal,
      timestamp: now.toISOString(),
      dishes: [{ name: sample.name, portion: 1.0, price: '' }],
      items: [{ name: sample.name, portion: 1.0, price: '' }],
      nutrients: {
        calories: sample.cals,
        protein: sample.p,
        carbs: sample.c,
        fat: sample.f,
        sodium: sample.s,
        fiber: 6,
      },
      total_calories: sample.cals,
      total_protein: sample.p,
      total_carbs: sample.c,
      total_fats: sample.f,
      total_sodium: sample.s,
    };
    handleSaveMealToLog(mealEntry);
  };

  const calProgress = Math.min(100, Math.round((consumedToday.calories / (targets.target_calories_kcal || 2000)) * 100));
  const protProgress = Math.min(100, Math.round((consumedToday.protein / (targets.target_protein_g || 1)) * 100));
  const carbsProgress = Math.min(100, Math.round((consumedToday.carbs / (targets.target_carbs_g || 1)) * 100));
  const fatProgress = Math.min(100, Math.round((consumedToday.fats / (targets.target_fats_g || 65)) * 100));
  const sodiumCeiling = guardrails.sodium_ceiling_mg || 2300;
  const sodiumProgress = Math.min(100, Math.round((consumedToday.sodium / sodiumCeiling) * 100));

  return (
    <div className="space-y-10 animate-in fade-in duration-200">
      {/* 1. Welcome Hero Banner */}
      <div className="rounded-3xl bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-950 text-white p-6 sm:p-8 shadow-xl relative overflow-hidden border border-slate-800">
        <div className="relative z-10 max-w-3xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/30 text-emerald-300 text-xs font-semibold backdrop-blur-md">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Clinical Decision Support Engine Active</span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-black tracking-tight leading-tight">
            Welcome back{isAuthenticated && user?.email ? `, ${user.email.split('@')[0]}` : ''}!
          </h1>

          <p className="text-slate-300 text-sm sm:text-base leading-relaxed max-w-2xl">
            NutriMenu AI dynamically screens restaurant menus against your clinical conditions,
            sodium ceilings, and macro targets to curate the safest, highest-scoring dishes.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <Link
              to="/menu"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-bold text-sm shadow-md transition-all hover:scale-102 cursor-pointer"
            >
              <Salad className="w-4 h-4" />
              <span>Scan New Menu</span>
              <ArrowRight className="w-4 h-4 ml-0.5" />
            </Link>

            <Link
              to="/calendar"
              className="inline-flex items-center gap-2 px-5 py-2.5 rounded-full bg-white/10 hover:bg-white/20 text-white font-semibold text-sm backdrop-blur-sm border border-white/10 transition cursor-pointer"
            >
              <Calendar className="w-4 h-4 text-emerald-400" />
              <span>View Meal Log</span>
            </Link>

            {plate.length > 0 && (
              <button
                onClick={() => navigate('/plate')}
                className="inline-flex items-center gap-2 px-4 py-2.5 rounded-full bg-emerald-900/60 hover:bg-emerald-800/80 text-emerald-200 border border-emerald-500/40 text-xs font-bold transition cursor-pointer"
              >
                <Utensils className="w-3.5 h-3.5" />
                <span>Plate: {plate.length} staged</span>
              </button>
            )}
          </div>
        </div>

        {/* Decorative graphic background pattern */}
        <div className="absolute -right-10 -bottom-10 w-80 h-80 rounded-full bg-emerald-500/10 blur-3xl pointer-events-none" />
        <div className="absolute right-12 top-10 opacity-10 hidden lg:block pointer-events-none">
          <Salad className="w-64 h-64 text-emerald-300" />
        </div>
      </div>

      {/* 2. Target Macros & Daily Progress Grid (Complete 5-Metric Suite with Fats) */}
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400 flex items-center gap-2">
            <Flame className="w-4 h-4 text-amber-500" />
            <span>Today's Caloric & Macronutrient Compliance</span>
          </h2>
          <span className="text-xs text-slate-400 dark:text-slate-500 font-medium">
            Based on Mifflin-St Jeor Formula
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {/* 1. Calories Card */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 shadow-xs flex flex-col justify-between transition-colors">
            <div className="flex items-center justify-between text-slate-600 dark:text-slate-400 mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Daily Calories</span>
              <div className="w-8 h-8 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center font-bold">
                <Flame className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-black text-slate-900 dark:text-white tabular-nums">
                {Math.round(consumedToday.calories)}{' '}
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">
                  / {Math.round(targets.target_calories_kcal)} kcal
                </span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 mt-3 overflow-hidden">
                <div
                  className="bg-amber-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${calProgress}%` }}
                />
              </div>
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 flex justify-between font-medium">
              <span>{calProgress}% consumed</span>
              <span>{Math.max(0, Math.round(targets.target_calories_kcal - consumedToday.calories))} kcal left</span>
            </div>
          </div>

          {/* 2. Protein Card */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 shadow-xs flex flex-col justify-between transition-colors">
            <div className="flex items-center justify-between text-slate-600 dark:text-slate-400 mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Protein</span>
              <div className="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 flex items-center justify-center font-bold">
                <Dumbbell className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-black text-slate-900 dark:text-white tabular-nums">
                {Math.round(consumedToday.protein)}g{' '}
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">
                  / {Math.round(targets.target_protein_g)}g
                </span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 mt-3 overflow-hidden">
                <div
                  className="bg-indigo-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${protProgress}%` }}
                />
              </div>
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 font-medium flex justify-between">
              <span>{protProgress}% of target</span>
              <span>{(targets.target_protein_pct || 25)}% ratio</span>
            </div>
          </div>

          {/* 3. Carbohydrates Card */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 shadow-xs flex flex-col justify-between transition-colors">
            <div className="flex items-center justify-between text-slate-600 dark:text-slate-400 mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Carbohydrates</span>
              <div className="w-8 h-8 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold">
                <Wheat className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-black text-slate-900 dark:text-white tabular-nums">
                {Math.round(consumedToday.carbs)}g{' '}
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">
                  / {Math.round(targets.target_carbs_g)}g
                </span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 mt-3 overflow-hidden">
                <div
                  className="bg-emerald-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${carbsProgress}%` }}
                />
              </div>
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 font-medium flex justify-between">
              <span>{carbsProgress}% of target</span>
              <span>Low-GI target</span>
            </div>
          </div>

          {/* 4. Dietary Fats Card (Fixed: Added full fat macro support!) */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 shadow-xs flex flex-col justify-between transition-colors">
            <div className="flex items-center justify-between text-slate-600 dark:text-slate-400 mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Dietary Fats</span>
              <div className="w-8 h-8 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center font-bold">
                <Zap className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-black text-slate-900 dark:text-white tabular-nums">
                {Math.round(consumedToday.fats)}g{' '}
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">
                  / {Math.round(targets.target_fats_g || 65)}g
                </span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 mt-3 overflow-hidden">
                <div
                  className="bg-amber-500 h-2 rounded-full transition-all duration-500"
                  style={{ width: `${fatProgress}%` }}
                />
              </div>
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 font-medium flex justify-between">
              <span>{fatProgress}% consumed</span>
              <span>Healthy lipids</span>
            </div>
          </div>

          {/* 5. Sodium Guardrail Card */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-5 shadow-xs flex flex-col justify-between transition-colors">
            <div className="flex items-center justify-between text-slate-600 dark:text-slate-400 mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">Sodium Ceiling</span>
              <div className="w-8 h-8 rounded-xl bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 flex items-center justify-center font-bold">
                <Droplet className="w-4 h-4" />
              </div>
            </div>
            <div>
              <div className="text-2xl font-black text-slate-900 dark:text-white tabular-nums">
                {Math.round(consumedToday.sodium)}mg{' '}
                <span className="text-xs font-semibold text-slate-400 dark:text-slate-500">
                  / {sodiumCeiling}mg
                </span>
              </div>
              <div className="w-full bg-slate-100 dark:bg-slate-800 rounded-full h-2 mt-3 overflow-hidden">
                <div
                  className={`h-2 rounded-full transition-all duration-500 ${
                    consumedToday.sodium > sodiumCeiling ? 'bg-rose-500' : 'bg-teal-500'
                  }`}
                  style={{ width: `${sodiumProgress}%` }}
                />
              </div>
            </div>
            <div className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 font-medium">
              {(profile.health_conditions || []).includes('hypertension') ? 'Strict 1,800mg HTN Cap Active' : 'Standard 2,300mg Cap'}
            </div>
          </div>
        </div>
      </div>

      {/* 3. Living Data Hub: Today's Logged Meals + Active Plate Staging */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Today's Meals Timeline (7 cols) */}
        <div className="lg:col-span-7 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-xs space-y-4 transition-colors">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold">
                <Calendar className="w-4 h-4" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Today's Meal Timeline</h3>
                <span className="text-[11px] text-slate-400">
                  {todaysMeals.length} {todaysMeals.length === 1 ? 'meal entry' : 'meal entries'} recorded today
                </span>
              </div>
            </div>

            <Link
              to="/calendar"
              className="text-xs font-bold text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 flex items-center gap-1 cursor-pointer"
            >
              <span>Full Calendar</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
          </div>

          {todaysMeals.length === 0 ? (
            <div className="p-8 text-center bg-slate-50/70 dark:bg-slate-800/40 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 space-y-3">
              <Utensils className="w-8 h-8 text-slate-400 mx-auto opacity-60" />
              <div>
                <h4 className="text-xs font-bold text-slate-800 dark:text-slate-200">No Meals Logged Yet Today</h4>
                <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                  Scan a restaurant menu or log a quick meal below to track your daily burn-down.
                </p>
              </div>

              {plate.length > 0 && (
                <div className="p-2.5 rounded-xl bg-emerald-50/80 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300 flex items-center justify-between">
                  <span>🍽️ <b>{plate.length}</b> dish{plate.length > 1 ? 'es' : ''} ready on staging plate</span>
                  <Link to="/plate" className="font-bold underline hover:text-emerald-900 dark:hover:text-emerald-200 flex items-center gap-0.5">
                    Manage Plate →
                  </Link>
                </div>
              )}

              <div className="flex flex-wrap items-center justify-center gap-2 pt-1">
                <Link
                  to="/menu"
                  className="px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-2xs transition"
                >
                  Scan Menu
                </Link>
                <button
                  onClick={() => handleQuickLogSampleMeal('Lunch')}
                  className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold text-xs transition border border-slate-200 dark:border-slate-700 cursor-pointer"
                >
                  + Quick Lunch (580 kcal)
                </button>
                <Link
                  to="/calendar"
                  className="px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-bold text-xs transition border border-slate-200 dark:border-slate-700"
                >
                  Calendar Log
                </Link>
              </div>
            </div>
          ) : (
            <div className="space-y-3 max-h-[360px] overflow-y-auto pr-1">
              {todaysMeals.map((meal) => {
                const nut = meal.nutrients || {};
                return (
                  <div
                    key={meal.id}
                    className="p-3.5 rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-slate-50/60 dark:bg-slate-800/60 hover:border-slate-300 dark:hover:border-slate-700 transition shadow-2xs space-y-2"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded-md bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 font-bold text-[10px] uppercase tracking-wider">
                          {meal.mealSlot || 'Meal'}
                        </span>
                        <span className="text-[10px] text-slate-400 flex items-center gap-1 font-medium">
                          <Clock className="w-3 h-3" /> {meal.timestamp || 'Today'}
                        </span>
                      </div>

                      {handleRemoveLoggedMeal && (
                        <button
                          onClick={() => handleRemoveLoggedMeal(meal.id)}
                          className="text-slate-400 hover:text-rose-500 p-1 transition cursor-pointer"
                          title="Delete meal entry"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      )}
                    </div>

                    <div className="space-y-1">
                      {(meal.items || []).map((dish, idx) => (
                        <div key={idx} className="text-xs text-slate-800 dark:text-slate-200 font-semibold flex items-center justify-between">
                          <span>
                            {dish.name} {dish.portion && dish.portion !== 1 ? `(${dish.portion}x)` : ''}
                          </span>
                          {dish.price && <span className="text-[10px] text-slate-400 font-mono">{dish.price}</span>}
                        </div>
                      ))}
                    </div>

                    <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800 flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400">
                      <span>🔥 <b>{Math.round(meal.total_calories || nut.calories || 0)}</b> kcal</span>
                      <span>P: <b>{Math.round(meal.total_protein || nut.protein || 0)}g</b></span>
                      <span>C: <b>{Math.round(meal.total_carbs || nut.carbs || 0)}g</b></span>
                      <span>F: <b>{Math.round(meal.total_fats || nut.fat || 0)}g</b></span>
                      <span>Na: <b>{Math.round(meal.total_sodium || nut.sodium || 0)}mg</b></span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Active Plate & Clinical Shields (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {/* Active Plate Widget */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-xs space-y-4 transition-colors">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <div className="w-8 h-8 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center font-bold">
                  <Utensils className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-sm font-bold text-slate-900 dark:text-white">Active Staging Plate</h3>
                  <span className="text-[11px] text-slate-400">
                    {plate.length} {plate.length === 1 ? 'item staged' : 'items staged'}
                  </span>
                </div>
              </div>

              <Link
                to="/plate"
                className="text-xs font-bold text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 flex items-center gap-1"
              >
                <span>Manage Plate</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>

            {plate.length === 0 ? (
              <div className="p-5 text-center bg-slate-50/70 dark:bg-slate-800/40 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 space-y-2">
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Your staging plate is currently empty.
                </p>
                <Link
                  to="/menu"
                  className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs transition shadow-2xs"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add Dishes from Scanner</span>
                </Link>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="space-y-1.5 max-h-[160px] overflow-y-auto pr-1">
                  {plate.map((item, idx) => (
                    <div
                      key={idx}
                      className="px-3 py-2 rounded-xl bg-slate-50 dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/80 flex items-center justify-between text-xs"
                    >
                      <span className="font-semibold text-slate-800 dark:text-slate-200 truncate">{item.name}</span>
                      <span className="text-[11px] text-emerald-700 dark:text-emerald-300 font-bold shrink-0 ml-2">
                        {item.portion || 1}x portion
                      </span>
                    </div>
                  ))}
                </div>

                <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-[11px] text-slate-600 dark:text-slate-300 font-medium flex items-center justify-between">
                  <span>🔥 ~<b>{stagedPlateNutrients.calories}</b> kcal</span>
                  <span>P: <b>{stagedPlateNutrients.protein}g</b></span>
                  <span>C: <b>{stagedPlateNutrients.carbs}g</b></span>
                  <span>Na: <b>{stagedPlateNutrients.sodium}mg</b></span>
                </div>

                <button
                  onClick={handleQuickLogPlate}
                  className="w-full py-2.5 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs shadow-xs transition flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Log {plate.length} {plate.length === 1 ? 'Dish' : 'Dishes'} to Today's Intake</span>
                </button>
              </div>
            )}
          </div>

          {/* Clinical Profile Active Shield */}
          <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 p-6 shadow-xs space-y-3 transition-colors">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">Active Clinical Safeguards</h3>
              </div>
              <Link
                to="/profile"
                className="text-xs font-bold text-slate-500 hover:text-emerald-600 dark:text-slate-400 dark:hover:text-emerald-400"
              >
                Edit
              </Link>
            </div>

            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Dishes violating these clinical parameters are automatically flagged in Red (Tier 3) or penalized.
            </p>

            <div className="flex flex-wrap gap-1.5 pt-1">
              {(profile.health_conditions || []).map((c) => (
                <span
                  key={c}
                  className="px-2.5 py-1 rounded-lg bg-rose-50 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 text-xs font-bold border border-rose-200 dark:border-rose-900"
                >
                  🫀 {c.replace('_', ' ')}
                </span>
              ))}

              {(profile.allergies || []).map((a) => (
                <span
                  key={a}
                  className="px-2.5 py-1 rounded-lg bg-amber-50 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 text-xs font-bold border border-amber-200 dark:border-amber-900"
                >
                  ⚠️ No {a}
                </span>
              ))}

              {(profile.dietary_preferences || []).map((d) => (
                <span
                  key={d}
                  className="px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 text-xs font-bold border border-emerald-200 dark:border-emerald-900"
                >
                  🌱 {d}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
