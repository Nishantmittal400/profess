import React from "react";
import { warm } from "../lib/utils";

const SummaryCell = ({ label, value }) => (
  <div className={`${warm.card} p-4`}>
    <div className={`text-xs ${warm.sub}`}>{label}</div>
    <div className="text-xl font-semibold mt-1">{value}</div>
  </div>
);

export default function CoachReport({ report }) {
  if (!report) return null;

  const {
    transcript_meta: meta = {},
    moves = [],
    global_feedback: feedback = {},
  } = report;
  const topics = Array.isArray(report.topics) ? report.topics.filter((t) => typeof t === "string" && t.trim()) : [];
  const topicSummary = topics.length
    ? `This session focused on ${topics.slice(0, 3).join(", ")}${topics.length > 3 ? ", and related concepts" : ""}. Encourage students to revisit these sub-topics and connect them to upcoming lessons.`
    : "";

  const rubric = feedback.rubric_flags || {};

  return (
    <section className="grid gap-5">
      <div className="grid sm:grid-cols-3 gap-4">
        <SummaryCell label="Turns Analyzed" value={meta.num_turns ?? 0} />
        <SummaryCell
          label="Observation Present"
          value={(meta.has_observe ? "Yes" : "No")}
        />
        <SummaryCell
          label="Knowledge Question"
          value={(meta.has_knowledge_question ? "Yes" : "No")}
        />
      </div>

      {topics.length ? (
        <section className={`${warm.card} p-5 md:p-6`}>
          <h3 className="font-semibold mb-2">Sub-Topics Highlighted</h3>
          <ul className="flex flex-wrap gap-2 text-sm">
            {topics.map((topic, idx) => (
              <li key={`${topic}-${idx}`} className="px-3 py-1 rounded-full border border-amber-200 bg-amber-50/70">
                {topic}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <section className={`${warm.card} p-5 md:p-6`}>
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold">Discourse Moves</h3>
          <span className="text-xs text-stone-500">
            {moves.length} move{moves.length === 1 ? "" : "s"}
          </span>
        </div>
        {moves.length ? (
          <div className="rounded-xl border border-stone-200 overflow-hidden">
            <table className="w-full text-sm">
              <thead className="bg-stone-50 text-stone-500">
                <tr>
                  <th className="px-3 py-2 text-left font-medium">Move</th>
                  <th className="px-3 py-2 text-left font-medium">Turns</th>
                  <th className="px-3 py-2 text-left font-medium">Speakers</th>
                  <th className="px-3 py-2 text-left font-medium w-1/2">Summary</th>
                  <th className="px-3 py-2 text-left font-medium">Act</th>
                  <th className="px-3 py-2 text-left font-medium">OHCR</th>
                  <th className="px-3 py-2 text-left font-medium w-1/3">Coach Note</th>
                </tr>
              </thead>
              <tbody>
                {moves.map((mv) => (
                  <tr key={mv.move_id} className="odd:bg-white even:bg-stone-50/60 align-top">
                    <td className="px-3 py-2 text-xs font-semibold">{mv.move_id}</td>
                    <td className="px-3 py-2 text-xs">{mv.turn_range}</td>
                    <td className="px-3 py-2 text-xs">{(mv.speakers || []).join(", ")}</td>
                    <td className="px-3 py-2 text-xs">{mv.utterance_summary}</td>
                    <td className="px-3 py-2 text-xs capitalize">{mv.discourse_act}</td>
                    <td className="px-3 py-2 text-xs uppercase">{mv.ohcr}</td>
                    <td className="px-3 py-2 text-xs">{mv.coach_notes}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-sm text-stone-500">
            No discourse moves detected for this transcript.
          </div>
        )}
      </section>

      <section className={`${warm.card} p-5 md:p-6 grid gap-3`}>
        <h3 className="font-semibold">Suggestions to Improve Teaching</h3>
        {feedback.diagnosis && (
          <div>
            <div className="text-xs font-medium text-stone-500 uppercase tracking-wide">Diagnosis</div>
            <p className="text-sm mt-1">{feedback.diagnosis}</p>
          </div>
        )}

        {(feedback.improvements || []).length ? (
          <div>
            <div className="text-xs font-medium text-stone-500 uppercase tracking-wide">Improvements</div>
            <ul className="list-disc ml-5 mt-1 text-sm grid gap-1">
              {feedback.improvements.map((tip, idx) => (
                <li key={idx}>{tip}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {topicSummary && (
          <div>
            <div className="text-xs font-medium text-stone-500 uppercase tracking-wide">Topic Context</div>
            <p className="text-sm mt-1">{topicSummary}</p>
          </div>
        )}

        {feedback.next_time_observe_script && (
          <div>
            <div className="text-xs font-medium text-stone-500 uppercase tracking-wide">
              Next-Time Observe Script
            </div>
            <blockquote className="mt-1 text-sm rounded-xl border-l-4 border-amber-400 bg-amber-50/80 p-3">
              {feedback.next_time_observe_script}
            </blockquote>
          </div>
        )}

        {Object.keys(rubric).length ? (
          <div>
            <div className="text-xs font-medium text-stone-500 uppercase tracking-wide">
              Rubric Flags
            </div>
            <ul className="grid sm:grid-cols-2 gap-2 mt-2 text-xs">
              {Object.entries(rubric).map(([key, val]) => (
                <li
                  key={key}
                  className={`rounded-lg border px-3 py-2 ${
                    val ? "border-emerald-200 bg-emerald-50/70 text-emerald-700" : "border-amber-200 bg-amber-50/60 text-amber-700"
                  }`}
                >
                  <span className="font-medium mr-2">{val ? "✔" : "✻"}</span>
                  {key.replace(/_/g, " ")}
                </li>
              ))}
            </ul>
          </div>
        ) : null}
      </section>
    </section>
  );
}
