import React, { useState, useEffect, useCallback } from 'react';
import { Salad, ShieldCheck, User, Settings, Sparkles, Calendar, Utensils } from 'lucide-react';
import AccountDrawerModal from './components/AccountDrawerModal';
import MenuUploadSection from './components/MenuUploadSection';
import RecommendationTableSection from './components/RecommendationTableSection';
import MealPlateDrawer from './components/MealPlateDrawer';
import { generateHealthMatrix, evaluateRecommendations } from './api';

const DEFAULT_PROFILE = {
  age: 45,
  gender: 'male',
  height_cm: 176,
  weight_kg: 86,
  activity_level: 'sedentary',
  primary_goal: 'fat_loss',
  health_conditions: ['hypertension', 'type_2_diabetes', 'gerd'],
  allergies: ['peanuts'],
  dietary_preferences: ['vegetarian'],
  raw_bio_text: '',
};

function computeLocalMatrix(p) {
  const age = Number(p.age) || 30;
  const gender = String(p.gender || 'male').toLowerCase();
  const height = Number(p.height_cm) || 170;
  const weight = Number(p.weight_kg) || 70;
  const activity = String(p.activity_level || 'sedentary').toLowerCase();
  const goal = String(p.primary_goal || 'maintenance').toLowerCase();

  const s = gender === 'male' ? 5.0 : -161.0;
  const bmr = 10.0 * weight + 6.25 * height - 5.0 * age + s;
  const palMap = { sedentary: 1.2, light: 1.375, moderate: 1.55, heavy: 1.725, athlete: 1.9 };
  const pal = palMap[activity] || 1.2;
  const tdee = bmr * pal;

  let adj = 0.0;
  if (goal.includes('fat_loss') || goal.includes('deficit') || goal.includes('weight_loss')) {
    adj = -0.20;
  } else if (goal.includes('muscle') || goal.includes('gain') || goal.includes('surplus')) {
    adj = 0.10;
  }
  const targetCalories = Math.max(1000, tdee * (1.0 + adj));
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

  const hasDiabetes = (p.health_conditions || []).some(c => c.includes('diabet'));
  const hasHTN = (p.health_conditions || []).includes('hypertension');

  return {
    user_id: 'active_user',
    user_summary: `${age}yo ${gender}, ${goal.replace('_', ' ')} (${Math.round(targetCalories)} kcal/day)`,
    metabolic_targets: {
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
      protein_g_per_kg: pPerKg,
      target_water_liters: 2.5,
      strategy_summary: `Targeting ${Math.round(targetCalories)} kcal with ${Math.round(pG)}g protein.`,
    },
    clinical_risk_weights: {
      glycemic_sensitivity: hasDiabetes ? 0.9 : 0.3,
      cardiovascular_risk_weight: hasHTN ? 0.8 : 0.4,
      lipid_optimization_weight: 0.5,
      inflammation_index_weight: 0.4,
      digestive_sensitivity_weight: (p.health_conditions || []).includes('gerd') ? 0.8 : 0.3,
      satiety_demand_weight: 0.6,
    },
    nutritional_guardrails: {
      sodium_ceiling_mg: hasHTN ? 1800 : 2300,
      saturated_fat_max_pct: 0.08,
      added_sugar_max_g: hasDiabetes ? 15.0 : 25.0,
      dietary_fiber_min_g: 30.0,
      potassium_target_mg: 3500,
      omega3_min_g: 1.5,
      digestive_triggers_to_avoid: (p.health_conditions || []).includes('gerd') ? ['deep_fried', 'excess_chili', 'citrus'] : [],
      key_micronutrient_priorities: ['potassium', 'magnesium', 'vitamin_d'],
    },
    food_group_weights: {},
    exclusion_mask: [
      ...(p.dietary_preferences || []),
      ...(p.allergies || []),
    ],
    metadata: { source: 'instant_local_reactive' },
  };
}

export default function App() {
  const [profile, setProfile] = useState(() => {
    try {
      const saved = localStorage.getItem('nutrimenu_account_profile');
      return saved ? JSON.parse(saved) : DEFAULT_PROFILE;
    } catch {
      return DEFAULT_PROFILE;
    }
  });

  const [userMatrix, setUserMatrix] = useState(() => computeLocalMatrix(profile));
  const [loadingMatrix, setLoadingMatrix] = useState(false);
  const [isAccountModalOpen, setIsAccountModalOpen] = useState(false);

  // Active Plate & Multi-Dish State
  const [plate, setPlate] = useState(() => {
    try {
      const saved = localStorage.getItem('nutrimenu_active_plate');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });
  const [isPlateDrawerOpen, setIsPlateDrawerOpen] = useState(false);

  // Logged Daily Meals History
  const [loggedMeals, setLoggedMeals] = useState(() => {
    try {
      const saved = localStorage.getItem('nutrimenu_daily_logged_meals');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [dishes, setDishes] = useState([]);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  const [evalResult, setEvalResult] = useState(null);
  const [evalLoading, setEvalLoading] = useState(false);

  useEffect(() => {
    try {
      localStorage.setItem('nutrimenu_account_profile', JSON.stringify(profile));
    } catch {}
    setUserMatrix((prev) => prev || computeLocalMatrix(profile));
  }, [profile]);

  useEffect(() => {
    try {
      localStorage.setItem('nutrimenu_active_plate', JSON.stringify(plate));
    } catch {}
  }, [plate]);

  useEffect(() => {
    try {
      localStorage.setItem('nutrimenu_daily_logged_meals', JSON.stringify(loggedMeals));
    } catch {}
  }, [loggedMeals]);

  const syncMatrix = useCallback(async (currentProfile) => {
    setLoadingMatrix(true);
    try {
      const data = await generateHealthMatrix(currentProfile);
      if (data?.matrix) {
        setUserMatrix(data.matrix);
        return data.matrix;
      }
    } catch (err) {
      console.warn('Backend matrix generation fallback to local:', err);
    } finally {
      setLoadingMatrix(false);
    }
    const fallback = computeLocalMatrix(currentProfile);
    setUserMatrix(fallback);
    return fallback;
  }, []);

  useEffect(() => {
    syncMatrix(profile);
  }, []);

  const runEvaluation = async (
    activeMatrix = userMatrix,
    activeDishes = dishes
  ) => {
    const matrixToUse = activeMatrix || computeLocalMatrix(profile);
    if (!matrixToUse || activeDishes.length === 0) return;

    setEvalLoading(true);
    try {
      const payloadDishes = activeDishes.map((dish) => {
        if (typeof dish === 'object' && dish !== null) {
          return {
            name: dish.name || dish.label || String(dish),
            price: dish.price || '',
            description: dish.description || '',
            tags: dish.tags || [],
          };
        }
        return { name: String(dish), price: '', description: '', tags: [] };
      });

      const data = await evaluateRecommendations({
        matrix: matrixToUse,
        dishes: payloadDishes,
        items: payloadDishes,
        profile: profile,
      });

      const rawRes = data?.result || data?.recommendations || data || {};
      const t1 = rawRes.good_items || rawRes.tier_1_optimal || rawRes.good || [];
      const t2 = rawRes.medium_items || rawRes.tier_2_moderate || rawRes.medium || [];
      const t3 = rawRes.bad_items || rawRes.tier_3_avoid || rawRes.bad || [];

      const normalizedResult = {
        good_items: t1,
        medium_items: t2,
        bad_items: t3,
        tier_1_optimal: t1,
        tier_2_moderate: t2,
        tier_3_avoid: t3,
        good: t1,
        medium: t2,
        bad: t3,
        ...rawRes,
      };

      setEvalResult(normalizedResult);
    } catch (err) {
      console.error('Recommendation evaluation failed:', err);
    } finally {
      setEvalLoading(false);
    }
  };

  const handleSaveProfile = async () => {
    const updatedMatrix = await syncMatrix(profile);
    if (updatedMatrix && dishes.length > 0) {
      runEvaluation(updatedMatrix, dishes);
    }
  };

  useEffect(() => {
    if (dishes.length > 0) {
      const matrixToUse = userMatrix || computeLocalMatrix(profile);
      runEvaluation(matrixToUse, dishes);
    } else {
      setEvalResult(null);
    }
  }, [dishes, userMatrix]);

  // Plate Management Handlers
  const handleAddToPlate = (dish) => {
    const name = dish.name || dish.dish_name || String(dish);
    const existing = plate.find((p) => p.name.toLowerCase() === name.toLowerCase());
    if (existing) {
      setPlate(plate.map((p) => 
        p.name.toLowerCase() === name.toLowerCase() 
          ? { ...p, portion: (p.portion || 1.0) + 0.5 }
          : p
      ));
    } else {
      setPlate([...plate, { name, price: dish.price || '', portion: 1.0 }]);
    }
    setIsPlateDrawerOpen(true);
  };

  const handleUpdatePortion = (dishName, newPortion) => {
    setPlate(plate.map((p) => 
      p.name.toLowerCase() === dishName.toLowerCase() 
        ? { ...p, portion: newPortion }
        : p
    ));
  };

  const handleRemoveFromPlate = (dishName) => {
    setPlate(plate.filter((p) => p.name.toLowerCase() !== dishName.toLowerCase()));
  };

  const handleClearPlate = () => {
    setPlate([]);
  };

  const handleSaveMealToLog = (mealEntry) => {
    setLoggedMeals((prev) => [mealEntry, ...prev]);
    setPlate([]); // Clears active plate to start fresh for the next meal
  };

  const handleRemoveLoggedMeal = (mealId) => {
    setLoggedMeals((prev) => prev.filter((m) => m.id !== mealId));
  };

  const dietLabels = (profile.dietary_preferences || []).join(', ');
  const allergyLabels = (profile.allergies || []).join(', ');

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-900 flex flex-col justify-between selection:bg-emerald-500 selection:text-white font-sans">
      <header className="border-b border-slate-200/90 bg-white/95 backdrop-blur-md sticky top-0 z-40 shadow-xs">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-gradient-to-tr from-emerald-600 to-teal-500 flex items-center justify-center shadow-sm">
              <Salad className="w-5 h-5 text-white font-bold" />
            </div>
            <div>
              <span className="font-black text-lg text-slate-900 tracking-tight flex items-center gap-1.5">
                NutriMenu <span className="text-emerald-600">AI</span>
              </span>
              <span className="text-[10px] text-slate-500 block leading-none font-semibold">
                Clinical 3-Tier Food Recommendation Engine
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Active Plate Quick Opener */}
            <button
              onClick={() => setIsPlateDrawerOpen(true)}
              className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-emerald-50 border border-emerald-200 text-emerald-800 hover:bg-emerald-100 transition text-xs font-bold shadow-2xs cursor-pointer"
            >
              <Utensils className="w-4 h-4 text-emerald-600" />
              <span>My Plate</span>
              <span className="w-5 h-5 rounded-full bg-emerald-600 text-white text-[10px] flex items-center justify-center">
                {plate.length}
              </span>
            </button>

            {/* Profile Drawer Opener */}
            <button
              onClick={() => setIsAccountModalOpen(true)}
              className="flex items-center gap-3 px-3.5 py-1.5 rounded-full bg-slate-50 border border-slate-200 hover:border-emerald-400 hover:bg-slate-100/80 transition-all text-xs font-semibold text-slate-800 shadow-xs cursor-pointer"
            >
              <div className="relative w-8 h-8 rounded-full bg-slate-900 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                <User className="w-4 h-4" />
                <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 border-2 border-white rounded-full" />
              </div>
              <div className="text-left leading-tight hidden sm:block">
                <div className="font-bold text-slate-900 flex items-center gap-1.5">
                  <span>{dietLabels || 'Standard'}</span>
                  {allergyLabels && (
                    <span className="px-1.5 py-0.2 rounded-md bg-amber-100 text-amber-800 text-[10px] font-extrabold">
                      {allergyLabels}
                    </span>
                  )}
                </div>
                <div className="text-[10px] text-slate-500 font-medium">
                  {userMatrix?.metabolic_targets ? `${Math.round(userMatrix.metabolic_targets.target_calories_kcal)} kcal • Edit Profile` : 'Click to setup profile'}
                </div>
              </div>
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex-1 w-full space-y-8">
        {/* Section 1: OCR Menu Upload */}
        <MenuUploadSection
          profile={profile}
          dishes={dishes}
          setDishes={setDishes}
          ocrLoading={ocrLoading}
          setOcrLoading={setOcrLoading}
          ocrError={ocrError}
          setOcrError={setOcrError}
          imagePreview={imagePreview}
          setImagePreview={setImagePreview}
        />

        {/* Section 2: 3-Tier Recommendations */}
        <RecommendationTableSection
          dishes={dishes}
          userMatrix={userMatrix}
          userProfile={profile}
          evalResult={evalResult}
          evalLoading={evalLoading}
          onRunEvaluation={() => runEvaluation(userMatrix, dishes)}
          plate={plate}
          onAddToPlate={handleAddToPlate}
          onOpenPlateDrawer={() => setIsPlateDrawerOpen(true)}
        />
      </main>

      {/* Slide-out Meal Plate & Macro Burn-Down Drawer */}
      <MealPlateDrawer
        isOpen={isPlateDrawerOpen}
        onClose={() => setIsPlateDrawerOpen(false)}
        plate={plate}
        onUpdatePortion={handleUpdatePortion}
        onRemoveItem={handleRemoveFromPlate}
        onClearPlate={handleClearPlate}
        onAddItem={handleAddToPlate}
        allDishes={dishes}
        userMatrix={userMatrix}
        profile={profile}
        loggedMeals={loggedMeals}
        onSaveMealToLog={handleSaveMealToLog}
        onRemoveLoggedMeal={handleRemoveLoggedMeal}
      />

      <AccountDrawerModal
        isOpen={isAccountModalOpen}
        onClose={() => setIsAccountModalOpen(false)}
        profile={profile}
        setProfile={setProfile}
        userMatrix={userMatrix}
        onSaveProfile={handleSaveProfile}
        loadingMatrix={loadingMatrix}
      />

      <footer className="border-t border-slate-200/80 bg-white py-6 text-center text-xs text-slate-500">
        <div className="max-w-4xl mx-auto px-4">
          <p className="flex items-center justify-center gap-1.5 mb-1 text-slate-700 font-semibold">
            <ShieldCheck className="w-4 h-4 text-emerald-600" /> Medical & Nutritional Guidance Disclaimer
          </p>
          <p className="text-[11px] text-slate-500 leading-relaxed">
            Recommendations are computational estimates based on user biometric inputs and published clinical nutritional literature.
          </p>
        </div>
      </footer>
    </div>
  );
}
