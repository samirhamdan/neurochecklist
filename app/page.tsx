import Hero from "@/components/Hero";
import CredibilityBar from "@/components/CredibilityBar";
import PainSection from "@/components/PainSection";
import MethodSection from "@/components/MethodSection";
import KitSection from "@/components/KitSection";
import AuthorSection from "@/components/AuthorSection";
import AudienceSection from "@/components/AudienceSection";
import FaqSection from "@/components/FaqSection";
import OfferSection from "@/components/OfferSection";
import SectionCta from "@/components/SectionCta";
import StickyCta from "@/components/StickyCta";
import Footer from "@/components/Footer";
import { site, faqItems } from "@/lib/site";
// import Testimonials from "@/components/Testimonials";        // [PREENCHER] ativar quando houver depoimentos reais (ver components/Testimonials.tsx)
// import LimitedBonusBanner from "@/components/LimitedBonusBanner"; // ativar apenas com campanha real (ver components/LimitedBonusBanner.tsx)

/** Schema.org — Product + Person (autor) + FAQPage */
function JsonLd() {
  const data = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Product",
        name: site.productFullName,
        description: site.metaDescription,
        brand: { "@type": "Brand", name: site.productName },
        offers: {
          "@type": "Offer",
          url: site.url,
          price: site.price.fullNumber,
          priceCurrency: site.price.currency,
          availability: "https://schema.org/InStock",
        },
      },
      {
        "@type": "Person",
        name: "Amer Cavalheiro Hamdan",
        honorificPrefix: "Prof. Dr.",
        jobTitle: "Professor de Neuropsicologia",
        worksFor: {
          "@type": "CollegeOrUniversity",
          name: "Universidade Federal do Paraná",
        },
        alumniOf: [
          { "@type": "CollegeOrUniversity", name: "UNIFESP" },
          { "@type": "CollegeOrUniversity", name: "McGill University" },
        ],
      },
      {
        "@type": "FAQPage",
        mainEntity: faqItems.map((item) => ({
          "@type": "Question",
          name: item.question,
          acceptedAnswer: { "@type": "Answer", text: item.answer },
        })),
      },
    ],
  };

  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{ __html: JSON.stringify(data) }}
    />
  );
}

export default function Page() {
  return (
    <>
      <JsonLd />

      {/* <LimitedBonusBanner /> */}

      <main>
        {/* a. Hero + b. barra de credibilidade */}
        <Hero />
        <CredibilityBar />

        {/* c. A dor + d. a virada */}
        <PainSection />
        <MethodSection />
        <SectionCta
          location="apos-metodo"
          headline="Comece a estruturar sua triagem ainda esta semana."
        />

        {/* e. O que você recebe + f. autoridade */}
        <KitSection />
        <AuthorSection />
        <SectionCta
          location="apos-autor"
          headline="O protocolo de 30 anos de pesquisa, pronto para a sua clínica."
        />

        {/* Depoimentos — ativar apenas com depoimentos reais e autorizados */}
        {/* <Testimonials /> */}

        {/* g. Qualificação + h. FAQ */}
        <AudienceSection />
        <FaqSection />

        {/* i. Oferta final */}
        <OfferSection />
      </main>

      {/* j. Rodapé */}
      <Footer />

      {/* CTA fixo no mobile */}
      <StickyCta />
    </>
  );
}
