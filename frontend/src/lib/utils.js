export const warm = {
  bg: "bg-amber-50",
  card: "bg-white/90 backdrop-blur shadow-lg rounded-2xl",
  accent: "from-amber-300 via-rose-200 to-pink-200",
  text: "text-stone-800",
  sub: "text-stone-500",
  ring: "ring-amber-300/60",
};

export const prettyPct = (x) => `${Math.round((x ?? 0) * 100)}%`;
export const ms = (s) => `${Math.round(s)}s`;
export const prettyMs = (value) => {
  const msValue = Number.isFinite(value) ? value : 0;
  if (msValue < 1000) return `${msValue|0} ms`;
  const seconds = msValue / 1000;
  if (seconds < 60) return `${seconds.toFixed(seconds >= 10 ? 1 : 2)} s`;
  const minutes = Math.floor(seconds / 60);
  const rem = seconds % 60;
  return `${minutes}m ${rem.toFixed(rem >= 10 ? 0 : 1)}s`;
};
