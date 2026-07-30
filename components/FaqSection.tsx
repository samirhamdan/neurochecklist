"use client";

import { faqItems } from "@/lib/site";

export default function FaqSection() {
  return (
    <section className="bg-paper py-[clamp(64px,9vw,120px)]" id="faq">
      <div className="wrap narrow rv">
        <span className="eyebrow">Dúvidas frequentes</span>
        <h2>Antes de decidir.</h2>
        <div className="mt-10">
          {faqItems.map((item, i) => (
            <details
              key={item.question}
              className="mb-3 border border-line bg-white transition-colors duration-200 hover:border-[#B9C2D4] open:border-amber"
              open={i === 0}
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-[18px] px-6 py-5 text-[1.02rem] font-medium text-ink [&::-webkit-details-marker]:hidden">
                {item.question}
                <span className="flex-none font-mono text-[1.3rem] text-amber-ink transition-transform duration-200 [[open]_&]:hidden">
                  +
                </span>
                <span className="hidden flex-none font-mono text-[1.3rem] text-amber-ink [[open]_&]:inline">
                  −
                </span>
              </summary>
              <p className="m-0 px-6 pb-[22px] text-[.97rem]">
                {item.answer}
              </p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
