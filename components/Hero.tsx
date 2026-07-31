import Image from "next/image";
import CtaButton from "./CtaButton";
import { site } from "@/lib/site";

const HEADLINES = {
  1: (
    <>
      Envelhecimento normal ou início de demência?{" "}
      <em className="italic text-amber">Pare de decidir no achismo.</em>
    </>
  ),
  2: (
    <>
      O protocolo de triagem neuropsicológica de quem ajudou a normatizar{" "}
      <em className="italic text-amber">os testes que você já usa.</em>
    </>
  ),
  3: (
    <>
      Da suspeita à conduta em 2 sessões:{" "}
      <em className="italic text-amber">
        um protocolo estruturado de triagem neuropsicológica.
      </em>
    </>
  ),
} as const;

const ACTIVE_HEADLINE: keyof typeof HEADLINES = 1;

const KIT_ITEMS = [
  { num: "01", label: "Guia Master de Triagem" },
  { num: "02", label: "Fluxograma de Decisão Clínica" },
  { num: "03", label: "Guia de Entrevista com o Familiar" },
  { num: "04", label: "Template de Relatório Técnico (Word)" },
  { num: "05", label: "Ficha de Evolução de Prontuário" },
];

export default function Hero() {
  return (
    <header className="relative overflow-hidden pt-[clamp(56px,7vw,90px)]" id="topo">
      <a id="conteudo" tabIndex={-1} />
      <div className="wrap grid items-center gap-16 lg:grid-cols-[1.15fr_.85fr]">
        <div>
          <span className="mb-7 inline-block rounded-full border border-line bg-white px-3.5 py-[7px] font-mono text-[.72rem] uppercase tracking-[.12em] text-ink-soft">
            Para psicólogos que atendem idosos
          </span>
          <h1>{HEADLINES[ACTIVE_HEADLINE]}</h1>
          <p className="mt-6 max-w-[52ch] text-[1.15rem]">
            Um protocolo estruturado de triagem neuropsicológica: critérios
            objetivos, fluxograma de decisão e modelos de documento — com
            parâmetros de referência para a população brasileira.
          </p>
          <div className="mt-9">
            <CtaButton location="hero">{site.cta.label}</CtaButton>
            <p className="micro">{site.cta.microcopy}</p>
          </div>
        </div>

        <div
          className="relative border border-line bg-white shadow-[0_24px_60px_-30px_rgba(15,23,43,.32)]"
        >
          <div className="border-b border-line bg-paper leading-[0]">
            <Image
              src="/capa-neurochecklist.webp"
              alt="Capa do Checklist de Triagem Neuropsicológica"
              width={461}
              height={600}
              priority
              className="block h-auto w-full max-h-[200px] object-cover object-top lg:max-h-none"
            />
          </div>
          <div className="bg-ink px-7 py-[26px]">
            <span className="font-mono text-[.7rem] uppercase tracking-[.18em] text-amber-soft">
              Kit clínico digital
            </span>
            <h3 className="mt-2 text-[1.7rem] text-white">
              Checklist de Triagem Neuropsicológica
            </h3>
            <p className="mt-1 text-[.9rem] text-[#A3AFC6]">
              Guia prático para psicólogos
            </p>
          </div>
          <ul className="list-none px-7 py-[22px]">
            {KIT_ITEMS.map((item, i) => (
              <li
                key={item.num}
                className={`flex gap-3 py-[11px] text-[.96rem] text-ink-soft ${
                  i < KIT_ITEMS.length - 1
                    ? "border-b border-dashed border-line"
                    : ""
                }`}
              >
                <span className="font-mono text-[.85rem] text-sage">
                  {item.num}
                </span>
                {item.label}
              </li>
            ))}
          </ul>
          <div className="absolute -bottom-3.5 -right-3.5 bg-amber px-4 py-2.5 font-mono text-[.72rem] uppercase tracking-[.1em] text-white">
            Aplicável em 2 sessões
          </div>
        </div>
      </div>
    </header>
  );
}
