import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertCircle,
  XCircle,
  Sparkles,
  Lightbulb,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { sanitizeDishFlags } from '../utils/flagUtils';

export default function DishCard({ dish }) {
  const [isExpanded, setIsExpanded] = useState(false);

  const isGood = dish.tier === 'GOOD';
  const isMedium = dish.tier === 'MEDIUM';

  const tierStyles = isGood
    ? {
        border: 'border-emerald-500/30 hover:border-emerald-400/60',
        bg: 'bg-slate-900/70',
        badgeBg: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
        dot: 'bg-emerald-400',
        tierLabel: 'Tier 1: GOOD',
        icon: <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />,
      }
    : isMedium
    ? {
        border: 'border-amber-500/30 hover:border-amber-400/60',
        bg: 'bg-slate-900/70',
        badgeBg: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
        dot: 'bg-amber-400',
        tierLabel: 'Tier 2: MEDIUM',
        icon: <AlertCircle className="w-4 h-4 text-amber-400 shrink-0" />,
      }
    : {
        border: 'border-rose-500/30 hover:border-rose-400/60',
        bg: 'bg-slate-900/70',
        badgeBg: 'bg-rose-500/10 text-rose-400 border-rose-500/30',
        dot: 'bg-rose-400',
        tierLabel: 'Tier 3: BAD',
        icon: <XCircle className="w-4 h-4 text-rose-400 shrink-0" />,
      };

  const { allergenWarnings, greenFlags, redFlags } = sanitizeDishFlags(dish);
  const topGreenFlags = greenFlags.slice(0, isGood ? 2 : 1);
  const topRedFlags = redFlags.slice(0, isGood ? 1 : 2);
  const hasMoreDetails =
    dish.customization_tips ||
    greenFlags.length > topGreenFlags.length ||
    redFlags.length > topRedFlags.length ||
    dish.estimated_calories;

  return (
    <div
      className={`rounded-2xl p-4 sm:p-5 border transition-all duration-200 ${tierStyles.border} ${tierStyles.bg} backdrop-blur-md flex flex-col justify-between gap-3 shadow-sm hover:shadow-md`}
    >
      <div className="space-y-2.5">
        {/* Top Header: Title, Tier & Fit Score */}
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h3
              className="text-base font-bold text-white leading-snug truncate"
              title={dish.dish_name}
            >
              {dish.dish_name}
            </h3>
            {dish.price && (
              <span className="text-[11px] font-medium text-slate-400 mt-0.5 inline-block">
                {dish.price}
              </span>
            )}
          </div>

          <div className="flex items-center gap-1.5 shrink-0">
            <div
              className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border text-xs font-bold ${tierStyles.badgeBg}`}
            >
              <span className={`w-1.5 h-1.5 rounded-full ${tierStyles.dot}`} />
              <span className="tabular-nums font-mono">{dish.fit_score}</span>
              <span className="text-[10px] opacity-70">/100</span>
            </div>
          </div>
        </div>

        {/* Hard Exclusion Banner */}
        {allergenWarnings.length > 0 && (
          <div className="px-2.5 py-1.5 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center gap-2">
            <ShieldAlert className="w-3.5 h-3.5 text-rose-400 shrink-0" />
            <div className="text-[11px] text-rose-300 font-semibold truncate">
              {allergenWarnings.join(' • ')}
            </div>
          </div>
        )}

        {/* Concise Clinical Assessment */}
        <p className="text-xs text-slate-300 leading-relaxed line-clamp-2" title={dish.summary_reason}>
          {dish.summary_reason}
        </p>

        {/* Compact Key Tags (Max 2 for clean scanning) */}
        {(topGreenFlags.length > 0 || topRedFlags.length > 0) && (
          <div className="flex flex-wrap gap-1.5 pt-0.5">
            {topGreenFlags.map((flag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[11px] font-medium"
                title={flag}
              >
                <Sparkles className="w-2.5 h-2.5 text-emerald-400 shrink-0" />
                <span className="truncate max-w-[130px]">{flag}</span>
              </span>
            ))}

            {topRedFlags.map((flag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[11px] font-medium"
                title={flag}
              >
                <span className="text-[9px] text-rose-400 shrink-0">⚠️</span>
                <span className="truncate max-w-[130px]">{flag}</span>
              </span>
            ))}
          </div>
        )}

        {/* Expandable Chef Tip & Deep Details */}
        {hasMoreDetails && (
          <div className="pt-1 border-t border-slate-800/80">
            <button
              type="button"
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-[11px] font-bold text-slate-400 hover:text-emerald-400 flex items-center gap-1 transition-colors py-0.5 cursor-pointer"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-3 h-3" /> Hide Chef Tip & Breakdown
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3" /> View Chef Tip & Breakdown
                </>
              )}
            </button>

            {isExpanded && (
              <div className="mt-2 space-y-2 pt-1 text-xs animate-in fade-in duration-150">
                {dish.customization_tips && (
                  <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-200 text-[11px] flex items-start gap-1.5 leading-relaxed">
                    <Lightbulb className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-amber-300">Chef's Advice:</span>{' '}
                      {dish.customization_tips}
                    </div>
                  </div>
                )}

                {dish.estimated_calories != null && (
                  <div className="flex items-center gap-2 p-1.5 rounded-lg bg-slate-800/60 border border-slate-700/50 text-[10px] text-slate-300 font-medium">
                    <span>🔥 <b>{dish.estimated_calories}</b> kcal</span>
                    <span>•</span>
                    <span>P: <b>{dish.estimated_protein_g ?? '-'}g</b></span>
                    <span>•</span>
                    <span>C: <b>{dish.estimated_carbs_g ?? '-'}g</b></span>
                    <span>•</span>
                    <span>F: <b>{dish.estimated_fat_g ?? '-'}g</b></span>
                  </div>
                )}

                {/* Remaining Tags */}
                {(greenFlags.length > topGreenFlags.length || redFlags.length > topRedFlags.length) && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {greenFlags.slice(topGreenFlags.length).map((flag, idx) => (
                      <span key={`g-${idx}`} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-emerald-500/10 text-emerald-400 text-[10px] font-medium">
                        <Sparkles className="w-2.5 h-2.5 text-emerald-400 shrink-0" /> {flag}
                      </span>
                    ))}
                    {redFlags.slice(topRedFlags.length).map((flag, idx) => (
                      <span key={`r-${idx}`} className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-rose-500/10 text-rose-400 text-[10px] font-medium">
                        <span className="text-rose-500 text-[9px] shrink-0">⚠️</span> {flag}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
