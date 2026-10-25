// Welcome hero: a stylized night map, not live data. Three walks share a start and
// an end. Color follows the score bands (mint / amber / coral). The lit route
// bends around the weaker stretch. Motion is CSS-only and skipped when the
// visitor asks for less motion.

const LIT =
  "M78 318 C128 230 168 132 286 96 C404 60 520 78 590 150 C648 208 678 252 682 300";
const MIXED =
  "M78 318 C170 274 300 252 430 268 C540 282 620 286 682 300";
const LOW =
  "M78 318 C150 380 240 436 380 442 C520 448 610 400 682 300";

const BLOCKS: Array<[number, number, number, number]> = [
  [24, 22, 128, 78],
  [168, 28, 92, 64],
  [276, 18, 148, 70],
  [440, 26, 112, 72],
  [568, 20, 168, 86],
  [24, 128, 104, 70],
  [586, 132, 150, 68],
  [28, 360, 132, 78],
  [24, 470, 150, 66],
  [196, 486, 118, 52],
  [520, 478, 216, 58],
];

const TONE = {
  high: "#9cf0d2",
  mid: "#f0b429",
  low: "#ff9b7a",
} as const;

function ScoreBadge({
  x, y, score, name, tone,
}: { x: number; y: number; score: string; name: string; tone: keyof typeof TONE }) {
  const stroke = TONE[tone];
  return (
    <g className="hero-badge" transform={`translate(${x} ${y})`}>
      <rect className="badge-halo" x={-58} y={-32} width={116} height={64} rx={20} fill={stroke} />
      <rect x={-52} y={-26} width={104} height={52} rx={16} fill="#0c1915" stroke={stroke} strokeWidth={1.6} />
      <text className="hero-score" x={0} y={2} textAnchor="middle" fill="#ffffff" fontSize={24}>{score}</text>
      <text x={0} y={18} textAnchor="middle" fill={stroke} fontSize={11} fontWeight={700}>{name}</text>
    </g>
  );
}

function GlowRoute({ d, color, id, dash }: { d: string; color: string; id?: string; dash?: string }) {
  return (
    <g>
      <path d={d} fill="none" stroke={color} strokeWidth={18} strokeLinecap="round" filter="url(#hero-glow)" />
      <path id={id} d={d} fill="none" stroke={color} strokeWidth={5.5} strokeLinecap="round" />
      <path d={d} fill="none" stroke="#f7fffc" strokeWidth={1.8} strokeLinecap="round" />
      {dash ? (
        <path className={dash} d={d} fill="none" stroke="#ffffff" strokeWidth={2} strokeLinecap="round" />
      ) : null}
    </g>
  );
}

export function RouteIllustration({ gapLabel = "Weaker stretch (220 m)" }: { gapLabel?: string }) {
  return (
    <figure className="card tight hero-stage">
      <svg className="hero-map" viewBox="0 0 760 560" role="img"
        aria-label={`Illustration: a lit route curves around a ${gapLabel.toLowerCase()}`}
        width="100%">
        <defs>
          <radialGradient id="hero-vignette" cx="50%" cy="42%" r="68%">
            <stop offset="0" stopColor="#12302a" />
            <stop offset="1" stopColor="#07110e" />
          </radialGradient>
          <pattern id="hero-grid" width="28" height="28" patternUnits="userSpaceOnUse">
            <path d="M28 0H0V28" fill="none" stroke="#14302a" strokeWidth="1" />
          </pattern>
          <filter id="hero-glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3.4" />
          </filter>
        </defs>
        <rect width="760" height="560" fill="url(#hero-vignette)" />
        <rect width="760" height="560" fill="url(#hero-grid)" opacity={0.45} />

        {BLOCKS.map(([x, y, w, h], i) => (
          <g key={`${x}-${y}`}>
            <rect x={x} y={y} width={w} height={h} rx={8} fill="#081410" stroke="#1a3330" />
            {Array.from({ length: 3 }, (_, row) => (
              Array.from({ length: 4 }, (_, col) => {
                const wx = x + 14 + col * 18;
                const wy = y + 14 + row * 16;
                if (wx > x + w - 12 || wy > y + h - 12) return null;
                const lit = (i + col + row) % 5 === 0;
                return (
                  <rect key={`${row}-${col}`} x={wx} y={wy} width={4} height={3} rx={0.6}
                    fill={lit ? "#b7ffe8" : "#1d4038"} opacity={lit ? 0.9 : 0.7} />
                );
              })
            ))}
          </g>
        ))}

        <ellipse cx="400" cy="168" rx="78" ry="40" fill="#0d2822" stroke="#1e463c" />
        <text x="400" y="172" textAnchor="middle" fill="#7d9e94" fontSize="11" fontWeight="700">PARK</text>

        <GlowRoute d={LOW} color={TONE.low} dash="route-dash route-dash-low" />
        <GlowRoute d={MIXED} color={TONE.mid} dash="route-dash route-dash-mid" />
        <GlowRoute d={LIT} color={TONE.high} id="hero-lit-route" dash="route-dash route-dash-high" />

        <path d="M250 424 C330 456 470 456 548 390" fill="none" stroke="#f0b429" strokeWidth="8"
          strokeLinecap="round" strokeDasharray="2 10" opacity={0.95} />
        <text x="400" y="408" textAnchor="middle" fill="#f0b429" fontSize="12" fontWeight="700">
          {gapLabel.toUpperCase()}
        </text>

        {[[210, 150], [330, 92], [500, 118], [610, 196]].map(([cx, cy]) => (
          <g key={`${cx}-${cy}`}>
            <circle cx={cx} cy={cy} r="7" fill="#07110e" stroke="#d7f0ae" strokeWidth="1.6" />
            <circle cx={cx} cy={cy} r="2.4" fill="#d7f0ae" />
          </g>
        ))}

        <ScoreBadge x={168} y={78} score="82" name="LIT & ACTIVE" tone="high" />
        <ScoreBadge x={300} y={248} score="61" name="MIXED" tone="mid" />
        <ScoreBadge x={470} y={500} score="34" name="FEWER" tone="low" />

        <g className="hero-walker" aria-hidden="true">
          <circle r="11" fill="#9cf0d2" opacity="0.28" />
          <circle r="4.5" fill="#ffffff" />
        </g>

        <g>
          <circle cx="78" cy="318" r="8" fill="#07110e" stroke="#f4f7f4" strokeWidth="2.5" />
          <text x="78" y="344" textAnchor="middle" fill="#f4f7f4" fontSize="12" fontWeight="700">START · 8 PM</text>
          <circle cx="682" cy="300" r="8" fill="#9cf0d2" stroke="#07110e" strokeWidth="2.5" />
          <text x="682" y="276" textAnchor="middle" fill="#f4f7f4" fontSize="12" fontWeight="700">ARRIVAL</text>
        </g>
      </svg>
      <div className="legend hero-legend">
        <span><i className="route-key route-key-high" /> Most lit &amp; active</span>
        <span><i className="route-key route-key-mid" /> Mixed</span>
        <span><i className="route-key route-key-low" /> Fewer supports</span>
      </div>
      <p className="caption">Sample scores on an illustration, not a live route.</p>
    </figure>
  );
}
