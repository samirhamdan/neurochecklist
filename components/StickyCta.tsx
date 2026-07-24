"use client";

import { useEffect, useState } from "react";
import CtaButton from "./CtaButton";
import { site } from "@/lib/site";

/**
 * CTA fixo no mobile — aparece após o primeiro scroll (~1 altura de tela)
 * e some no desktop (md:hidden). Some também quando a oferta final está
 * visível, para não duplicar o CTA na mesma tela.
 */
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

    const offer = document.getElementById("oferta");
    const observer = offer
      ? new IntersectionObserver(
          ([entry]) => {
            offerVisible = entry.isIntersecting;
            update();
          },
          { threshold: 0.15 }
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
      className={`fixed inset-x-0 bottom-0 z-50 border-t border-slate-200 bg-white/95 px-4 py-3 shadow-[0_-4px_16px_rgba(0,0,0,0.08)] backdrop-blur transition-transform duration-300 md:hidden ${
        visible ? "translate-y-0" : "translate-y-full"
      }`}
      aria-hidden={!visible}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="text-sm font-bold text-brand-950">{site.price.full}</p>
          <p className="truncate text-xs text-slate-500">
            ou {site.price.installments} · Garantia de {site.guaranteeDays} dias
          </p>
        </div>
        <CtaButton location="sticky-mobile" size="md" className="shrink-0">
          Quero o protocolo
        </CtaButton>
      </div>
    </div>
  );
}
