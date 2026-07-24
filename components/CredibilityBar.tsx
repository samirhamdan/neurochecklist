/**
 * Barra de credibilidade — mini-bio de 1 linha logo abaixo do hero.
 */
export default function CredibilityBar() {
  return (
    <aside className="border-y border-brand-100 bg-brand-900">
      <div className="section-container py-4">
        <p className="text-center text-sm leading-relaxed text-brand-100 sm:text-base">
          Por <strong className="text-white">Prof. Dr. Amer Cavalheiro Hamdan</strong>{" "}
          — Professor de Neuropsicologia da UFPR · Pós-doutorado McGill
          University · Especialista em Neuropsicologia (CFP)
        </p>
      </div>
    </aside>
  );
}
