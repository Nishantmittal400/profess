import React from "react";
import Header from "./components/Header";
import Footer from "./components/Footer";
import Uploader from "./components/Uploader";
import MetricCard from "./components/MetricCard";
import TimelineChart from "./components/TimelineChart";
import OHCRDonut from "./components/OHCRDonut";
import JsonPanel from "./components/JsonPanel";
import ProcessingSteps from "./components/ProcessingSteps";
import CoachReport from "./components/CoachReport";
import { warm, prettyPct } from "./lib/utils";
import { processAudio } from "./lib/api";

export default function App(){
  const [file, setFile] = React.useState(null);
  const [busy, setBusy] = React.useState(false);
  const [step, setStep] = React.useState("idle");
  const [error, setError] = React.useState("");
  const [resp, setResp] = React.useState(null);

  async function onAnalyze(){
    if (!file) return;
    setError("");
    setBusy(true);
    setStep("upload");
    setResp(null);
    try {
      setStep("processing");
      const j = await processAudio(file);
      setResp(j);
      setStep("done");
    } catch (e) {
      setError(String(e.message || e));
      setStep("error");
    } finally {
      setBusy(false);
    }
  }

  const timeline = resp?.timeline ?? [];
  const m = resp?.metrics ?? {};
  const ohcrCounts = m?.ohcr_counts ?? {};
  const steps = resp?.steps ?? {};
  const coachAnalysis = steps.coach_analysis;
  const coachReport = resp?.coach_report ?? coachAnalysis?.report;

  return (
    <div className={`min-h-screen ${warm.bg} ${warm.text} antialiased`}>
      <Header />

      <main className="max-w-6xl mx-auto px-4 md:px-8 py-8 grid gap-6">
        <Uploader file={file} setFile={setFile} onAnalyze={onAnalyze} busy={busy} step={step} error={error} />

        {(step !== "idle" || busy || resp) && (
          <ProcessingSteps steps={steps} stepState={step} busy={busy} />
        )}

        {resp ? (
          <>
            <section className="grid gap-4">
              <div>
                <h3 className="text-lg font-semibold">Qualitative Assessment of Class</h3>
                <p className={`text-sm ${warm.sub}`}>Key discourse signals captured from the session.</p>
              </div>

              <div className="grid md:grid-cols-3 gap-4">
                <MetricCard title="Class Duration" value={m.class_duration_formatted || `${Math.round(resp.duration_sec ?? 0)}s`} hint="Total instruction time" />
                <MetricCard title="Teacher Talk" value={prettyPct(m.teacher_talk_pct)} hint="Share of speaking time" />
                <MetricCard title="Student Talk" value={prettyPct(m.student_talk_pct)} hint="Share of speaking time" />
              </div>

              <div className="grid md:grid-cols-4 gap-4">
                <MetricCard title="Number of Interactions" value={`${m.interaction_count ?? 0}`} hint="Back-and-forth exchanges between teacher and students" />
                <MetricCard title="Sub-Topics Covered" value={`${m.subtopic_count ?? 0}`} hint="Distinct concepts discussed" />
                <MetricCard title="Teacher Questions" value={`${m.teacher_question_count ?? 0}`} hint="Questions posed by instructor" />
                <MetricCard title="Student Questions" value={`${m.student_question_count ?? 0}`} hint="Questions raised by learners" />
              </div>

              <div className="grid md:grid-cols-4 gap-4">
                <MetricCard
                  title="Observations Shared"
                  value={`${m.observe_count ?? 0}`}
                  hint={m.observe_context || "“What do we notice?” Highlight concrete evidence."}
                />
                <MetricCard
                  title="Hypotheses Generated"
                  value={`${m.hypothesis_count ?? 0}`}
                  hint={m.hypothesis_context || "“What could explain the observation?”"}
                />
                <MetricCard
                  title="Challenges Raised"
                  value={`${m.challenge_count ?? 0}`}
                  hint={m.challenge_context || "“Does this hypothesis hold up?”"}
                />
                <MetricCard
                  title="Resolutions Provided"
                  value={`${m.resolution_count ?? 0}`}
                  hint={m.resolution_context || "“What have we learned?”"}
                />
              </div>

              <OHCRDonut counts={ohcrCounts} />
            </section>

            <TimelineChart data={timeline} />
            <CoachReport report={coachReport} />
            <JsonPanel data={resp} />
          </>
        ) : (
          <section className={`${warm.card} p-6`}>
            <div className="grid gap-3">
              <h3 className="font-semibold">How it works</h3>
              <ol className="list-decimal ml-5 text-sm text-stone-500 grid gap-1">
                <li>Upload an audio clip of a classroom discussion.</li>
                <li>We transcribe, diarize (separate speakers), and label each utterance with OHCR and IAM phases.</li>
                <li>We compute participation, back-and-forth interactions, questions, and a knowledge-construction timeline.</li>
                <li>Results appear below with a warm, friendly visual summary.</li>
              </ol>
            </div>
          </section>
        )}
      </main>

      <Footer />
    </div>
  );
}
