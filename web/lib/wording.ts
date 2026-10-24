// Wording rules (AGENTS.md section 6): never call a route "safe"; calm, plain words.
// The product name "Safe Smart Maps" and the notice "do not guarantee safety" are allowed.

// "safe-area" is the CSS/iOS safe-area inset (layout), not a claim about routes.
const ALLOWED = [/safe smart maps?/gi, /safe-area(-inset-(top|right|bottom|left))?/gi];

const BANNED: { pattern: RegExp; hint: string }[] = [
  { pattern: /\bsafest\b/i, hint: 'use "Most lit & active"' },
  { pattern: /\bsafe\b/i, hint: 'use "better lit and more active"' },
  { pattern: /\bsafely\b/i, hint: "describe conditions, do not promise safety" },
  { pattern: /\bhazard(ous)?\b/i, hint: "alarming; use plain words" },
  { pattern: /\bdangerous\b/i, hint: "alarming; use plain words" },
  { pattern: /\bcrime[- ]free\b/i, hint: "we cannot promise that" },
];

export type WordingProblem = { match: string; hint: string };

export function findBannedWording(text: string): WordingProblem[] {
  const cleaned = ALLOWED.reduce((t, re) => t.replace(re, " "), text);
  const problems: WordingProblem[] = [];
  for (const { pattern, hint } of BANNED) {
    const found = cleaned.match(pattern);
    if (found) problems.push({ match: found[0], hint });
  }
  return problems;
}
