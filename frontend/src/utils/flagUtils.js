/**
 * Utility to sanitize, deduplicate, and declutter flags and allergen warnings for dishes.
 * Eliminates placeholder chips ('None', 'N/A'), removes duplicate violation warnings,
 * and standardizes typography and appearance across cards and tables.
 */

const PLACEHOLDER_REGEX = /^(none|n\/a|na|nil|null|no green flags|no red flags|none\.|not applicable|\s*)$/i;

export function cleanString(str) {
  if (!str || typeof str !== 'string') return '';
  return str.replace(/^[⛔⚠️✨✓🌿•\-*\s]+/, '').trim();
}

export function isPlaceholderFlag(str) {
  if (!str || typeof str !== 'string') return true;
  const cleaned = cleanString(str);
  return !cleaned || PLACEHOLDER_REGEX.test(cleaned);
}

export function formatBadgeText(str) {
  const cleaned = cleanString(str);
  if (!cleaned) return '';
  return cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
}

export function sanitizeDishFlags(dish = {}) {
  const isBad = dish.tier === 'BAD' || dish.tier === 'Tier 3: BAD';

  // 1. Clean and deduplicate allergen warnings
  const rawWarnings = Array.isArray(dish.allergen_warnings) ? dish.allergen_warnings : [];
  const cleanWarnings = [];
  const seenWarnings = new Set();

  for (const w of rawWarnings) {
    const cleaned = formatBadgeText(w);
    if (!cleaned || isPlaceholderFlag(cleaned)) continue;
    const lower = cleaned.toLowerCase();
    if (!seenWarnings.has(lower)) {
      seenWarnings.add(lower);
      cleanWarnings.push(cleaned);
    }
  }

  // 2. Clean green flags (Avoid/Bad tier dishes must NEVER have positive green flags)
  const rawGreens = isBad ? [] : (Array.isArray(dish.green_flags) ? dish.green_flags : []);
  const cleanGreens = [];
  const seenGreens = new Set();

  for (const g of rawGreens) {
    const cleaned = formatBadgeText(g);
    if (!cleaned || isPlaceholderFlag(cleaned)) continue;
    const lower = cleaned.toLowerCase();
    if (!seenGreens.has(lower)) {
      seenGreens.add(lower);
      cleanGreens.push(cleaned);
    }
  }

  // 3. Clean red flags and filter out those that duplicate allergen_warnings
  const rawReds = Array.isArray(dish.red_flags) ? dish.red_flags : [];
  const cleanReds = [];
  const seenReds = new Set();

  for (const r of rawReds) {
    const cleaned = formatBadgeText(r);
    if (!cleaned || isPlaceholderFlag(cleaned)) continue;
    const lower = cleaned.toLowerCase();

    // Check if this red flag is already covered in allergen warnings
    const isRedundant = cleanWarnings.some((w) => {
      const wLow = w.toLowerCase();
      // Direct overlap
      if (lower.includes(wLow) || wLow.includes(lower)) return true;
      // Meat / vegetarian overlap
      const rIsMeat = lower.includes('meat') || lower.includes('non-veg') || lower.includes('animal protein');
      const wIsMeat = wLow.includes('meat') || wLow.includes('non-veg') || wLow.includes('chicken') || wLow.includes('mutton') || wLow.includes('fish') || wLow.includes('beef') || wLow.includes('pork');
      if (rIsMeat && wIsMeat) return true;
      // Dairy / egg overlap
      const rIsDairy = lower.includes('dairy') || lower.includes('milk') || lower.includes('cheese') || lower.includes('egg');
      const wIsDairy = wLow.includes('dairy') || wLow.includes('milk') || wLow.includes('cheese') || wLow.includes('egg');
      if (rIsDairy && wIsDairy) return true;
      // Allergen phrase overlap
      const strippedW = wLow.replace(/^(contains|strict dietary violation:|allergen:|declared allergen:)\s*/g, '').trim();
      if (strippedW && (lower.includes(strippedW) || strippedW.includes(lower))) return true;
      return false;
    });

    if (!isRedundant && !seenReds.has(lower)) {
      seenReds.add(lower);
      cleanReds.push(cleaned);
    }
  }

  return {
    allergenWarnings: cleanWarnings,
    greenFlags: cleanGreens,
    redFlags: cleanReds,
  };
}
