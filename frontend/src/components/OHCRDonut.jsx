import React from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import { warm } from "../lib/utils";

const COLORS = { O: "#fde047", H: "#fca5a5", C: "#fb7185", R: "#34d399", None: "#d1d5db" };

const OHCR_DEFS = [
  { key: "O", label: "Observe", description: "“What do we notice?”" },
  { key: "H", label: "Hypothesize", description: "“What could explain the observation?”" },
  { key: "C", label: "Challenge", description: "“Does this hypothesis hold up?”" },
  { key: "R", label: "Resolve", description: "“What have we learned?”" },
];

export default function OHCRDonut({ counts }){
  const data = Object.entries(counts || {}).map(([k,v]) => ({ name: k, value: v }))
    .filter(d => d.value > 0);

  return (
    <section className={`${warm.card} p-5 md:p-6`}>
      <div className="mb-3">
        <h3 className="font-semibold">OHCR Distribution</h3>
        <p className={`text-sm ${warm.sub}`}>Share of Observe / Hypothesize / Challenge / Resolve</p>
      </div>
      <div className="h-64">
        <ResponsiveContainer>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={60} outerRadius={90} paddingAngle={2}>
              {data.map((e, i) => (
                <Cell key={e.name} fill={COLORS[e.name] || "#ccc"} />
              ))}
            </Pie>
            <Tooltip formatter={(v, n) => [v, n]} />
          </PieChart>
        </ResponsiveContainer>
      </div>
      <div className="grid sm:grid-cols-2 gap-3 mt-4 text-xs leading-relaxed">
        {OHCR_DEFS.map(({ key, label, description }) => (
          <div key={key} className="flex items-start gap-2">
            <span className="inline-block w-3 h-3 mt-1 rounded" style={{ background: COLORS[key] }} />
            <div>
              <div className="font-semibold">{label}</div>
              <div className={`text-[11px] ${warm.sub}`}>{description}</div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
