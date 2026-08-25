import React from 'react';
import { CheckCircle2, AlertCircle, XCircle, Sparkles, Lightbulb, ShieldAlert } from 'lucide-react';

export default function DishCard({ dish }) {
  const isGood = dish.tier === 'GOOD';
  const isMedium = dish.tier === 'MEDIUM';
  const isBad = dish.tier === 'BAD';

  const tierStyles = isGood
    ? {
        border: 'border-emerald-500/40 hover:border-emerald-400',
        bg: 'bg-gradient-to-br from-emerald-950/20 via-slate-900/60 to-slate-900/40',
        badgeBg: 'bg-emerald-500 text-slate-950',
        badgeText: 'Tier 1: GOOD',
        icon: <CheckCircle2 className="w-5 h-5 text-emerald-400" />,
        shadow: 'hover:shadow-glow-green',
      }
    : isMedium
    ? {
        border: 'border-amber-500/40 hover:border-amber-400',
        bg: 'bg-gradient-to-br from-amber-950/20 via-slate-900/60 to-slate-900/40',
        badgeBg: 'bg-amber-500 text-slate-950',
        badgeText: 'Tier 2: MEDIUM',
        icon: <AlertCircle className="w-5 h-5 text-amber-400" />,
        shadow: 'hover:shadow-glow-amber',
      }
    : {
        border: 'border-rose-500/40 hover:border-rose-400',
        bg: 'bg-gradient-to-br from-rose-950/20 via-slate-900/60 to-slate-900/40',
        badgeBg: 'bg-rose-500 text-white',
        badgeText: 'Tier 3: BAD',
        icon: <XCircle className="w-5 h-5 text-rose-400" />,
        shadow: 'hover:shadow-glow-red',
      };

  return (
    <div
      className={`rounded-3xl p-6 border transition-all duration-300 ${tierStyles.border} ${tierStyles.bg} ${tierStyles.shadow} backdrop-blur-xl flex flex-col justify-between`}
    >
      <div>
        {/* Top Header with Badges */}
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2">
            {tierStyles.icon}
            <span className={`px-2.5 py-0.5 rounded-full text-xs font-black uppercase tracking-wider ${tierStyles.badgeBg}`}>
              {tierStyles.badgeText}
            </span>
          </div>

          <div className="flex items-center gap-2">
            {dish.price && (
              <span className="text-xs font-bold px-2 py-0.5 rounded-lg bg-slate-800 text-slate-300 border border-slate-700">
                {dish.price}
              </span>
            )}
            <span
              className={`text-xs font-extrabold px-2.5 py-0.5 rounded-lg ${
                isGood ? 'bg-emerald-500/20 text-emerald-300' : isMedium ? 'bg-amber-500/20 text-amber-300' : 'bg-rose-500/20 text-rose-300'
              }`}
            >
              Fit: {dish.fit_score}/100
            </span>
          </div>
        </div>

        {/* Dish Title */}
        <h3 className="text-lg font-bold text-white mb-2 leading-snug">{dish.dish_name}</h3>

        {/* Hard Exclusion Banner */}
        {dish.allergen_warnings && dish.allergen_warnings.length > 0 && (
          <div className="p-3 mb-3 rounded-2xl bg-rose-500/20 border border-rose-500/40 flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
            <div className="text-xs text-rose-200 font-bold">
              ⛔ HARD CONFLICT: {dish.allergen_warnings.join(', ')}
            </div>
          </div>
        )}

        {/* Clinical / Dietary Summary */}
        <p className="text-xs text-slate-300 mb-4 leading-relaxed italic">
          "{dish.summary_reason}"
        </p>

        {/* Tags Grid */}
        <div className="flex flex-wrap gap-1.5 mb-4">
          {(dish.green_flags || []).map((flag, idx) => (
            <span
              key={idx}
              className="px-2.5 py-1 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-[11px] font-semibold flex items-center gap-1"
            >
              <Sparkles className="w-3 h-3 text-emerald-400" /> {flag}
            </span>
          ))}

          {(dish.red_flags || []).map((flag, idx) => (
            <span
              key={idx}
              className="px-2.5 py-1 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-[11px] font-semibold flex items-center gap-1"
            >
              ⚠️ {flag}
            </span>
          ))}
        </div>
      </div>

      {/* Chef Customization Callout */}
      {dish.customization_tips && (
        <div className="p-3 rounded-2xl bg-slate-900/80 border border-slate-800 text-xs text-slate-300 flex items-start gap-2 mt-2">
          <Lightbulb className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-bold text-amber-300">Chef's Customization Advice:</span>{' '}
            {dish.customization_tips}
          </div>
        </div>
      )}
    </div>
  );
}
