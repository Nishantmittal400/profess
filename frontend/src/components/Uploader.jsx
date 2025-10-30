import React from "react";
import { warm } from "../lib/utils";
import Waveform from "./Waveform";

export default function Uploader({ file, setFile, onAnalyze, busy, step, error }) {
  const inputRef = React.useRef(null);
  const [drag, setDrag] = React.useState(false);

  const onPick = (e) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const onDrop = (e) => {
    e.preventDefault(); setDrag(false);
    const f = e.dataTransfer.files?.[0]; if (f) setFile(f);
  };

  return (
    <section className={`${warm.card} p-5 md:p-6`}>
      <div className="grid md:grid-cols-2 gap-6">
        <div>
          <h2 className="text-lg font-semibold">Upload audio</h2>
          <p className={`text-sm ${warm.sub}`}>Drag & drop or choose a file (m4a/mp3/wav/webm)</p>

          <div
            onDragOver={(e)=>{e.preventDefault(); setDrag(true);}}
            onDragLeave={()=>setDrag(false)}
            onDrop={onDrop}
            className={`mt-3 border-2 ${drag ? 'border-amber-400' : 'border-dashed border-amber-200'} rounded-2xl p-6 text-center bg-white/70`}
          >
            {!file ? (
              <>
                <div className="text-sm">Drop file here</div>
                <div className={`text-xs mt-1 ${warm.sub}`}>or</div>
                <button
                  className={`mt-3 px-3 py-2 rounded-xl text-sm font-medium text-stone-900 bg-gradient-to-r ${warm.accent} shadow`}
                  onClick={() => inputRef.current?.click()}
                >Choose File</button>
                <input ref={inputRef} type="file" accept="audio/*" onChange={onPick} hidden />
              </>
            ) : (
              <div className="grid gap-2">
                <div className="text-sm font-medium">{file.name}</div>
                <Waveform file={file} />
                <div className="flex gap-2 justify-center mt-2">
                  <button
                    onClick={onAnalyze}
                    disabled={busy}
                    className={`px-4 py-2 rounded-xl text-sm font-medium text-stone-900 bg-gradient-to-r ${warm.accent} shadow disabled:opacity-60`}
                  >{busy ? (step === 'processing' ? 'Processing…' : 'Uploading…') : 'Analyze'}</button>
                  <button
                    onClick={()=>setFile(null)}
                    className="px-3 py-2 rounded-xl text-sm border border-stone-200 bg-white/80 hover:bg-white"
                  >Clear</button>
                </div>
              </div>
            )}
          </div>
          {error && (
            <div className="mt-3 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-xl p-3">
              <strong>Error:</strong> {error}
            </div>
          )}
          {busy && (
            <div className="mt-3 flex items-center gap-3 text-sm">
              <span className="inline-flex h-2 w-2 rounded-full bg-amber-400 animate-pulse" />
              <span>
                {step === "upload" && "Uploading audio…"}
                {step === "processing" && "Transcribing, diarizing, labeling, computing metrics…"}
              </span>
            </div>
          )}
        </div>

        <div className="grid content-start gap-3">
          <div className="text-sm font-medium">Preview</div>
          <div className={`${warm.card} p-4`}>
            {file ? <Waveform file={file} height={96} /> : <div className={`text-sm ${warm.sub}`}>No file selected</div>}
          </div>
        </div>
      </div>
    </section>
  );
}
