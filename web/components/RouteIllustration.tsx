// The welcome picture: one lit route that arcs around a weaker stretch. Drawn here (not copied from
// Figma assets, which expire). It describes the idea; it is not real data.
export function RouteIllustration({ gapLabel = "Weaker stretch (220 m)" }: { gapLabel?: string }) {
  return (
    <figure className="card tight">
      <svg viewBox="0 0 360 176" role="img" aria-label={`Illustration: a lit route curves around a ${gapLabel.toLowerCase()}`}
        width="100%" style={{ background: "#0b0f0e", borderRadius: 8, display: "block" }}>
        <path d="M24 100 H336" stroke="#f2b632" strokeWidth="3" strokeDasharray="8 5" fill="none" />
        <path d="M24 100 C 90 20, 270 20, 336 100" stroke="#a5f2d7" strokeWidth="4" fill="none" strokeLinecap="round" />
        {[110, 180, 250].map((x, i) => (
          <circle key={x} cx={x} cy={[44, 30, 44][i]} r="5" fill="#0b0f0e" stroke="#e0e3e1" strokeWidth="2" />
        ))}
        <circle cx="24" cy="100" r="7" fill="#0b0f0e" stroke="#e0e3e1" strokeWidth="2" />
        <circle cx="336" cy="100" r="7" fill="#0b0f0e" stroke="#e0e3e1" strokeWidth="2" />
        <text x="24" y="128" fill="#e0e3e1" fontSize="10" fontWeight="600">ORIGIN</text>
        <text x="336" y="128" fill="#e0e3e1" fontSize="10" fontWeight="600" textAnchor="end">DESTINATION</text>
        <text x="180" y="14" fill="#89d5bc" fontSize="10" fontWeight="600" textAnchor="middle">LIT ROUTE</text>
        <text x="180" y="88" fill="#f2b632" fontSize="10" fontWeight="600" textAnchor="middle">{`▲ ${gapLabel.toUpperCase()}`}</text>
      </svg>
      <div className="legend" style={{ marginTop: 12 }}>
        <span><span className="dot" /> Better lit &amp; active</span>
        <span><i style={{ color: "#f2b632" }}>▲</i> Fewer supports</span>
        <span><span className="dot" style={{ background: "transparent", border: "1.5px solid #c6c8ba" }} /> Open storefronts</span>
      </div>
    </figure>
  );
}
