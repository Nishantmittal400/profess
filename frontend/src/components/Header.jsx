import React from "react";
import { warm } from "../lib/utils";
import { getApiBase, setApiBase } from "../lib/api";

export default function Header() {
  const [v, setV] = React.useState(getApiBase());
  return (
    <header className="sticky top-0 z-10 border-b border-amber-200/60 bg-gradient-to-r from-amber-100 via-rose-50 to-pink-50/70 backdrop-blur px-4 md:px-8 py-4">
      <div className="max-w-6xl mx-auto flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-br from-amber-400 to-rose-300 shadow" />
          <div>
            <h1 className="text-xl font-semibold">Make Teaching Great Again</h1>
            <p className={`text-xs md:text-sm ${warm.sub}`}>Transcribe → Diarize → Label → Coach</p>
          </div>
        </div>
        <div className="hidden md:flex items-center gap-2">
          <label className="text-sm mr-2">API</label>
          <input
            className={`px-3 py-2 text-sm rounded-xl border border-amber-200/80 bg-white/80 focus:outline-none focus:ring-2 ${warm.ring}`}
            value={v}
            onChange={(e) => setV(e.target.value)}
            onBlur={() => setApiBase(v)}
            placeholder="http://127.0.0.1:8000"
          />
        </div>
      </div>
    </header>
  );
}
