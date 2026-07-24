import { ImageIcon } from "lucide-react";

/**
 * Seção da dor — a cena clínica real. Copy oficial.
 */
export default function PainSection() {
  return (
    <section className="bg-white">
      <div className="section-container section-padding">
        <div className="grid gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:items-start">
          <div className="mx-auto max-w-3xl lg:mx-0">
            <h2 className="text-2xl font-bold tracking-tight text-brand-950 sm:text-3xl">
              Você reconhece esta cena.
            </h2>

            <div className="mt-8 space-y-5 text-lg leading-relaxed text-slate-600">
              <p className="rounded-r-xl border-l-4 border-brand-300 bg-brand-50/70 py-4 pl-5 pr-4 italic text-slate-700 shadow-sm">
                A filha traz o pai ao consultório. &ldquo;Ele anda esquecido,
                doutora. Repete as coisas. A senhora acha que é
                Alzheimer?&rdquo;
              </p>
              <p>
                Você aplica os instrumentos que conhece. Os escores ficam numa
                zona cinzenta. A queixa é real, mas a idade também explica
                parte do quadro. E agora?
              </p>
              <p>
                Encaminhar para o neurologista já? Com base em quê? Aprofundar
                a avaliação? Investigando o quê, exatamente? Tranquilizar a
                família? E se você estiver diante de um quadro inicial?
              </p>
              <p>
                A formação em avaliação psicológica ensina os instrumentos —
                mas raramente ensina o caminho da decisão: o que investigar
                primeiro, quando aprofundar, como registrar e como comunicar o
                achado ao médico sem parecer inseguro.
              </p>
              <p className="font-medium text-brand-900">
                É nesse vão entre a suspeita e a conduta que a maioria dos
                psicólogos se sente sozinha.
              </p>
            </div>
          </div>

          {/*
            [PREENCHER] Foto de contexto clínico — idealmente uma imagem real
            e humanizada do consultório (psicólogo(a), paciente idoso e
            familiar em conversa). Salve em /public/cena-clinica.webp e troque
            o placeholder por:

            <Image src="/cena-clinica.webp" width={480} height={600}
              alt="Atendimento clínico com paciente idoso e familiar"
              className="h-full w-full rounded-2xl object-cover shadow-xl" />
          */}
          <div
            className="relative mx-auto flex aspect-[4/5] w-full max-w-sm items-center justify-center overflow-hidden rounded-2xl border border-slate-200 bg-gradient-to-br from-slate-100 to-brand-50 shadow-lg lg:max-w-none"
            role="img"
            aria-label="Foto de um atendimento clínico com paciente idoso e familiar"
          >
            <div className="flex flex-col items-center gap-3 text-slate-400">
              <ImageIcon className="h-14 w-14" strokeWidth={1.25} aria-hidden="true" />
              <p className="max-w-[14rem] text-center text-xs leading-relaxed">
                [PREENCHER: foto de contexto clínico — consultório, paciente
                idoso e familiar]
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
