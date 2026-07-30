export default function CredibilityBar() {
  return (
    <div className="bg-ink py-5 text-[.92rem] text-[#B7C2D6]">
      <div className="wrap flex flex-wrap items-center justify-center gap-x-[26px] gap-y-2.5 text-center">
        <span className="font-mono text-[.76rem] uppercase tracking-[.08em] text-amber-soft">
          Autoria
        </span>
        <p className="m-0">
          <b className="font-medium text-white">
            Prof. Dr. Amer Cavalheiro Hamdan
          </b>{" "}
          — Professor de Neuropsicologia da UFPR · Pós-doutorado McGill
          University · Especialista em Neuropsicologia (CFP)
        </p>
      </div>
    </div>
  );
}
