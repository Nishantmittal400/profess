# OHCR Frontend (Vite + React + Tailwind)

Modern warm UI with drag/drop + waveform preview, OHCR donut, speaker balance bar, and timeline chart.

## Run locally
```bash
npm install
npm run dev
```
Backend should be running at `http://127.0.0.1:8000` (you can edit in the header field).

## Build
```bash
npm run build && npm run preview
```

## Notes
- Waveform preview uses **wavesurfer.js**; it renders from a Blob URL (no upload).
- Charts are built with **recharts**.
- Tailwind provides the warm, soft aesthetic.
