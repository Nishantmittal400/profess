import React from "react";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts";
import { warm, ms } from "../lib/utils";

export default function TimelineChart({ data }){
  return (
    <section className={`${warm.card} p-5 md:p-6`}>
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="font-semibold">Knowledge Construction over Time</h3>
          <p className={`text-sm ${warm.sub}`}>Higher bands (4–5) indicate deeper reasoning/resolve</p>
        </div>
      </div>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, bottom: 0, left: 0 }}>
            <defs>
              <linearGradient id="kcs" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.5} />
                <stop offset="95%" stopColor="#fb7185" stopOpacity={0.2} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(0,0,0,0.06)" />
            <XAxis dataKey="time" tickFormatter={(v) => ms(v)} tick={{ fontSize: 12 }} />
            <YAxis domain={[1, 5]} tickCount={5} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v, n) => (n === "level" ? [`Level ${v}`, "Level"] : v)} labelFormatter={(l) => `t=${ms(l)}`} />
            <ReferenceLine y={3} stroke="#94a3b8" strokeDasharray="4 4" />
            <Area type="monotone" dataKey="level" stroke="#f59e0b" fill="url(#kcs)" strokeWidth={2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
