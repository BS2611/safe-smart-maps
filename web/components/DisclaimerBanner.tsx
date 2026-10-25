// Required notice on first-run screens (FIGMA_REVIEW.md, FUNCTIONAL_SPEC section 3).
export const DISCLAIMER_TEXT = "We describe conditions. We do not guarantee safety.";
export const EMERGENCY_TEXT = "In an emergency, call 911.";

export function DisclaimerBanner({ compact = false }: { compact?: boolean }) {
  return (
    <aside aria-label="Important notice" className="notice">
      <p className={compact ? "small" : undefined}>{DISCLAIMER_TEXT}</p>
      <p className="emergency small">{EMERGENCY_TEXT}</p>
    </aside>
  );
}
