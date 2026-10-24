// Required notice on first-run screens (FIGMA_REVIEW.md, FUNCTIONAL_SPEC section 3).
export const DISCLAIMER_TEXT = "We describe conditions. We do not guarantee safety.";
export const EMERGENCY_TEXT = "In an emergency, call 911.";

export function DisclaimerBanner() {
  return (
    <aside aria-label="Important notice" className="disclaimer">
      <p>{DISCLAIMER_TEXT}</p>
      <p className="emergency">{EMERGENCY_TEXT}</p>
    </aside>
  );
}
