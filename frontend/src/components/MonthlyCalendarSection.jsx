import React, { useState, useMemo } from 'react';
import {
  Calendar as CalendarIcon,
  ChevronLeft,
  ChevronRight,
  Flame,
  Zap,
  Heart,
  TrendingUp,
  Sparkles,
  Plus,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Clock,
  Utensils,
  RefreshCw,
  Download,
  Info,
  Layers,
  X,
  ShieldAlert,
} from 'lucide-react';
import { exportMealsToCsv, openClinicalDoctorReport } from '../utils/exportUtils';

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const WEEKDAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function MonthlyCalendarSection({
  loggedMeals = [],
  onSaveMealToLog,
  onRemoveLoggedMeal,
  onClearAllLoggedMeals,
  userMatrix,
  userProfile,
  dishes = [],
  activePlate = [],
  onAddToPlate,
}) {
  const today = new Date();
  const [currentYear, setCurrentYear] = useState(today.getFullYear());
  const [currentMonth, setCurrentMonth] = useState(today.getMonth()); // 0-indexed
  
  // Format today as YYYY-MM-DD
  const todayStr = useMemo(() => {
    const y = today.getFullYear();
    const m = String(today.getMonth() + 1).padStart(2, '0');
    const d = String(today.getDate()).padStart(2, '0');
    return `${y}-${m}-${d}`;
  }, []);

  const [selectedDate, setSelectedDate] = useState(todayStr);
  const [isAddMealModalOpen, setIsAddMealModalOpen] = useState(false);
  const [newMealSlot, setNewMealSlot] = useState('Lunch');
  const [newMealDishName, setNewMealDishName] = useState('');
  const [newMealCalories, setNewMealCalories] = useState('450');
  const [newMealProtein, setNewMealProtein] = useState('22');
  const [newMealCarbs, setNewMealCarbs] = useState('50');
  const [newMealFat, setNewMealFat] = useState('14');
  const [newMealSodium, setNewMealSodium] = useState('480');

  // Daily target constants from matrix or fallback
  const dailyTargets = useMemo(() => ({
    calories: Number(userMatrix?.metabolic_targets?.target_calories_kcal || 2000),
    protein: Number(userMatrix?.metabolic_targets?.target_protein_g || 120),
    carbs: Number(userMatrix?.metabolic_targets?.target_carbs_g || 225),
    fat: Number(userMatrix?.metabolic_targets?.target_fats_g || 65),
    sodium_ceiling: Number(userMatrix?.nutritional_guardrails?.sodium_ceiling_mg || 2300),
    fiber_min: Number(userMatrix?.nutritional_guardrails?.dietary_fiber_min_g || 30),
  }), [userMatrix]);

  // Navigate Months
  const handlePrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear(currentYear - 1);
    } else {
      setCurrentMonth(currentMonth - 1);
    }
  };

  const handleNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear(currentYear + 1);
    } else {
      setCurrentMonth(currentMonth + 1);
    }
  };

  const handleJumpToToday = () => {
    setCurrentYear(today.getFullYear());
    setCurrentMonth(today.getMonth());
    setSelectedDate(todayStr);
  };

  // Calendar matrix calculation
  const calendarDays = useMemo(() => {
    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    // Monday as first day of week: (day + 6) % 7
    const firstDayIndex = (new Date(currentYear, currentMonth, 1).getDay() + 6) % 7;
    const days = [];

    // Previous month filler days
    const prevMonthDays = new Date(currentYear, currentMonth, 0).getDate();
    for (let i = firstDayIndex - 1; i >= 0; i--) {
      const d = prevMonthDays - i;
      const prevMonth = currentMonth === 0 ? 11 : currentMonth - 1;
      const prevYear = currentMonth === 0 ? currentYear - 1 : currentYear;
      const dateStr = `${prevYear}-${String(prevMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({ dayNumber: d, dateStr, isCurrentMonth: false });
    }

    // Current month days
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({ dayNumber: d, dateStr, isCurrentMonth: true });
    }

    // Next month filler days to complete grid (multiples of 7)
    const remaining = (7 - (days.length % 7)) % 7;
    for (let d = 1; d <= remaining; d++) {
      const nextMonth = currentMonth === 11 ? 0 : currentMonth + 1;
      const nextYear = currentMonth === 11 ? currentYear + 1 : currentYear;
      const dateStr = `${nextYear}-${String(nextMonth + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
      days.push({ dayNumber: d, dateStr, isCurrentMonth: false });
    }

    return days;
  }, [currentYear, currentMonth]);

  // Aggregate daily stats map for lookup
  const dailyStatsMap = useMemo(() => {
    const map = {};
    loggedMeals.forEach((meal) => {
      const d = meal.date || (meal.timestamp && String(meal.timestamp).split('T')[0]);
      if (!d) return;
      if (!map[d]) {
        map[d] = {
          calories: 0,
          protein: 0,
          carbs: 0,
          fat: 0,
          sodium: 0,
          fiber: 0,
          meals: [],
        };
      }
      const cals = Number(meal.total_calories ?? meal.nutrients?.calories ?? 0);
      const prot = Number(meal.total_protein ?? meal.nutrients?.protein ?? 0);
      const carbs = Number(meal.total_carbs ?? meal.nutrients?.carbs ?? 0);
      const fat = Number(meal.total_fats ?? meal.nutrients?.fat ?? meal.nutrients?.fats ?? 0);
      const sod = Number(meal.total_sodium ?? meal.nutrients?.sodium ?? 0);
      const fib = Number(meal.nutrients?.fiber ?? 0);

      map[d].calories += cals;
      map[d].protein += prot;
      map[d].carbs += carbs;
      map[d].fat += fat;
      map[d].sodium += sod;
      map[d].fiber += fib;
      map[d].meals.push(meal);
    });
    return map;
  }, [loggedMeals]);

  // Whole Monthly Plan Metrics
  const monthlyMetrics = useMemo(() => {
    const monthPrefix = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}`;
    const datesInMonth = Object.keys(dailyStatsMap).filter((d) => d.startsWith(monthPrefix));
    const loggedDaysCount = datesInMonth.length;

    let totalCals = 0;
    let totalProtein = 0;
    let totalCarbs = 0;
    let totalFat = 0;
    let totalSodium = 0;
    let optimalDaysCount = 0;
    let totalMealsCount = 0;

    datesInMonth.forEach((d) => {
      const stat = dailyStatsMap[d];
      totalCals += stat.calories;
      totalProtein += stat.protein;
      totalCarbs += stat.carbs;
      totalFat += stat.fat;
      totalSodium += stat.sodium;
      totalMealsCount += stat.meals.length;

      const calRatio = stat.calories / (dailyTargets.calories || 2000);
      const sodiumSafe = stat.sodium <= dailyTargets.sodium_ceiling;
      if (calRatio >= 0.85 && calRatio <= 1.15 && sodiumSafe) {
        optimalDaysCount++;
      }
    });

    const avgDailyCals = loggedDaysCount > 0 ? Math.round(totalCals / loggedDaysCount) : 0;
    const avgDailyProtein = loggedDaysCount > 0 ? Math.round(totalProtein / loggedDaysCount) : 0;
    const avgDailyCarbs = loggedDaysCount > 0 ? Math.round(totalCarbs / loggedDaysCount) : 0;
    const avgDailyFat = loggedDaysCount > 0 ? Math.round(totalFat / loggedDaysCount) : 0;
    const avgDailySodium = loggedDaysCount > 0 ? Math.round(totalSodium / loggedDaysCount) : 0;
    const complianceRate = loggedDaysCount > 0 ? Math.round((optimalDaysCount / loggedDaysCount) * 100) : 0;

    // Projected Weight Delta for month based on caloric deficit/surplus
    const calDelta = avgDailyCals - dailyTargets.calories;
    const projectedWeightChangeKg = loggedDaysCount > 0 ? Number(((calDelta * 30) / 7700).toFixed(1)) : 0;

    return {
      loggedDaysCount,
      totalMealsCount,
      avgDailyCals,
      avgDailyProtein,
      avgDailyCarbs,
      avgDailyFat,
      avgDailySodium,
      complianceRate,
      optimalDaysCount,
      projectedWeightChangeKg,
    };
  }, [dailyStatsMap, currentYear, currentMonth, dailyTargets]);

  // Selected Day Details
  const selectedDayData = dailyStatsMap[selectedDate] || {
    calories: 0,
    protein: 0,
    carbs: 0,
    fat: 0,
    sodium: 0,
    fiber: 0,
    meals: [],
  };

  const selectedDayRatio = selectedDayData.calories / (dailyTargets.calories || 2000);
  const selectedDayStatus =
    selectedDayData.meals.length === 0
      ? 'EMPTY'
      : selectedDayData.sodium > dailyTargets.sodium_ceiling || selectedDayRatio > 1.15
      ? 'OVER'
      : selectedDayRatio >= 0.85
      ? 'OPTIMAL'
      : 'MODERATE';

  // Helper to determine cell status for calendar day
  const getDayStatus = (dateStr) => {
    const data = dailyStatsMap[dateStr];
    if (!data || data.meals.length === 0) return 'EMPTY';
    const ratio = data.calories / (dailyTargets.calories || 2000);
    if (data.sodium > dailyTargets.sodium_ceiling || ratio > 1.15) return 'OVER';
    if (ratio >= 0.85 && ratio <= 1.15) return 'OPTIMAL';
    return 'MODERATE';
  };

  // Quick Action: Add Current Active Plate to Selected Day (Dynamic Nutrients Binding)
  const handleAddActivePlateToSelectedDay = () => {
    if (!activePlate || activePlate.length === 0 || !onSaveMealToLog) return;
    const now = new Date();

    let totalCals = 0;
    let totalProtein = 0;
    let totalCarbs = 0;
    let totalFat = 0;
    let totalSodium = 0;
    let totalFiber = 0;

    activePlate.forEach((p) => {
      const portion = Number(p.portion) || 1.0;
      // Look up if dish exists in dishes array with estimated or evaluated nutrients
      const matched = dishes.find(
        (d) => (typeof d === 'string' ? d : d.name || '').toLowerCase() === (p.name || '').toLowerCase()
      );
      const dishNutrients = p.nutrients || (matched && typeof matched === 'object' ? matched.nutrients || matched : {}) || {};

      const cals = Number(dishNutrients.calories || matched?.calories) || 380;
      const prot = Number(dishNutrients.protein || matched?.protein) || 20;
      const carbs = Number(dishNutrients.carbs || matched?.carbs) || 45;
      const fat = Number(dishNutrients.fat || matched?.fat) || 14;
      const sod = Number(dishNutrients.sodium || matched?.sodium) || 420;
      const fib = Number(dishNutrients.fiber || matched?.fiber) || 5;

      totalCals += cals * portion;
      totalProtein += prot * portion;
      totalCarbs += carbs * portion;
      totalFat += fat * portion;
      totalSodium += sod * portion;
      totalFiber += fib * portion;
    });

    const mealEntry = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      name: `Plate Entry (${activePlate.length} dishes)`,
      meal_type: 'Dinner',
      date: selectedDate,
      mealSlot: 'Dinner',
      timestamp: now.toISOString(),
      dishes: activePlate.map((p) => ({
        name: p.name,
        portion: p.portion || 1.0,
        price: p.price || '',
      })),
      items: activePlate.map((p) => ({
        name: p.name,
        portion: p.portion || 1.0,
        price: p.price || '',
      })),
      nutrients: {
        calories: Math.round(totalCals),
        protein: Math.round(totalProtein),
        carbs: Math.round(totalCarbs),
        fat: Math.round(totalFat),
        sodium: Math.round(totalSodium),
        fiber: Math.round(totalFiber),
      },
      total_calories: Math.round(totalCals),
      total_protein: Math.round(totalProtein),
      total_carbs: Math.round(totalCarbs),
      total_fats: Math.round(totalFat),
      total_sodium: Math.round(totalSodium),
    };

    onSaveMealToLog(mealEntry);
  };

  // Quick Action: Custom Meal Form Submit
  const handleSaveCustomMeal = (e) => {
    e.preventDefault();
    if (!newMealDishName.trim()) return;

    const cals = Number(newMealCalories) || 350;
    const prot = Number(newMealProtein) || 15;
    const carbs = Number(newMealCarbs) || 40;
    const fat = Number(newMealFat) || 12;
    const sod = Number(newMealSodium) || 400;

    const mealEntry = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      name: newMealDishName.trim(),
      meal_type: newMealSlot,
      date: selectedDate,
      mealSlot: newMealSlot,
      timestamp: new Date().toISOString(),
      dishes: [
        {
          name: newMealDishName.trim(),
          portion: 1.0,
          price: '',
        },
      ],
      items: [
        {
          name: newMealDishName.trim(),
          portion: 1.0,
          price: '',
        },
      ],
      nutrients: {
        calories: cals,
        protein: prot,
        carbs: carbs,
        fat: fat,
        sodium: sod,
        fiber: 5,
      },
      total_calories: cals,
      total_protein: prot,
      total_carbs: carbs,
      total_fats: fat,
      total_sodium: sod,
    };

    onSaveMealToLog(mealEntry);
    setIsAddMealModalOpen(false);
    setNewMealDishName('');
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* 1. Monthly Plan Health Dashboard Banner */}
      <section className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-6 transition-colors">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 flex items-center justify-center font-bold">
                <CalendarIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              </div>
              <h2 className="text-lg font-black text-slate-900 dark:text-white tracking-tight">
                Monthly Nutrition Calendar & Plan Analytics
              </h2>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
              Tracks continuous daily meal consumption against your personalized metabolic targets and clinical safety limits.
            </p>
          </div>

          {/* Month Navigation & Clear Actions */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center bg-slate-100 dark:bg-slate-800 p-1 rounded-2xl border border-slate-200 dark:border-slate-700">
              <button
                onClick={handlePrevMonth}
                className="p-1.5 rounded-xl hover:bg-white dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition cursor-pointer"
                title="Previous Month"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-3 text-xs font-bold text-slate-800 dark:text-slate-200 min-w-[120px] text-center select-none">
                {MONTH_NAMES[currentMonth]} {currentYear}
              </span>
              <button
                onClick={handleNextMonth}
                className="p-1.5 rounded-xl hover:bg-white dark:hover:bg-slate-700 text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white transition cursor-pointer"
                title="Next Month"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <button
              onClick={handleJumpToToday}
              className="px-3 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold transition cursor-pointer"
            >
              Today
            </button>

            {loggedMeals.length > 0 && (
              <>
                <button
                  onClick={() => exportMealsToCsv(loggedMeals, dailyTargets)}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 hover:bg-emerald-100 dark:hover:bg-emerald-900 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-xs font-bold transition cursor-pointer shadow-2xs"
                  title="Download your monthly meal and macro log as CSV report"
                >
                  <Download className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  <span>Export CSV</span>
                </button>

                <button
                  onClick={() => openClinicalDoctorReport({ profile: userProfile, userMatrix, loggedMeals })}
                  className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 hover:bg-indigo-100 dark:hover:bg-indigo-900 text-indigo-800 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 text-xs font-bold transition cursor-pointer shadow-2xs"
                  title="Print/PDF Clinical Consultation Dossier for Doctors or Dietitians"
                >
                  <FileText className="w-3.5 h-3.5 text-indigo-600 dark:text-indigo-400" />
                  <span>Physician Report</span>
                </button>
              </>
            )}

            {loggedMeals.length > 0 && onClearAllLoggedMeals && (
              <button
                onClick={() => {
                  if (window.confirm('Clear all logged meals from your calendar?')) {
                    onClearAllLoggedMeals();
                  }
                }}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-rose-50 dark:hover:bg-rose-950/60 hover:text-rose-700 dark:hover:text-rose-400 hover:border-rose-200 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700 text-xs font-bold transition cursor-pointer"
                title="Clear all recorded meals"
              >
                <Trash2 className="w-3.5 h-3.5 text-slate-400 hover:text-rose-600" />
                <span>Clear All Logs</span>
              </button>
            )}
          </div>
        </div>

        {/* Basic Metrics of the Whole Plan (KPI Cards) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Caloric Intake vs Target */}
          <div className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-[11px] font-bold uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <Flame className="w-3.5 h-3.5 text-amber-500" /> Avg Daily Calories
              </span>
              <span className="text-[10px] text-slate-400 dark:text-slate-500">Target: {dailyTargets.calories}</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-black text-slate-900 dark:text-white tabular-nums">
                {monthlyMetrics.avgDailyCals} <span className="text-xs font-normal text-slate-500 dark:text-slate-400">kcal/day</span>
              </span>
            </div>
            {/* Progress bar */}
            <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  monthlyMetrics.avgDailyCals > dailyTargets.calories * 1.15
                    ? 'bg-rose-500'
                    : 'bg-emerald-500'
                }`}
                style={{
                  width: `${Math.min(100, (monthlyMetrics.avgDailyCals / (dailyTargets.calories || 2000)) * 100)}%`,
                }}
              />
            </div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400 font-medium flex justify-between">
              <span>{monthlyMetrics.loggedDaysCount} days recorded</span>
              <span className={monthlyMetrics.avgDailyCals <= dailyTargets.calories ? 'text-emerald-700 dark:text-emerald-400 font-bold' : 'text-amber-700 dark:text-amber-400 font-bold'}>
                {monthlyMetrics.avgDailyCals <= dailyTargets.calories ? 'Deficit' : 'Surplus'} (
                {Math.abs(monthlyMetrics.avgDailyCals - dailyTargets.calories)} kcal)
              </span>
            </div>
          </div>

          {/* Average Daily Protein & Split */}
          <div className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-[11px] font-bold uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-emerald-500" /> Average Macros
              </span>
              <span className="text-[10px] text-slate-400 dark:text-slate-500">P / C / F</span>
            </div>
            <div className="text-xl font-black text-slate-900 dark:text-white tabular-nums">
              {monthlyMetrics.avgDailyProtein}g <span className="text-xs font-bold text-emerald-600 dark:text-emerald-400">Protein</span>
            </div>
            <div className="text-[11px] text-slate-600 dark:text-slate-300 font-medium">
              Carbs: <b>{monthlyMetrics.avgDailyCarbs}g</b> • Fat: <b>{monthlyMetrics.avgDailyFat}g</b>
            </div>
            <div className="text-[10px] text-slate-400 dark:text-slate-500">
              Protein Target: {dailyTargets.protein}g ({Math.round((monthlyMetrics.avgDailyProtein / (dailyTargets.protein || 120)) * 100)}%)
            </div>
          </div>

          {/* Plan Adherence Rate */}
          <div className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-[11px] font-bold uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-blue-500" /> Plan Adherence
              </span>
              <span className="text-[10px] text-slate-400 dark:text-slate-500">Compliance</span>
            </div>
            <div className="text-xl font-black text-slate-900 dark:text-white tabular-nums">
              {monthlyMetrics.complianceRate}%
            </div>
            <div className="w-full bg-slate-200 dark:bg-slate-700 h-1.5 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-500"
                style={{ width: `${monthlyMetrics.complianceRate}%` }}
              />
            </div>
            <div className="text-[10px] text-slate-500 dark:text-slate-400 font-medium">
              {monthlyMetrics.optimalDaysCount} of {monthlyMetrics.loggedDaysCount} recorded days optimal
            </div>
          </div>

          {/* Clinical Guardrail & Sodium Safety */}
          <div className="p-4 rounded-2xl bg-slate-50/80 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-800 shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-[11px] font-bold uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <Heart className="w-3.5 h-3.5 text-rose-500" /> Sodium & Safety
              </span>
              <span className="text-[10px] text-slate-400 dark:text-slate-500">Ceiling: {dailyTargets.sodium_ceiling}mg</span>
            </div>
            <div className="text-xl font-black text-slate-900 dark:text-white tabular-nums">
              {monthlyMetrics.avgDailySodium} <span className="text-xs font-normal text-slate-500 dark:text-slate-400">mg/day</span>
            </div>
            <div className="text-[10px] font-semibold mt-1">
              {monthlyMetrics.avgDailySodium <= dailyTargets.sodium_ceiling ? (
                <span className="text-emerald-700 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-950/60 px-2 py-0.5 rounded-md border border-emerald-200 dark:border-emerald-800 inline-block">
                  ✓ Safe Clinical Range
                </span>
              ) : (
                <span className="text-rose-700 dark:text-rose-300 bg-rose-50 dark:bg-rose-950/60 px-2 py-0.5 rounded-md border border-rose-200 dark:border-rose-900 inline-block">
                  ⚠️ Above Sodium Limit
                </span>
              )}
            </div>
            <div className="text-[10px] text-slate-400 dark:text-slate-500">
              Total monthly meals: {monthlyMetrics.totalMealsCount}
            </div>
          </div>
        </div>
      </section>

      {/* 2. Main Calendar Grid + Selected Day Breakdown Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left / Center: Interactive Monthly Calendar Grid (7 columns) */}
        <div className="lg:col-span-7 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-4 transition-colors">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 dark:text-white text-sm flex items-center gap-2">
              <CalendarIcon className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              {MONTH_NAMES[currentMonth]} {currentYear} Calendar View
            </h3>

            {/* Legend */}
            <div className="flex items-center gap-3 text-[10px] font-semibold text-slate-500 dark:text-slate-400">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> Optimal
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-amber-500" /> Moderate
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-rose-500" /> Over/Warning
              </span>
            </div>
          </div>

          {/* Responsive Scrollable Container to prevent overlapping cell content */}
          <div className="overflow-x-auto pb-2">
            <div className="min-w-[500px]">
              {/* Weekday Header */}
              <div className="grid grid-cols-7 gap-1 text-center text-xs font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider py-1 border-b border-slate-100 dark:border-slate-800">
                {WEEKDAY_NAMES.map((name) => (
                  <div key={name} className="py-1">
                    {name}
                  </div>
                ))}
              </div>

              {/* Calendar Grid Cells */}
              <div className="grid grid-cols-7 gap-1.5 mt-2">
                {calendarDays.map((item, idx) => {
                  const { dayNumber, dateStr, isCurrentMonth } = item;
                  const isSelected = selectedDate === dateStr;
                  const isToday = todayStr === dateStr;
                  const dayStat = dailyStatsMap[dateStr];
                  const status = getDayStatus(dateStr);

                  // Status background styling
                  let statusBorder = 'border-slate-100 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700';
                  let statusPill = null;

                  if (status === 'OPTIMAL') {
                    statusBorder = 'border-emerald-200 dark:border-emerald-800 bg-emerald-50/20 dark:bg-emerald-950/20';
                    statusPill = 'bg-emerald-500 text-white';
                  } else if (status === 'MODERATE') {
                    statusBorder = 'border-amber-200 dark:border-amber-800 bg-amber-50/20 dark:bg-amber-950/20';
                    statusPill = 'bg-amber-500 text-white';
                  } else if (status === 'OVER') {
                    statusBorder = 'border-rose-200 dark:border-rose-800 bg-rose-50/20 dark:bg-rose-950/20';
                    statusPill = 'bg-rose-500 text-white';
                  }

                  return (
                    <button
                      key={idx}
                      onClick={() => setSelectedDate(dateStr)}
                      className={`min-h-[80px] p-2 rounded-2xl border text-left flex flex-col justify-between transition-all duration-150 cursor-pointer ${
                        isCurrentMonth ? 'bg-white dark:bg-slate-800/90' : 'bg-slate-50/50 dark:bg-slate-900/60 text-slate-300 dark:text-slate-600 opacity-50'
                      } ${statusBorder} ${
                        isSelected ? 'ring-2 ring-emerald-500 shadow-md border-emerald-500 dark:border-emerald-500' : ''
                      }`}
                    >
                      <div className="flex items-center justify-between w-full">
                        <span
                          className={`text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center ${
                            isToday ? 'bg-emerald-600 text-white' : 'text-slate-700 dark:text-slate-300'
                          }`}
                        >
                          {dayNumber}
                        </span>

                        {dayStat && dayStat.meals.length > 0 && (
                          <span className={`w-1.5 h-1.5 rounded-full ${statusPill}`} />
                        )}
                      </div>

                      {/* Daily Calorie Summary in cell */}
                      {dayStat && dayStat.meals.length > 0 ? (
                        <div className="mt-1">
                          <div className="text-[10px] font-extrabold text-slate-800 dark:text-slate-200 tabular-nums">
                            {Math.round(dayStat.calories)} <span className="text-[8px] font-normal text-slate-400">kcal</span>
                          </div>
                          <div className="text-[9px] text-slate-400 dark:text-slate-500">
                            {dayStat.meals.length} {dayStat.meals.length === 1 ? 'meal' : 'meals'}
                          </div>
                        </div>
                      ) : (
                        <div className="text-[9px] text-slate-300 dark:text-slate-600 mt-2 italic">
                          —
                        </div>
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          </div>
        </div>

        {/* Right: Selected Day Consumption Breakdown */}
        <div className="lg:col-span-5 bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-3xl p-6 shadow-sm space-y-6 flex flex-col justify-between transition-colors">
          <div className="space-y-5">
            {/* Header with Selected Date & Adherence Status */}
            <div className="border-b border-slate-100 dark:border-slate-800 pb-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500 block">
                    Daily Consumption Breakdown
                  </span>
                  <h3 className="text-base font-black text-slate-900 dark:text-white mt-0.5">
                    {new Date(selectedDate + 'T00:00:00').toLocaleDateString(undefined, {
                      weekday: 'long',
                      month: 'short',
                      day: 'numeric',
                      year: 'numeric',
                    })}
                  </h3>
                </div>

                {/* Day Status Pill */}
                {selectedDayStatus === 'OPTIMAL' && (
                  <span className="px-2.5 py-1 rounded-full bg-emerald-100 dark:bg-emerald-950/60 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 text-xs font-black flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" /> Optimal Fit
                  </span>
                )}
                {selectedDayStatus === 'MODERATE' && (
                  <span className="px-2.5 py-1 rounded-full bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 border border-amber-200 dark:border-amber-800 text-xs font-black flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400" /> Moderate
                  </span>
                )}
                {selectedDayStatus === 'OVER' && (
                  <span className="px-2.5 py-1 rounded-full bg-rose-100 dark:bg-rose-950/60 text-rose-800 dark:text-rose-300 border border-rose-200 dark:border-rose-800 text-xs font-black flex items-center gap-1">
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" /> Over Budget
                  </span>
                )}
                {selectedDayStatus === 'EMPTY' && (
                  <span className="px-2.5 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-xs font-bold">
                    No Logs Yet
                  </span>
                )}
              </div>

              {/* Day Macro Gauges */}
              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                <div className="p-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-800">
                  <div className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Calories</div>
                  <div className="text-sm font-black text-slate-900 dark:text-white tabular-nums">
                    {Math.round(selectedDayData.calories)}
                  </div>
                  <div className="text-[9px] text-slate-400 dark:text-slate-500">of {dailyTargets.calories} kcal</div>
                </div>

                <div className="p-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-800">
                  <div className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Protein</div>
                  <div className="text-sm font-black text-emerald-600 dark:text-emerald-400 tabular-nums">
                    {Math.round(selectedDayData.protein)}g
                  </div>
                  <div className="text-[9px] text-slate-400 dark:text-slate-500">of {dailyTargets.protein}g</div>
                </div>

                <div className="p-2 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-100 dark:border-slate-800">
                  <div className="text-[10px] text-slate-400 dark:text-slate-500 font-bold uppercase">Sodium</div>
                  <div className="text-sm font-black text-slate-800 dark:text-slate-200 tabular-nums">
                    {Math.round(selectedDayData.sodium)}
                  </div>
                  <div className="text-[9px] text-slate-400 dark:text-slate-500">of {dailyTargets.sodium_ceiling} mg</div>
                </div>
              </div>
            </div>

            {/* List of Meals Consumed on Selected Date */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700 dark:text-slate-200 flex items-center gap-1.5">
                  <Utensils className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                  Meals Consumed ({selectedDayData.meals.length})
                </span>

                <button
                  onClick={() => setIsAddMealModalOpen(true)}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 hover:bg-emerald-100 dark:hover:bg-emerald-900 border border-emerald-200 dark:border-emerald-800 text-xs font-bold transition cursor-pointer"
                >
                  <Plus className="w-3 h-3" /> Log Meal
                </button>
              </div>

              {selectedDayData.meals.length === 0 ? (
                <div className="p-6 text-center bg-slate-50/60 dark:bg-slate-800/40 rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 space-y-2">
                  <p className="text-xs text-slate-500 dark:text-slate-400 font-medium">No meals logged on this date.</p>
                  {activePlate.length > 0 ? (
                    <button
                      onClick={handleAddActivePlateToSelectedDay}
                      className="px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-2xs transition cursor-pointer"
                    >
                      Log Current Plate ({activePlate.length} items) Here
                    </button>
                  ) : (
                    <button
                      onClick={() => setIsAddMealModalOpen(true)}
                      className="px-3 py-1.5 rounded-xl bg-slate-200 dark:bg-slate-800 text-slate-700 dark:text-slate-300 text-xs font-bold hover:bg-slate-300 dark:hover:bg-slate-700 transition cursor-pointer"
                    >
                      + Add Meal Entry
                    </button>
                  )}
                </div>
              ) : (
                <div className="space-y-2.5 max-h-[360px] overflow-y-auto pr-1">
                  {selectedDayData.meals.map((meal) => (
                    <div
                      key={meal.id}
                      className="p-3 rounded-2xl border border-slate-200/90 dark:border-slate-800 bg-white dark:bg-slate-800/90 hover:border-slate-300 dark:hover:border-slate-700 transition-all shadow-2xs space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded-md bg-slate-100 dark:bg-slate-800 text-slate-800 dark:text-slate-200 font-bold text-[10px] uppercase tracking-wider">
                            {meal.mealSlot || 'Meal'}
                          </span>
                          <span className="text-[10px] text-slate-400 dark:text-slate-500 flex items-center gap-1">
                            <Clock className="w-3 h-3" /> {meal.timestamp || 'Logged'}
                          </span>
                        </div>

                        {onRemoveLoggedMeal && (
                          <button
                            onClick={() => onRemoveLoggedMeal(meal.id)}
                            className="text-slate-300 dark:text-slate-600 hover:text-rose-500 dark:hover:text-rose-400 p-1 transition cursor-pointer"
                            title="Delete this meal entry"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>

                      {/* Dishes consumed in this meal */}
                      <div className="space-y-1">
                        {(meal.items || []).map((dishItem, i) => (
                          <div key={i} className="text-xs text-slate-800 dark:text-slate-200 font-semibold flex items-center justify-between">
                            <span>
                              {dishItem.name}{' '}
                              {dishItem.portion && dishItem.portion !== 1 && (
                                <span className="text-[10px] text-slate-400 dark:text-slate-500 font-normal">
                                  ({dishItem.portion}x)
                                </span>
                              )}
                            </span>
                            {dishItem.price && (
                              <span className="text-[10px] text-slate-400 dark:text-slate-500 font-mono">
                                {dishItem.price}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Meal Nutrients pill */}
                      <div className="pt-1.5 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between text-[10px] text-slate-500 dark:text-slate-400">
                        <span>🔥 <b>{Math.round(meal.nutrients?.calories || 0)}</b> kcal</span>
                        <span>P: <b>{Math.round(meal.nutrients?.protein || 0)}g</b></span>
                        <span>C: <b>{Math.round(meal.nutrients?.carbs || 0)}g</b></span>
                        <span>F: <b>{Math.round(meal.nutrients?.fat || 0)}g</b></span>
                        <span>Na: <b>{Math.round(meal.nutrients?.sodium || 0)}mg</b></span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Quick Footer Action in breakdown card */}
          {activePlate.length > 0 && selectedDayData.meals.length > 0 && (
            <div className="pt-4 border-t border-slate-100 dark:border-slate-800">
              <button
                onClick={handleAddActivePlateToSelectedDay}
                className="w-full py-2 px-3 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-emerald-600 hover:text-white text-slate-700 dark:text-slate-200 text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Add Active Plate ({activePlate.length} items) to this day</span>
              </button>
            </div>
          )}
        </div>
      </div>

      {/* 3. Quick Log Meal Modal */}
      {isAddMealModalOpen && (
        <div className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-xl max-w-md w-full p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
              <h3 className="font-bold text-slate-900 dark:text-white text-base flex items-center gap-2">
                <Utensils className="w-4 h-4 text-emerald-600 dark:text-emerald-400" /> Log Meal Entry
              </h3>
              <button
                onClick={() => setIsAddMealModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 p-1 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveCustomMeal} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-500 dark:text-slate-400 font-bold mb-1">Meal Slot</label>
                <div className="grid grid-cols-4 gap-1.5">
                  {['Breakfast', 'Lunch', 'Dinner', 'Snacks'].map((slot) => (
                    <button
                      key={slot}
                      type="button"
                      onClick={() => setNewMealSlot(slot)}
                      className={`py-1.5 text-center font-bold rounded-xl border transition cursor-pointer ${
                        newMealSlot === slot
                          ? 'bg-emerald-600 text-white border-emerald-600'
                          : 'bg-slate-50 dark:bg-slate-800 text-slate-700 dark:text-slate-300 border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700'
                      }`}
                    >
                      {slot}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-slate-500 dark:text-slate-400 font-bold mb-1">Dish Name or Description</label>
                {dishes && dishes.length > 0 ? (
                  <div className="space-y-1.5">
                    <input
                      type="text"
                      list="candidate-dishes"
                      value={newMealDishName}
                      onChange={(e) => setNewMealDishName(e.target.value)}
                      placeholder="e.g. Lauki Channa Dal with Roti"
                      className="w-full px-3 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                      required
                    />
                    <datalist id="candidate-dishes">
                      {dishes.map((d, i) => (
                        <option key={i} value={typeof d === 'string' ? d : d.name || ''} />
                      ))}
                    </datalist>
                  </div>
                ) : (
                  <input
                    type="text"
                    value={newMealDishName}
                    onChange={(e) => setNewMealDishName(e.target.value)}
                    placeholder="e.g. Steamed Rice with Vegetable Sambar"
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                    required
                  />
                )}
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-slate-500 dark:text-slate-400 font-bold mb-1">Calories (kcal)</label>
                  <input
                    type="number"
                    value={newMealCalories}
                    onChange={(e) => setNewMealCalories(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-500 dark:text-slate-400 font-bold mb-1">Protein (g)</label>
                  <input
                    type="number"
                    value={newMealProtein}
                    onChange={(e) => setNewMealProtein(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-500 dark:text-slate-400 font-bold mb-1">Sodium (mg)</label>
                  <input
                    type="number"
                    value={newMealSodium}
                    onChange={(e) => setNewMealSodium(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-xl border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white text-xs font-mono"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 dark:border-slate-800 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsAddMealModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 font-bold hover:bg-slate-200 dark:hover:bg-slate-700 transition cursor-pointer"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-emerald-600 text-white font-bold hover:bg-emerald-700 transition shadow-sm cursor-pointer"
                >
                  Save Entry
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
