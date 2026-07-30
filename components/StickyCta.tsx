"use client";

import { useEffect, useState } from "react";
import { site } from "@/lib/site";
import CtaButton from "./CtaButton";

export default function StickyCta() {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    let offerVisible = false;
    let scrolled = false;

    const update = () => setVisible(scrolled && !offerVisible);

    const onScroll = () => {
      scrolled = window.scrollY > window.innerHeight * 0.8;
      update();
    };

    const offer = document.getElementById("adquirir");
    const observer = offer
      ? new IntersectionObserver(
          ([entry]) => {
            offerVisible = entry.isIntersecting;
            update();
          },
          { threshold: 0.18 }
        )
      : null;
    if (offer && observer) observer.observe(offer);

    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    return () => {
      window.removeEventListener("scroll", onScroll);
      observer?.disconnect();
    };
  }, []);

  return (
    <div
      className={`fixed inset-x-0 bottom-0 z-[60] hidden items-center justify-between gap-3.5 border-t border-line bg-white px-4 py-3 shadow-[0_-8px_24px_-12px_rgba(15,23,43,.28)] transition-transform duration-[.25s] max-[900px]:flex ${
        visible ? "translate-y-0" : "translate-y-[120%]"
      }`}
      aria-hidden={!visible}
    >
      <div className="font-mono text-[.8rem] text-ink">
        {site.price.full}{" "}
        <span className="opacity-60">· {site.price.installments}</span>
      </div>
      <CtaButton location="sticky-mobile" size="md" className="shrink-0">
        Quero o protocolo
      </CtaButton>
    </div>
  );
}
