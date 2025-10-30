import React from "react";
import WaveSurfer from "wavesurfer.js";

export default function Waveform({ file, height = 72 }) {
  const containerRef = React.useRef(null);
  const wsRef = React.useRef(null);

  React.useEffect(() => {
    if (!file || !containerRef.current) return;
    if (wsRef.current) { wsRef.current.destroy(); wsRef.current = null; }

    const objectUrl = URL.createObjectURL(file);
    const ws = WaveSurfer.create({
      container: containerRef.current,
      height,
      waveColor: "#f59e0b",
      progressColor: "#fb7185",
      cursorWidth: 1,
      cursorColor: "#333",
      barWidth: 2,
      interact: false,
      normalize: true,
    });
    ws.load(objectUrl);
    wsRef.current = ws;

    return () => {
      if (wsRef.current) { wsRef.current.destroy(); wsRef.current = null; }
      URL.revokeObjectURL(objectUrl);
    };
  }, [file, height]);

  return <div ref={containerRef} className="w-full" />;
}
