import React from "react";
import { warm, ms } from "../lib/utils";

const SummaryCard = ({ title, value, hint }) => (
  <div className={`${warm.card} p-5`}>
    <div className={`text-sm ${warm.sub}`}>{title}</div>
    <div className="text-2xl font-semibold mt-1">{value}</div>
    {hint && <div className={`text-xs ${warm.sub} mt-1`}>{hint}</div>}
  </div>
);

const renderSequence = (seq = []) => seq.join(" → ");

export default function DiscourseAnalysis({ analysis }) {
  if (!analysis) {
    return null;
  }

  const { summary = {}, episodes = [], general_segments = [] } = analysis;

  return (
    <section className="grid gap-5">
      <div className="grid md:grid-cols-5 gap-4">
        <SummaryCard title="Acts Detected" value={summary.total_acts ?? 0} hint="Complete + partial sequences" />
        <SummaryCard title="Complete Acts" value={summary.complete_acts ?? 0} hint="Contain O→H→C→R" />
        <SummaryCard title="Partial Acts" value={summary.partial_acts ?? 0} hint="Missing one or more moves" />
        <SummaryCard title="Avg Quality" value={(summary.avg_quality_score ?? 0).toFixed(2)} hint="Coverage + confidence + flow" />
        <SummaryCard title="Avg Coverage" value={(summary.avg_coverage ?? 0).toFixed(2)} hint="Share of OHCR moves present" />
      </div>

      <section className={`${warm.card} p-5 md:p-6`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold">Discourse Acts</h3>
          <span className="text-xs text-stone-500">Ordered by timeline</span>
        </div>
        {episodes.length ? (
          <div className="rounded-xl border border-stone-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-stone-50 text-stone-500">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">#</th>
                  <th className="px-3 py-2 text-left font-medium">Start</th>
                  <th className="px-3 py-2 text-left font-medium">End</th>
                  <th className="px-3 py-2 text-left font-medium">Duration</th>
                  <th className="px-3 py-2 text-left font-medium">Sequence</th>
                  <th className="px-3 py-2 text-left font-medium">Quality</th>
                  <th className="px-3 py-2 text-left font-medium">Coverage</th>
                  <th className="px-3 py-2 text-left font-medium">Teacher</th>
                  <th className="px-3 py-2 text-left font-medium">Student</th>
                </tr>
              </thead>
              <tbody>
                {episodes.map((ep, idx) => (
                  <tr key={ep.id ?? idx} className="odd:bg-white even:bg-stone-50/60 align-top">
                    <td className="px-3 py-2 text-xs text-stone-500">{ep.id ?? idx + 1}</td>
                    <td className="px-3 py-2 text-xs">{ms(ep.start ?? 0)}</td>
                    <td className="px-3 py-2 text-xs">{ms(ep.end ?? 0)}</td>
                    <td className="px-3 py-2 text-xs">{ms(ep.duration ?? 0)}</td>
                    <td className="px-3 py-2 text-xs font-medium">{renderSequence(ep.sequence)}</td>
                    <td className="px-3 py-2 text-xs">{(ep.quality_score ?? 0).toFixed(2)}</td>
                    <td className="px-3 py-2 text-xs">{(ep.coverage ?? 0).toFixed(2)}</td>
                    <td className="px-3 py-2 text-xs">{ep.teacher_moves ?? 0}</td>
                    <td className="px-3 py-2 text-xs">{ep.student_moves ?? 0}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-sm text-stone-500">No complete OHCR acts detected in this recording.</div>
        )}
      </section>

      {general_segments.length ? (
        <section className={`${warm.card} p-5 md:p-6`}>
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold">General Discussion</h3>
            <span className="text-xs text-stone-500">
              {general_segments.length} segment{general_segments.length > 1 ? "s" : ""}
            </span>
          </div>
          <div className="grid gap-3 text-sm">
            {general_segments.map((seg, idx) => (
              <div key={`${seg.start}-${idx}`} className="rounded-xl border border-amber-100 bg-white/70 p-4">
                <div className="flex flex-wrap gap-3 text-xs text-stone-500">
                  <span>Segment #{idx + 1}</span>
                  <span>{ms(seg.start ?? 0)} → {ms(seg.end ?? 0)}</span>
                  <span>{seg.utterance_count ?? 0} utterances</span>
                </div>
                <ol className="mt-2 grid gap-1">
                  {(seg.utterances ?? []).slice(0, 5).map((u) => (
                    <li key={`${u.index}-${u.start}`} className="text-xs">
                      <span className="font-medium">{u.speaker || u.role}</span>: {u.text}
                    </li>
                  ))}
                  {(seg.utterances ?? []).length > 5 && (
                    <li className="text-xs text-stone-400">…</li>
                  )}
                </ol>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </section>
  );
}
