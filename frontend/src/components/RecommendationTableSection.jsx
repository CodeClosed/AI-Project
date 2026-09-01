import React, { useState, useRef, useEffect } from 'react';
import {
  Trophy,
  Search,
  Download,
  CheckCircle2,
  AlertCircle,
  XCircle,
  Sparkles,
  Lightbulb,
  ShieldAlert,
  Play,
  Loader2,
  ChevronDown,
  ChevronUp,
  FileSpreadsheet,
  FileText,
  FileCode,
  Printer,
  File,
  Layers,
  Table,
  Activity,
  Heart,
  Flame,
  ShieldCheck,
  Zap,
  Info,
  Utensils,
  Plus,
  Check,
} from 'lucide-react';

export default function RecommendationTableSection({
  dishes,
  userMatrix,
  userProfile,
  evalResult,
  evalLoading,
  onRunEvaluation,
  plate = [],
  onAddToPlate,
  onOpenPlateDrawer,
}) {
  const [viewMode, setViewMode] = useState('STACKED'); // 'STACKED' | 'TABLE'
  const [activeTab, setActiveTab] = useState('ALL'); // 'ALL' | 'GOOD' | 'MEDIUM' | 'BAD'
  const [searchQuery, setSearchQuery] = useState('');
  const [isDownloadMenuOpen, setIsDownloadMenuOpen] = useState(false);
  const [isMatrixExpanded, setIsMatrixExpanded] = useState(true);
  const dropdownRef = useRef(null);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDownloadMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const counts = evalResult?.tier_counts || {
    GOOD: (evalResult?.good_items || []).length,
    MEDIUM: (evalResult?.medium_items || []).length,
    BAD: (evalResult?.bad_items || []).length,
  };
  
  const allRecs = evalResult?.all_recommendations || [
    ...(evalResult?.good_items || []),
    ...(evalResult?.medium_items || []),
    ...(evalResult?.bad_items || []),
  ];

  const goodRecs = evalResult?.good_items || allRecs.filter(r => r.tier === 'GOOD');
  const mediumRecs = evalResult?.medium_items || allRecs.filter(r => r.tier === 'MEDIUM');
  const badRecs = evalResult?.bad_items || allRecs.filter(r => r.tier === 'BAD');

  const filterList = (list) => {
    if (!searchQuery.trim()) return list;
    const q = searchQuery.toLowerCase().trim();
    return list.filter((item) => {
      const matchName = (item.dish_name || '').toLowerCase().includes(q);
      const matchSummary = (item.summary_reason || '').toLowerCase().includes(q);
      const matchFlags = [...(item.green_flags || []), ...(item.red_flags || [])].some((f) =>
        f.toLowerCase().includes(q)
      );
      const matchTips = (item.customization_tips || '').toLowerCase().includes(q);
      return matchName || matchSummary || matchFlags || matchTips;
    });
  };

  const filteredAll = filterList(
    activeTab === 'ALL'
      ? allRecs
      : allRecs.filter((item) => item.tier === activeTab)
  );

  const filteredGood = filterList(goodRecs);
  const filteredMedium = filterList(mediumRecs);
  const filteredBad = filterList(badRecs);

  const triggerDownload = (content, filename, mimeType) => {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    setIsDownloadMenuOpen(false);
  };

  // 1. JSON Export
  const exportJSON = () => {
    if (!evalResult) return;
    const jsonStr = JSON.stringify(
      {
        exported_at: new Date().toISOString(),
        referenced_matrix: userMatrix,
        metadata: evalResult.metadata || {},
        tier_counts: counts,
        top_pick: evalResult.top_pick,
        recommendations: allRecs,
      },
      null,
      2
    );
    triggerDownload(jsonStr, 'nutrimenu_3tier_recommendations.json', 'application/json');
  };

  // 2. CSV Export
  const exportCSV = () => {
    if (!evalResult) return;
    const headers = [
      'Tier',
      'Fit Score',
      'Dish Name',
      'Price',
      'Clinical Assessment',
      'Green Flags',
      'Red Flags',
      'Allergen Warnings',
      'Chef Customization Tips',
    ];

    const escapeCsv = (val) => {
      const str = String(val || '').replace(/"/g, '""');
      return `"${str}"`;
    };

    const rows = allRecs.map((r) => [
      escapeCsv(r.tier),
      escapeCsv(r.fit_score),
      escapeCsv(r.dish_name),
      escapeCsv(r.price || ''),
      escapeCsv(r.summary_reason),
      escapeCsv((r.green_flags || []).join('; ')),
      escapeCsv((r.red_flags || []).join('; ')),
      escapeCsv((r.allergen_warnings || []).join('; ')),
      escapeCsv(r.customization_tips || ''),
    ]);

    const csvContent = [headers.map(escapeCsv).join(','), ...rows.map((r) => r.join(','))].join('\r\n');
    triggerDownload(csvContent, 'nutrimenu_3tier_recommendations.csv', 'text/csv;charset=utf-8;');
  };

  // 3. Markdown Report Export
  const exportMarkdown = () => {
    if (!evalResult) return;
    const dateStr = new Date().toLocaleDateString();
    let md = `# 🥗 NutriMenu AI — Clinical 3-Tier Recommendation Report\n\n`;
    md += `**Generated Date**: ${dateStr}\n`;
    md += `**User Context**: ${userMatrix?.user_summary || 'Custom Health Profile'}\n`;
    md += `**Total Dishes Evaluated**: ${allRecs.length}\n\n`;
    md += `### 📊 Tier Summary\n`;
    md += `- 🟢 **Tier 1 (GOOD)**: ${counts.GOOD} items\n`;
    md += `- 🟡 **Tier 2 (MEDIUM)**: ${counts.MEDIUM} items\n`;
    md += `- 🔴 **Tier 3 (BAD)**: ${counts.BAD} items\n\n`;

    if (evalResult.top_pick) {
      md += `### 🏆 Top Pick Spotlight\n`;
      md += `**${evalResult.top_pick.dish_name}** (Fit Score: ${evalResult.top_pick.fit_score}/100)\n`;
      md += `_${evalResult.top_pick.summary_reason}_\n\n`;
    }

    md += `## 📋 3-Tier Classification Table\n\n`;
    md += `| Tier | Score | Dish Name | Price | Clinical Assessment | Nutritional Flags | Chef Tip |\n`;
    md += `| :--- | :---: | :--- | :---: | :--- | :--- | :--- |\n`;

    allRecs.forEach((r) => {
      const tierBadge = r.tier === 'GOOD' ? '🟢 GOOD' : r.tier === 'MEDIUM' ? '🟡 MEDIUM' : '🔴 BAD';
      const flags = [
        ...(r.allergen_warnings || []).map((a) => `⛔ ALLERGY: ${a}`),
        ...(r.green_flags || []).map((g) => `🌿 ${g}`),
        ...(r.red_flags || []).map((rf) => `⚠️ ${rf}`),
      ].join('<br/>');

      md += `| ${tierBadge} | ${r.fit_score}/100 | **${r.dish_name}** | ${r.price || '-'} | ${r.summary_reason} | ${flags || '-'} | ${r.customization_tips || '-'} |\n`;
    });

    md += `\n---\n*Disclaimer: NutriMenu AI recommendations are computational estimates based on personal biometric inputs and health matrices. Not medical advice.*`;

    triggerDownload(md, 'nutrimenu_3tier_recommendations.md', 'text/markdown');
  };

  // 4. HTML Printable Report Export
  const exportHTML = () => {
    if (!evalResult) return;
    const dateStr = new Date().toLocaleDateString();

    const rowsHtml = allRecs
      .map((r) => {
        const isGood = r.tier === 'GOOD';
        const isMedium = r.tier === 'MEDIUM';
        const tierColor = isGood ? '#059669' : isMedium ? '#D97706' : '#E11D48';
        const tierBg = isGood ? '#ECFDF5' : isMedium ? '#FFFBEB' : '#FFF1F2';

        return `
        <tr style="border-bottom: 1px solid #E2E8F0;">
          <td style="padding: 12px; vertical-align: top;">
            <span style="display:inline-block; padding: 4px 8px; border-radius: 6px; font-weight: bold; font-size: 11px; background:${tierBg}; color:${tierColor};">
              ${r.tier} (${r.fit_score}/100)
            </span>
          </td>
          <td style="padding: 12px; vertical-align: top;">
            <strong style="font-size: 13px; color: #0F172A;">${r.dish_name}</strong>
            ${r.price ? `<div style="font-size: 11px; color: #059669; font-weight: bold; margin-top: 2px;">${r.price}</div>` : ''}
          </td>
          <td style="padding: 12px; vertical-align: top; font-size: 12px; color: #334155; font-style: italic;">
            "${r.summary_reason}"
          </td>
          <td style="padding: 12px; vertical-align: top; font-size: 11px;">
            ${(r.allergen_warnings || []).map((a) => `<div style="color: #BE123C; font-weight: bold; margin-bottom: 3px;">⛔ ${a}</div>`).join('')}
            ${(r.green_flags || []).map((g) => `<div style="color: #047857; margin-bottom: 2px;">🌿 ${g}</div>`).join('')}
            ${(r.red_flags || []).map((rf) => `<div style="color: #B45309; margin-bottom: 2px;">⚠️ ${rf}</div>`).join('')}
          </td>
          <td style="padding: 12px; vertical-align: top; font-size: 11px; color: #475569;">
            ${r.customization_tips ? `<div style="background: #FEF3C7; padding: 6px; border-radius: 6px; color: #92400E;">💡 ${r.customization_tips}</div>` : '-'}
          </td>
        </tr>`;
      })
      .join('');

    const htmlContent = `<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>NutriMenu AI — Clinical 3-Tier Recommendation Report</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background: #FFFFFF; color: #0F172A; margin: 40px; line-height: 1.5; }
    h1 { font-size: 24px; color: #0F172A; margin-bottom: 4px; }
    .meta { font-size: 12px; color: #64748B; margin-bottom: 24px; }
    .summary { display: flex; gap: 12px; margin-bottom: 24px; }
    .card { flex: 1; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0; text-align: center; }
    table { width: 100%; border-collapse: collapse; text-align: left; margin-top: 16px; font-size: 12px; }
    th { background: #F8FAFC; padding: 10px 12px; font-size: 11px; text-transform: uppercase; color: #64748B; border-bottom: 2px solid #CBD5E1; }
    @media print { body { margin: 10px; } .no-print { display: none; } }
  </style>
</head>
<body>
  <h1>🥗 NutriMenu AI — Clinical 3-Tier Recommendation Report</h1>
  <div class="meta">Generated: ${dateStr} • Total Items Evaluated: ${allRecs.length} • Context: ${userMatrix?.user_summary || ''}</div>
  
  <div class="summary">
    <div class="card" style="background:#ECFDF5; border-color:#A7F3D0;"><div style="font-size:20px; font-weight:bold; color:#059669;">${counts.GOOD}</div><div style="font-size:11px; color:#047857;">🟢 Tier 1: Good</div></div>
    <div class="card" style="background:#FFFBEB; border-color:#FDE68A;"><div style="font-size:20px; font-weight:bold; color:#D97706;">${counts.MEDIUM}</div><div style="font-size:11px; color:#B45309;">🟡 Tier 2: Medium</div></div>
    <div class="card" style="background:#FFF1F2; border-color:#FECDD3;"><div style="font-size:20px; font-weight:bold; color:#E11D48;">${counts.BAD}</div><div style="font-size:11px; color:#BE123C;">🔴 Tier 3: Bad</div></div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width: 140px;">Tier & Score</th>
        <th style="width: 200px;">Dish Name & Price</th>
        <th>Clinical Assessment</th>
        <th style="width: 200px;">Flags & Allergens</th>
        <th style="width: 180px;">Chef Advice</th>
      </tr>
    </thead>
    <tbody>
      ${rowsHtml}
    </tbody>
  </table>

  <div style="margin-top: 40px; font-size: 10px; color: #94A3B8; text-align: center;">
    NutriMenu AI • Computational Clinical Nutrition Engine
  </div>
</body>
</html>`;

    triggerDownload(htmlContent, 'nutrimenu_3tier_recommendations.html', 'text/html');
  };

  // 5. Plain Text Summary Export
  const exportText = () => {
    if (!evalResult) return;
    const dateStr = new Date().toLocaleDateString();
    let txt = `====================================================\n`;
    txt += `  NUTRIMENU AI - 3-TIER FOOD RECOMMENDATIONS REPORT\n`;
    txt += `  Generated: ${dateStr}\n`;
    txt += `  Context: ${userMatrix?.user_summary || ''}\n`;
    txt += `====================================================\n\n`;
    txt += `Summary Counts:\n`;
    txt += `  - 🟢 Tier 1 (GOOD):   ${counts.GOOD}\n`;
    txt += `  - 🟡 Tier 2 (MEDIUM): ${counts.MEDIUM}\n`;
    txt += `  - 🔴 Tier 3 (BAD):    ${counts.BAD}\n\n`;

    allRecs.forEach((r, idx) => {
      txt += `[${r.tier}] ${idx + 1}. ${r.dish_name} (${r.fit_score}/100) ${r.price || ''}\n`;
      txt += `   Clinical Assessment: "${r.summary_reason}"\n`;
      if (r.allergen_warnings?.length) txt += `   ⛔ Allergen Warning: ${r.allergen_warnings.join(', ')}\n`;
      if (r.green_flags?.length) txt += `   🌿 Green Flags: ${r.green_flags.join(', ')}\n`;
      if (r.red_flags?.length) txt += `   ⚠️ Red Flags: ${r.red_flags.join(', ')}\n`;
      if (r.customization_tips) txt += `   💡 Chef Tip: ${r.customization_tips}\n`;
      txt += `\n`;
    });

    triggerDownload(txt, 'nutrimenu_3tier_recommendations.txt', 'text/plain');
  };

  // Render Card Item
  const renderDishItem = (item, idx) => {
    const isGood = item.tier === 'GOOD';
    const isMedium = item.tier === 'MEDIUM';

    const badgeClass = isGood
      ? 'bg-emerald-100 text-emerald-900 border border-emerald-300'
      : isMedium
      ? 'bg-amber-100 text-amber-900 border border-amber-300'
      : 'bg-rose-100 text-rose-900 border border-rose-300';

    const borderClass = isGood
      ? 'border-emerald-200 hover:border-emerald-400 bg-white'
      : isMedium
      ? 'border-amber-200 hover:border-amber-400 bg-white'
      : 'border-rose-200 hover:border-rose-400 bg-white';

    return (
      <div
        key={idx}
        className={`p-4 rounded-2xl border ${borderClass} shadow-xs transition-all hover:shadow-md flex flex-col justify-between gap-3`}
      >
        <div className="space-y-2">
          {/* Header row: Name, price, and score badge */}
          <div className="flex items-start justify-between gap-2">
            <div>
              <div className="font-bold text-slate-900 text-sm leading-snug">{item.dish_name}</div>
              {item.price && (
                <span className="inline-block mt-0.5 text-[11px] font-bold px-2 py-0.5 rounded-md bg-slate-50 text-emerald-800 border border-slate-200 tabular-nums">
                  {item.price}
                </span>
              )}
            </div>
            <div className={`shrink-0 inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-black uppercase tracking-wider ${badgeClass}`}>
              {isGood ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 stroke-[2.5]" />
              ) : isMedium ? (
                <AlertCircle className="w-3.5 h-3.5 text-amber-600 stroke-[2.5]" />
              ) : (
                <XCircle className="w-3.5 h-3.5 text-rose-600 stroke-[2.5]" />
              )}
              <span className="tabular-nums font-mono">{item.fit_score}/100</span>
            </div>
          </div>

          {/* Clinical Assessment Reason */}
          <p className="text-xs text-slate-700 leading-relaxed italic bg-slate-50/80 p-2.5 rounded-xl border border-slate-100">
            "{item.summary_reason}"
          </p>

          {/* Allergen & Dietary Warnings */}
          {item.allergen_warnings && item.allergen_warnings.length > 0 && (
            <div className="px-2.5 py-1.5 rounded-lg bg-rose-50 text-rose-900 border border-rose-200 text-[11px] font-bold flex items-center gap-1.5">
              <ShieldAlert className="w-3.5 h-3.5 text-rose-600 shrink-0" />
              <span>⛔ {item.allergen_warnings.join(', ')}</span>
            </div>
          )}

          {/* Green & Red Flags */}
          <div className="flex flex-wrap gap-1 pt-1">
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
        </div>

        {/* Customization Tip */}
        {item.customization_tips && (
          <div className="pt-2 border-t border-slate-100 text-[11px] text-slate-700">
            <div className="p-2 rounded-xl bg-amber-50/90 border border-amber-200 text-slate-800 flex items-start gap-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-amber-600 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold text-amber-900">Chef's Advice:</span> {item.customization_tips}
              </div>
            </div>
          </div>
        )}

        {/* Add to Plate Action Button */}
        {onAddToPlate && (
          <div className="pt-2 border-t border-slate-100">
            {(() => {
              const plateItem = plate.find((p) => p.name.toLowerCase() === item.dish_name.toLowerCase());
              return plateItem ? (
                <button
                  onClick={() => onAddToPlate({ name: item.dish_name, price: item.price })}
                  className="w-full py-2 px-3 rounded-xl bg-emerald-50 text-emerald-800 border border-emerald-300 hover:bg-emerald-100 text-xs font-bold flex items-center justify-center gap-1.5 transition cursor-pointer shadow-2xs"
                >
                  <Check className="w-3.5 h-3.5 stroke-[2.5]" />
                  <span>On Plate ({plateItem.portion || 1}x) • Add +1</span>
                </button>
              ) : (
                <button
                  onClick={() => onAddToPlate({ name: item.dish_name, price: item.price })}
                  className="w-full py-2 px-3 rounded-xl bg-slate-100 hover:bg-emerald-600 hover:text-white text-slate-700 text-xs font-bold flex items-center justify-center gap-1.5 transition active:scale-[0.98] cursor-pointer"
                >
                  <Plus className="w-3.5 h-3.5" />
                  <span>Add to Plate</span>
                </button>
              );
            })()}
          </div>
        )}
      </div>
    );
  };

  const metabolic = userMatrix?.metabolic_targets;
  const guardrails = userMatrix?.nutritional_guardrails;
  const risks = userMatrix?.clinical_risk_weights;

  return (
    <section className="bg-white border border-slate-200/90 rounded-3xl p-6 shadow-sm space-y-6">
      {/* Section Header & Action Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 flex items-center gap-2">
            <Layers className="w-5 h-5 text-emerald-600" /> 3-Tier Food Recommendation System
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Evaluates all available menu items against your active metabolic health matrix and classifies them into stacked Good, Medium, and Bad tiers.
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

      {/* Referenced Health Matrix Card */}
      {userMatrix && (
        <div className="bg-slate-50/90 border border-slate-200 rounded-2xl p-4 transition-all">
          <div className="flex items-center justify-between cursor-pointer" onClick={() => setIsMatrixExpanded(!isMatrixExpanded)}>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold">
                <Activity className="w-4 h-4 text-emerald-600" />
              </div>
              <div>
                <span className="text-xs font-black text-slate-900 uppercase tracking-wider block">
                  Referenced Health Matrix & Personal Constraints
                </span>
                <span className="text-[11px] text-slate-500 font-medium">
                  {userMatrix.user_summary || 'Active user biometric and clinical profile'}
                </span>
              </div>
            </div>
            <button className="text-slate-400 hover:text-slate-600 p-1">
              {isMatrixExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
            </button>
          </div>

          {isMatrixExpanded && (
            <div className="mt-4 pt-3 border-t border-slate-200/80 grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
              {/* Target Calories */}
              <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs">
                <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-bold uppercase tracking-wider mb-1">
                  <Flame className="w-3.5 h-3.5 text-amber-500" /> Caloric Target
                </div>
                <div className="text-base font-black text-slate-900">
                  {metabolic ? `${Math.round(metabolic.target_calories_kcal)} kcal` : '2,000 kcal'}
                </div>
                <div className="text-[10px] text-slate-400 font-medium mt-0.5">
                  BMR: {metabolic?.bmr_kcal ? Math.round(metabolic.bmr_kcal) : '-'} • TDEE: {metabolic?.tdee_kcal ? Math.round(metabolic.tdee_kcal) : '-'}
                </div>
              </div>

              {/* Target Protein & Macros */}
              <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs">
                <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-bold uppercase tracking-wider mb-1">
                  <Zap className="w-3.5 h-3.5 text-emerald-500" /> Target Protein
                </div>
                <div className="text-base font-black text-slate-900">
                  {metabolic ? `${Math.round(metabolic.target_protein_g)}g` : '120g'}
                  <span className="text-xs font-normal text-slate-500 ml-1">({metabolic ? Math.round(metabolic.target_protein_pct) : '25'}%)</span>
                </div>
                <div className="text-[10px] text-slate-400 font-medium mt-0.5">
                  Carbs: {metabolic?.target_carbs_g ? Math.round(metabolic.target_carbs_g) : '-'}g • Fat: {metabolic?.target_fats_g ? Math.round(metabolic.target_fats_g) : '-'}g
                </div>
              </div>

              {/* Clinical Guardrails */}
              <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs">
                <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-bold uppercase tracking-wider mb-1">
                  <Heart className="w-3.5 h-3.5 text-rose-500" /> Clinical Limits
                </div>
                <div className="text-xs font-black text-slate-800">
                  Sodium: &lt; {guardrails?.sodium_ceiling_mg || 2300} mg
                </div>
                <div className="text-[10px] text-slate-500 font-medium mt-0.5">
                  Glycemic Sens: {risks?.glycemic_sensitivity ? (risks.glycemic_sensitivity > 0.6 ? 'High (Strict)' : 'Moderate') : 'Normal'}
                </div>
              </div>

              {/* Active Exclusions & Allergies */}
              <div className="p-3 bg-white rounded-xl border border-slate-200 shadow-2xs">
                <div className="flex items-center gap-1.5 text-slate-500 text-[10px] font-bold uppercase tracking-wider mb-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-teal-500" /> Safety Rules
                </div>
                <div className="text-xs font-bold text-slate-800 truncate" title={(userMatrix.exclusion_mask || []).join(', ') || 'None'}>
                  {(userMatrix.exclusion_mask || []).length > 0 ? (userMatrix.exclusion_mask || []).join(', ') : 'Standard Diet'}
                </div>
                <div className="text-[10px] text-emerald-600 font-semibold mt-0.5">
                  Instant Zero-Score Exclusion
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {evalLoading && (
        <div className="p-12 text-center flex flex-col items-center justify-center bg-slate-50 rounded-2xl border border-slate-200">
          <Loader2 className="w-8 h-8 text-emerald-600 animate-spin mb-3" />
          <h3 className="text-sm font-bold text-slate-900 mb-1">Synthesizing 3-Tier Clinical Recommendations...</h3>
          <p className="text-xs text-slate-500">Evaluating each dish against your metabolic matrix, macro targets, and clinical guardrails.</p>
        </div>
      )}

      {evalResult && !evalLoading && (
        <div className="space-y-6">
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

          {/* Controls Bar: View Mode, Filter Tabs, Search & Download */}
          <div className="flex flex-col lg:flex-row items-center justify-between gap-3">
            {/* View Mode Toggle & Filter Tabs */}
            <div className="flex flex-wrap items-center gap-2 w-full lg:w-auto">
              <div className="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200">
                <button
                  onClick={() => setViewMode('STACKED')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    viewMode === 'STACKED'
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <Layers className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Stacked 3-Tier View</span>
                </button>
                <button
                  onClick={() => setViewMode('TABLE')}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                    viewMode === 'TABLE'
                      ? 'bg-white text-slate-900 shadow-xs'
                      : 'text-slate-500 hover:text-slate-900'
                  }`}
                >
                  <Table className="w-3.5 h-3.5 text-slate-600" />
                  <span>Unified Table View</span>
                </button>
              </div>

              {viewMode === 'TABLE' && (
                <div className="inline-flex p-1 bg-slate-100 rounded-xl border border-slate-200">
                  {[
                    { id: 'ALL', label: `All (${allRecs.length})` },
                    { id: 'GOOD', label: `🟢 Good (${counts.GOOD})` },
                    { id: 'MEDIUM', label: `🟡 Medium (${counts.MEDIUM})` },
                    { id: 'BAD', label: `🔴 Bad (${counts.BAD})` },
                  ].map((tab) => (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                        activeTab === tab.id
                          ? 'bg-white text-slate-900 shadow-xs'
                          : 'text-slate-500 hover:text-slate-900'
                      }`}
                    >
                      {tab.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Search & Export */}
            <div className="flex items-center gap-2 w-full lg:w-auto">
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

              {/* Multi-Format Export Dropdown */}
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setIsDownloadMenuOpen(!isDownloadMenuOpen)}
                  className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-white border border-slate-300 text-slate-700 hover:text-emerald-700 hover:border-emerald-400 text-xs font-bold shadow-xs transition-all active:scale-[0.96] cursor-pointer"
                  title="Export Options"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Report</span>
                  <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                </button>

                {isDownloadMenuOpen && (
                  <div className="absolute right-0 mt-1.5 w-64 bg-white border border-slate-200 rounded-2xl shadow-xl z-30 py-1.5 text-xs text-slate-700 animate-in fade-in zoom-in-95 duration-100">
                    <div className="px-3 py-1.5 text-[10px] font-bold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                      Choose Export Format
                    </div>

                    <button
                      onClick={exportCSV}
                      className="w-full px-3 py-2 text-left flex items-center gap-2.5 hover:bg-slate-50 hover:text-emerald-700 transition-colors cursor-pointer"
                    >
                      <FileSpreadsheet className="w-4 h-4 text-emerald-600" />
                      <div>
                        <div className="font-bold">CSV Spreadsheet (.csv)</div>
                        <div className="text-[10px] text-slate-400">For Excel & Google Sheets</div>
                      </div>
                    </button>

                    <button
                      onClick={exportMarkdown}
                      className="w-full px-3 py-2 text-left flex items-center gap-2.5 hover:bg-slate-50 hover:text-emerald-700 transition-colors cursor-pointer"
                    >
                      <FileText className="w-4 h-4 text-blue-600" />
                      <div>
                        <div className="font-bold">Markdown Report (.md)</div>
                        <div className="text-[10px] text-slate-400">For Notion, Obsidian & GitHub</div>
                      </div>
                    </button>

                    <button
                      onClick={exportHTML}
                      className="w-full px-3 py-2 text-left flex items-center gap-2.5 hover:bg-slate-50 hover:text-emerald-700 transition-colors cursor-pointer"
                    >
                      <Printer className="w-4 h-4 text-indigo-600" />
                      <div>
                        <div className="font-bold">Printable HTML / PDF (.html)</div>
                        <div className="text-[10px] text-slate-400">Ready to print or save as PDF</div>
                      </div>
                    </button>

                    <button
                      onClick={exportJSON}
                      className="w-full px-3 py-2 text-left flex items-center gap-2.5 hover:bg-slate-50 hover:text-emerald-700 transition-colors cursor-pointer"
                    >
                      <FileCode className="w-4 h-4 text-amber-600" />
                      <div>
                        <div className="font-bold">Raw JSON Payload (.json)</div>
                        <div className="text-[10px] text-slate-400">Complete structured data</div>
                      </div>
                    </button>

                    <button
                      onClick={exportText}
                      className="w-full px-3 py-2 text-left flex items-center gap-2.5 hover:bg-slate-50 hover:text-emerald-700 transition-colors cursor-pointer border-t border-slate-100"
                    >
                      <File className="w-4 h-4 text-slate-500" />
                      <div>
                        <div className="font-bold">Plain Text Summary (.txt)</div>
                        <div className="text-[10px] text-slate-400">Quick notes format</div>
                      </div>
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* VIEW MODE 1: STACKED 3-TIER VIEW (Tiered upon each other) */}
          {viewMode === 'STACKED' && (
            <div className="space-y-8">
              {/* TIER 1: GOOD */}
              <div className="rounded-3xl border-2 border-emerald-200 bg-emerald-50/20 p-5 space-y-4 shadow-xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-emerald-200/80 pb-3">
                  <div className="flex items-center gap-2.5">
                    <span className="w-7 h-7 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                      1
                    </span>
                    <div>
                      <h3 className="font-black text-emerald-950 text-base flex items-center gap-2">
                        🟢 Tier 1: GOOD — Recommended & Optimal Fit
                        <span className="px-2 py-0.5 rounded-full bg-emerald-200 text-emerald-900 text-xs font-bold">
                          {filteredGood.length} {filteredGood.length === 1 ? 'dish' : 'dishes'}
                        </span>
                      </h3>
                      <p className="text-xs text-emerald-800/90 mt-0.5">
                        High nutritional alignment with your metabolic energy targets, optimal glycemic index, and safe clinical profile.
                      </p>
                    </div>
                  </div>
                </div>

                {filteredGood.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500 italic bg-white/60 rounded-2xl border border-dashed border-emerald-200">
                    No dishes currently qualify for Tier 1 based on active health guardrails.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredGood.map((item, idx) => renderDishItem(item, idx))}
                  </div>
                )}
              </div>

              {/* TIER 2: MEDIUM */}
              <div className="rounded-3xl border-2 border-amber-200 bg-amber-50/20 p-5 space-y-4 shadow-xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-amber-200/80 pb-3">
                  <div className="flex items-center gap-2.5">
                    <span className="w-7 h-7 rounded-xl bg-amber-600 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                      2
                    </span>
                    <div>
                      <h3 className="font-black text-amber-950 text-base flex items-center gap-2">
                        🟡 Tier 2: MEDIUM — Moderate / Consume with Portion Care
                        <span className="px-2 py-0.5 rounded-full bg-amber-200 text-amber-900 text-xs font-bold">
                          {filteredMedium.length} {filteredMedium.length === 1 ? 'dish' : 'dishes'}
                        </span>
                      </h3>
                      <p className="text-xs text-amber-800/90 mt-0.5">
                        Acceptable choices with moderate saturated fat or glycemic density. Best enjoyed with portion moderation or custom chef tips.
                      </p>
                    </div>
                  </div>
                </div>

                {filteredMedium.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500 italic bg-white/60 rounded-2xl border border-dashed border-amber-200">
                    No dishes classified in Tier 2.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredMedium.map((item, idx) => renderDishItem(item, idx))}
                  </div>
                )}
              </div>

              {/* TIER 3: BAD */}
              <div className="rounded-3xl border-2 border-rose-200 bg-rose-50/20 p-5 space-y-4 shadow-xs">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-rose-200/80 pb-3">
                  <div className="flex items-center gap-2.5">
                    <span className="w-7 h-7 rounded-xl bg-rose-600 text-white flex items-center justify-center font-bold text-xs shadow-xs">
                      3
                    </span>
                    <div>
                      <h3 className="font-black text-rose-950 text-base flex items-center gap-2">
                        🔴 Tier 3: BAD — Strict Avoidance / High Clinical Risk
                        <span className="px-2 py-0.5 rounded-full bg-rose-200 text-rose-900 text-xs font-bold">
                          {filteredBad.length} {filteredBad.length === 1 ? 'dish' : 'dishes'}
                        </span>
                      </h3>
                      <p className="text-xs text-rose-800/90 mt-0.5">
                        Conflicts with declared allergens, ethical diets (e.g. vegetarian), or exceeds hypertension/glycemic thresholds.
                      </p>
                    </div>
                  </div>
                </div>

                {filteredBad.length === 0 ? (
                  <div className="p-6 text-center text-xs text-slate-500 italic bg-white/60 rounded-2xl border border-dashed border-rose-200">
                    Zero items classified in Tier 3. All available dishes are safe.
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {filteredBad.map((item, idx) => renderDishItem(item, idx))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* VIEW MODE 2: UNIFIED TABLE VIEW */}
          {viewMode === 'TABLE' && (
            <div className="bg-white rounded-2xl border border-slate-200 overflow-hidden shadow-xs">
              {filteredAll.length === 0 ? (
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
                      {filteredAll.map((item, idx) => {
                        const isGood = item.tier === 'GOOD';
                        const isMedium = item.tier === 'MEDIUM';

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
                                {isGood ? (
                                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 stroke-[2.5]" />
                                ) : isMedium ? (
                                  <AlertCircle className="w-3.5 h-3.5 text-amber-600 stroke-[2.5]" />
                                ) : (
                                  <XCircle className="w-3.5 h-3.5 text-rose-600 stroke-[2.5]" />
                                )}
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
          )}
        </div>
      )}
    </section>
  );
}
