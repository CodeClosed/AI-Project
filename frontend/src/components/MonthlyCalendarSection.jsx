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

const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

const WEEKDAY_NAMES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export default function MonthlyCalendarSection({
  loggedMeals = [],
  onSaveMealToLog,
  onRemoveLoggedMeal,
  userMatrix,
  userProfile,
  dishes = [],
  activePlate = [],
  onAddToPlate,
  onOpenPlateDrawer,
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
      const d = meal.date;
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
      map[d].calories += meal.nutrients?.calories || 0;
      map[d].protein += meal.nutrients?.protein || 0;
      map[d].carbs += meal.nutrients?.carbs || 0;
      map[d].fat += meal.nutrients?.fat || 0;
      map[d].sodium += meal.nutrients?.sodium || 0;
      map[d].fiber += meal.nutrients?.fiber || 0;
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

  // Quick Action: Add Current Active Plate to Selected Day
  const handleAddActivePlateToSelectedDay = () => {
    if (!activePlate || activePlate.length === 0 || !onSaveMealToLog) return;
    const now = new Date();
    const plateCals = activePlate.reduce((acc, p) => acc + (p.portion || 1) * 320, 0);
    const plateProtein = activePlate.reduce((acc, p) => acc + (p.portion || 1) * 14, 0);
    const plateCarbs = activePlate.reduce((acc, p) => acc + (p.portion || 1) * 40, 0);
    const plateFat = activePlate.reduce((acc, p) => acc + (p.portion || 1) * 12, 0);
    const plateSodium = activePlate.reduce((acc, p) => acc + (p.portion || 1) * 380, 0);

    const mealEntry = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      date: selectedDate,
      mealSlot: 'Dinner',
      timestamp: now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      items: activePlate.map((p) => ({
        name: p.name,
        portion: p.portion || 1.0,
        price: p.price || '',
      })),
      nutrients: {
        calories: Math.round(plateCals),
        protein: Math.round(plateProtein),
        carbs: Math.round(plateCarbs),
        fat: Math.round(plateFat),
        sodium: Math.round(plateSodium),
        fiber: 8,
      },
    };

    onSaveMealToLog(mealEntry);
  };

  // Quick Action: Custom Meal Form Submit
  const handleSaveCustomMeal = (e) => {
    e.preventDefault();
    if (!newMealDishName.trim()) return;

    const mealEntry = {
      id: `${Date.now()}_${Math.random().toString(36).substr(2, 4)}`,
      date: selectedDate,
      mealSlot: newMealSlot,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      items: [
        {
          name: newMealDishName.trim(),
          portion: 1.0,
          price: '',
        },
      ],
      nutrients: {
        calories: Number(newMealCalories) || 350,
        protein: Number(newMealProtein) || 15,
        carbs: Number(newMealCarbs) || 40,
        fat: Number(newMealFat) || 12,
        sodium: Number(newMealSodium) || 400,
        fiber: 5,
      },
    };

    onSaveMealToLog(mealEntry);
    setIsAddMealModalOpen(false);
    setNewMealDishName('');
  };

  // Sample Month Generator (High-value feature for instant exploration)
  const handleGenerateSampleMonth = () => {
    if (!onSaveMealToLog) return;
    const isVeg = (userProfile?.dietary_preferences || []).some((d) => d.toLowerCase().includes('veg'));
    const breakfastOptions = isVeg
      ? [
          { name: 'Oatmeal with Almond Milk & Berries', cal: 340, p: 12, c: 55, f: 8, na: 120 },
          { name: 'Moong Dal Chilla with Mint Chutney', cal: 320, p: 16, c: 42, f: 9, na: 380 },
          { name: 'Sprouted Bean Salad & Masala Chai', cal: 280, p: 14, c: 40, f: 6, na: 250 },
        ]
      : [
          { name: 'Poached Eggs with Avocado on Whole Wheat', cal: 380, p: 22, c: 30, f: 18, na: 350 },
          { name: 'Greek Yogurt with Walnuts & Honey', cal: 310, p: 20, c: 28, f: 12, na: 95 },
        ];

    const lunchOptions = isVeg
      ? [
          { name: 'Dal Tadka, Tandoori Roti & Cucumber Salad', cal: 580, p: 24, c: 85, f: 14, na: 520 },
          { name: 'Paneer Tikka with Quinoa Pulao', cal: 620, p: 28, c: 70, f: 22, na: 580 },
          { name: 'Rajma Chawal with Steamed Greens', cal: 590, p: 22, c: 92, f: 12, na: 610 },
        ]
      : [
          { name: 'Grilled Chicken Breast with Brown Rice & Greens', cal: 560, p: 44, c: 55, f: 14, na: 480 },
          { name: 'Tandoori Fish Tikka with Lemon Herb Salad', cal: 490, p: 40, c: 25, f: 16, na: 520 },
        ];

    const dinnerOptions = isVeg
      ? [
          { name: 'Stir-Fried Tofu with Asian Vegetables', cal: 450, p: 26, c: 35, f: 18, na: 460 },
          { name: 'Lauki Channa Dal with Multigrain Phulka', cal: 420, p: 18, c: 62, f: 10, na: 410 },
          { name: 'Warm Lentil Soup with Mixed Veggies', cal: 380, p: 19, c: 50, f: 9, na: 390 },
        ]
      : [
          { name: 'Herb Roasted Salmon with Asparagus', cal: 520, p: 38, c: 18, f: 26, na: 380 },
          { name: 'Clear Chicken Vegetable Wonton Soup', cal: 390, p: 32, c: 28, f: 10, na: 540 },
        ];

    const daysInMonth = new Date(currentYear, currentMonth + 1, 0).getDate();
    // Pre-populate ~22 days
    for (let day = 1; day <= daysInMonth; day++) {
      if (day % 4 === 0) continue; // Skip a few days to simulate real life
      const dateStr = `${currentYear}-${String(currentMonth + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
      
      const b = breakfastOptions[day % breakfastOptions.length];
      const l = lunchOptions[(day + 1) % lunchOptions.length];
      const d = dinnerOptions[(day + 2) % dinnerOptions.length];

      // Breakfast
      onSaveMealToLog({
        id: `demo_${dateStr}_b`,
        date: dateStr,
        mealSlot: 'Breakfast',
        timestamp: '08:30 AM',
        items: [{ name: b.name, portion: 1.0, price: '' }],
        nutrients: { calories: b.cal, protein: b.p, carbs: b.c, fat: b.f, sodium: b.na, fiber: 6 },
      });

      // Lunch
      onSaveMealToLog({
        id: `demo_${dateStr}_l`,
        date: dateStr,
        mealSlot: 'Lunch',
        timestamp: '01:15 PM',
        items: [{ name: l.name, portion: 1.0, price: '' }],
        nutrients: { calories: l.cal, protein: l.p, carbs: l.c, fat: l.f, sodium: l.na, fiber: 9 },
      });

      // Dinner
      onSaveMealToLog({
        id: `demo_${dateStr}_d`,
        date: dateStr,
        mealSlot: 'Dinner',
        timestamp: '07:45 PM',
        items: [{ name: d.name, portion: 1.0, price: '' }],
        nutrients: { calories: d.cal, protein: d.p, carbs: d.c, fat: d.f, sodium: d.na, fiber: 7 },
      });
    }
  };

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* 1. Monthly Plan Health Dashboard Banner */}
      <section className="bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-100 pb-5">
          <div>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                <CalendarIcon className="w-4 h-4 text-emerald-600" />
              </div>
              <h2 className="text-lg font-black text-slate-900 tracking-tight">
                Monthly Nutrition Calendar & Plan Analytics
              </h2>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Tracks continuous daily meal consumption against your personalized metabolic targets and clinical safety limits.
            </p>
          </div>

          {/* Month Navigation & Demo Actions */}
          <div className="flex flex-wrap items-center gap-2">
            <div className="inline-flex items-center bg-slate-100 p-1 rounded-2xl border border-slate-200">
              <button
                onClick={handlePrevMonth}
                className="p-1.5 rounded-xl hover:bg-white text-slate-600 hover:text-slate-900 transition cursor-pointer"
                title="Previous Month"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="px-3 text-xs font-bold text-slate-800 min-w-[120px] text-center select-none">
                {MONTH_NAMES[currentMonth]} {currentYear}
              </span>
              <button
                onClick={handleNextMonth}
                className="p-1.5 rounded-xl hover:bg-white text-slate-600 hover:text-slate-900 transition cursor-pointer"
                title="Next Month"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>

            <button
              onClick={handleJumpToToday}
              className="px-3 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-bold transition cursor-pointer"
            >
              Today
            </button>

            <button
              onClick={handleGenerateSampleMonth}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-emerald-50 hover:bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-bold transition shadow-2xs cursor-pointer"
              title="Pre-populate month with clinically balanced sample meals matching your matrix"
            >
              <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
              <span>Demo Sample Plan</span>
            </button>
          </div>
        </div>

        {/* Basic Metrics of the Whole Plan (KPI Cards) */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Caloric Intake vs Target */}
          <div className="p-4 rounded-2xl bg-slate-50/80 border border-slate-200 shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-slate-500 text-[11px] font-bold uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <Flame className="w-3.5 h-3.5 text-amber-500" /> Avg Daily Calories
              </span>
              <span className="text-[10px] text-slate-400">Target: {dailyTargets.calories}</span>
            </div>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-black text-slate-900 tabular-nums">
                {monthlyMetrics.avgDailyCals} <span className="text-xs font-normal text-slate-500">kcal/day</span>
              </span>
            </div>
            {/* Progress bar */}
            <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
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
            <div className="text-[10px] text-slate-500 font-medium flex justify-between">
              <span>{monthlyMetrics.loggedDaysCount} days recorded</span>
              <span className={monthlyMetrics.avgDailyCals <= dailyTargets.calories ? 'text-emerald-700 font-bold' : 'text-amber-700 font-bold'}>
                {monthlyMetrics.avgDailyCals <= dailyTargets.calories ? 'Deficit' : 'Surplus'} (
                {Math.abs(monthlyMetrics.avgDailyCals - dailyTargets.calories)} kcal)
              </span>
            </div>
          </div>

          {/* Average Daily Protein & Split */}
          <div className="p-4 rounded-2xl bg-slate-50/80 border border-slate-200 shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-slate-500 text-[11px] font-bold uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-emerald-500" /> Average Macros
              </span>
              <span className="text-[10px] text-slate-400">P / C / F</span>
            </div>
            <div className="text-xl font-black text-slate-900 tabular-nums">
              {monthlyMetrics.avgDailyProtein}g <span className="text-xs font-bold text-emerald-600">Protein</span>
            </div>
            <div className="text-[11px] text-slate-600 font-medium">
              Carbs: <b>{monthlyMetrics.avgDailyCarbs}g</b> • Fat: <b>{monthlyMetrics.avgDailyFat}g</b>
            </div>
            <div className="text-[10px] text-slate-400">
              Protein Target: {dailyTargets.protein}g ({Math.round((monthlyMetrics.avgDailyProtein / (dailyTargets.protein || 120)) * 100)}%)
            </div>
          </div>

          {/* Plan Adherence Rate */}
          <div className="p-4 rounded-2xl bg-slate-50/80 border border-slate-200 shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-slate-500 text-[11px] font-bold uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5 text-blue-500" /> Plan Adherence
              </span>
              <span className="text-[10px] text-slate-400">Compliance</span>
            </div>
            <div className="text-xl font-black text-slate-900 tabular-nums">
              {monthlyMetrics.complianceRate}%
            </div>
            <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-500"
                style={{ width: `${monthlyMetrics.complianceRate}%` }}
              />
            </div>
            <div className="text-[10px] text-slate-500 font-medium">
              {monthlyMetrics.optimalDaysCount} of {monthlyMetrics.loggedDaysCount} recorded days optimal
            </div>
          </div>

          {/* Clinical Guardrail & Sodium Safety */}
          <div className="p-4 rounded-2xl bg-slate-50/80 border border-slate-200 shadow-2xs space-y-2">
            <div className="flex items-center justify-between text-slate-500 text-[11px] font-bold uppercase tracking-wider">
              <span className="flex items-center gap-1.5">
                <Heart className="w-3.5 h-3.5 text-rose-500" /> Sodium & Safety
              </span>
              <span className="text-[10px] text-slate-400">Ceiling: {dailyTargets.sodium_ceiling}mg</span>
            </div>
            <div className="text-xl font-black text-slate-900 tabular-nums">
              {monthlyMetrics.avgDailySodium} <span className="text-xs font-normal text-slate-500">mg/day</span>
            </div>
            <div className="text-[10px] font-semibold mt-1">
              {monthlyMetrics.avgDailySodium <= dailyTargets.sodium_ceiling ? (
                <span className="text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded-md border border-emerald-200 inline-block">
                  ✓ Safe Clinical Range
                </span>
              ) : (
                <span className="text-rose-700 bg-rose-50 px-2 py-0.5 rounded-md border border-rose-200 inline-block">
                  ⚠️ Above Sodium Limit
                </span>
              )}
            </div>
            <div className="text-[10px] text-slate-400">
              Total monthly meals: {monthlyMetrics.totalMealsCount}
            </div>
          </div>
        </div>
      </section>

      {/* 2. Main Calendar Grid + Selected Day Breakdown Split Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left / Center: Interactive Monthly Calendar Grid (7 columns) */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="font-bold text-slate-900 text-sm flex items-center gap-2">
              <CalendarIcon className="w-4 h-4 text-emerald-600" />
              {MONTH_NAMES[currentMonth]} {currentYear} Calendar View
            </h3>

            {/* Legend */}
            <div className="flex items-center gap-3 text-[10px] font-semibold text-slate-500">
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

          {/* Weekday Header */}
          <div className="grid grid-cols-7 gap-1 text-center text-xs font-bold text-slate-400 uppercase tracking-wider py-1 border-b border-slate-100">
            {WEEKDAY_NAMES.map((name) => (
              <div key={name} className="py-1">
                {name}
              </div>
            ))}
          </div>

          {/* Calendar Grid Cells */}
          <div className="grid grid-cols-7 gap-1.5">
            {calendarDays.map((item, idx) => {
              const { dayNumber, dateStr, isCurrentMonth } = item;
              const isSelected = selectedDate === dateStr;
              const isToday = todayStr === dateStr;
              const dayStat = dailyStatsMap[dateStr];
              const status = getDayStatus(dateStr);

              // Status background styling
              let statusBorder = 'border-slate-100 hover:border-slate-300';
              let statusPill = null;

              if (status === 'OPTIMAL') {
                statusBorder = 'border-emerald-200 bg-emerald-50/20';
                statusPill = 'bg-emerald-500 text-white';
              } else if (status === 'MODERATE') {
                statusBorder = 'border-amber-200 bg-amber-50/20';
                statusPill = 'bg-amber-500 text-white';
              } else if (status === 'OVER') {
                statusBorder = 'border-rose-200 bg-rose-50/20';
                statusPill = 'bg-rose-500 text-white';
              }

              return (
                <button
                  key={idx}
                  onClick={() => setSelectedDate(dateStr)}
                  className={`min-h-[80px] p-2 rounded-2xl border text-left flex flex-col justify-between transition-all duration-150 cursor-pointer ${
                    isCurrentMonth ? 'bg-white' : 'bg-slate-50/50 text-slate-300 opacity-60'
                  } ${statusBorder} ${
                    isSelected ? 'ring-2 ring-emerald-500 shadow-md border-emerald-500' : ''
                  }`}
                >
                  <div className="flex items-center justify-between w-full">
                    <span
                      className={`text-xs font-bold w-5 h-5 rounded-full flex items-center justify-center ${
                        isToday ? 'bg-emerald-600 text-white' : 'text-slate-700'
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
                      <div className="text-[10px] font-extrabold text-slate-800 tabular-nums">
                        {Math.round(dayStat.calories)} <span className="text-[8px] font-normal text-slate-400">kcal</span>
                      </div>
                      <div className="text-[9px] text-slate-400">
                        {dayStat.meals.length} {dayStat.meals.length === 1 ? 'meal' : 'meals'}
                      </div>
                    </div>
                  ) : (
                    <div className="text-[9px] text-slate-300 mt-2 italic">
                      —
                    </div>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Right: Selected Day Consumption Breakdown */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-3xl p-6 shadow-sm space-y-6 flex flex-col justify-between">
          <div className="space-y-5">
            {/* Header with Selected Date & Adherence Status */}
            <div className="border-b border-slate-100 pb-4">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 block">
                    Daily Consumption Breakdown
                  </span>
                  <h3 className="text-base font-black text-slate-900 mt-0.5">
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
                  <span className="px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 text-xs font-black flex items-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" /> Optimal Fit
                  </span>
                )}
                {selectedDayStatus === 'MODERATE' && (
                  <span className="px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 border border-amber-200 text-xs font-black flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5 text-amber-600" /> Moderate
                  </span>
                )}
                {selectedDayStatus === 'OVER' && (
                  <span className="px-2.5 py-1 rounded-full bg-rose-100 text-rose-800 border border-rose-200 text-xs font-black flex items-center gap-1">
                    <ShieldAlert className="w-3.5 h-3.5 text-rose-600" /> Over Budget
                  </span>
                )}
                {selectedDayStatus === 'EMPTY' && (
                  <span className="px-2.5 py-1 rounded-full bg-slate-100 text-slate-500 text-xs font-bold">
                    No Logs Yet
                  </span>
                )}
              </div>

              {/* Day Macro Gauges */}
              <div className="mt-4 grid grid-cols-3 gap-2 text-center">
                <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Calories</div>
                  <div className="text-sm font-black text-slate-900 tabular-nums">
                    {Math.round(selectedDayData.calories)}
                  </div>
                  <div className="text-[9px] text-slate-400">of {dailyTargets.calories} kcal</div>
                </div>

                <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Protein</div>
                  <div className="text-sm font-black text-emerald-600 tabular-nums">
                    {Math.round(selectedDayData.protein)}g
                  </div>
                  <div className="text-[9px] text-slate-400">of {dailyTargets.protein}g</div>
                </div>

                <div className="p-2 rounded-xl bg-slate-50 border border-slate-100">
                  <div className="text-[10px] text-slate-400 font-bold uppercase">Sodium</div>
                  <div className="text-sm font-black text-slate-800 tabular-nums">
                    {Math.round(selectedDayData.sodium)}
                  </div>
                  <div className="text-[9px] text-slate-400">of {dailyTargets.sodium_ceiling} mg</div>
                </div>
              </div>
            </div>

            {/* List of Meals Consumed on Selected Date */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-700 flex items-center gap-1.5">
                  <Utensils className="w-3.5 h-3.5 text-emerald-600" />
                  Meals Consumed ({selectedDayData.meals.length})
                </span>

                <button
                  onClick={() => setIsAddMealModalOpen(true)}
                  className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200 text-xs font-bold transition cursor-pointer"
                >
                  <Plus className="w-3 h-3" /> Log Meal
                </button>
              </div>

              {selectedDayData.meals.length === 0 ? (
                <div className="p-6 text-center bg-slate-50/60 rounded-2xl border border-dashed border-slate-200 space-y-2">
                  <p className="text-xs text-slate-500 font-medium">No meals logged on this date.</p>
                  {activePlate.length > 0 ? (
                    <button
                      onClick={handleAddActivePlateToSelectedDay}
                      className="px-3 py-1.5 rounded-xl bg-emerald-600 text-white text-xs font-bold shadow-2xs hover:bg-emerald-700 transition cursor-pointer"
                    >
                      Log Current Plate ({activePlate.length} items) Here
                    </button>
                  ) : (
                    <button
                      onClick={() => setIsAddMealModalOpen(true)}
                      className="px-3 py-1.5 rounded-xl bg-slate-200 text-slate-700 text-xs font-bold hover:bg-slate-300 transition cursor-pointer"
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
                      className="p-3 rounded-2xl border border-slate-200/90 bg-white hover:border-slate-300 transition-all shadow-2xs space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <span className="px-2 py-0.5 rounded-md bg-slate-100 text-slate-800 font-bold text-[10px] uppercase tracking-wider">
                            {meal.mealSlot || 'Meal'}
                          </span>
                          <span className="text-[10px] text-slate-400 flex items-center gap-1">
                            <Clock className="w-3 h-3" /> {meal.timestamp || 'Logged'}
                          </span>
                        </div>

                        {onRemoveLoggedMeal && (
                          <button
                            onClick={() => onRemoveLoggedMeal(meal.id)}
                            className="text-slate-300 hover:text-rose-500 p-1 transition cursor-pointer"
                            title="Delete this meal entry"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>

                      {/* Dishes consumed in this meal */}
                      <div className="space-y-1">
                        {(meal.items || []).map((dishItem, i) => (
                          <div key={i} className="text-xs text-slate-800 font-semibold flex items-center justify-between">
                            <span>
                              {dishItem.name}{' '}
                              {dishItem.portion && dishItem.portion !== 1 && (
                                <span className="text-[10px] text-slate-400 font-normal">
                                  ({dishItem.portion}x)
                                </span>
                              )}
                            </span>
                            {dishItem.price && (
                              <span className="text-[10px] text-slate-400 font-mono">
                                {dishItem.price}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>

                      {/* Meal Nutrients pill */}
                      <div className="pt-1.5 border-t border-slate-100 flex items-center justify-between text-[10px] text-slate-500">
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
            <div className="pt-4 border-t border-slate-100">
              <button
                onClick={handleAddActivePlateToSelectedDay}
                className="w-full py-2 px-3 rounded-xl bg-slate-100 hover:bg-emerald-600 hover:text-white text-slate-700 text-xs font-bold transition flex items-center justify-center gap-1.5 cursor-pointer"
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
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl border border-slate-200 shadow-xl max-w-md w-full p-6 space-y-4 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <h3 className="font-bold text-slate-900 text-base flex items-center gap-2">
                <Utensils className="w-4 h-4 text-emerald-600" /> Log Meal Entry
              </h3>
              <button
                onClick={() => setIsAddMealModalOpen(false)}
                className="text-slate-400 hover:text-slate-600 p-1 cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveCustomMeal} className="space-y-3 text-xs">
              <div>
                <label className="block text-slate-500 font-bold mb-1">Meal Slot</label>
                <div className="grid grid-cols-4 gap-1.5">
                  {['Breakfast', 'Lunch', 'Dinner', 'Snacks'].map((slot) => (
                    <button
                      key={slot}
                      type="button"
                      onClick={() => setNewMealSlot(slot)}
                      className={`py-1.5 text-center font-bold rounded-xl border transition cursor-pointer ${
                        newMealSlot === slot
                          ? 'bg-emerald-600 text-white border-emerald-600'
                          : 'bg-slate-50 text-slate-700 border-slate-200 hover:bg-slate-100'
                      }`}
                    >
                      {slot}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-slate-500 font-bold mb-1">Dish Name or Description</label>
                {dishes && dishes.length > 0 ? (
                  <div className="space-y-1.5">
                    <input
                      type="text"
                      list="candidate-dishes"
                      value={newMealDishName}
                      onChange={(e) => setNewMealDishName(e.target.value)}
                      placeholder="e.g. Lauki Channa Dal with Roti"
                      className="w-full px-3 py-2 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
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
                    className="w-full px-3 py-2 rounded-xl border border-slate-300 text-slate-900 focus:outline-none focus:ring-2 focus:ring-emerald-500/20"
                    required
                  />
                )}
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="block text-slate-500 font-bold mb-1">Calories (kcal)</label>
                  <input
                    type="number"
                    value={newMealCalories}
                    onChange={(e) => setNewMealCalories(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-xl border border-slate-300 text-slate-900 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-500 font-bold mb-1">Protein (g)</label>
                  <input
                    type="number"
                    value={newMealProtein}
                    onChange={(e) => setNewMealProtein(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-xl border border-slate-300 text-slate-900 text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-slate-500 font-bold mb-1">Sodium (mg)</label>
                  <input
                    type="number"
                    value={newMealSodium}
                    onChange={(e) => setNewMealSodium(e.target.value)}
                    className="w-full px-2.5 py-1.5 rounded-xl border border-slate-300 text-slate-900 text-xs font-mono"
                  />
                </div>
              </div>

              <div className="pt-3 border-t border-slate-100 flex justify-end gap-2">
                <button
                  type="button"
                  onClick={() => setIsAddMealModalOpen(false)}
                  className="px-4 py-2 rounded-xl bg-slate-100 text-slate-600 font-bold hover:bg-slate-200 transition cursor-pointer"
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
