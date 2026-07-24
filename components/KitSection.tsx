import { BookOpenCheck, Workflow, Mic, FileEdit, ClipboardList } from "lucide-react";
import { kitItems } from "@/lib/site";

/**
 * Ícones por item — na mesma ordem de kitItems em lib/site.ts:
 * Guia Master, Fluxograma, Entrevista com o Familiar, Template, Ficha.
 */
const ICONS = [BookOpenCheck, Workflow, Mic, FileEdit, ClipboardList];

/**
 * O que você recebe — kit completo com os 5 itens. Copy oficial em lib/site.ts.
 *
 * [PREENCHER] Mockups: cada card tem um placeholder de ícone. Quando houver
 * mockups reais (capa de cada PDF/documento, idealmente em 3D ou tela de
 * laptop/tablet mostrando o fluxograma), salve em /public/mockups/ e
 * substitua o bloco de ícone por <Image /> (next/image).
 */
export default function KitSection() {
  return (
    <section className="bg-white" id="kit">
      <div className="section-container section-padding">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-2xl font-bold tracking-tight text-brand-950 sm:text-3xl">
            O kit clínico completo
          </h2>
        </div>

        <div className="mt-14 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {kitItems.map((item, i) => {
            const Icon = ICONS[i];
            return (
              <article
                key={item.title}
                className={`surface-card surface-card-hover flex flex-col p-6 ${
                  item.isBonus ? "border-accent-100" : "border-brand-100"
                }`}
              >
                {/* Placeholder de ícone — [PREENCHER] trocar por mockup real */}
                <div
                  className={`mb-5 flex h-16 w-16 items-center justify-center rounded-xl ${
                    item.isBonus
                      ? "bg-accent-50 text-accent-600"
                      : "bg-brand-50 text-brand-500"
                  }`}
                  aria-hidden="true"
                >
                  <Icon className="h-8 w-8" strokeWidth={1.5} />
                </div>

                <span
                  className={`mb-3 inline-block w-fit rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${
                    item.isBonus
                      ? "bg-accent-100 text-accent-800"
                      : "bg-brand-100 text-brand-800"
                  }`}
                >
                  {item.tag}
                </span>
                <h3 className="text-lg font-bold text-brand-950">
                  {item.title}
                </h3>
                <p className="mt-2 text-base leading-relaxed text-slate-600">
                  {item.description}
                </p>
              </article>
            );
          })}

          {/*
            [PREENCHER] Card visual extra (opcional): mockup de laptop/tablet
            mostrando o Fluxograma de Decisão Clínica em uso. Adicionar como
            imagem em /public/mockups/fluxograma-mockup.webp.
          */}
        </div>
      </div>
    </section>
  );
}
