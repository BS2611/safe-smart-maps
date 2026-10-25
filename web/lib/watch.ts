// Heart-rate check basics (stretch). Types follow CONTRACTS.md "Watch relay endpoints".
// Readings live in memory only: nothing here touches storage. The real Galaxy Watch source
// (Wear OS app -> backend relay -> SSE) will implement ReadingSource later.

export type WatchSource = "wearos" | "band" | "simulated";

export type WatchReading = { bpm: number; ts: string; source: WatchSource };

export interface ReadingSource {
  start(onReading: (reading: WatchReading) => void): void;
  stop(): void;
}

export const SIMULATED_RANGE = { min: 70, max: 110 } as const;
export const SIMULATED_START_BPM = 85;
export const SIMULATED_INTERVAL_MS = 2000;

const LABELS: Record<WatchSource, string> = {
  wearos: "Galaxy Watch",
  band: "Bluetooth band",
  simulated: "Simulated",
};

export function sourceLabel(source: WatchSource): string {
  return LABELS[source];
}

export function isSimulated(source: WatchSource): boolean {
  return source === "simulated";
}

/** Small random step, kept inside the simulated range. `rng` returns 0..1. */
export function nextSimulatedBpm(prev: number, rng: () => number = Math.random): number {
  const step = Math.round((rng() - 0.5) * 6);
  return Math.min(SIMULATED_RANGE.max, Math.max(SIMULATED_RANGE.min, prev + step));
}

export function createSimulatedSource(
  opts: { intervalMs?: number; rng?: () => number; now?: () => Date } = {},
): ReadingSource {
  const { intervalMs = SIMULATED_INTERVAL_MS, rng = Math.random, now = () => new Date() } = opts;
  let timer: ReturnType<typeof setInterval> | null = null;
  return {
    start(onReading) {
      if (timer) return;
      let bpm = SIMULATED_START_BPM;
      const emit = () => onReading({ bpm, ts: now().toISOString(), source: "simulated" });
      emit();
      timer = setInterval(() => {
        bpm = nextSimulatedBpm(bpm, rng);
        emit();
      }, intervalMs);
    },
    stop() {
      if (timer) clearInterval(timer);
      timer = null;
    },
  };
}

export const UNSUPPORTED_INPUT_TEXT =
  "Heart-rate input is not supported on this browser. Use a paired watch or the simulated reading.";
