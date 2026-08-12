import { kitItems } from "@/lib/site";
import CtaButton from "./CtaButton";

function Badge({ isBonus }: { isBonus: boolean }) {
  if (isBonus) {
    return (
      <span className="inline-block bg-amber px-2.5 py-[3px] font-mono text-[.66rem] uppercase tracking-[.14em] text-white">
        Bônus
      </span>
    );
  }
  return (
    <span className="inline-block bg-ink px-2.5 py-[3px] font-mono text-[.66rem] uppercase tracking-[.14em] text-paper-warm">
      Incluso
    </span>
  );
}

function MockupPlaceholder({ tall }: { tall?: boolean }) {
  return (
    <div
      className={`flex items-center justify-center bg-paper ${
        tall ? "min-h-[200px]" : "min-h-[140px]"
      }`}
      role="img"
      aria-label="Mockup do material"
    >
      {/* TODO: substituir por <Image src="/mockups/..." /> quando os arquivos estiverem prontos */}
      <svg
        className="h-12 w-12 text-line"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.25"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
        />
      </svg>
    </div>
  );
}

export default function KitSection() {
  const master = kitItems[0];
  const rest = kitItems.slice(1);

  return (
    <section className="bg-paper py-[clamp(64px,9vw,120px)]" id="kit">
      <div className="wrap rv">
        <span className="eyebrow">O que você recebe</span>
        <h2>O kit clínico completo</h2>

        {/* Faixa de resumo */}
        <div className="mt-8 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 border border-line bg-white px-6 py-4 text-center font-mono text-[.78rem] uppercase tracking-[.1em] text-ink-soft md:justify-start md:text-left">
          <span className="flex items-center gap-2">
            <span className="text-amber-ink">5</span> materiais
          </span>
          <span className="hidden h-3 w-px bg-line md:block" aria-hidden="true" />
          <span className="flex items-center gap-2">
            Aplicação em <span className="text-amber-ink">2 sessões</span>
          </span>
          <span className="hidden h-3 w-px bg-line md:block" aria-hidden="true" />
          <span>Acesso vitalício</span>
        </div>

        {/* Card destaque — Guia Master */}
        <article className="mt-6 grid border border-line bg-white transition-all duration-200 hover:shadow-[0_18px_40px_-26px_rgba(15,23,43,.25)] md:grid-cols-[.45fr_.55fr]">
          <MockupPlaceholder tall />
          <div className="flex flex-col justify-center px-7 py-7 md:px-10 md:py-9">
            <div className="mb-3 flex flex-wrap items-center gap-2.5">
              <Badge isBonus={master.isBonus} />
              <span className="font-mono text-[.66rem] uppercase tracking-[.14em] text-amber-ink">
                Item principal
              </span>
            </div>
            <h3 className="text-[1.5rem] leading-[1.2]">{master.title}</h3>
            <p className="m-0 mt-3 text-[.98rem]">{master.description}</p>
            <p className="m-0 mt-4 font-mono text-[.76rem] tracking-[.02em] text-sage">
              {master.spec}
            </p>
          </div>
        </article>

        {/* Grid 2×2 — demais itens */}
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {rest.map((item) => (
            <article
              key={item.title}
              className="flex flex-col border border-line bg-white transition-all duration-200 hover:shadow-[0_18px_40px_-26px_rgba(15,23,43,.25)]"
            >
              <MockupPlaceholder />
              <div className="flex flex-1 flex-col px-6 py-5">
                <div className="mb-2.5">
                  <Badge isBonus={item.isBonus} />
                </div>
                <h3 className="mb-1">{item.title}</h3>
                <p className="m-0 flex-1 text-[.95rem]">{item.description}</p>
                <p className="m-0 mt-3 font-mono text-[.76rem] tracking-[.02em] text-sage">
                  {item.spec}
                </p>
              </div>
            </article>
          ))}
        </div>

        <div className="mt-12 text-center">
          <CtaButton location="apos-kit">Quero o protocolo completo</CtaButton>
          <p className="micro text-center">
            Acesso imediato · Garantia de 7 dias · Compra segura via Hotmart
          </p>
        </div>
      </div>
    </section>
  );
}
