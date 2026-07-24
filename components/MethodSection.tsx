/**
 * A virada — o caminho estruturado (apresentação do método). Copy oficial.
 */
export default function MethodSection() {
  return (
    <section className="bg-slate-50">
      <div className="section-container section-padding">
        <div className="mx-auto max-w-3xl">
          <h2 className="text-2xl font-bold tracking-tight text-brand-950 sm:text-3xl">
            Existe um caminho estruturado — e ele cabe em duas sessões.
          </h2>

          <div className="mt-6 space-y-5 text-lg leading-relaxed text-slate-600">
            <p>
              Depois de quase 30 anos pesquisando e ensinando avaliação
              neuropsicológica do envelhecimento, o Prof. Dr. Amer Hamdan
              organizou o percurso da triagem em um protocolo objetivo: o que
              observar, em que ordem investigar, quais parâmetros usar como
              referência para a população brasileira e como transformar tudo
              isso em documento técnico.
            </p>
            <p>
              Não é um curso teórico. Não é mais um livro para a estante. É a
              ferramenta de trabalho que fica aberta na sua mesa durante o
              atendimento.
            </p>
          </div>

          <p className="mt-8 rounded-xl border border-brand-200 bg-white px-5 py-4 text-base leading-relaxed text-slate-600 shadow-sm">
            <strong className="text-brand-900">Importante:</strong> trata-se de
            um instrumento de triagem e apoio ao raciocínio clínico. Ele não
            substitui a avaliação neuropsicológica completa nem o diagnóstico
            médico, que é multidisciplinar — ele organiza o caminho até eles.
          </p>
        </div>
      </div>
    </section>
  );
}
