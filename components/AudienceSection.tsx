const FOR_YOU = [
  "Você é psicólogo(a) e atende — ou quer atender — pacientes idosos",
  "Já sentiu insegurança diante de uma queixa de memória, sem saber se aprofunda, encaminha ou tranquiliza",
  "Quer estruturar sua triagem com critérios objetivos e referências brasileiras",
  "Quer se comunicar com geriatras e neurologistas em pé de igualdade técnica",
];

const NOT_FOR_YOU = [
  'Busca um atalho para "dar diagnóstico" sem avaliação adequada — este material existe justamente para o oposto',
  "Espera uma formação completa em neuropsicologia; este é um instrumento prático de triagem",
  "Não atende nem pretende atender população idosa",
];

export default function AudienceSection() {
  return (
    <section className="py-[clamp(64px,9vw,120px)]" id="qualificacao">
      <div className="wrap narrow rv">
        <span className="eyebrow">Qualificação</span>
        <h2>Este material é para você?</h2>
        <div className="mt-10 grid gap-7 max-[900px]:grid-cols-1 min-[901px]:grid-cols-2">
          <div className="border border-line bg-white p-8 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_18px_40px_-26px_rgba(15,23,43,.35)]">
            <h3 className="mb-5 flex items-center gap-2.5 text-[1.2rem]">
              É para você se
            </h3>
            <ul className="list-none">
              {FOR_YOU.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-3 py-[9px] text-[.97rem]"
                >
                  <span className="flex-none font-mono text-[.9rem] leading-[1.6] text-sage">
                    ✓
                  </span>
                  {item}
                </li>
              ))}
            </ul>
          </div>

          <div className="border border-line bg-paper p-8 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-[0_18px_40px_-26px_rgba(15,23,43,.35)]">
            <h3 className="mb-5 flex items-center gap-2.5 text-[1.2rem]">
              Não é para você se
            </h3>
            <ul className="list-none">
              {NOT_FOR_YOU.map((item) => (
                <li
                  key={item}
                  className="flex items-start gap-3 py-[9px] text-[.97rem]"
                >
                  <span className="flex-none font-mono text-[.9rem] leading-[1.6] text-[#B08A84]">
                    ✕
                  </span>
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
