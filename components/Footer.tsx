import Link from "next/link";
import { site } from "@/lib/site";

export default function Footer() {
  return (
    <footer className="bg-ink px-0 py-14 text-[.88rem] text-[#8D98AE]">
      <div className="wrap narrow">
        <p>
          <b className="font-medium text-white">
            Prof. Dr. Amer Cavalheiro Hamdan
          </b>{" "}
          — Doutor em Psicobiologia
        </p>
        <p>{site.footerDisclaimer}</p>
        <p>
          A compra é processada pela Hotmart, responsável pelo pagamento, entrega
          e reembolso.
        </p>
        <p>
          <Link
            href="/politica-de-privacidade"
            className="text-amber-soft hover:underline"
          >
            Política de Privacidade
          </Link>{" "}
          ·{" "}
          <Link
            href="/termos-de-uso"
            className="text-amber-soft hover:underline"
          >
            Termos de Uso
          </Link>
        </p>
        <p className="mt-6 opacity-60">
          © 2026 NeuroChecklist. Todos os direitos reservados.
        </p>
      </div>
    </footer>
  );
}
