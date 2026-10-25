import type { Band } from "@/lib/types";

const RING = {
  high: "#9cf0d2",
  mid: "#f0b429",
  low: "#ff9b7a",
  unknown: "#a8b4bc",
} as const;

function tone(score: number | null): keyof typeof RING {
  if (score === null) return "unknown";
  if (score >= 70) return "high";
  if (score >= 45) return "mid";
  return "low";
}

/** Visual route score. Decorative: the words next to it carry the meaning. */
export function ScoreRing({ score, size = 72 }: { score: number | null; size?: number }) {
  const value = score === null ? 0 : Math.max(0, Math.min(100, score));
  const color = RING[tone(score)];
  const radius = 40;
  const turn = 2 * Math.PI * radius;
  const dash = (value / 100) * turn;
  const label = score === null ? "—" : String(Math.round(score));
  return (
    <span className="score-lockup" aria-hidden="true">
      <span className={`score-ring tone-${tone(score)}`} style={{ width: size, height: size }}>
        <svg className="score-svg" viewBox="0 0 100 100" aria-hidden="true" focusable="false">
          <circle cx="50" cy="50" r="46" fill="#10211c" />
          <circle cx="50" cy="50" r={radius} fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth="7" />
          <circle cx="50" cy="50" r={radius} fill="none" stroke={color} strokeWidth="7" strokeLinecap="round"
            strokeDasharray={`${dash} ${turn - dash}`} transform="rotate(-90 50 50)" />
          <text x="50" y="57" textAnchor="middle" fill="#ffffff" fontSize="26" fontWeight="700"
            fontFamily="Georgia, serif">{label}</text>
        </svg>
      </span>
      <span className="score-caption">Score</span>
    </span>
  );
}

/** Colored stretches along a route. Color is paired with the legend elsewhere. */
export function ScoreRibbon({ segments }: { segments: { segment_id: string; band: Band; length_m: number }[] }) {
  if (!segments.length) return null;
  return (
    <div className="mini-strip" aria-hidden="true">
      {segments.map((s) => (
        <span key={s.segment_id} className={`band-${s.band}`} style={{ flexGrow: Math.max(s.length_m, 1) }} />
      ))}
    </div>
  );
}
