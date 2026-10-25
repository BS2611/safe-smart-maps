// Normal web build by default. `BUILD_TARGET=android` exports plain static files that the Android app
// (Capacitor) packages inside the APK. See docs/PHONE_TESTING.md section E.
const forAndroid = process.env.BUILD_TARGET === "android";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  ...(forAndroid ? { output: "export", trailingSlash: true, images: { unoptimized: true } } : {}),
};
export default nextConfig;
