import CtaButton from "./CtaButton";
import GuaranteeBadge from "./GuaranteeBadge";

type Props = {
  location: string;
  label?: string;
  headline?: string;
};

/**
 * Bloco de CTA intermediário — reutilizado entre as seções (a cada 2 seções).
 */
export default function SectionCta({
  location,
  label = "Quero o protocolo completo",
  headline,
}: Props) {
  return (
    <div className="section-container py-14 sm:py-16">
      <div className="surface-card mx-auto flex max-w-2xl flex-col items-center gap-4 border-brand-100 bg-brand-50/60 px-6 py-10 text-center">
        {headline && (
          <p className="text-lg font-medium text-brand-900">{headline}</p>
        )}
        <CtaButton location={location}>{label}</CtaButton>
        <GuaranteeBadge />
      </div>
    </div>
  );
}
