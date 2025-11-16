import React from "react";
import { warm, prettyMs } from "../lib/utils";

const TableBlock = ({ table }) => {
  if (!table || !Array.isArray(table.headers) || !Array.isArray(table.rows)) return null;
  return (
    <div className="overflow-auto rounded-xl border border-stone-200">
      <table className="w-full text-xs">
        <thead className="bg-stone-50">
          <tr>
            {table.headers.map((h, idx) => (
              <th key={`${h}-${idx}`} className="px-3 py-2 text-left font-semibold uppercase tracking-wide text-[11px] text-stone-500">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, ridx) => (
            <tr key={`row-${ridx}`} className={ridx % 2 === 0 ? "bg-white" : "bg-stone-50/70"}>
              {row.map((cell, cidx) => (
                <td key={`cell-${ridx}-${cidx}`} className="px-3 py-2 align-top">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {(table.notes || []).length ? (
        <div className="px-3 py-2 text-[11px] text-stone-500 border-t border-stone-200">
          {(table.notes || []).map((note, idx) => (
            <div key={`note-${idx}`}>{note}</div>
          ))}
        </div>
      ) : null}
    </div>
  );
};

const ExamplesBlock = ({ examples }) => {
  if (!Array.isArray(examples) || !examples.length) return null;
  return (
    <div className="grid gap-3">
      {examples.map((ex, idx) => (
        <div key={`example-${idx}`} className="rounded-xl border border-amber-200 bg-amber-50/70 p-3">
          <div className="text-xs font-semibold text-amber-700">{ex.label}</div>
          <blockquote className="text-sm mt-1 whitespace-pre-line">
            {(ex.quote || []).join("\n")}
          </blockquote>
          {ex.annotation ? <div className="text-xs text-stone-600 mt-1">{ex.annotation}</div> : null}
        </div>
      ))}
    </div>
  );
};

const SectionBlock = ({ section }) => {
  if (!section) return null;
  const paragraphs = Array.isArray(section.paragraphs) ? section.paragraphs : [];
  const bullets = Array.isArray(section.bullets) ? section.bullets : [];
  return (
    <div className="grid gap-2">
      <h5 className="text-sm font-semibold uppercase tracking-wide text-stone-600">{section.title}</h5>
      {paragraphs.map((p, idx) => (
        <p key={`para-${idx}`} className="text-sm leading-relaxed">
          {p}
        </p>
      ))}
      {bullets.length ? (
        <ul className="list-disc pl-5 text-sm text-stone-700 space-y-1">
          {bullets.map((item, idx) => (
            <li key={`bullet-${idx}`}>{item}</li>
          ))}
        </ul>
      ) : null}
      <TableBlock table={section.table} />
      <ExamplesBlock examples={section.examples} />
    </div>
  );
};

function normalizeOutput(output) {
  if (!output) return null;
  if (typeof output === "object") return output;
  try {
    return JSON.parse(output);
  } catch (err) {
    return {
      summary: typeof output === "string" ? output : "Unstructured tier output",
      sections: [
        {
          title: "Raw Output",
          paragraphs: [String(output)],
        },
      ],
      reliability_flags: [],
      notes: [],
    };
  }
}

function TierCard({ tier }) {
  const { title, id, description, output, duration_ms: duration, meta = {} } = tier;
  const structured = normalizeOutput(output) || { sections: [] };
  const sections = Array.isArray(structured.sections) ? structured.sections : [];
  const reliability = Array.isArray(structured.reliability_flags) ? structured.reliability_flags : [];
  const notes = Array.isArray(structured.notes) ? structured.notes : [];

  return (
    <article className={`${warm.card} p-5 md:p-6 grid gap-4`}>
      <header className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
        <div>
          <h4 className="font-semibold text-base">{title || id}</h4>
          {description ? <p className={`text-sm ${warm.sub}`}>{description}</p> : null}
          {structured.summary ? <p className="text-sm mt-2 text-stone-700">{structured.summary}</p> : null}
        </div>
        <div className="text-xs text-stone-500 text-right space-y-1">
          {duration != null ? <div>Runtime: {prettyMs(duration)}</div> : null}
          {meta.ptoks != null || meta.ctoks != null ? (
            <div>
              {meta.ptoks != null ? `Prompt: ${meta.ptoks} · ` : ""}
              {meta.ctoks != null ? `Completion: ${meta.ctoks}` : ""}
            </div>
          ) : null}
          {meta.source ? <div>Source: {meta.source}</div> : null}
        </div>
      </header>

      <div className="grid gap-4">
        {sections.map((section, idx) => (
          <SectionBlock key={`${tier.id}-section-${idx}`} section={section} />
        ))}
      </div>

      {reliability.length ? (
        <div className="rounded-xl border border-amber-200 bg-amber-50/70 p-3 text-xs text-amber-800">
          <div className="font-semibold uppercase tracking-wide text-[11px]">Reliability Flags</div>
          <ul className="mt-1 list-disc pl-4 space-y-1">
            {reliability.map((flag, idx) => (
              <li key={`flag-${idx}`}>{flag}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {notes.length ? (
        <div className="text-xs text-stone-500">
          {notes.map((note, idx) => (
            <div key={`note-${idx}`}>{note}</div>
          ))}
        </div>
      ) : null}
    </article>
  );
}

export default function TierReports({ tiers = [], transcript }) {
  if (!tiers.length) return null;

  return (
    <section className="grid gap-4">
      <div>
        <h3 className="text-lg font-semibold">Tiered Transcript Analyses</h3>
        <p className={`text-sm ${warm.sub}`}>Outputs from Tier 1–3 prompts, rendered exactly as produced by the LLM.</p>
      </div>

      <div className="grid gap-4">
        {tiers.map((tier) => (
          <TierCard key={tier.id} tier={tier} />
        ))}
      </div>

      {transcript ? (
        <details className={`${warm.card} p-5 md:p-6`}>
          <summary className="cursor-pointer font-semibold text-sm">Transcript sent to tier prompts</summary>
          <pre className="mt-3 text-sm whitespace-pre-wrap bg-stone-50 border border-stone-200 rounded-xl p-3 max-h-[320px] overflow-auto">
            {transcript}
          </pre>
        </details>
      ) : null}
    </section>
  );
}
