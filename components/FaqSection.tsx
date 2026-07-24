import { ChevronDown } from "lucide-react";
import { faqItems } from "@/lib/site";

/**
 * FAQ — acordeão nativo (<details>), acessível por teclado e sem JavaScript.
 * As perguntas/respostas vêm de lib/site.ts (também usadas no JSON-LD FAQPage).
 */
export default function FaqSection() {
  return (
    <section className="bg-white" id="faq">
      <div className="section-container section-padding">
        <h2 className="text-center text-2xl font-bold tracking-tight text-brand-950 sm:text-3xl">
          Perguntas frequentes
        </h2>

        <div className="mx-auto mt-12 max-w-3xl space-y-4">
          {faqItems.map((item) => (
            <details
              key={item.question}
              className="surface-card group px-6 py-5 open:shadow-lg"
            >
              <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-base font-semibold text-brand-950 marker:hidden [&::-webkit-details-marker]:hidden">
                {item.question}
                <ChevronDown
                  className="h-5 w-5 shrink-0 text-brand-400 transition-transform duration-200 group-open:rotate-180"
                  aria-hidden="true"
                />
              </summary>
              <p className="mt-3 text-base leading-relaxed text-slate-600">
                {item.answer}
              </p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
