import React, { useState, useEffect } from 'react';
import { Sparkles, Trophy, Download, Search, RefreshCw, ArrowLeft, Filter } from 'lucide-react';
import DishCard from './DishCard';
import { evaluateRecommendations } from '../api';

export default function Step3Recommendations({
  userMatrix,
  dishes,
  onBackToMatrix,
  onRestart,
}) {
  const [loading, setLoading] = useState(false);
  const [evalResult, setEvalResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeTierFilter, setActiveTierFilter] = useState('ALL'); // 'ALL' | 'GOOD' | 'MEDIUM' | 'BAD'
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    const runEvaluation = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await evaluateRecommendations(userMatrix, dishes);
        setEvalResult(data.result);
      } catch (err) {
        setError(err.message || 'Failed to evaluate recommendations.');
      } finally {
        setLoading(false);
      }
    };

    if (userMatrix && dishes.length > 0) {
      runEvaluation();
    }
  }, [userMatrix, dishes]);

  const counts = evalResult?.tier_counts || { GOOD: 0, MEDIUM: 0, BAD: 0 };
  const allRecs = evalResult?.all_recommendations || [];

  const filteredDishes = allRecs.filter((item) => {
    // Tier filter
    if (activeTierFilter !== 'ALL' && item.tier !== activeTierFilter) {
      return false;
    }
    // Search filter
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
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="text-center mb-8">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold mb-3">
          <Sparkles className="w-3.5 h-3.5" /> Model 3: Personalized 3-Tier Matchmaker
        </div>
        <h1 className="text-3xl sm:text-4xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-blue-400">
          3-Tier Nutritional Recommendations
        </h1>
        <p className="text-slate-400 text-sm sm:text-base mt-2 max-w-xl mx-auto">
          Every menu item analyzed against your personal health matrix and classified into 🟢 Good, 🟡 Medium, and 🔴 Bad tiers.
        </p>
      </div>

      {loading ? (
        <div className="glass-panel rounded-3xl p-16 text-center border border-slate-800 flex flex-col items-center justify-center">
          <div className="w-12 h-12 rounded-full border-4 border-emerald-500/20 border-t-emerald-400 animate-spin mb-4" />
          <h3 className="text-lg font-bold text-white mb-1">Evaluating menu against clinical matrix...</h3>
          <p className="text-xs text-slate-400">Testing allergies, sodium ceilings, and glycemic index load.</p>
        </div>
      ) : error ? (
        <div className="p-6 rounded-3xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-center">
          <h4 className="font-bold mb-2">Evaluation Error</h4>
          <p className="text-sm">{error}</p>
        </div>
      ) : (
        <>
          {/* KPI Stats Bar */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            <div className="glass-panel p-5 rounded-3xl border border-slate-800 text-center">
              <span className="text-2xl sm:text-3xl font-extrabold text-slate-300 block mb-0.5">
                {evalResult?.total_items_evaluated || 0}
              </span>
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Total Evaluated
              </span>
            </div>

            <div className="glass-panel p-5 rounded-3xl border border-emerald-500/20 text-center bg-emerald-950/10">
              <span className="text-2xl sm:text-3xl font-extrabold text-emerald-400 block mb-0.5">
                {counts.GOOD}
              </span>
              <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider">
                🟢 Tier 1: Good
              </span>
            </div>

            <div className="glass-panel p-5 rounded-3xl border border-amber-500/20 text-center bg-amber-950/10">
              <span className="text-2xl sm:text-3xl font-extrabold text-amber-400 block mb-0.5">
                {counts.MEDIUM}
              </span>
              <span className="text-xs font-bold text-amber-400 uppercase tracking-wider">
                🟡 Tier 2: Medium
              </span>
            </div>

            <div className="glass-panel p-5 rounded-3xl border border-rose-500/20 text-center bg-rose-950/10">
              <span className="text-2xl sm:text-3xl font-extrabold text-rose-400 block mb-0.5">
                {counts.BAD}
              </span>
              <span className="text-xs font-bold text-rose-400 uppercase tracking-wider">
                🔴 Tier 3: Bad
              </span>
            </div>
          </div>

          {/* Top Pick Spotlight */}
          {evalResult?.top_pick && evalResult.top_pick.tier === 'GOOD' && (
            <div className="mb-8 p-6 sm:p-8 rounded-3xl bg-gradient-to-r from-emerald-950/40 via-slate-900 to-teal-950/40 border-2 border-emerald-500/60 shadow-glow-green">
              <div className="flex items-center gap-2 text-emerald-400 font-bold text-xs uppercase tracking-wider mb-2">
                <Trophy className="w-4 h-4" /> Top Recommendation Spotlight
              </div>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-2xl font-black text-white">{evalResult.top_pick.dish_name}</h2>
                  <p className="text-sm text-slate-300 mt-1 italic max-w-2xl">
                    "{evalResult.top_pick.summary_reason}"
                  </p>
                </div>
                <div className="text-right shrink-0">
                  <span className="px-4 py-1.5 rounded-full bg-emerald-500 text-slate-950 font-black text-sm shadow-lg">
                    Fit Score: {evalResult.top_pick.fit_score}/100
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Search & Filter Controls */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4 mb-6">
            {/* Filter Tabs */}
            <div className="flex flex-wrap gap-1.5 glass-panel p-1.5 rounded-2xl border border-slate-800">
              {[
                { id: 'ALL', label: `All (${evalResult?.total_items_evaluated || 0})` },
                { id: 'GOOD', label: `🟢 Good (${counts.GOOD})` },
                { id: 'MEDIUM', label: `🟡 Medium (${counts.MEDIUM})` },
                { id: 'BAD', label: `🔴 Bad (${counts.BAD})` },
              ].map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTierFilter(tab.id)}
                  className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
                    activeTierFilter === tab.id
                      ? 'bg-slate-800 text-white shadow-md'
                      : 'text-slate-400 hover:text-white'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Search Input */}
            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search dishes or tags..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full glass-input rounded-2xl pl-10 pr-4 py-2 text-xs text-white focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
              />
            </div>
          </div>

          {/* Dishes Card Grid */}
          {filteredDishes.length === 0 ? (
            <div className="glass-panel rounded-3xl p-12 text-center text-slate-500 border border-slate-800">
              <Filter className="w-8 h-8 mx-auto mb-2 opacity-40" />
              <p className="text-xs">No dishes match the selected filter criteria.</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {filteredDishes.map((dish, idx) => (
                <DishCard key={idx} dish={dish} />
              ))}
            </div>
          )}

          {/* Export & Actions Footer */}
          <div className="mt-12 pt-6 border-t border-slate-800/80 flex flex-wrap justify-between items-center gap-4">
            <div className="flex gap-3">
              <button
                onClick={onBackToMatrix}
                className="flex items-center gap-2 px-5 py-2.5 rounded-2xl font-bold text-xs bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition-all cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4" /> Edit Health Matrix
              </button>
              <button
                onClick={onRestart}
                className="flex items-center gap-2 px-5 py-2.5 rounded-2xl font-bold text-xs bg-slate-900 border border-slate-800 text-slate-300 hover:text-white hover:border-slate-700 transition-all cursor-pointer"
              >
                <RefreshCw className="w-3.5 h-3.5" /> Scan New Menu
              </button>
            </div>

            <button
              onClick={downloadJson}
              className="flex items-center gap-2 px-6 py-2.5 rounded-2xl font-bold text-xs bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 hover:bg-emerald-500 hover:text-slate-950 transition-all cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" /> Export Data (.json)
            </button>
          </div>
        </>
      )}
    </div>
  );
}
