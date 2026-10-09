import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { useAuth } from './AuthContext';
import {
  API_BASE_URL,
  generateHealthMatrix,
  evaluateRecommendations,
  fetchUserProfile,
  updateUserProfile,
  fetchUserMeals,
  saveMealToDb,
  deleteMealFromDb,
  fetchSavedMenus,
  saveMenuToDb,
  deleteSavedMenu,
} from '../api';

const NutritionContext = createContext(null);

export const DEFAULT_PROFILE = {
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
  custom_targets_override: {
    enabled: false,
    target_calories_kcal: 2000,
    target_protein_g: 130,
    target_carbs_g: 220,
    target_fats_g: 65,
    sodium_ceiling_mg: 2000,
    prescribed_by: '',
    clinical_notes: '',
  },
};

export function computeLocalMatrix(p) {
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

  const override = p.custom_targets_override;
  const isOverride = Boolean(override?.enabled);

  const finalCalories = isOverride && Number(override.target_calories_kcal) > 0
    ? Math.round(Number(override.target_calories_kcal))
    : Math.round(targetCalories);

  const finalProtein = isOverride && Number(override.target_protein_g) > 0
    ? Math.round(Number(override.target_protein_g))
    : Math.round(pG);

  const finalCarbs = isOverride && Number(override.target_carbs_g) > 0
    ? Math.round(Number(override.target_carbs_g))
    : Math.round(cG);

  const finalFats = isOverride && Number(override.target_fats_g) > 0
    ? Math.round(Number(override.target_fats_g))
    : Math.round(fG);

  const finalSodiumCeiling = isOverride && Number(override.sodium_ceiling_mg) > 0
    ? Math.round(Number(override.sodium_ceiling_mg))
    : (hasHTN ? 1800 : 2300);

  const finalPPct = finalCalories > 0 ? Math.round(((finalProtein * 4) / finalCalories) * 100) : Math.round(pPct);
  const finalFPct = finalCalories > 0 ? Math.round(((finalFats * 9) / finalCalories) * 100) : Math.round(fPct);
  const finalCPct = Math.max(0, 100 - finalPPct - finalFPct);

  return {
    user_id: 'active_user',
    user_summary: `${age}yo ${gender}, ${goal.replace('_', ' ')} (${finalCalories} kcal/day)${isOverride ? ' [Clinician Prescribed]' : ''}`,
    metabolic_targets: {
      bmr_kcal: Math.round(bmr),
      tdee_kcal: Math.round(tdee),
      target_calories_kcal: finalCalories,
      caloric_adjustment_ratio: adj,
      target_protein_g: finalProtein,
      target_protein_pct: finalPPct,
      target_carbs_g: finalCarbs,
      target_carbs_pct: finalCPct,
      target_fats_g: finalFats,
      target_fats_pct: finalFPct,
      protein_g_per_kg: isOverride && weight > 0 ? Number((finalProtein / weight).toFixed(2)) : pPerKg,
      target_water_liters: 2.5,
      strategy_summary: isOverride
        ? `Clinician Prescription Active: ${finalCalories} kcal (${finalProtein}g P / ${finalCarbs}g C / ${finalFats}g F), Sodium Ceiling: ${finalSodiumCeiling}mg.`
        : `Targeting ${Math.round(targetCalories)} kcal with ${Math.round(pG)}g protein.`,
      is_custom_override: isOverride,
      clinician_notes: isOverride ? (override.clinical_notes || '') : '',
      prescribed_by: isOverride ? (override.prescribed_by || '') : '',
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
      sodium_ceiling_mg: finalSodiumCeiling,
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
    metadata: { source: isOverride ? 'clinician_override_matrix' : 'instant_local_reactive' },
  };
}

export function NutritionProvider({ children }) {
  const { user, isAuthenticated } = useAuth();

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
  // Active Plate & Multi-Dish State
  const [plate, setPlate] = useState(() => {
    try {
      const saved = localStorage.getItem('nutrimenu_active_plate');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Logged Daily Meals History
  const [loggedMeals, setLoggedMeals] = useState(() => {
    try {
      const saved = localStorage.getItem('nutrimenu_daily_logged_meals');
      if (!saved) return [];
      const parsed = JSON.parse(saved);
      if (!Array.isArray(parsed)) return [];
      return parsed
        .filter((m) => !m.id || !String(m.id).startsWith('demo_'))
        .map((m) => {
          const cals = Number(m.total_calories ?? m.nutrients?.calories ?? 0);
          const prot = Number(m.total_protein ?? m.nutrients?.protein ?? 0);
          const carbs = Number(m.total_carbs ?? m.nutrients?.carbs ?? 0);
          const fats = Number(m.total_fats ?? m.nutrients?.fat ?? m.nutrients?.fats ?? 0);
          const sod = Number(m.total_sodium ?? m.nutrients?.sodium ?? 0);
          return {
            ...m,
            total_calories: cals,
            total_protein: prot,
            total_carbs: carbs,
            total_fats: fats,
            total_sodium: sod,
            nutrients: {
              calories: cals,
              protein: prot,
              carbs: carbs,
              fat: fats,
              sodium: sod,
              fiber: Number(m.nutrients?.fiber) || 0,
            },
            dishes: m.dishes || m.items || [],
            items: m.items || m.dishes || [],
          };
        });
    } catch {
      return [];
    }
  });

  const [dishes, setDishes] = useState([]);
  const [ocrLoading, setOcrLoading] = useState(false);
  const [ocrError, setOcrError] = useState(null);
  const [imagePreview, setImagePreview] = useState(null);

  // Saved Menus History
  const [savedMenus, setSavedMenus] = useState(() => {
    try {
      const saved = localStorage.getItem('nutrimenu_saved_menus');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [evalResult, setEvalResult] = useState(null);
  const [evalLoading, setEvalLoading] = useState(false);

  const getStorageKey = useCallback((suffix) => {
    return user?.id ? `nutrimenu_user_${user.id}_${suffix}` : `nutrimenu_guest_${suffix}`;
  }, [user?.id]);

  useEffect(() => {
    try {
      localStorage.setItem(getStorageKey('saved_menus'), JSON.stringify(savedMenus));
    } catch {}
  }, [savedMenus, getStorageKey]);

  useEffect(() => {
    try {
      localStorage.setItem(getStorageKey('account_profile'), JSON.stringify(profile));
    } catch {}
    setUserMatrix(computeLocalMatrix(profile));
  }, [profile, getStorageKey]);

  useEffect(() => {
    try {
      localStorage.setItem(getStorageKey('active_plate'), JSON.stringify(plate));
    } catch {}
  }, [plate, getStorageKey]);

  useEffect(() => {
    try {
      localStorage.setItem(getStorageKey('daily_logged_meals'), JSON.stringify(loggedMeals));
    } catch {}
  }, [loggedMeals, getStorageKey]);

  // Clean in-memory user data immediately upon logout
  useEffect(() => {
    const handleLogout = () => {
      setPlate([]);
      setLoggedMeals([]);
      setSavedMenus([]);
      setDishes([]);
      setEvalResult(null);
      setImagePreview(null);
      setProfile(DEFAULT_PROFILE);
      setUserMatrix(computeLocalMatrix(DEFAULT_PROFILE));
    };
    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, []);

  const syncMatrix = useCallback(async (currentProfile) => {
    setLoadingMatrix(true);
    try {
      const data = await generateHealthMatrix(currentProfile);
      if (data?.matrix) {
        if (currentProfile?.custom_targets_override?.enabled) {
          const ov = currentProfile.custom_targets_override;
          const merged = { ...data.matrix };
          const cals = Number(ov.target_calories_kcal) || merged.metabolic_targets?.target_calories_kcal;
          const prot = Number(ov.target_protein_g) || merged.metabolic_targets?.target_protein_g;
          const carbs = Number(ov.target_carbs_g) || merged.metabolic_targets?.target_carbs_g;
          const fats = Number(ov.target_fats_g) || merged.metabolic_targets?.target_fats_g;
          const sod = Number(ov.sodium_ceiling_mg) || merged.nutritional_guardrails?.sodium_ceiling_mg;
          merged.metabolic_targets = {
            ...merged.metabolic_targets,
            target_calories_kcal: cals,
            target_protein_g: prot,
            target_carbs_g: carbs,
            target_fats_g: fats,
            strategy_summary: `Clinician Prescription Active: ${cals} kcal (${prot}g P / ${carbs}g C / ${fats}g F), Sodium Ceiling: ${sod}mg.`,
            is_custom_override: true,
            clinician_notes: ov.clinical_notes || '',
            prescribed_by: ov.prescribed_by || '',
          };
          merged.nutritional_guardrails = {
            ...merged.nutritional_guardrails,
            sodium_ceiling_mg: sod,
          };
          setUserMatrix(merged);
          return merged;
        }
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

  // Synchronize user profile & logged meals from database when logged in
  useEffect(() => {
    async function loadCloudUserData() {
      if (!isAuthenticated || !user) {
        setPlate([]);
        setLoggedMeals([]);
        setSavedMenus([]);
        setDishes([]);
        setEvalResult(null);
        setImagePreview(null);
        setProfile(DEFAULT_PROFILE);
        setUserMatrix(computeLocalMatrix(DEFAULT_PROFILE));
        return;
      }
      try {
        const cloudProfile = await fetchUserProfile();
        if (cloudProfile) {
          const mappedProfile = {
            age: cloudProfile.age ?? 35,
            gender: cloudProfile.gender ?? 'male',
            height_cm: cloudProfile.height_cm ?? 175,
            weight_kg: cloudProfile.weight_kg ?? 75,
            activity_level: cloudProfile.activity_level ?? 'moderate',
            primary_goal: cloudProfile.primary_goal ?? 'maintenance',
            health_conditions: cloudProfile.health_conditions || [],
            allergies: cloudProfile.allergies || [],
            dietary_preferences: cloudProfile.dietary_preferences || [],
            raw_bio_text: cloudProfile.raw_bio_text || '',
            custom_targets_override: cloudProfile.custom_targets_override || DEFAULT_PROFILE.custom_targets_override,
          };
          setProfile(mappedProfile);
          if (cloudProfile.cached_matrix) {
            setUserMatrix(cloudProfile.cached_matrix);
          } else {
            syncMatrix(mappedProfile);
          }
        } else {
          setProfile(DEFAULT_PROFILE);
          setUserMatrix(computeLocalMatrix(DEFAULT_PROFILE));
        }

        const cloudMeals = await fetchUserMeals();
        if (Array.isArray(cloudMeals)) {
          const normalized = cloudMeals.map((m) => {
            const cals = Number(m.total_calories ?? m.nutrients?.calories ?? 0);
            const prot = Number(m.total_protein ?? m.nutrients?.protein ?? 0);
            const carbs = Number(m.total_carbs ?? m.nutrients?.carbs ?? 0);
            const fats = Number(m.total_fats ?? m.nutrients?.fat ?? m.nutrients?.fats ?? 0);
            const sod = Number(m.total_sodium ?? m.nutrients?.sodium ?? 0);
            return {
              ...m,
              total_calories: cals,
              total_protein: prot,
              total_carbs: carbs,
              total_fats: fats,
              total_sodium: sod,
              nutrients: {
                calories: cals,
                protein: prot,
                carbs: carbs,
                fat: fats,
                sodium: sod,
                fiber: Number(m.nutrients?.fiber) || 0,
              },
              dishes: m.dishes || m.items || [],
              items: m.items || m.dishes || [],
            };
          });
          setLoggedMeals(normalized);
        } else {
          setLoggedMeals([]);
        }

        const cloudMenus = await fetchSavedMenus();
        if (Array.isArray(cloudMenus)) {
          setSavedMenus(cloudMenus);
        } else {
          setSavedMenus([]);
        }
      } catch (err) {
        console.warn('Failed loading cloud data:', err);
      }
    }
    loadCloudUserData();
  }, [isAuthenticated, user?.id, syncMatrix]);

  const handleSaveProfile = async () => {
    const updatedMatrix = await syncMatrix(profile);
    if (isAuthenticated) {
      try {
        await updateUserProfile({
          ...profile,
          cached_matrix: updatedMatrix,
        });
      } catch (err) {
        console.error('Failed saving profile to database:', err);
      }
    }
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

  // Saved Menu Management Handlers
  const handleLoadSavedMenu = (savedMenu) => {
    if (!savedMenu) return;
    if (savedMenu.dishes && Array.isArray(savedMenu.dishes)) {
      setDishes(savedMenu.dishes);
    }
    if (savedMenu.image_url) {
      const fullUrl = savedMenu.image_url.startsWith('http') 
        ? savedMenu.image_url 
        : `${API_BASE_URL}${savedMenu.image_url}`;
      setImagePreview(fullUrl);
    } else {
      setImagePreview(null);
    }
  };

  const handleDeleteSavedMenu = async (menuId) => {
    setSavedMenus((prev) => prev.filter((m) => m.id !== menuId));
    if (isAuthenticated) {
      try {
        await deleteSavedMenu(menuId);
      } catch (err) {
        console.error('Failed deleting saved menu from db:', err);
      }
    }
  };

  const handleSaveCurrentMenu = async (customTitle) => {
    if (!dishes || dishes.length === 0) return null;
    const newMenu = {
      id: `menu_${Date.now()}`,
      title: customTitle || `Menu Scan (${dishes.length} items)`,
      dishes: dishes,
      image_url: imagePreview && imagePreview.includes('/uploads/') ? imagePreview.replace(API_BASE_URL, '') : null,
      created_at: new Date().toISOString(),
    };
    setSavedMenus((prev) => [newMenu, ...prev]);
    if (isAuthenticated) {
      try {
        const saved = await saveMenuToDb(newMenu);
        if (saved?.id) {
          setSavedMenus((prev) => prev.map((m) => m.id === newMenu.id ? saved : m));
        }
      } catch (err) {
        console.error('Failed saving menu to database:', err);
      }
    }
    return newMenu;
  };

  // Plate Management Handlers
  const handleAddToPlate = (dish) => {
    const name = dish.name || dish.dish_name || String(dish);
    const existing = plate.find((p) => p.name.toLowerCase() === name.toLowerCase());
    if (existing) {
      setPlate(plate.map((p) => 
        p.name.toLowerCase() === name.toLowerCase() 
          ? { ...p, portion: (p.portion || 1.0) + 0.5, customization: dish.customization || p.customization }
          : p
      ));
    } else {
      setPlate([...plate, { name, price: dish.price || '', portion: 1.0, customization: dish.customization || null }]);
    }
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

  const handleSaveMealToLog = async (mealEntry) => {
    const cals = Number(mealEntry.total_calories ?? mealEntry.nutrients?.calories ?? 0);
    const prot = Number(mealEntry.total_protein ?? mealEntry.nutrients?.protein ?? 0);
    const carbs = Number(mealEntry.total_carbs ?? mealEntry.nutrients?.carbs ?? 0);
    const fats = Number(mealEntry.total_fats ?? mealEntry.nutrients?.fat ?? mealEntry.nutrients?.fats ?? 0);
    const sod = Number(mealEntry.total_sodium ?? mealEntry.nutrients?.sodium ?? 0);

    const normalized = {
      ...mealEntry,
      name: mealEntry.name || `${mealEntry.mealSlot || mealEntry.meal_type || 'Meal'} Plate`,
      meal_type: mealEntry.meal_type || mealEntry.mealSlot || 'Lunch',
      total_calories: cals,
      total_protein: prot,
      total_carbs: carbs,
      total_fats: fats,
      total_sodium: sod,
      nutrients: {
        calories: cals,
        protein: prot,
        carbs: carbs,
        fat: fats,
        sodium: sod,
        fiber: Number(mealEntry.nutrients?.fiber) || 0,
      },
      dishes: mealEntry.dishes || mealEntry.items || [],
      items: mealEntry.items || mealEntry.dishes || [],
    };

    setLoggedMeals((prev) => [normalized, ...prev]);
    setPlate([]);
    if (isAuthenticated) {
      try {
        await saveMealToDb(normalized);
      } catch (err) {
        console.error('Failed saving meal to database:', err);
      }
    }
  };

  const handleRemoveLoggedMeal = async (mealId) => {
    setLoggedMeals((prev) => prev.filter((m) => m.id !== mealId));
    if (isAuthenticated) {
      try {
        await deleteMealFromDb(mealId);
      } catch (err) {
        console.error('Failed deleting meal from database:', err);
      }
    }
  };

  const handleClearAllLoggedMeals = async () => {
    if (isAuthenticated) {
      try {
        for (const m of loggedMeals) {
          if (m.id) {
            await deleteMealFromDb(m.id).catch(() => {});
          }
        }
      } catch (err) {
        console.error('Failed clearing cloud meals:', err);
      }
    }
    setLoggedMeals([]);
    try {
      localStorage.removeItem('nutrimenu_daily_logged_meals');
      localStorage.removeItem(getStorageKey('daily_logged_meals'));
    } catch {}
  };

  const value = {
    profile,
    setProfile,
    userMatrix,
    setUserMatrix,
    loadingMatrix,
    syncMatrix,
    handleSaveProfile,
    plate,
    setPlate,
    handleAddToPlate,
    handleUpdatePortion,
    handleRemoveFromPlate,
    handleClearPlate,
    loggedMeals,
    setLoggedMeals,
    handleSaveMealToLog,
    handleRemoveLoggedMeal,
    handleClearAllLoggedMeals,
    dishes,
    setDishes,
    ocrLoading,
    setOcrLoading,
    ocrError,
    setOcrError,
    imagePreview,
    setImagePreview,
    savedMenus,
    setSavedMenus,
    handleLoadSavedMenu,
    handleDeleteSavedMenu,
    handleSaveCurrentMenu,
    evalResult,
    setEvalResult,
    evalLoading,
    runEvaluation,
  };

  return <NutritionContext.Provider value={value}>{children}</NutritionContext.Provider>;
}

export function useNutrition() {
  const context = useContext(NutritionContext);
  if (!context) {
    throw new Error('useNutrition must be used within a NutritionProvider');
  }
  return context;
}
