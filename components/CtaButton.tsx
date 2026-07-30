"use client";

import { useEffect, useState } from "react";
import { getCheckoutUrl, trackCheckoutClick } from "@/lib/checkout";
import { site } from "@/lib/site";

type Props = {
  location: string;
  children: React.ReactNode;
  variant?: "primary" | "ghost";
  size?: "md" | "lg";
  className?: string;
};

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
    "inline-block font-medium no-underline transition-all duration-[.18s] hover:-translate-y-0.5 text-center";
  const variants = {
    primary: "bg-ink text-paper-warm border border-ink hover:bg-amber hover:border-amber",
    ghost: "bg-transparent text-ink border border-ink hover:bg-ink hover:text-paper-warm",
  };
  const sizes = {
    md: "px-5 py-[11px] text-[.9rem]",
    lg: "px-[30px] py-4 text-[1.02rem] tracking-[.01em]",
  };

  return (
    <a
      href={href}
      onClick={() => trackCheckoutClick(location)}
      className={`${base} ${variants[variant]} ${sizes[size]} ${className}`}
      style={{ borderRadius: 2 }}
      aria-label={`Ir para o checkout seguro da Hotmart — ${site.price.full} ou ${site.price.installments}`}
    >
      {children}
    </a>
  );
}
