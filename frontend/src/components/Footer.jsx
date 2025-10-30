import React from "react";
import { warm } from "../lib/utils";
export default function Footer(){
  return (
    <footer className="px-4 md:px-8 py-8">
      <div className={`max-w-6xl mx-auto text-xs ${warm.sub}`}>
        Built for educators • v0.1 • Ensure backend CORS allows this origin
      </div>
    </footer>
  );
}
