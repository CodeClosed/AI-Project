/**
 * Export and Print utilities for NutriMenu AI.
 * Provides CSV export for monthly meal logs and print-ready Safe-Food Dining Guide.
 */

export function exportMealsToCsv(loggedMeals, targets = null) {
  if (!loggedMeals || loggedMeals.length === 0) {
    alert('No logged meals available to export.');
    return;
  }

  const headers = [
    'Date',
    'Meal Name',
    'Meal Type',
    'Total Calories (kcal)',
    'Protein (g)',
    'Carbs (g)',
    'Fats (g)',
    'Sodium (mg)',
    'Dishes Included',
  ];

  const rows = loggedMeals.map((m) => {
    const dishNames = (m.dishes || [])
      .map((d) => (typeof d === 'object' ? `${d.name || 'Item'} (x${d.portion || 1})` : String(d)))
      .join('; ');

    return [
      m.date || '',
      `"${(m.name || 'Meal Plate').replace(/"/g, '""')}"`,
      m.meal_type || 'Lunch',
      Number(m.total_calories || 0).toFixed(1),
      Number(m.total_protein || 0).toFixed(1),
      Number(m.total_carbs || 0).toFixed(1),
      Number(m.total_fats || 0).toFixed(1),
      Number(m.total_sodium || 0).toFixed(1),
      `"${dishNames.replace(/"/g, '""')}"`,
    ];
  });

  const csvContent = [headers.join(','), ...rows.map((r) => r.join(','))].join('\r\n');
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `nutrimenu_nutrition_report_${new Date().toISOString().split('T')[0]}.csv`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export function openPrintSafeFoodGuide({
  menuTitle = 'Restaurant Menu',
  evalResult,
  profile,
  userMatrix,
}) {
  if (!evalResult) {
    alert('No evaluated recommendations found to print.');
    return;
  }

  const good = evalResult.good_items || evalResult.tier_1_optimal || [];
  const medium = evalResult.medium_items || evalResult.tier_2_moderate || [];
  const bad = evalResult.bad_items || evalResult.tier_3_avoid || [];

  const targets = userMatrix?.metabolic_targets || {};
  const guardrails = userMatrix?.nutritional_guardrails || {};
  const conditions = (profile?.health_conditions || []).map((c) => c.replace(/_/g, ' ')).join(', ') || 'None';
  const allergies = (profile?.allergies || []).join(', ') || 'None reported';

  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('Please allow popups to open the print guide.');
    return;
  }

  const html = `
<!DOCTYPE html>
<html>
<head>
  <title>NutriMenu AI — Clinical Safe-Food Dining Guide</title>
  <style>
    @page { size: A4; margin: 15mm; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      line-height: 1.4;
      margin: 0;
      padding: 20px;
    }
    .header {
      border-bottom: 2px solid #10b981;
      padding-bottom: 12px;
      margin-bottom: 16px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }
    .logo {
      font-size: 24px;
      font-weight: 900;
      color: #0f172a;
    }
    .logo span { color: #059669; }
    .date { font-size: 11px; color: #64748b; }
    .profile-card {
      background: #f8fafc;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px 14px;
      margin-bottom: 16px;
      font-size: 11px;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 8px;
    }
    .profile-card div strong { display: block; color: #475569; font-size: 10px; text-transform: uppercase; }
    h2 { font-size: 15px; margin: 16px 0 8px; font-weight: 800; }
    .tier-optimal { color: #047857; }
    .tier-moderate { color: #d97706; }
    .tier-avoid { color: #b91c1c; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 14px; font-size: 11px; }
    th { background: #f1f5f9; text-align: left; padding: 6px 8px; font-weight: 700; border-bottom: 1px solid #cbd5e1; }
    td { padding: 6px 8px; border-bottom: 1px solid #f1f5f9; vertical-align: top; }
    .dish-name { font-weight: 700; font-size: 12px; }
    .badge {
      display: inline-block;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 9px;
      font-weight: 700;
      text-transform: uppercase;
    }
    .badge-good { background: #d1fae5; color: #065f46; }
    .badge-med { background: #fef3c7; color: #92400e; }
    .badge-bad { background: #fee2e2; color: #991b1b; }
    .footer {
      border-top: 1px solid #e2e8f0;
      padding-top: 10px;
      margin-top: 20px;
      font-size: 9px;
      color: #94a3b8;
      text-align: center;
    }
    @media print {
      body { padding: 0; }
      .no-print { display: none; }
    }
  </style>
</head>
<body>
  <div class="no-print" style="margin-bottom: 15px; background: #ecfdf5; padding: 10px; border-radius: 6px; border: 1px solid #a7f3d0; display: flex; justify-content: space-between; align-items: center;">
    <span style="font-size: 12px; color: #065f46; font-weight: 600;">✨ Print or Save as PDF to take with you to the restaurant.</span>
    <button onclick="window.print()" style="background: #059669; color: white; border: none; padding: 6px 14px; border-radius: 6px; font-weight: 700; cursor: pointer;">Print / Save as PDF</button>
  </div>

  <div class="header">
    <div>
      <div class="logo">NutriMenu <span>AI</span></div>
      <div style="font-size: 12px; font-weight: 700; color: #334155;">Clinical Safe-Food Dining Guide • ${menuTitle}</div>
    </div>
    <div class="date">Generated: ${new Date().toLocaleDateString()}</div>
  </div>

  <div class="profile-card">
    <div>
      <strong>Target Calories</strong>
      ${targets.target_calories_kcal ? Math.round(targets.target_calories_kcal) + ' kcal' : 'Standard'}
    </div>
    <div>
      <strong>Sodium Ceiling</strong>
      ${guardrails.sodium_ceiling_mg ? guardrails.sodium_ceiling_mg + ' mg' : '2300 mg'}
    </div>
    <div>
      <strong>Clinical Conditions</strong>
      ${conditions}
    </div>
    <div>
      <strong>Strict Allergens</strong>
      ${allergies}
    </div>
  </div>

  <h2 class="tier-optimal">🟢 Recommended / Optimal Choices (${good.length})</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 30%;">Dish Name</th>
        <th style="width: 20%;">Clinical Fit</th>
        <th style="width: 50%;">Nutritional Rationale</th>
      </tr>
    </thead>
    <tbody>
      ${good.map((d) => `
        <tr>
          <td><span class="dish-name">${d.name || d.dish_name}</span></td>
          <td><span class="badge badge-good">Safe & Optimal</span></td>
          <td>${d.reasoning || d.clinical_notes || d.description || 'Aligns with low glycemic load and macro ratios.'}</td>
        </tr>
      `).join('') || '<tr><td colspan="3" style="color: #94a3b8;">No items in this tier.</td></tr>'}
    </tbody>
  </table>

  <h2 class="tier-moderate">🟡 Moderate / Portion-Control Choices (${medium.length})</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 30%;">Dish Name</th>
        <th style="width: 20%;">Clinical Fit</th>
        <th style="width: 50%;">Guidance</th>
      </tr>
    </thead>
    <tbody>
      ${medium.map((d) => `
        <tr>
          <td><span class="dish-name">${d.name || d.dish_name}</span></td>
          <td><span class="badge badge-med">Moderate</span></td>
          <td>${d.reasoning || d.clinical_notes || 'Consume in moderation. Watch sodium and carbohydrate density.'}</td>
        </tr>
      `).join('') || '<tr><td colspan="3" style="color: #94a3b8;">No items in this tier.</td></tr>'}
    </tbody>
  </table>

  ${bad.length > 0 ? `
  <h2 class="tier-avoid">🔴 High Risk / Excluded Items (${bad.length})</h2>
  <table>
    <thead>
      <tr>
        <th style="width: 30%;">Dish Name</th>
        <th style="width: 20%;">Risk Level</th>
        <th style="width: 50%;">Clinical Contraindication</th>
      </tr>
    </thead>
    <tbody>
      ${bad.slice(0, 10).map((d) => `
        <tr>
          <td><span class="dish-name">${d.name || d.dish_name}</span></td>
          <td><span class="badge badge-bad">Avoid</span></td>
          <td>${d.reasoning || d.clinical_notes || 'High sodium, glycemic spike risk, or potential allergen conflict.'}</td>
        </tr>
      `).join('')}
    </tbody>
  </table>
  ` : ''}

  <div class="footer">
    NutriMenu AI • Recommendations are algorithmic nutritional assessments based on user profile inputs. Always verify allergen information directly with restaurant staff.
  </div>
</body>
</html>
  `;

  printWindow.document.open();
  printWindow.document.write(html);
  printWindow.document.close();
}

export function exportMealsToJson(loggedMeals) {
  if (!loggedMeals || loggedMeals.length === 0) {
    alert('No logged meals available to export.');
    return;
  }
  const blob = new Blob([JSON.stringify(loggedMeals, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', `nutrimenu_meal_history_${new Date().toISOString().split('T')[0]}.json`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

export function openClinicalDoctorReport({ profile, userMatrix, loggedMeals = [] }) {
  const printWindow = window.open('', '_blank');
  if (!printWindow) {
    alert('Please allow popups to open the clinical report.');
    return;
  }

  const targets = userMatrix?.metabolic_targets || {};
  const guardrails = userMatrix?.nutritional_guardrails || {};
  const conditions = (profile?.health_conditions || []).map((c) => c.replace(/_/g, ' ')).join(', ') || 'None recorded';
  const allergies = (profile?.allergies || []).join(', ') || 'None reported';
  const diet = (profile?.dietary_preferences || []).join(', ') || 'Standard';

  const weightKg = Number(profile?.weight_kg || 70);
  const heightCm = Number(profile?.height_cm || 170);
  const bmi = (weightKg / ((heightCm / 100) * (heightCm / 100))).toFixed(1);

  // Compliance calculations
  const totalMeals = loggedMeals.length;
  const targetCals = Number(targets.target_calories_kcal || 2000);
  const sodiumCeiling = Number(guardrails.sodium_ceiling_mg || 2300);

  let avgCalories = 0;
  let avgProtein = 0;
  let avgSodium = 0;
  let sodiumViolations = 0;

  if (totalMeals > 0) {
    const sums = loggedMeals.reduce((acc, m) => {
      const c = Number(m.total_calories || m.nutrients?.calories || 0);
      const p = Number(m.total_protein || m.nutrients?.protein || 0);
      const s = Number(m.total_sodium || m.nutrients?.sodium || 0);
      if (s > sodiumCeiling) sodiumViolations++;
      return { c: acc.c + c, p: acc.p + p, s: acc.s + s };
    }, { c: 0, p: 0, s: 0 });

    avgCalories = Math.round(sums.c / totalMeals);
    avgProtein = Math.round(sums.p / totalMeals);
    avgSodium = Math.round(sums.s / totalMeals);
  }

  const complianceRate = totalMeals > 0 ? Math.round(((totalMeals - sodiumViolations) / totalMeals) * 100) : 100;

  const html = `
<!DOCTYPE html>
<html>
<head>
  <title>NutriMenu AI — Clinical Nutrition Consultation Dossier</title>
  <style>
    @page { size: A4; margin: 12mm; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
      color: #0f172a;
      line-height: 1.4;
      margin: 0;
      padding: 24px;
      background: #fff;
    }
    .header {
      border-bottom: 3px solid #059669;
      padding-bottom: 12px;
      margin-bottom: 18px;
      display: flex;
      justify-content: space-between;
      align-items: flex-end;
    }
    .title { font-size: 20px; font-weight: 900; color: #047857; margin: 0; }
    .subtitle { font-size: 11px; color: #64748b; font-weight: 600; margin-top: 2px; }
    .meta-date { font-size: 11px; color: #475569; font-weight: 700; text-align: right; }
    
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 16px; }
    .card {
      border: 1px solid #e2e8f0;
      border-radius: 10px;
      padding: 12px 14px;
      background: #f8fafc;
    }
    .card h3 {
      margin: 0 0 8px 0;
      font-size: 11px;
      font-weight: 800;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      color: #334155;
      border-bottom: 1px solid #e2e8f0;
      padding-bottom: 4px;
    }
    .data-row { display: flex; justify-content: space-between; font-size: 11px; margin-bottom: 4px; }
    .data-label { color: #64748b; font-weight: 600; }
    .data-val { font-weight: 700; color: #0f172a; }
    
    .highlight-box {
      background: #ecfdf5;
      border: 1px solid #a7f3d0;
      border-radius: 10px;
      padding: 12px 16px;
      margin-bottom: 18px;
      display: flex;
      justify-content: space-around;
      text-align: center;
    }
    .stat-val { font-size: 20px; font-weight: 900; color: #065f46; }
    .stat-label { font-size: 10px; font-weight: 700; color: #047857; text-transform: uppercase; }

    table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 10px; }
    th { background: #f1f5f9; text-align: left; padding: 6px 8px; font-weight: 700; color: #334155; border-bottom: 1px solid #cbd5e1; }
    td { padding: 6px 8px; border-bottom: 1px solid #e2e8f0; color: #1e293b; }
    
    .sign-section {
      margin-top: 24px;
      padding-top: 14px;
      border-top: 1px dashed #cbd5e1;
      display: flex;
      justify-content: space-between;
      font-size: 11px;
      color: #475569;
    }
    .sign-line {
      width: 200px;
      border-bottom: 1px solid #94a3b8;
      height: 24px;
      margin-top: 6px;
    }
    .footer {
      margin-top: 20px;
      font-size: 9px;
      color: #94a3b8;
      text-align: center;
      border-top: 1px solid #f1f5f9;
      padding-top: 8px;
    }
  </style>
</head>
<body>
  <div class="header">
    <div>
      <h1 class="title">NutriMenu AI — Clinical Nutrition Consultation Dossier</h1>
      <div class="subtitle">Algorithmic Metabolic Profiling & Nutritional Adherence Summary</div>
    </div>
    <div class="meta-date">
      Report Date: ${new Date().toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}<br>
      Patient ID: NM-${Math.random().toString(36).substr(2, 6).toUpperCase()}
    </div>
  </div>

  <div class="highlight-box">
    <div>
      <div class="stat-val">${complianceRate}%</div>
      <div class="stat-label">Guardrail Compliance</div>
    </div>
    <div>
      <div class="stat-val">${totalMeals}</div>
      <div class="stat-label">Logged Meals Recorded</div>
    </div>
    <div>
      <div class="stat-val">${targetCals} kcal</div>
      <div class="stat-label">Target Energy Intake</div>
    </div>
    <div>
      <div class="stat-val">${sodiumCeiling} mg</div>
      <div class="stat-label">Sodium Safety Ceiling</div>
    </div>
  </div>

  <div class="grid">
    <div class="card">
      <h3>Patient Biometrics & Energetics</h3>
      <div class="data-row"><span class="data-label">Age / Biological Sex:</span><span class="data-val">${profile?.age || 45} yrs / ${(profile?.gender || 'Male').toUpperCase()}</span></div>
      <div class="data-row"><span class="data-label">Height / Weight:</span><span class="data-val">${heightCm} cm / ${weightKg} kg</span></div>
      <div class="data-row"><span class="data-label">Body Mass Index (BMI):</span><span class="data-val">${bmi} kg/m²</span></div>
      <div class="data-row"><span class="data-label">Basal Metabolic Rate (BMR):</span><span class="data-val">${targets.bmr_kcal || '~1650'} kcal/day</span></div>
      <div class="data-row"><span class="data-label">Activity Level:</span><span class="data-val">${(profile?.activity_level || 'Sedentary').replace('_', ' ')}</span></div>
      <div class="data-row"><span class="data-label">Primary Goal:</span><span class="data-val">${(profile?.primary_goal || 'Fat Loss').replace('_', ' ')}</span></div>
    </div>

    <div class="card">
      <h3>Clinical Profile & Guardrails</h3>
      <div class="data-row"><span class="data-label">Diagnosed Conditions:</span><span class="data-val" style="color: #b91c1c;">${conditions}</span></div>
      <div class="data-row"><span class="data-label">Declared Food Allergies:</span><span class="data-val" style="color: #b91c1c;">${allergies}</span></div>
      <div class="data-row"><span class="data-label">Dietary Preference:</span><span class="data-val">${diet}</span></div>
      <div class="data-row"><span class="data-label">Prescribed Sodium Ceiling:</span><span class="data-val">${sodiumCeiling} mg/day</span></div>
      <div class="data-row"><span class="data-label">Target Protein Intake:</span><span class="data-val">${targets.target_protein_g || 130}g/day</span></div>
      <div class="data-row"><span class="data-label">Fiber Target:</span><span class="data-val">≥ ${guardrails.dietary_fiber_min_g || 30}g/day</span></div>
    </div>
  </div>

  <div class="card">
    <h3>Recent Meal Logging & Compliance Audit (${Math.min(totalMeals, 8)} recorded)</h3>
    ${totalMeals === 0 ? '<p style="font-size: 11px; color: #94a3b8; margin: 6px 0;">No meals logged yet. Once meals are recorded in NutriMenu AI, daily intake trends appear here.</p>' : `
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Meal / Dishes</th>
          <th>Type</th>
          <th>Calories</th>
          <th>Protein</th>
          <th>Carbs</th>
          <th>Fats</th>
          <th>Sodium</th>
          <th>Clinical Status</th>
        </tr>
      </thead>
      <tbody>
        ${loggedMeals.slice(0, 8).map(m => {
          const s = Number(m.total_sodium || m.nutrients?.sodium || 0);
          const safe = s <= (sodiumCeiling * 0.45);
          return `
            <tr>
              <td>${m.date || 'Today'}</td>
              <td><b>${m.name || 'Meal Plate'}</b></td>
              <td>${m.meal_type || 'Lunch'}</td>
              <td>${Math.round(m.total_calories || m.nutrients?.calories || 0)} kcal</td>
              <td>${Math.round(m.total_protein || m.nutrients?.protein || 0)}g</td>
              <td>${Math.round(m.total_carbs || m.nutrients?.carbs || 0)}g</td>
              <td>${Math.round(m.total_fats || m.nutrients?.fat || 0)}g</td>
              <td>${Math.round(s)}mg</td>
              <td><span style="font-weight: 700; color: ${safe ? '#059669' : '#dc2626'};">${safe ? '✓ Compliant' : '⚠️ Sodium Alert'}</span></td>
            </tr>
          `;
        }).join('')}
      </tbody>
    </table>
    `}
  </div>

  <div class="sign-section">
    <div>
      <b>Patient Signature:</b>
      <div class="sign-line"></div>
    </div>
    <div>
      <b>Attending Clinician / Dietitian:</b>
      <div class="sign-line"></div>
      <div style="font-size: 9px; color: #94a3b8; margin-top: 3px;">License No. & Date</div>
    </div>
  </div>

  <div class="footer">
    Confidential Medical Nutrition Dossier • Generated by NutriMenu AI Clinical Decision Support Engine • For professional dietary consultation and clinical review.
  </div>
</body>
</html>
  `;

  printWindow.document.open();
  printWindow.document.write(html);
  printWindow.document.close();
}
