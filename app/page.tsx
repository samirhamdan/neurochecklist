import Nav from "@/components/Nav";
import Hero from "@/components/Hero";
import CredibilityBar from "@/components/CredibilityBar";
import PainSection from "@/components/PainSection";
import MethodSection from "@/components/MethodSection";
import AuthorSection from "@/components/AuthorSection";
import AudienceSection from "@/components/AudienceSection";
import FaqSection from "@/components/FaqSection";
import OfferSection from "@/components/OfferSection";
import Footer from "@/components/Footer";
import StickyCta from "@/components/StickyCta";
import RevealObserver from "@/components/RevealObserver";
import { site, faqItems } from "@/lib/site";
// import Testimonials from "@/components/Testimonials";
// import LimitedBonusBanner from "@/components/LimitedBonusBanner";

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

      <a
        className="absolute -left-[9999px] top-0 z-[100] bg-ink px-[18px] py-3 text-[.9rem] text-white no-underline focus:left-3 focus:top-3"
        href="#conteudo"
      >
        Ir para o conteúdo
      </a>

      <Nav />

      <main>
        <Hero />
        <CredibilityBar />
        <PainSection />
        <MethodSection />

        {/* <Testimonials /> */}

        <AuthorSection />
        <AudienceSection />
        <FaqSection />
        <OfferSection />
      </main>

      <Footer />
      <StickyCta />
      <RevealObserver />
    </>
  );
}
