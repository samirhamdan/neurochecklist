import { CheckCircle2 } from "lucide-react";
import CtaButton from "./CtaButton";
import { site } from "@/lib/site";

/**
 * ============================================================
 * HEADLINE — TESTE A/B
 * Três variações prontas. Ative UMA trocando ACTIVE_HEADLINE.
 *
 * 1 (dor → segurança):
 *    "Envelhecimento normal ou início de demência? Pare de decidir no achismo."
 * 2 (autoridade):
 *    "O protocolo de triagem neuropsicológica de quem ajudou a normatizar
 *     os testes que você já usa."
 * 3 (método/tempo):
 *    "Da suspeita à conduta em 2 sessões: um protocolo estruturado de
 *     triagem neuropsicológica."
 * ============================================================
 */
const HEADLINES = {
  1: (
    <>
      Envelhecimento normal ou início de demência?{" "}
      <span className="text-accent-600">Pare de decidir no achismo.</span>
    </>
  ),
  2: (
    <>
      O protocolo de triagem neuropsicológica de quem ajudou a normatizar{" "}
      <span className="text-accent-600">os testes que você já usa.</span>
    </>
  ),
  3: (
    <>
      Da suspeita à conduta em 2 sessões:{" "}
      <span className="text-accent-600">
        um protocolo estruturado de triagem neuropsicológica.
      </span>
    </>
  ),
} as const;

const ACTIVE_HEADLINE: keyof typeof HEADLINES = 1;

export default function Hero() {
  return (
    <section className="relative overflow-hidden bg-gradient-to-b from-brand-50 via-brand-50/60 to-white">
      {/* Fundo gráfico sutil — gradiente radial + formas orgânicas, decorativo */}
      <div
        className="pointer-events-none absolute inset-0 z-0 bg-hero-glow"
        aria-hidden="true"
      />
      <svg
        className="pointer-events-none absolute -right-24 -top-24 z-0 h-[28rem] w-[28rem] text-brand-200/40"
        viewBox="0 0 200 200"
        fill="currentColor"
        aria-hidden="true"
      >
        <path d="M45.3,-59.6C58.5,-51.6,68.5,-37.4,72.8,-21.6C77.1,-5.9,75.7,11.4,68.6,26C61.5,40.6,48.7,52.5,34,60.6C19.3,68.7,2.7,73,-13.8,71.1C-30.3,69.2,-46.7,61.1,-57.9,48.1C-69.1,35.1,-75.1,17.6,-74.6,0.5C-74.1,-16.6,-67.1,-33.2,-55.7,-41.9C-44.3,-50.6,-28.5,-51.4,-13.5,-56.1C1.5,-60.9,17.1,-69.5,45.3,-59.6Z" transform="translate(100 100)" />
      </svg>
      <svg
        className="pointer-events-none absolute -left-16 bottom-0 z-0 h-72 w-72 text-accent-100/60"
        viewBox="0 0 200 200"
        fill="currentColor"
        aria-hidden="true"
      >
        <circle cx="100" cy="100" r="100" />
      </svg>

      <div className="section-container relative z-10 grid items-center gap-10 py-16 sm:py-24 lg:grid-cols-2 lg:gap-14">
        <div>
          <p className="mb-4 inline-block rounded-full bg-brand-100 px-4 py-1.5 text-sm font-medium text-brand-800">
            Para psicólogos que atendem idosos
          </p>
          <h1 className="text-3xl font-bold leading-tight tracking-tight text-brand-950 sm:text-4xl lg:text-5xl">
            {HEADLINES[ACTIVE_HEADLINE]}
          </h1>
          <p className="mt-5 text-lg leading-relaxed text-slate-600 sm:text-xl">
            Um guia prático para psicólogos que atendem idosos: critérios
            objetivos, fluxograma de decisão e modelos de documento — com
            parâmetros validados para a população brasileira.
          </p>
          <div className="mt-8 flex flex-col items-start gap-3">
            <CtaButton location="hero">{site.cta.label}</CtaButton>
            <p className="text-sm text-slate-500">{site.cta.microcopy}</p>
          </div>
        </div>

        {/*
          [PREENCHER] Imagem do produto (mockup do kit).
          Substitua o placeholder abaixo por um mockup 3D real em
          /public/mockup-kit.webp e use next/image:

          <Image src="/mockup-kit.webp" alt="Kit NeuroChecklist: Guia Master,
            Fluxograma de Decisão Clínica e bônus" width={620} height={520}
            priority className="w-full" />
        */}
        <div
          className="relative mx-auto w-full max-w-md lg:max-w-none"
          aria-hidden="true"
        >
          <div className="rotate-1 rounded-2xl border border-brand-100 bg-white p-6 shadow-2xl shadow-brand-900/15 transition-transform duration-300 hover:rotate-0">
            <div className="rounded-xl bg-gradient-to-br from-brand-900 to-brand-800 p-6 text-white">
              <p className="text-xs uppercase tracking-widest text-brand-300">
                Kit clínico digital
              </p>
              <p className="mt-2 text-2xl font-bold leading-snug">
                Checklist de Triagem Neuropsicológica
              </p>
              <p className="mt-1 text-sm text-brand-200">
                Guia Prático para Psicólogos
              </p>
            </div>
            <ul className="mt-5 space-y-2.5 text-sm text-slate-600">
              {[
                "Guia Master Completo",
                "Fluxograma de Decisão Clínica",
                "+ 3 bônus de aplicação imediata",
              ].map((item) => (
                <li key={item} className="flex items-center gap-2.5">
                  <CheckCircle2
                    className="h-5 w-5 shrink-0 text-accent-600"
                    strokeWidth={2}
                  />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
