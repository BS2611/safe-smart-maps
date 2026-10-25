import { BAND_SYMBOL, BAND_TEXT } from "@/lib/format";
import { BAND_COLOR } from "@/lib/geometry";
import type { Band } from "@/lib/types";

const ORDER: Band[] = ["green", "yellow", "red", "unknown"];

/** Color plus symbol plus text for every band: color is never the only signal. */
export function MapLegend() {
  return (
    <ul className="legend" aria-label="Map legend" style={{ listStyle: "none", padding: 0, margin: 0 }}>
      {ORDER.map((band) => (
        <li key={band}>
          <i style={{ color: BAND_COLOR[band] }} aria-hidden="true">{BAND_SYMBOL[band]}</i>
          <span style={{ width: 18, height: 4, background: BAND_COLOR[band], display: "inline-block", borderRadius: 2 }} aria-hidden="true" />
          {BAND_TEXT[band]}
        </li>
      ))}
    </ul>
  );
}
