import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "Termos de Uso — NeuroChecklist",
  robots: { index: false },
};

/**
 * [PREENCHER] Página placeholder — substituir pelo texto jurídico definitivo
 * antes de veicular tráfego pago.
 */
export default function TermsPage() {
  return (
    <main className="section-container max-w-3xl py-16">
      <h1 className="text-3xl font-bold text-brand-950">Termos de Uso</h1>
      <div className="mt-6 space-y-4 leading-relaxed text-slate-600">
        <p>
          O Checklist de Triagem Neuropsicológica é um material digital de apoio
          à prática profissional do psicólogo. Ele não substitui avaliação
          neuropsicológica completa, julgamento clínico ou diagnóstico médico. A
          compra, a entrega, a garantia de 7 dias e eventuais reembolsos são
          processados pela Hotmart, conforme os termos da plataforma.
        </p>
        <p>
          [PREENCHER: texto completo dos Termos de Uso — incluir licença de uso
          do material (uso profissional individual), propriedade intelectual e
          foro. Recomenda-se revisão jurídica.]
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
