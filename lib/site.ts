/**
 * ============================================================
 * CONFIGURAÇÃO CENTRAL DA PÁGINA
 * Edite aqui: preço, links, CRP, nomes, FAQ e itens do kit.
 * Todos os componentes leem deste arquivo — não há preço/link
 * "hardcoded" espalhado pelo código.
 * ============================================================
 */

export const site = {
  productName: "NeuroChecklist",
  productFullName:
    "Checklist de Triagem Neuropsicológica — Guia Prático para Psicólogos",

  /** URL pública final (canonical/OG). Definida via env na Vercel. */
  url: process.env.NEXT_PUBLIC_SITE_URL || "https://neurochecklist.vercel.app",

  /** Link de checkout da Hotmart (os parâmetros UTM são anexados no clique) */
  checkoutUrl:
    "https://pay.hotmart.com/V106813542Y?off=ebi160sc&hotfeature=51",

  price: {
    full: "R$ 297",
    fullNumber: 297,
    installments: "12x de R$ 29,64",
    currency: "BRL",
  },

  guaranteeDays: 7,

  author: {
    name: "Prof. Dr. Amer Cavalheiro Hamdan",
    shortName: "Prof. Dr. Amer C. Hamdan",
    // [PREENCHER] CRP do autor — aparece na seção de autoridade e no rodapé
    crp: "CRP [PREENCHER]",
    role: "Professor de Neuropsicologia da UFPR",
  },

  /** CTA padrão e microcopy — usados em todos os botões */
  cta: {
    label: "Quero o protocolo completo",
    microcopy: "Acesso imediato · Garantia de 7 dias · Compra segura via Hotmart",
  },

  /** Aviso de escopo — rodapé */
  footerDisclaimer:
    "Este material é um instrumento de apoio à prática profissional do psicólogo e não substitui avaliação neuropsicológica completa, julgamento clínico ou diagnóstico médico.",

  metaTitle:
    "NeuroChecklist — Protocolo de Triagem Neuropsicológica para Psicólogos",
  metaDescription:
    "Da suspeita à conduta em 2 sessões: protocolo estruturado de triagem neuropsicológica para psicólogos que atendem idosos, com parâmetros validados para a população brasileira. Por Prof. Dr. Amer C. Hamdan (UFPR).",
};

/** Itens do kit — seção "O que você recebe" (copy oficial) */
export const kitItems = [
  {
    title: "Guia Master de Triagem Neuropsicológica",
    description:
      "O manual central: fundamentação técnica, critérios objetivos de investigação, pontos de corte de referência e o passo a passo da aplicação do protocolo em até 2 sessões.",
    tag: "Item 1",
    isBonus: false,
  },
  {
    title: "Fluxograma de Decisão Clínica",
    description:
      "O mapa visual da conduta: a partir de cada achado, o caminho a seguir — aprofundar, encaminhar ou acompanhar. Para consultar durante o atendimento.",
    tag: "Item 2",
    isBonus: false,
  },
  {
    title: "Guia de Entrevista com o Familiar",
    description:
      "As 10 perguntas que revelam mudanças sutis de comportamento e funcionalidade que o idoso não relata — muitas vezes, o dado mais importante da triagem.",
    tag: "Bônus 1",
    isBonus: true,
  },
  {
    title: "Template de Relatório Técnico (Word editável)",
    description:
      "O modelo de documento para comunicar seus achados ao geriatra ou neurologista com estrutura e vocabulário que a rede médica reconhece. Preencha e envie.",
    tag: "Bônus 2",
    isBonus: true,
  },
  {
    title: "Ficha de Evolução de Prontuário",
    description:
      "Resumo de escores em uma página A4, para arquivamento rápido e resguardo ético do seu prontuário.",
    tag: "Bônus 3",
    isBonus: true,
  },
];

/** FAQ — usado na seção de perguntas e no JSON-LD (FAQPage). Copy oficial. */
export const faqItems = [
  {
    question: "Este checklist substitui a avaliação neuropsicológica completa?",
    answer:
      "Não — e nenhum material sério prometeria isso. Ele estrutura a triagem: a etapa que define se há indicação de avaliação aprofundada, encaminhamento médico ou acompanhamento. A decisão diagnóstica sobre demências é médica e multidisciplinar.",
  },
  {
    question: "Preciso ser neuropsicólogo(a) para usar?",
    answer:
      "Não. O material foi desenhado para psicólogos clínicos em geral. Os instrumentos e critérios utilizados estão dentro do escopo de atuação do psicólogo, e o guia orienta exatamente quando o caso pede um especialista.",
  },
  {
    question: "Como recebo o acesso?",
    answer:
      "Imediatamente após a confirmação do pagamento, você recebe por e-mail o acesso a todos os arquivos (PDF + Word editável) pela plataforma Hotmart. O acesso é vitalício, incluindo atualizações do material.",
  },
  {
    question: "E se não for o que eu esperava?",
    answer:
      "Você tem 7 dias de garantia incondicional. Basta solicitar o reembolso pela própria Hotmart e receberá 100% do valor, sem perguntas.",
  },
  {
    question: "Quais as formas de pagamento?",
    answer:
      "Cartão de crédito (em até 12x), Pix e boleto, processados com segurança pela Hotmart.",
  },
  {
    question: "Posso usar o template de relatório no meu consultório?",
    answer:
      "Sim — o template é editável e foi feito para isso. Você adapta com seus dados, seu CRP e o caso concreto.",
  },
];
