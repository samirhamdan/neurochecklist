import Link from "next/link";
import { site } from "@/lib/site";

/**
 * Rodapé — CRP, aviso de escopo, Hotmart, políticas. Copy oficial.
 */
export default function Footer() {
  return (
    <footer className="border-t border-slate-200 bg-white">
      <div className="section-container py-14">
        <div className="mx-auto max-w-3xl space-y-4 text-center text-sm leading-relaxed text-slate-500">
          <p className="font-medium text-slate-700">
            {site.author.name} · {site.author.crp}
            {/* [PREENCHER] CRP em lib/site.ts */}
          </p>
          <p>{site.footerDisclaimer}</p>
          <p>
            A compra é processada pela Hotmart, responsável pelo pagamento,
            entrega e reembolso.
          </p>
          <p className="flex items-center justify-center gap-2">
            <Link
              href="/politica-de-privacidade"
              className="underline underline-offset-2 hover:text-brand-700"
            >
              Política de Privacidade
            </Link>
            <span aria-hidden="true">·</span>
            <Link
              href="/termos-de-uso"
              className="underline underline-offset-2 hover:text-brand-700"
            >
              Termos de Uso
            </Link>
          </p>
          <p>© 2026 — Todos os direitos reservados.</p>
        </div>
      </div>
    </footer>
  );
}
