// Normal web build by default. `BUILD_TARGET=android` exports plain static files that the Android app
// (Capacitor) packages inside the APK. See docs/PHONE_TESTING.md section E.
const forAndroid = process.env.BUILD_TARGET === "android";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // A production test build can use its own folder so `next dev` can keep serving .next.
  // With `output: "export"`, Next treats a custom distDir as the HTML folder (not `out`)
  // and still writes the build cache to `.next`. capacitor.config.ts reads that same folder.
  distDir: process.env.NEXT_DIST_DIR || ".next",
  ...(forAndroid ? { output: "export", trailingSlash: true, images: { unoptimized: true } } : {}),
};
export default nextConfig;
