export default function PainSection() {
  return (
    <section className="bg-paper py-[clamp(64px,9vw,120px)]" id="problema">
      <div className="wrap narrow rv">
        <span className="eyebrow">O problema</span>
        <h2>Você reconhece esta cena.</h2>
        <blockquote className="my-10 border-l-2 border-amber py-1.5 pl-7 font-serif italic text-ink" style={{ fontSize: "clamp(1.5rem, 3vw, 2.1rem)", lineHeight: 1.35 }}>
          &ldquo;Ele anda esquecido, doutora. Repete as coisas. A senhora acha
          que é Alzheimer?&rdquo;
        </blockquote>
        <p>
          Você aplica os instrumentos que conhece. Os escores ficam numa zona
          cinzenta. A queixa é real, mas a idade também explica parte do quadro.
          E agora?
        </p>
        <p>
          Encaminhar para o neurologista já? Com base em quê? Aprofundar a
          avaliação? Investigando o quê, exatamente? Tranquilizar a família? E se
          você estiver diante de um quadro inicial?
        </p>
        <p>
          A formação em avaliação psicológica ensina os instrumentos — mas
          raramente ensina o{" "}
          <b className="text-ink">caminho da decisão</b>: o que investigar
          primeiro, quando aprofundar, como registrar e como comunicar o achado
          ao médico sem parecer inseguro.
        </p>
        <p className="text-[1.08rem] font-semibold text-ink">
          É nesse vão entre a suspeita e a conduta que a maioria dos psicólogos
          se sente sozinha.
        </p>
      </div>
    </section>
  );
}
