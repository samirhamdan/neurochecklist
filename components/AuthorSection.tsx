import { Landmark, GraduationCap, Globe2, Award, User } from "lucide-react";
import { site } from "@/lib/site";

/** Linha do tempo de credenciais — mesmo texto usado antes, agora com ícone + marcador visual */
const TIMELINE = [
  { icon: Landmark, label: "Prof. UFPR desde 2005" },
  { icon: GraduationCap, label: "Doutorado UNIFESP" },
  { icon: Globe2, label: "Pós-doc McGill" },
  { icon: Award, label: "Especialista em Neuropsicologia (CFP)" },
];

/**
 * Seção de autoridade completa do Prof. Hamdan. Copy oficial.
 * Tratamento de destaque: fundo escuro dramático, foto grande, citação de
 * impacto para o gancho do RAVLT/Trilhas, credenciais em linha do tempo.
 */
export default function AuthorSection() {
  return (
    <section
      className="bg-gradient-to-b from-brand-950 via-brand-950 to-brand-900 text-white"
      id="autor"
    >
      <div className="section-container section-padding">
        <div className="mx-auto max-w-4xl">
          {/* Citação de impacto — gancho RAVLT/Trilhas */}
          <div className="relative mx-auto max-w-3xl">
            <span
              className="pointer-events-none absolute -left-3 -top-10 select-none font-serif text-8xl leading-none text-gold-400/25 sm:-left-8 sm:text-9xl"
              aria-hidden="true"
            >
              &ldquo;
            </span>
            <blockquote className="relative border-l-4 border-gold-400 py-1 pl-6 sm:pl-9">
              <p className="text-balance text-2xl font-bold leading-snug tracking-tight sm:text-3xl lg:text-4xl">
                Se você usa as normas brasileiras do{" "}
                <span className="text-accent-400">RAVLT</span> ou do{" "}
                <span className="text-accent-400">Teste das Trilhas</span>,
                você já usa a pesquisa dele.
              </p>
            </blockquote>
          </div>

          <div className="mt-16 grid items-center gap-10 lg:grid-cols-[300px_1fr] lg:gap-14">
            {/*
              [PREENCHER] Foto profissional do Prof. Hamdan.
              Salve em /public/prof-hamdan.webp (ideal: 640x640, WebP) e troque
              o placeholder por:

              <Image src="/prof-hamdan.webp" width={300} height={300}
                alt="Prof. Dr. Amer Cavalheiro Hamdan"
                className="aspect-square w-full rounded-2xl object-cover" />
            */}
            <div className="relative mx-auto w-full max-w-[280px] lg:mx-0">
              <div
                className="absolute -inset-3 rounded-3xl border border-gold-400/25"
                aria-hidden="true"
              />
              <div
                className="relative flex aspect-square items-center justify-center overflow-hidden rounded-2xl border border-brand-700 bg-brand-900 shadow-2xl shadow-black/30"
                role="img"
                aria-label="Foto do Prof. Dr. Amer Cavalheiro Hamdan"
              >
                <div className="flex flex-col items-center gap-2 text-brand-400">
                  <User className="h-16 w-16" strokeWidth={1.25} aria-hidden="true" />
                  <p className="max-w-[10rem] text-center text-xs">
                    [PREENCHER: foto profissional]
                  </p>
                </div>
              </div>
            </div>

            <div className="space-y-4 text-lg leading-relaxed text-brand-100">
              <p>
                O <strong className="text-white">{site.author.name}</strong> é
                professor de Neuropsicologia da Universidade Federal do
                Paraná, onde ensina avaliação neuropsicológica há mais de duas
                décadas.
              </p>
              <p>
                Doutor em Psicobiologia pela UNIFESP, com pós-doutorado na
                McGill University (Canadá) e título de Especialista em
                Neuropsicologia pelo Conselho Federal de Psicologia, dedicou
                sua carreira a uma única pergunta:{" "}
                <em className="text-white">
                  como diferenciar, com rigor, o envelhecimento cognitivo
                  normal do patológico?
                </em>
              </p>
              <p>
                Dessa trajetória vieram estudos de normatização de
                instrumentos que hoje fazem parte da rotina de laudo de
                psicólogos em todo o Brasil — entre eles o RAVLT e o Teste das
                Trilhas —, além de livro e capítulos em obras de referência da
                neuropsicologia brasileira.
              </p>
              <p className="font-medium text-white">
                Este checklist é a versão prática desses 30 anos: o que a
                pesquisa mostra, organizado do jeito que a clínica precisa.
              </p>
            </div>
          </div>

          {/* Linha do tempo de credenciais */}
          <div className="mt-16">
            <ol className="relative grid gap-8 sm:grid-cols-4 sm:gap-4">
              <div
                className="absolute left-0 right-0 top-6 hidden h-px bg-gradient-to-r from-transparent via-brand-700 to-transparent sm:block"
                aria-hidden="true"
              />
              {TIMELINE.map(({ icon: Icon, label }) => (
                <li
                  key={label}
                  className="relative flex flex-col items-center gap-3 text-center"
                >
                  <span className="flex h-12 w-12 shrink-0 items-center justify-center rounded-full border border-gold-400/40 bg-brand-900 text-gold-400 shadow-md shadow-black/20">
                    <Icon className="h-5 w-5" strokeWidth={1.75} aria-hidden="true" />
                  </span>
                  <span className="text-sm font-medium text-brand-100">
                    {label}
                  </span>
                </li>
              ))}
            </ol>

            {/* [PREENCHER] CRP em lib/site.ts */}
            <p className="mt-10 text-center text-sm text-brand-400">
              {site.author.crp}
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
