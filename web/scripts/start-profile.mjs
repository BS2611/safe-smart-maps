import { readFileSync } from "node:fs";
import { spawn } from "node:child_process";
import { resolve } from "node:path";

const profile = process.argv[2] ?? "local";
if (!new Set(["local", "demo"]).has(profile)) {
  console.error("Usage: node scripts/start-profile.mjs <local|demo>");
  process.exit(2);
}

const envPath = resolve(`.env.${profile}`);
let contents;
try {
  contents = readFileSync(envPath, "utf8");
} catch {
  console.error(`Missing ${envPath}. Copy web/.env.${profile}.example to it and fill in the values.`);
  process.exit(1);
}

const profileEnv = {};
for (const line of contents.split(/\r?\n/)) {
  const match = line.match(/^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$/);
  if (!match || line.trimStart().startsWith("#")) continue;
  profileEnv[match[1]] = match[2].replace(/^['"]|['"]$/g, "");
}

const port = profile === "demo" ? "3001" : "3000";
const npm = process.platform === "win32" ? "npm.cmd" : "npm";
const child = spawn(npm, ["exec", "--", "next", "dev", "-p", port], {
  env: { ...process.env, ...profileEnv },
  stdio: "inherit",
});

child.on("exit", (code, signal) => {
  if (signal) process.kill(process.pid, signal);
  else process.exit(code ?? 1);
});
