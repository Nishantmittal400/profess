import React from "react";
import { warm, prettyPct } from "../lib/utils";

export default function SpeakerBalanceBar({ teacherPct = 0, studentPct = 0 }){
  const t = Math.min(100, Math.max(0, Math.round(teacherPct * 100)));
  const s = 100 - t;
  return (
    <section className={`${warm.card} p-5 md:p-6`}>
      <h3 className="font-semibold mb-3">Speaker Balance</h3>
      <div className="text-sm mb-2 text-stone-600">% of total speaking time</div>
      <div className="w-full h-6 rounded-full bg-stone-100 overflow-hidden border border-stone-200">
        <div className="h-full bg-amber-300" style={{width: `${t}%`}} />
      </div>
      <div className="flex justify-between text-xs mt-2">
        <span>Teacher: {prettyPct(teacherPct)}</span>
        <span>Student: {prettyPct(studentPct)}</span>
      </div>
    </section>
  );
}
