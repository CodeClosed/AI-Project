import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './AuthContext';
import {
  API_BASE_URL,
  getStoredUser,
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
  age: 30,
  gender: 'male',
  height_cm: 175,
  weight_kg: 70,
  activity_level: 'moderate',
  primary_goal: 'maintenance',
  health_conditions: [],
  allergies: [],
  dietary_preferences: [],
  raw_bio_text: '',
  custom_targets_override: {
    enabled: false,
    target_calories_kcal: 2000,
    target_protein_g: 130,
    target_carbs_g: 220,
    target_fats_g: 65,
    sodium_ceiling_mg: 2300,
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
  const { user, isAuthenticated, isLoading } = useAuth();

  const [profile, setProfile] = useState(() => {
    try {
      const storedUser = getStoredUser();
      const userKey = storedUser?.id ? `nutrimenu_user_${storedUser.id}_account_profile` : null;
      const saved = (userKey && localStorage.getItem(userKey)) || localStorage.getItem('nutrimenu_account_profile');
      return saved ? JSON.parse(saved) : DEFAULT_PROFILE;
    } catch {
      return DEFAULT_PROFILE;
    }
  });

  const [userMatrix, setUserMatrix] = useState(() => computeLocalMatrix(profile));
  const [loadingMatrix, setLoadingMatrix] = useState(false);

  // AI Mode Selection: 'fast' (Groq LPU) vs 'main' (Google Gemini)
  const [aiMode, setAiModeState] = useState(() => {
    try {
      return localStorage.getItem('nutrimenu_ai_mode') || 'fast';
    } catch {
      return 'fast';
    }
  });

  const setAiMode = (newMode) => {
    setAiModeState(newMode);
    try {
      localStorage.setItem('nutrimenu_ai_mode', newMode);
    } catch {}
  };

  const toggleAiMode = () => {
    setAiMode(aiMode === 'fast' ? 'main' : 'fast');
  };
  // Active Plate & Multi-Dish State
  const [plate, setPlate] = useState(() => {
    try {
      const storedUser = getStoredUser();
      const userKey = storedUser?.id ? `nutrimenu_user_${storedUser.id}_active_plate` : null;
      const saved = (userKey && localStorage.getItem(userKey)) || localStorage.getItem('nutrimenu_active_plate');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  // Logged Daily Meals History
  const [loggedMeals, setLoggedMeals] = useState(() => {
    try {
      const storedUser = getStoredUser();
      const userKey = storedUser?.id ? `nutrimenu_user_${storedUser.id}_daily_logged_meals` : null;
      const saved = (userKey && localStorage.getItem(userKey)) || localStorage.getItem('nutrimenu_daily_logged_meals');
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
      const storedUser = getStoredUser();
      const userKey = storedUser?.id ? `nutrimenu_user_${storedUser.id}_saved_menus` : null;
      const saved = (userKey && localStorage.getItem(userKey)) || localStorage.getItem('nutrimenu_saved_menus');
      return saved ? JSON.parse(saved) : [];
    } catch {
      return [];
    }
  });

  const [evalResult, setEvalResult] = useState(null);
  const [evalLoading, setEvalLoading] = useState(false);

  const isLoggingOutRef = useRef(false);
  const profileDebounceRef = useRef(null);
  const initialLoadDoneRef = useRef(false);

  const getStorageKey = useCallback((suffix) => {
    return user?.id ? `nutrimenu_user_${user.id}_${suffix}` : `nutrimenu_guest_${suffix}`;
  }, [user?.id]);

  useEffect(() => {
    if (isLoggingOutRef.current) return;
    try {
      const key = getStorageKey('saved_menus');
      localStorage.setItem(key, JSON.stringify(savedMenus));
      if (!user?.id) {
        localStorage.setItem('nutrimenu_saved_menus', JSON.stringify(savedMenus));
      }
    } catch {}
  }, [savedMenus, getStorageKey, user?.id]);

  useEffect(() => {
    if (isLoggingOutRef.current) return;
    try {
      const key = getStorageKey('account_profile');
      localStorage.setItem(key, JSON.stringify(profile));
      if (!user?.id) {
        localStorage.setItem('nutrimenu_account_profile', JSON.stringify(profile));
      }
    } catch {}
    setUserMatrix(computeLocalMatrix(profile));
  }, [profile, getStorageKey, user?.id]);

  useEffect(() => {
    if (isLoggingOutRef.current) return;
    try {
      const key = getStorageKey('active_plate');
      localStorage.setItem(key, JSON.stringify(plate));
      if (!user?.id) {
        localStorage.setItem('nutrimenu_active_plate', JSON.stringify(plate));
      }
    } catch {}
  }, [plate, getStorageKey, user?.id]);

  useEffect(() => {
    if (isLoggingOutRef.current) return;
    try {
      const key = getStorageKey('daily_logged_meals');
      localStorage.setItem(key, JSON.stringify(loggedMeals));
      if (!user?.id) {
        localStorage.setItem('nutrimenu_daily_logged_meals', JSON.stringify(loggedMeals));
      }
    } catch {}
  }, [loggedMeals, getStorageKey, user?.id]);

  // Clean in-memory user data immediately upon logout without wiping saved cache
  useEffect(() => {
    const handleLogout = () => {
      isLoggingOutRef.current = true;
      initialLoadDoneRef.current = false;
      if (profileDebounceRef.current) {
        clearTimeout(profileDebounceRef.current);
      }
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
        mode: aiMode,
        ai_provider: aiMode === 'fast' ? 'groq' : 'gemini',
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
      // Do nothing while auth is still verifying on app start or refresh
      if (isLoading) {
        return;
      }

      if (!isAuthenticated || !user?.id) {
        return;
      }

      isLoggingOutRef.current = false;

      // 1. Immediately rehydrate from locally cached user storage to eliminate delay
      let localCachedProfile = null;
      try {
        const cachedProfileStr = localStorage.getItem(`nutrimenu_user_${user.id}_account_profile`);
        if (cachedProfileStr) {
          const parsed = JSON.parse(cachedProfileStr);
          if (parsed && typeof parsed === 'object') {
            localCachedProfile = parsed;
            setProfile(parsed);
            setUserMatrix(computeLocalMatrix(parsed));
          }
        }

        const cachedPlateStr = localStorage.getItem(`nutrimenu_user_${user.id}_active_plate`);
        if (cachedPlateStr) {
          const parsed = JSON.parse(cachedPlateStr);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setPlate(parsed);
          }
        } else {
          // If user plate is empty, check if guest had items to migrate
          const guestPlateStr = localStorage.getItem('nutrimenu_guest_active_plate') || localStorage.getItem('nutrimenu_active_plate');
          if (guestPlateStr) {
            const guestPlate = JSON.parse(guestPlateStr);
            if (Array.isArray(guestPlate) && guestPlate.length > 0) {
              setPlate(guestPlate);
            }
          }
        }

        const cachedMealsStr = localStorage.getItem(`nutrimenu_user_${user.id}_daily_logged_meals`);
        if (cachedMealsStr) {
          const parsed = JSON.parse(cachedMealsStr);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setLoggedMeals(parsed);
          }
        }

        const cachedMenusStr = localStorage.getItem(`nutrimenu_user_${user.id}_saved_menus`);
        if (cachedMenusStr) {
          const parsed = JSON.parse(cachedMenusStr);
          if (Array.isArray(parsed) && parsed.length > 0) {
            setSavedMenus(parsed);
          }
        }
      } catch (err) {
        console.warn('Error reading local user cache on login:', err);
      }

      // 2. Fetch authoritative cloud data from backend database
      try {
        const cloudProfile = await fetchUserProfile();
        if (cloudProfile) {
          const mappedProfile = {
            age: cloudProfile.age ?? localCachedProfile?.age ?? 35,
            gender: cloudProfile.gender ?? localCachedProfile?.gender ?? 'male',
            height_cm: cloudProfile.height_cm ?? localCachedProfile?.height_cm ?? 175,
            weight_kg: cloudProfile.weight_kg ?? localCachedProfile?.weight_kg ?? 75,
            activity_level: cloudProfile.activity_level ?? localCachedProfile?.activity_level ?? 'moderate',
            primary_goal: cloudProfile.primary_goal ?? localCachedProfile?.primary_goal ?? 'maintenance',
            health_conditions: cloudProfile.health_conditions || localCachedProfile?.health_conditions || [],
            allergies: cloudProfile.allergies || localCachedProfile?.allergies || [],
            dietary_preferences: cloudProfile.dietary_preferences || localCachedProfile?.dietary_preferences || [],
            raw_bio_text: cloudProfile.raw_bio_text || localCachedProfile?.raw_bio_text || '',
            custom_targets_override:
              cloudProfile.cached_matrix?.custom_targets_override ||
              cloudProfile.custom_targets_override ||
              localCachedProfile?.custom_targets_override ||
              DEFAULT_PROFILE.custom_targets_override,
          };
          setProfile(mappedProfile);
          if (cloudProfile.cached_matrix) {
            setUserMatrix(cloudProfile.cached_matrix);
          } else {
            setUserMatrix(computeLocalMatrix(mappedProfile));
          }

          // If active plate in local state is still empty, restore active_plate from cloud matrix backup
          if (Array.isArray(cloudProfile.cached_matrix?.active_plate) && cloudProfile.cached_matrix.active_plate.length > 0) {
            setPlate((prev) => (prev.length === 0 ? cloudProfile.cached_matrix.active_plate : prev));
          }
        }

        const cloudMeals = await fetchUserMeals();
        if (Array.isArray(cloudMeals) && cloudMeals.length > 0) {
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
        }

        const cloudMenus = await fetchSavedMenus();
        if (Array.isArray(cloudMenus) && cloudMenus.length > 0) {
          setSavedMenus(cloudMenus);
        }
      } catch (err) {
        console.warn('Failed loading cloud data:', err);
      } finally {
        // Mark cloud data hydration as completed for this session
        initialLoadDoneRef.current = true;
      }
    }
    loadCloudUserData();
  }, [isAuthenticated, isLoading, user?.id]);

  // Auto-save biometric profile updates to database with 1.5s debounce
  useEffect(() => {
    if (!isAuthenticated || !user?.id || isLoggingOutRef.current) return;

    // Do NOT trigger autosave if cloud profile hasn't loaded yet!
    if (!initialLoadDoneRef.current) {
      return;
    }

    if (profileDebounceRef.current) {
      clearTimeout(profileDebounceRef.current);
    }

    profileDebounceRef.current = setTimeout(async () => {
      try {
        const localMatrix = userMatrix || computeLocalMatrix(profile);
        await updateUserProfile({
          ...profile,
          cached_matrix: {
            ...localMatrix,
            custom_targets_override: profile.custom_targets_override,
            active_plate: plate,
          },
        });
      } catch (err) {
        // Silently catch background autosave
      }
    }, 1500);

    return () => {
      if (profileDebounceRef.current) {
        clearTimeout(profileDebounceRef.current);
      }
    };
  }, [profile, isAuthenticated, user?.id, plate]);

  const handleSaveProfile = async (profileOverride = null) => {
    const profileToSave = profileOverride || profile;
    const baseMatrix = userMatrix || computeLocalMatrix(profileToSave);

    // 1. Immediately save to backend database with current/base matrix so it never hangs
    if (isAuthenticated) {
      try {
        await updateUserProfile({
          ...profileToSave,
          cached_matrix: {
            ...baseMatrix,
            custom_targets_override: profileToSave.custom_targets_override,
            active_plate: plate,
          },
        });
      } catch (err) {
        console.error('Failed saving profile to database:', err);
      }
    }

    // 2. Request updated AI matrix in background/async
    try {
      const updatedMatrix = await syncMatrix(profileToSave);
      if (isAuthenticated && updatedMatrix) {
        try {
          await updateUserProfile({
            ...profileToSave,
            cached_matrix: {
              ...updatedMatrix,
              custom_targets_override: profileToSave.custom_targets_override,
              active_plate: plate,
            },
          });
        } catch (err) {
          console.warn('Failed saving updated matrix to database:', err);
        }
      }
      if (updatedMatrix && dishes.length > 0) {
        runEvaluation(updatedMatrix, dishes);
      }
      return updatedMatrix;
    } catch (err) {
      console.warn('Backend matrix generation fallback to local:', err);
      return baseMatrix;
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
    const todayStr = new Date().toISOString().split('T')[0];
    const mealId = mealEntry.id || `meal_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;

    const normalized = {
      ...mealEntry,
      id: mealId,
      date: mealEntry.date || todayStr,
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
    aiMode,
    setAiMode,
    toggleAiMode,
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
