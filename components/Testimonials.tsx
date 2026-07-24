/**
 * ============================================================
 * SEÇÃO DE DEPOIMENTOS — DESATIVADA
 *
 * NÃO ativar com depoimentos fictícios (vedado pelas normas de
 * publicidade do CFP e pela diretriz do projeto).
 *
 * Quando houver depoimentos REAIS (com autorização por escrito
 * do autor do depoimento, incluindo uso de nome, CRP e foto):
 *
 * 1. Preencha o array TESTIMONIALS abaixo;
 * 2. Salve as fotos autorizadas em /public/depoimentos/;
 * 3. Em app/page.tsx, descomente a linha <Testimonials />.
 * ============================================================
 */

type Testimonial = {
  quote: string;
  name: string;
  crp: string;
  /** Caminho da foto autorizada em /public/depoimentos/ (opcional) */
  photo?: string;
};

// [PREENCHER] Apenas depoimentos reais e autorizados:
const TESTIMONIALS: Testimonial[] = [
  // {
  //   quote: "Texto integral do depoimento, sem edições que alterem o sentido.",
  //   name: "Nome Completo",
  //   crp: "CRP 00/00000",
  //   photo: "/depoimentos/nome.webp",
  // },
];

export default function Testimonials() {
  if (TESTIMONIALS.length === 0) return null;

  return (
    <section className="bg-brand-50/50">
      <div className="section-container py-16 sm:py-20">
        <h2 className="text-center text-2xl font-bold tracking-tight text-brand-950 sm:text-3xl">
          O que dizem colegas que já usam o protocolo
        </h2>
        <div className="mx-auto mt-10 grid max-w-4xl gap-6 md:grid-cols-2">
          {TESTIMONIALS.map((t) => (
            <figure
              key={t.name}
              className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
            >
              <blockquote className="text-base leading-relaxed text-slate-600">
                “{t.quote}”
              </blockquote>
              <figcaption className="mt-4 flex items-center gap-3">
                {t.photo && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={t.photo}
                    alt={`Foto de ${t.name}`}
                    width={44}
                    height={44}
                    loading="lazy"
                    className="h-11 w-11 rounded-full object-cover"
                  />
                )}
                <div>
                  <p className="font-semibold text-brand-950">{t.name}</p>
                  <p className="text-sm text-slate-500">{t.crp}</p>
                </div>
              </figcaption>
            </figure>
          ))}
        </div>
      </div>
    </section>
  );
}
