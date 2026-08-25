import React, { useState } from 'react';
import { Trophy, Search, Download, CheckCircle2, AlertCircle, XCircle, Sparkles, Lightbulb, ShieldAlert, Play, Loader2 } from 'lucide-react';

export default function RecommendationTableSection({
  dishes,
  userMatrix,
  evalResult,
  evalLoading,
  onRunEvaluation,
}) {
  const [activeTab, setActiveTab] = useState('ALL'); // 'ALL' | 'GOOD' | 'MEDIUM' | 'BAD'
  const [searchQuery, setSearchQuery] = useState('');

  const counts = evalResult?.tier_counts || { GOOD: 0, MEDIUM: 0, BAD: 0 };
  const allRecs = evalResult?.all_recommendations || [];

  const filtered = allRecs.filter((item) => {
    if (activeTab !== 'ALL' && item.tier !== activeTab) {
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

  const downloadJson = () => {
    if (!evalResult) return;
    const blob = new Blob([JSON.stringify(evalResult, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'nutrimenu_recommendations.json';
    a.click();
  };

  return (
    <section className="bg-white border border-slate-200/90 rounded-3xl p-6 shadow-sm space-y-6">
      {/* Section Header & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            3. 3-Tier Recommendation Tables & Matchmaker Engine
          </h2>
          <p className="text-xs text-slate-500">
            Evaluates all menu items against your active health matrix and classifies them into Good, Medium, Bad, and Unified tables.
          </p>
        </div>

        {/* Generate Button */}
        <button
          onClick={onRunEvaluation}
          disabled={dishes.length === 0 || evalLoading || !userMatrix}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-2xl font-bold text-xs shadow-sm transition-all active:scale-[0.96] ${
            dishes.length > 0 && userMatrix && !evalLoading
              ? 'bg-emerald-600 hover:bg-emerald-700 text-white cursor-pointer shadow-md'
              : 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
          }`}
        >
          {evalLoading ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" /> Evaluating Dishes...
            </>
          ) : (
            <>
              <Play className="w-4 h-4 fill-current" /> Generate 3-Tier Recommendations
            </>
          )}
        </button>
      </div>

      {evalLoading && (
        <div className="p-12 text-center flex flex-col items-center justify-center bg-slate-50 rounded-2xl border border-slate-200">
          <Loader2 className="w-8 h-8 text-emerald-600 animate-spin mb-3" />
          <h3 className="text-sm font-bold text-slate-900 mb-1">Running 3-Tier Matchmaker Evaluation...</h3>
          <p className="text-xs text-slate-500">Applying allergen hard exclusions, glycemic penalties, and macro scoring.</p>
        </div>
      )}

      {evalResult && !evalLoading && (
        <div className="space-y-5">
          {/* Top Pick Spotlight */}
          {evalResult.top_pick && evalResult.top_pick.tier === 'GOOD' && (
            <div className="p-5 rounded-2xl bg-gradient-to-r from-emerald-50 via-teal-50/40 to-slate-50 border-2 border-emerald-300 shadow-xs flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div>
                <span className="flex items-center gap-1.5 text-emerald-800 font-bold text-[11px] uppercase tracking-wider mb-1">
                  <Trophy className="w-3.5 h-3.5 text-emerald-600" /> Top Recommendation Spotlight
                </span>
                <h3 className="text-lg font-black text-slate-900">{evalResult.top_pick.dish_name}</h3>
                <p className="text-xs text-slate-700 mt-0.5 italic">
                  "{evalResult.top_pick.summary_reason}"
                </p>
              </div>
              <div className="shrink-0">
                <span className="px-3.5 py-1.5 rounded-full bg-emerald-600 text-white font-black text-xs tabular-nums shadow-xs">
                  Fit Score: {evalResult.top_pick.fit_score}/100
                </span>
              </div>
            </div>
          )}

          {/* Table Filters & Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
            {/* Filter Tabs (Segmented Control) */}
            <div className="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200">
              {[
                { id: 'ALL', label: `📊 Unified Combined Table (${evalResult.total_items_evaluated})` },
                { id: 'GOOD', label: `🟢 Tier 1: Good (${counts.GOOD})` },
                { id: 'MEDIUM', label: `🟡 Tier 2: Medium (${counts.MEDIUM})` },
                { id: 'BAD', label: `🔴 Tier 3: Bad (${counts.BAD})` },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all active:scale-[0.96] ${
                    activeTab === tab.id
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Search & Export */}
            <div className="flex items-center gap-2 w-full sm:w-auto">
              <div className="relative w-full sm:w-60">
                <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter by dish or ingredient..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-900 focus:bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500/30"
                />
              </div>

              <button
                onClick={downloadJson}
                title="Download JSON Report"
                className="p-2 rounded-xl bg-white border border-slate-300 text-slate-600 hover:text-emerald-700 hover:border-emerald-400 transition-all active:scale-[0.96] shadow-xs cursor-pointer"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>
          </div>

          {/* Unified Structured Table View */}
          <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
            {filtered.length === 0 ? (
              <div className="p-8 text-center text-slate-400 text-xs">
                No recommendation items match the selected filter.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead className="bg-slate-50 text-slate-600 text-[11px] font-bold uppercase tracking-wider border-b border-slate-200">
                    <tr>
                      <th className="py-3 px-4 w-36">Tier & Fit Score</th>
                      <th className="py-3 px-4 w-52">Dish Name & Price</th>
                      <th className="py-3 px-4">Clinical Assessment / Reason</th>
                      <th className="py-3 px-4 w-60">Nutritional Flags & Allergens</th>
                      <th className="py-3 px-4 w-56">Chef Customization Advice</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 text-slate-700">
                    {filtered.map((item, idx) => {
                      const isGood = item.tier === 'GOOD';
                      const isMedium = item.tier === 'MEDIUM';
                      const isBad = item.tier === 'BAD';

                      const badgeClass = isGood
                        ? 'bg-emerald-100 text-emerald-900 border border-emerald-300'
                        : isMedium
                        ? 'bg-amber-100 text-amber-900 border border-amber-300'
                        : 'bg-rose-100 text-rose-900 border border-rose-300';

                      const rowBg = isGood
                        ? 'hover:bg-emerald-50/40'
                        : isMedium
                        ? 'hover:bg-amber-50/40'
                        : 'hover:bg-rose-50/40';

                      return (
                        <tr key={idx} className={`${rowBg} transition-colors`}>
                          {/* Tier & Score */}
                          <td className="py-3.5 px-4 align-top">
                            <div className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-black uppercase tracking-wider ${badgeClass}`}>
                              {isGood ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 stroke-[2.5]" /> : isMedium ? <AlertCircle className="w-3.5 h-3.5 text-amber-600 stroke-[2.5]" /> : <XCircle className="w-3.5 h-3.5 text-rose-600 stroke-[2.5]" />}
                              <span>{item.tier}</span>
                              <span className="tabular-nums font-mono">({item.fit_score})</span>
                            </div>
                          </td>

                          {/* Dish Name & Price */}
                          <td className="py-3.5 px-4 align-top">
                            <div className="font-bold text-slate-900 text-sm leading-snug">{item.dish_name}</div>
                            {item.price && (
                              <span className="inline-block mt-1 text-[11px] font-bold px-2 py-0.5 rounded-md bg-slate-50 text-emerald-800 border border-slate-200 tabular-nums">
                                {item.price}
                              </span>
                            )}
                          </td>

                          {/* Clinical Reason */}
                          <td className="py-3.5 px-4 align-top text-xs text-slate-700 leading-relaxed italic">
                            "{item.summary_reason}"
                          </td>

                          {/* Flags & Allergens */}
                          <td className="py-3.5 px-4 align-top space-y-1.5">
                            {item.allergen_warnings && item.allergen_warnings.length > 0 && (
                              <div className="px-2 py-1 rounded-md bg-rose-50 text-rose-900 border border-rose-200 text-[11px] font-bold flex items-center gap-1">
                                <ShieldAlert className="w-3 h-3 text-rose-600 shrink-0" />
                                <span>⛔ {item.allergen_warnings.join(', ')}</span>
                              </div>
                            )}

                            <div className="flex flex-wrap gap-1">
                              {(item.green_flags || []).map((flag, i) => (
                                <span
                                  key={i}
                                  className="px-2 py-0.5 rounded-md bg-emerald-50 border border-emerald-200 text-emerald-800 text-[10px] font-semibold flex items-center gap-0.5"
                                >
                                  <Sparkles className="w-2.5 h-2.5 text-emerald-600" /> {flag}
                                </span>
                              ))}
                              {(item.red_flags || []).map((flag, i) => (
                                <span
                                  key={i}
                                  className="px-2 py-0.5 rounded-md bg-rose-50 border border-rose-200 text-rose-800 text-[10px] font-semibold"
                                >
                                  ⚠️ {flag}
                                </span>
                              ))}
                            </div>
                          </td>

                          {/* Customization Tip */}
                          <td className="py-3.5 px-4 align-top text-[11px] text-slate-700">
                            {item.customization_tips ? (
                              <div className="p-2 rounded-lg bg-amber-50/80 border border-amber-200 text-slate-800 flex items-start gap-1">
                                <Lightbulb className="w-3 h-3 text-amber-600 shrink-0 mt-0.5" />
                                <div>
                                  <span className="font-bold text-amber-800">Tip:</span> {item.customization_tips}
                                </div>
                              </div>
                            ) : (
                              <span className="text-slate-400">-</span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}
