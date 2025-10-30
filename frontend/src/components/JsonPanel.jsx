import React from "react";
import { warm } from "../lib/utils";
export default function JsonPanel({ data }){
  return (
    <details className={`${warm.card} p-5 md:p-6`}>
      <summary className="cursor-pointer font-medium">Raw Response JSON</summary>
      <pre className="mt-3 text-xs overflow-auto max-h-80 bg-stone-50 p-3 rounded-xl border border-stone-200">{JSON.stringify(data, null, 2)}</pre>
    </details>
  );
}
