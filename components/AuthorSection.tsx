import Image from "next/image";

const TIMELINE = [
  { time: "Doutorado", label: "Psicobiologia — UNIFESP" },
  { time: "Pós-doc", label: "McGill University, Canadá" },
  { time: "2005 →", label: "Docente de Neuropsicologia — UFPR" },
  { time: "Pesquisa", label: "Normatização brasileira do RAVLT e do Teste das Trilhas" },
];

export default function AuthorSection() {
  return (
    <section
      className="bg-ink py-[clamp(64px,9vw,120px)] text-[#B7C2D6]"
      id="autor"
    >
      <div className="wrap rv">
        <span className="eyebrow text-steel before:bg-steel">Quem assina</span>
        <p
          className="font-serif leading-[1.2] text-white"
          style={{ fontSize: "clamp(1.9rem, 4vw, 3rem)", maxWidth: "22ch" }}
        >
          Se você usa as normas brasileiras do{" "}
          <b className="font-normal italic text-amber-soft">RAVLT</b> ou do{" "}
          <b className="font-normal italic text-amber-soft">
            Teste das Trilhas
          </b>
          , você já usa a pesquisa dele.
        </p>

        <div className="mt-12 grid items-start gap-[60px] max-[900px]:grid-cols-1 min-[901px]:grid-cols-[.9fr_1.1fr]">
          <div>
            <figure className="relative grid place-items-end justify-items-center pt-[18px] max-[900px]:mx-auto max-[900px]:max-w-[320px]">
              <div
                className="absolute left-1/2 top-[8%] z-0 aspect-square w-[88%] -translate-x-1/2 rounded-full"
                style={{
                  background:
                    "radial-gradient(circle, rgba(196,121,46,.24) 0%, rgba(196,121,46,.06) 45%, transparent 70%)",
                }}
                aria-hidden="true"
              />
              <Image
                src="/prof-hamdan.webp"
                alt="Prof. Dr. Amer Cavalheiro Hamdan"
                width={340}
                height={340}
                className="relative z-[1] block h-auto w-full max-w-[340px]"
                style={{
                  filter:
                    "grayscale(.22) contrast(1.05) drop-shadow(0 22px 34px rgba(0,0,0,.45))",
                }}
              />
              <figcaption className="relative z-[2] mt-3.5 w-full border-t border-[#27334B] pt-4 font-mono text-[.78rem] leading-relaxed text-[#EAEEF6]">
                Prof. Dr. Amer Cavalheiro Hamdan
                <br />
                <span className="text-[.7rem] uppercase tracking-[.12em] text-amber-soft">
                  Neuropsicologia do envelhecimento
                </span>
              </figcaption>
            </figure>
          </div>
          <div>
            <p>
              O{" "}
              <b className="font-medium text-white">
                Prof. Dr. Amer Cavalheiro Hamdan
              </b>{" "}
              é professor de Neuropsicologia da Universidade Federal do Paraná,
              onde ensina avaliação neuropsicológica há mais de duas décadas.
            </p>
            <p>
              Doutor em Psicobiologia pela UNIFESP, com pós-doutorado na McGill
              University, dedicou a carreira a uma única
              pergunta: como diferenciar, com rigor, o envelhecimento cognitivo
              normal do patológico.
            </p>
            <p>
              Dessa trajetória vieram estudos de normatização de instrumentos que
              hoje fazem parte da rotina de laudo de psicólogos em todo o Brasil,
              além de livro e capítulos em obras de referência da neuropsicologia
              brasileira.
            </p>
            <p className="text-[#DEE5F1]">
              Este checklist é a versão prática desses trinta anos: o que a
              pesquisa mostra, organizado do jeito que a clínica precisa.
            </p>

            <ul className="mt-10 list-none border-t border-[#27334B60]">
              {TIMELINE.map(({ time, label }) => (
                <li
                  key={time}
                  className="flex items-baseline gap-[18px] border-b border-[#27334B] py-4"
                >
                  <time className="w-24 flex-none font-mono text-[.78rem] tracking-[.02em] text-amber-soft">
                    {time}
                  </time>
                  <span className="text-[.97rem] text-[#C7D2E4]">{label}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
