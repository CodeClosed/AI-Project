import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Utensils } from 'lucide-react';
import { useNutrition } from '../context/NutritionContext';
import MenuUploadSection from '../components/MenuUploadSection';
import RecommendationTableSection from '../components/RecommendationTableSection';

export default function MenuScannerPage() {
  const navigate = useNavigate();
  const {
    profile,
    userMatrix,
    dishes,
    setDishes,
    ocrLoading,
    setOcrLoading,
    ocrError,
    setOcrError,
    imagePreview,
    setImagePreview,
    evalResult,
    evalLoading,
    runEvaluation,
    plate,
    handleAddToPlate,
  } = useNutrition();

  return (
    <div className="space-y-8 animate-in fade-in duration-150 relative">
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
      <RecommendationTableSection
        dishes={dishes}
        userMatrix={userMatrix}
        userProfile={profile}
        evalResult={evalResult}
        evalLoading={evalLoading}
        onRunEvaluation={() => runEvaluation(userMatrix, dishes)}
        plate={plate}
        onAddToPlate={handleAddToPlate}
      />

      {/* Floating Quick Action Pill when plate has items */}
      {plate.length > 0 && (
        <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-30 animate-in slide-in-from-bottom-4 duration-200">
          <Link
            to="/plate"
            className="flex items-center gap-2.5 px-5 py-2.5 rounded-full bg-slate-900/95 dark:bg-emerald-700/95 text-white backdrop-blur-md shadow-2xl hover:scale-105 transition-all text-xs font-bold border border-slate-700/60 dark:border-emerald-600 cursor-pointer"
          >
            <Utensils className="w-4 h-4 text-emerald-400 dark:text-emerald-200" />
            <span>{plate.length} {plate.length === 1 ? 'dish staged' : 'dishes staged'}</span>
            <span className="text-emerald-400 dark:text-emerald-200 font-extrabold flex items-center gap-1">
              Go to My Plate tab →
            </span>
          </Link>
        </div>
      )}
    </div>
  );
}
