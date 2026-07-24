import CtaButton from "./CtaButton";
import { site, kitItems } from "@/lib/site";

/**
 * Oferta final — preço, parcelamento, garantia e CTA. Copy oficial.
 */
export default function OfferSection() {
  return (
    <section className="bg-slate-50" id="oferta">
      <div className="section-container section-padding">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-center text-2xl font-bold tracking-tight text-brand-950 sm:text-3xl">
            Quanto custa a segurança na sua conduta?
          </h2>

          <p className="mx-auto mt-6 max-w-2xl text-center text-lg leading-relaxed text-slate-600">
            Uma única supervisão clínica custa, em média, R$ 150–300. Um curso
            de avaliação neuropsicológica, alguns milhares de reais. Este kit
            condensa o essencial da triagem — protocolo, fluxograma, entrevista,
            relatório e prontuário — por menos do que uma sessão do seu próprio
            atendimento:
          </p>

          <div className="mx-auto mt-10 max-w-xl rounded-3xl border-2 border-brand-900 bg-white p-8 shadow-2xl shadow-brand-900/15 transition-shadow duration-300 hover:shadow-brand-900/20 sm:p-10">
            <p className="text-center text-sm font-semibold uppercase tracking-widest text-brand-500">
              {site.productFullName}
            </p>

            {/* Resumo do que está incluído */}
            <ul className="mx-auto mt-6 max-w-sm space-y-2 text-sm text-slate-600">
              {kitItems.map((item) => (
                <li key={item.title} className="flex items-start gap-2.5">
                  <svg
                    className="mt-0.5 h-4 w-4 shrink-0 text-accent-700"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2.5"
                    aria-hidden="true"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
                  </svg>
                  {item.title}
                </li>
              ))}
            </ul>

            <div className="mt-8 text-center">
              {/*
                ANCORAGEM DE PREÇO — exibir apenas se for real (preço praticado
                anteriormente). Para ativar, descomente a linha abaixo:

                <p className="text-lg text-slate-400 line-through">De R$ 497</p>
              */}
              <p className="text-5xl font-bold tracking-tight text-brand-950">
                {site.price.full}
              </p>
              <p className="mt-2 text-lg text-slate-600">
                ou <strong>{site.price.installments}</strong>
              </p>
            </div>

            <div className="mt-8 flex flex-col items-center gap-3">
              <CtaButton location="oferta-final" className="w-full sm:w-auto">
                {site.cta.label}
              </CtaButton>
              <p className="text-center text-sm text-slate-500">
                Acesso imediato e vitalício · Garantia incondicional de 7 dias ·
                Compra processada pela Hotmart
              </p>
            </div>

            {/* Selos de segurança da compra */}
            <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-3 border-t border-slate-100 pt-6 text-xs text-slate-500">
              <span className="flex items-center gap-1.5">
                <svg className="h-4 w-4 text-accent-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
                </svg>
                Compra segura Hotmart
              </span>
              <span className="flex items-center gap-1.5">
                <svg className="h-4 w-4 text-accent-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M2.25 8.25h19.5M2.25 9h19.5m-16.5 5.25h6m-6 2.25h3m-3.75 3h15a2.25 2.25 0 0 0 2.25-2.25V6.75A2.25 2.25 0 0 0 19.5 4.5h-15a2.25 2.25 0 0 0-2.25 2.25v10.5A2.25 2.25 0 0 0 4.5 19.5Z" />
                </svg>
                Cartão em até 12x
              </span>
              <span className="flex items-center gap-1.5">
                <svg className="h-4 w-4 text-accent-700" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Pix e boleto
              </span>
            </div>
          </div>

          {/* Garantia em destaque */}
          <div className="mx-auto mt-10 flex max-w-xl items-start gap-4 rounded-2xl border border-accent-100 bg-accent-50/60 p-6 shadow-sm">
            <svg
              className="h-10 w-10 shrink-0 text-accent-700"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9 12.75 11.25 15 15 9.75M12 3l7.5 3v5.25c0 4.5-3 8.25-7.5 9.75-4.5-1.5-7.5-5.25-7.5-9.75V6L12 3z"
              />
            </svg>
            <div>
              <h3 className="font-bold text-brand-950">
                Garantia incondicional de {site.guaranteeDays} dias
              </h3>
              <p className="mt-1 text-base leading-relaxed text-slate-600">
                Acesse o material completo. Se entender que não é para você,
                solicite o reembolso pela própria Hotmart dentro de{" "}
                {site.guaranteeDays} dias e receba 100% do valor de volta.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
