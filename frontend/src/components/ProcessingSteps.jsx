import React from "react";
import { warm, prettyMs } from "../lib/utils";

const STEP_ORDER = [
  { key: "transcription", label: "Transcription" },
  { key: "diarization", label: "Diarization" },
  { key: "labeling", label: "LLM Labeling" },
  { key: "metrics", label: "Metrics" },
  { key: "coach_analysis", label: "Coach Report" },
];

const STATUS_ICON = {
  done: "✓",
  active: "…",
  pending: "",
  error: "!",
};

export default function ProcessingSteps({ steps = {}, stepState, busy }) {
  const firstIncomplete = STEP_ORDER.find(({ key }) => !steps[key]);

  return (
    <section className={`${warm.card} p-5 md:p-6`}>
      <h3 className="font-semibold mb-3">Processing Steps</h3>
      <ul className="grid gap-3">
        {STEP_ORDER.map(({ key, label }) => {
          const detail = steps[key];
          let status = "pending";
          if (detail) {
            status = "done";
          } else if (stepState === "error") {
            status = firstIncomplete?.key === key ? "error" : "pending";
          } else if (busy && firstIncomplete?.key === key) {
            status = "active";
          }

          const icon = STATUS_ICON[status];
          const duration = detail?.duration_ms;

          return (
            <li
              key={key}
              className={`flex items-start gap-3 rounded-xl border border-amber-100/70 px-3 py-3 ${
                status === "done"
                  ? "bg-emerald-50/60 border-emerald-200 text-emerald-800"
                  : status === "active"
                  ? "bg-amber-50/80 border-amber-200 text-amber-700"
                  : status === "error"
                  ? "bg-rose-50/70 border-rose-200 text-rose-700"
                  : "bg-white/70 text-stone-700"
              }`}
            >
              <span className="mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full border border-current text-sm">
                {icon}
              </span>
              <div className="flex-1">
                <div className="text-sm font-medium">{label}</div>
                <div className="text-xs text-stone-600">
                  {status === "done" && duration != null
                    ? `Completed in ${prettyMs(duration)}`
                    : status === "active"
                    ? "Running…"
                    : status === "error"
                    ? "Encountered an error"
                    : "Waiting"}
                </div>
              </div>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
