import { kitItems } from "@/lib/site";
import CtaButton from "./CtaButton";

export default function MethodSection() {
  return (
    <section className="py-[clamp(64px,9vw,120px)]" id="metodo">
      <div className="wrap narrow rv">
        <span className="eyebrow">O caminho</span>
        <h2>
          Existe um percurso estruturado — e ele cabe em duas sessões.
        </h2>
        <p className="mt-6">
          Depois de quase 30 anos pesquisando e ensinando avaliação
          neuropsicológica do envelhecimento, o Prof. Dr. Amer Hamdan organizou o
          percurso da triagem em um protocolo objetivo: o que observar, em que
          ordem investigar, quais parâmetros usar como referência e como
          transformar tudo isso em documento técnico.
        </p>
        <p>
          Não é um curso teórico. Não é mais um livro para a estante. É a
          ferramenta de trabalho que fica aberta na sua mesa durante o
          atendimento.
        </p>

        <ol className="relative mt-12 list-none">
          {kitItems.map((item, i) => (
            <li key={item.title} className="relative flex gap-[22px] pb-[34px] last:pb-0">
              {i < kitItems.length - 1 && (
                <div
                  className="absolute bottom-0 left-[22px] top-[44px] w-px"
                  style={{
                    background:
                      "repeating-linear-gradient(to bottom, #A05A1E 0 4px, transparent 4px 9px)",
                  }}
                  aria-hidden="true"
                />
              )}
              <div className="z-10 grid h-[44px] w-[44px] flex-none place-items-center rounded-full border-[1.5px] border-amber-ink bg-paper-warm font-mono text-[.95rem] text-amber-ink">
                {i + 1}
              </div>
              <div>
                <h3 className="mb-1">
                  {item.title}
                  {item.isBonus && (
                    <span className="ml-2.5 inline-block translate-y-[-3px] border border-sage px-[7px] py-0.5 font-mono text-[.66rem] uppercase tracking-[.14em] text-sage">
                      Bônus
                    </span>
                  )}
                </h3>
                <p className="m-0 text-[.98rem]">{item.description}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-10 border border-line border-l-[3px] border-l-sage bg-white p-[22px_26px] text-[.95rem]">
          <b className="text-ink">Importante:</b> trata-se de um instrumento de
          triagem e apoio ao raciocínio clínico. Ele não substitui a avaliação
          neuropsicológica completa nem o diagnóstico médico, que é
          multidisciplinar — ele organiza o caminho até eles.
        </div>

        <p className="mt-10">
          <CtaButton location="apos-metodo">Quero o protocolo completo</CtaButton>
        </p>
      </div>
    </section>
  );
}
