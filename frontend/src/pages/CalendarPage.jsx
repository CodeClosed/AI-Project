import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useNutrition } from '../context/NutritionContext';
import MonthlyCalendarSection from '../components/MonthlyCalendarSection';

export default function CalendarPage() {
  const navigate = useNavigate();
  const {
    loggedMeals,
    handleSaveMealToLog,
    handleRemoveLoggedMeal,
    handleClearAllLoggedMeals,
    userMatrix,
    profile,
    dishes,
    plate,
    handleAddToPlate,
  } = useNutrition();

  return (
    <div className="space-y-8 animate-in fade-in duration-150">
      <MonthlyCalendarSection
        loggedMeals={loggedMeals}
        onSaveMealToLog={handleSaveMealToLog}
        onRemoveLoggedMeal={handleRemoveLoggedMeal}
        onClearAllLoggedMeals={handleClearAllLoggedMeals}
        userMatrix={userMatrix}
        userProfile={profile}
        dishes={dishes}
        activePlate={plate}
        onAddToPlate={handleAddToPlate}
      />
    </div>
  );
}
