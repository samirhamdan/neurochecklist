"use client";

import { useEffect, useRef } from "react";

export default function Nav() {
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const bar = barRef.current;
    if (!bar) return;

    const onScroll = () => {
      const d = document.documentElement;
      const pct = d.scrollTop / (d.scrollHeight - d.clientHeight);
      bar.style.width = `${(pct * 100).toFixed(1)}%`;
    };

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav className="sticky top-0 z-50 border-b border-line bg-[rgba(246,247,245,.88)] backdrop-blur-[10px]">
      <div
        ref={barRef}
        className="absolute bottom-[-1px] left-0 h-[2px] w-0 bg-amber-ink"
      />
      <div className="wrap flex h-16 items-center justify-between">
        <a
          href="#topo"
          className="font-mono text-[.85rem] tracking-[.1em] text-ink no-underline"
        >
          NEURO<b className="font-medium text-amber">CHECKLIST</b>
        </a>
        <a
          href="#adquirir"
          className="hidden border border-ink bg-transparent px-5 py-[11px] text-[.9rem] font-medium text-ink no-underline transition-all duration-[.18s] hover:-translate-y-0.5 hover:border-ink hover:bg-ink hover:text-paper-warm sm:inline-block"
          style={{ borderRadius: 2 }}
        >
          Adquirir o protocolo
        </a>
      </div>
    </nav>
  );
}
