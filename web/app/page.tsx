import { DisclaimerBanner } from "@/components/DisclaimerBanner";

// Placeholder home. Real screens come from the fixed Figma design (docs/design/FIGMA_REVIEW.md).
export default function Home() {
  return (
    <main>
      <h1>Safe Smart Maps</h1>
      <p>Compare walking routes for the time you will be on the street.</p>
      <DisclaimerBanner />
    </main>
  );
}
