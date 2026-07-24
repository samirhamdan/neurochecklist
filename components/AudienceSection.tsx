import { CheckCircle2, XCircle } from "lucide-react";

/**
 * Para quem é / para quem não é — qualificação honesta. Copy oficial.
 */

const FOR_YOU = [
  "Você é psicólogo(a) e atende (ou quer atender) pacientes idosos",
  "Já sentiu insegurança diante de uma queixa de memória — sem saber se aprofunda, encaminha ou tranquiliza",
  "Quer estruturar sua triagem com critérios objetivos e referências brasileiras",
  "Quer se comunicar com geriatras e neurologistas em pé de igualdade técnica",
];

const NOT_FOR_YOU = [
  "Você busca um atalho para “dar diagnóstico” sem avaliação adequada — este material existe justamente para o oposto",
  "Espera um curso completo de neuropsicologia — este é um instrumento prático de triagem, não uma formação",
  "Não atende nem pretende atender população idosa",
];

export default function AudienceSection() {
  return (
    <section className="bg-slate-50">
      <div className="section-container section-padding">
        <h2 className="text-center text-2xl font-bold tracking-tight text-brand-950 sm:text-3xl">
          Este material é para você?
        </h2>

        <div className="mx-auto mt-14 grid max-w-4xl gap-6 md:grid-cols-2">
          <div className="surface-card border-accent-100 bg-accent-50/50 p-7">
            <h3 className="text-lg font-bold text-accent-800">
              É para você se:
            </h3>
            <ul className="mt-6 space-y-5">
              {FOR_YOU.map((item) => (
                <li
                  key={item}
                  className="flex gap-3.5 text-base leading-relaxed text-slate-700"
                >
                  <CheckCircle2
                    className="mt-0.5 h-6 w-6 shrink-0 fill-accent-600 text-white"
                    strokeWidth={2}
                    aria-hidden="true"
                  />
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="surface-card bg-white p-7">
            <h3 className="text-lg font-bold text-slate-700">
              Não é para você se:
            </h3>
            <ul className="mt-6 space-y-5">
              {NOT_FOR_YOU.map((item) => (
                <li
                  key={item}
                  className="flex gap-3.5 text-base leading-relaxed text-slate-600"
                >
                  <XCircle
                    className="mt-0.5 h-6 w-6 shrink-0 fill-slate-300 text-white"
                    strokeWidth={2}
                    aria-hidden="true"
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
