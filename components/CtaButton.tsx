"use client";

import { useEffect, useState } from "react";
import { getCheckoutUrl, trackCheckoutClick } from "@/lib/checkout";
import { site } from "@/lib/site";

type Props = {
  /** Identificador da posição do CTA (vai para o GA4 como cta_location) */
  location: string;
  children: React.ReactNode;
  variant?: "primary" | "outline";
  size?: "md" | "lg";
  className?: string;
};

/**
 * Botão de CTA — todos apontam para o checkout Hotmart.
 * No mount, o href é atualizado com os UTMs preservados da sessão;
 * no clique, dispara InitiateCheckout (Meta) e begin_checkout/cta_click (GA4).
 */
export default function CtaButton({
  location,
  children,
  variant = "primary",
  size = "lg",
  className = "",
}: Props) {
  const [href, setHref] = useState(site.checkoutUrl);

  useEffect(() => {
    setHref(getCheckoutUrl());
  }, []);

  const base =
    "inline-flex items-center justify-center gap-2 rounded-xl font-semibold transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0 focus:outline-none focus-visible:ring-2 focus-visible:ring-accent-500 focus-visible:ring-offset-2 text-center";
  const variants = {
    primary:
      "bg-accent-700 text-white hover:bg-accent-600 shadow-lg shadow-accent-700/25 hover:shadow-xl hover:shadow-accent-700/30",
    outline:
      "border-2 border-brand-900 text-brand-900 hover:bg-brand-50",
  };
  const sizes = {
    md: "px-6 py-3 text-base",
    lg: "px-8 py-4 text-lg",
  };

  return (
    <a
      href={href}
      onClick={() => trackCheckoutClick(location)}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      aria-label={`Ir para o checkout seguro da Hotmart — ${site.price.full} ou ${site.price.installments}`}
    >
      {children}
    </a>
  );
}
