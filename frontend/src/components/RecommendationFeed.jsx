import React, { useState } from 'react';
import { Trophy, Search, Download, CheckCircle2, AlertCircle, XCircle, Sparkles, Lightbulb, ShieldAlert, Filter, ArrowUpDown } from 'lucide-react';

export default function RecommendationFeed({ evalResult, evalLoading, onOpenProfile }) {
  const [activeTierFilter, setActiveTierFilter] = useState('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortByScore, setSortByScore] = useState(true);

  if (evalLoading) {
    return (
      <div className="glass-panel rounded-[24px] p-16 text-center border border-slate-800 flex flex-col items-center justify-center">
        <div className="w-10 h-10 rounded-full border-3 border-emerald-500/20 border-t-emerald-400 animate-spin mb-4" />
        <h3 className="text-base font-bold text-white mb-1">Evaluating dishes against personal health matrix...</h3>
        <p className="text-xs text-slate-400">Verifying allergen safety, sodium ceilings, and glycemic index load.</p>
      </div>
    );
  }

  if (!evalResult || !evalResult.all_recommendations || evalResult.all_recommendations.length === 0) {
    return null;
  }

  const counts = evalResult.tier_counts || { GOOD: 0, MEDIUM: 0, BAD: 0 };
  const allRecs = evalResult.all_recommendations || [];

  let filtered = allRecs.filter((item) => {
    if (activeTierFilter !== 'ALL' && item.tier !== activeTierFilter) {
      return false;
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase().trim();
      const matchName = item.dish_name.toLowerCase().includes(q);
      const matchSummary = (item.summary_reason || '').toLowerCase().includes(q);
      const matchFlags = [...(item.green_flags || []), ...(item.red_flags || [])].some((f) =>
        f.toLowerCase().includes(q)
      );
      return matchName || matchSummary || matchFlags;
    }
    return true;
  });

  if (sortByScore) {
    filtered = [...filtered].sort((a, b) => b.fit_score - a.fit_score);
  }

  const downloadJson = () => {
    const blob = new Blob([JSON.stringify(evalResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'nutrimenu_recommendations.json';
    a.click();
  };

  return (
    <div className="space-y-6">
      {/* KPI Counters Bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="glass-panel p-4 rounded-2xl border border-slate-800 text-center">
          <span className="text-2xl font-extrabold text-slate-300 block tabular-nums">{evalResult.total_items_evaluated}</span>
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Total Evaluated</span>
        </div>
        <div className="glass-panel p-4 rounded-2xl border border-emerald-500/20 bg-emerald-950/10 text-center">
          <span className="text-2xl font-extrabold text-emerald-400 block tabular-nums">{counts.GOOD}</span>
          <span className="text-[11px] font-bold text-emerald-400 uppercase tracking-wider">🟢 Tier 1: Good</span>
        </div>
        <div className="glass-panel p-4 rounded-2xl border border-amber-500/20 bg-amber-950/10 text-center">
          <span className="text-2xl font-extrabold text-amber-400 block tabular-nums">{counts.MEDIUM}</span>
          <span className="text-[11px] font-bold text-amber-400 uppercase tracking-wider">🟡 Tier 2: Medium</span>
        </div>
        <div className="glass-panel p-4 rounded-2xl border border-rose-500/20 bg-rose-950/10 text-center">
          <span className="text-2xl font-extrabold text-rose-400 block tabular-nums">{counts.BAD}</span>
          <span className="text-[11px] font-bold text-rose-400 uppercase tracking-wider">🔴 Tier 3: Bad</span>
        </div>
      </div>

      {/* Top Pick Spotlight */}
      {evalResult.top_pick && evalResult.top_pick.tier === 'GOOD' && (
        <div className="p-6 rounded-[24px] bg-gradient-to-r from-emerald-950/40 via-slate-900 to-teal-950/40 border-2 border-emerald-500/60 shadow-glow-green">
          <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-xs uppercase tracking-wider mb-2">
            <Trophy className="w-4 h-4" /> Top Recommendation Spotlight
          </div>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div>
              <h2 className="text-xl sm:text-2xl font-black text-white">{evalResult.top_pick.dish_name}</h2>
              <p className="text-xs sm:text-sm text-slate-300 mt-1 italic max-w-2xl">
                "{evalResult.top_pick.summary_reason}"
              </p>
            </div>
            <div className="shrink-0">
              <span className="px-4 py-1.5 rounded-full bg-emerald-500 text-slate-950 font-black text-xs sm:text-sm shadow-md tabular-nums">
                Fit Score: {evalResult.top_pick.fit_score}/100
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Tier Tabs (Apple Segmented Picker) */}
        <div className="inline-flex p-1 bg-slate-900/80 rounded-xl border border-slate-800">
          {[
            { id: 'ALL', label: `All (${evalResult.total_items_evaluated})` },
            { id: 'GOOD', label: `🟢 Good (${counts.GOOD})` },
            { id: 'MEDIUM', label: `🟡 Medium (${counts.MEDIUM})` },
            { id: 'BAD', label: `🔴 Bad (${counts.BAD})` },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTierFilter(tab.id)}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.96] ${
                activeTierFilter === tab.id
                  ? 'bg-slate-800 text-white shadow-sm'
                  : 'text-slate-400 hover:text-white'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* Search Input */}
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search dishes or tags..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full glass-input rounded-xl pl-9 pr-3 py-1.5 text-xs text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
            />
          </div>

          <button
            onClick={downloadJson}
            title="Download JSON Report"
            className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-400 hover:text-emerald-400 hover:border-emerald-500/30 transition-all active:scale-[0.96]"
          >
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 3-Tier Dish Cards Grid */}
      {filtered.length === 0 ? (
        <div className="glass-panel rounded-2xl p-10 text-center text-slate-500 border border-slate-800">
          <Filter className="w-6 h-6 mx-auto mb-2 opacity-40" />
          <p className="text-xs">No dishes match the selected filter criteria.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filtered.map((dish, idx) => {
            const isGood = dish.tier === 'GOOD';
            const isMedium = dish.tier === 'MEDIUM';
            const isBad = dish.tier === 'BAD';

            const cardStyle = isGood
              ? {
                  border: 'border-emerald-500/30 hover:border-emerald-400/80',
                  bg: 'bg-gradient-to-br from-emerald-950/20 via-slate-900/60 to-slate-900/40',
                  badgeBg: 'bg-emerald-500 text-slate-950',
                  badgeText: 'Tier 1: GOOD',
                  icon: <CheckCircle2 className="w-4 h-4 text-emerald-400 stroke-[2]" />,
                }
              : isMedium
              ? {
                  border: 'border-amber-500/30 hover:border-amber-400/80',
                  bg: 'bg-gradient-to-br from-amber-950/20 via-slate-900/60 to-slate-900/40',
                  badgeBg: 'bg-amber-500 text-slate-950',
                  badgeText: 'Tier 2: MEDIUM',
                  icon: <AlertCircle className="w-4 h-4 text-amber-400 stroke-[2]" />,
                }
              : {
                  border: 'border-rose-500/30 hover:border-rose-400/80',
                  bg: 'bg-gradient-to-br from-rose-950/20 via-slate-900/60 to-slate-900/40',
                  badgeBg: 'bg-rose-500 text-white',
                  badgeText: 'Tier 3: BAD',
                  icon: <XCircle className="w-4 h-4 text-rose-400 stroke-[2]" />,
                };

            return (
              <div
                key={idx}
                className={`rounded-[20px] p-5 border transition-all duration-200 ${cardStyle.border} ${cardStyle.bg} flex flex-col justify-between`}
              >
                <div>
                  {/* Card Header */}
                  <div className="flex items-start justify-between gap-2 mb-2.5">
                    <div className="flex items-center gap-1.5">
                      {cardStyle.icon}
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wider ${cardStyle.badgeBg}`}>
                        {cardStyle.badgeText}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5">
                      {dish.price && (
                        <span className="text-[11px] font-bold px-1.5 py-0.5 rounded-md bg-slate-800 text-slate-300 border border-slate-700 tabular-nums">
                          {dish.price}
                        </span>
                      )}
                      <span
                        className={`text-[11px] font-black px-2 py-0.5 rounded-md tabular-nums ${
                          isGood ? 'bg-emerald-500/20 text-emerald-300' : isMedium ? 'bg-amber-500/20 text-amber-300' : 'bg-rose-500/20 text-rose-300'
                        }`}
                      >
                        {dish.fit_score}/100
                      </span>
                    </div>
                  </div>

                  {/* Title */}
                  <h3 className="text-base font-bold text-white mb-1.5 leading-snug">{dish.dish_name}</h3>

                  {/* Allergy Banner */}
                  {dish.allergen_warnings && dish.allergen_warnings.length > 0 && (
                    <div className="p-2.5 mb-2.5 rounded-xl bg-rose-500/20 border border-rose-500/40 flex items-start gap-1.5">
                      <ShieldAlert className="w-3.5 h-3.5 text-rose-400 shrink-0 mt-0.5" />
                      <div className="text-[11px] text-rose-200 font-bold">
                        ⛔ HARD CONFLICT: {dish.allergen_warnings.join(', ')}
                      </div>
                    </div>
                  )}

                  {/* Summary */}
                  <p className="text-xs text-slate-300 mb-3 leading-relaxed italic">
                    "{dish.summary_reason}"
                  </p>

                  {/* Tags */}
                  <div className="flex flex-wrap gap-1 mb-3">
                    {(dish.green_flags || []).map((flag, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 text-[10px] font-semibold flex items-center gap-1"
                      >
                        <Sparkles className="w-2.5 h-2.5 text-emerald-400" /> {flag}
                      </span>
                    ))}

                    {(dish.red_flags || []).map((flag, i) => (
                      <span
                        key={i}
                        className="px-2 py-0.5 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[10px] font-semibold flex items-center gap-1"
                      >
                        ⚠️ {flag}
                      </span>
                    ))}
                  </div>
                </div>

                {/* Chef Tip */}
                {dish.customization_tips && (
                  <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 text-[11px] text-slate-300 flex items-start gap-1.5 mt-2">
                    <Lightbulb className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold text-amber-300">Customization:</span> {dish.customization_tips}
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
