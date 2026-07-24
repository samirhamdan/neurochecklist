import { site } from "@/lib/site";

/**
 * Selo de garantia — exibido junto a todos os CTAs.
 */
export default function GuaranteeBadge({
  className = "",
}: {
  className?: string;
}) {
  return (
    <p
      className={`flex items-center justify-center gap-2 text-sm text-slate-500 ${className}`}
    >
      <svg
        className="h-5 w-5 shrink-0 text-accent-700"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12.75 11.25 15 15 9.75M12 3l7.5 3v5.25c0 4.5-3 8.25-7.5 9.75-4.5-1.5-7.5-5.25-7.5-9.75V6L12 3z"
        />
      </svg>
      Garantia incondicional de {site.guaranteeDays} dias · Compra segura via
      Hotmart
    </p>
  );
}
