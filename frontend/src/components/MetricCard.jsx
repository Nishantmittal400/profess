import React from "react";
import { warm } from "../lib/utils";
export default function MetricCard({ title, value, hint }){
  return (
    <div className={`${warm.card} p-5`}>
      <div className={`text-sm ${warm.sub}`}>{title}</div>
      <div className="text-2xl font-semibold mt-1">{value ?? "—"}</div>
      {hint && <div className={`text-xs ${warm.sub} mt-1`}>{hint}</div>}
    </div>
  );
}
