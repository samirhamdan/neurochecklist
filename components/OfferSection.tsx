import CtaButton from "./CtaButton";
import { site, kitItems } from "@/lib/site";

export default function OfferSection() {
  return (
    <section className="py-[clamp(64px,9vw,120px)] text-center" id="adquirir">
      <div className="wrap narrow rv">
        <span className="eyebrow justify-center">A oferta</span>
        <h2>Quanto custa a segurança na sua conduta?</h2>
        <p className="mt-5">
          Uma única supervisão clínica custa, em média, o equivalente a uma
          sessão do seu próprio atendimento. Um curso de avaliação
          neuropsicológica, alguns milhares de reais. Este kit condensa o
          essencial da triagem — protocolo, fluxograma, entrevista, relatório e
          prontuário.
        </p>

        <div className="mx-auto mt-10 max-w-[520px] border border-ink bg-white p-[40px_32px] shadow-[0_28px_60px_-34px_rgba(15,23,43,.4)]">
          <ul className="mb-[26px] list-none border-b border-dashed border-line pb-[22px] text-left">
            {kitItems.map((item) => (
              <li
                key={item.title}
                className="flex gap-[11px] py-1.5 text-[.95rem] text-ink-soft"
              >
                <span className="font-mono text-[.85rem] text-sage">✓</span>
                {item.title}
              </li>
            ))}
          </ul>

          {/*
            ANCORAGEM DE PREÇO — exibir apenas se for real (preço praticado
            anteriormente). Para ativar, descomente a linha abaixo:

            <p className="text-lg text-body line-through">De R$ 497</p>
          */}

          <div className="font-serif text-ink" style={{ fontSize: "4rem", lineHeight: 1 }}>
            <small className="mr-1 align-[.9rem] text-[1.4rem]">R$</small>197
          </div>
          <div className="mt-1.5 font-mono text-[.9rem] text-body">
            ou {site.price.installments}
          </div>

          <div className="my-[22px] inline-flex items-center gap-2.5 border border-sage px-3.5 py-2 font-mono text-[.76rem] uppercase tracking-[.08em] text-sage">
            ✓ Garantia incondicional de {site.guaranteeDays} dias
          </div>

          <div>
            <CtaButton location="oferta-final">{site.cta.label}</CtaButton>
            <p className="micro text-center">
              Acesso imediato e vitalício · Compra processada pela Hotmart
            </p>
            <ul className="mt-[18px] flex list-none flex-wrap justify-center gap-2">
              {["Pix", "Cartão em até 20×", "Boleto"].map((method) => (
                <li
                  key={method}
                  className="rounded-sm border border-line px-[11px] py-1.5 font-mono text-[.7rem] uppercase tracking-[.08em] text-body"
                >
                  {method}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
