import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Política de Privacidade — NeuroChecklist",
  robots: { index: false },
};

/**
 * [PREENCHER] Página placeholder — substituir pelo texto jurídico definitivo
 * (LGPD) antes de veicular tráfego pago.
 */
export default function PrivacyPage() {
  return (
    <main className="section-container max-w-3xl py-16">
      <h1 className="text-3xl font-bold text-brand-950">
        Política de Privacidade
      </h1>
      <div className="mt-6 space-y-4 leading-relaxed text-slate-600">
        <p>
          Esta página utiliza cookies e tecnologias de rastreamento (Meta Pixel
          e Google Analytics) para mensuração de audiência e de campanhas de
          marketing. Nenhum dado sensível é coletado por este site; o pagamento
          é processado integralmente pela Hotmart, em ambiente próprio.
        </p>
        <p>
          [PREENCHER: texto completo da Política de Privacidade em conformidade
          com a LGPD — recomenda-se revisão jurídica antes da veiculação de
          tráfego pago.]
        </p>
      </div>
      <p className="mt-10">
        <Link href="/" className="text-brand-700 underline underline-offset-2">
          ← Voltar para a página principal
        </Link>
      </p>
    </main>
  );
}
