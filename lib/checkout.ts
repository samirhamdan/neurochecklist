/**
 * Utilidades de checkout: preservação de UTM + eventos de rastreamento.
 *
 * Fluxo de atribuição:
 * 1. Na primeira visita, <Analytics /> salva os parâmetros utm_* (e src/sck,
 *    usados pela Hotmart) no sessionStorage.
 * 2. No clique de qualquer CTA, os parâmetros são anexados ao link do
 *    checkout Hotmart — a Hotmart captura utm_* para atribuição de
 *    campanhas e afiliados.
 */

import { site } from "./site";

const TRACKED_PARAMS = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
  "src",
  "sck",
];

const STORAGE_KEY = "nc_utm_params";

/** Chamado uma vez no carregamento da página (em <Analytics />). */
export function captureUtmParams(): void {
  if (typeof window === "undefined") return;
  try {
    const current = new URLSearchParams(window.location.search);
    const stored: Record<string, string> = JSON.parse(
      sessionStorage.getItem(STORAGE_KEY) || "{}"
    );
    let changed = false;
    for (const key of TRACKED_PARAMS) {
      const value = current.get(key);
      if (value) {
        stored[key] = value;
        changed = true;
      }
    }
    if (changed) sessionStorage.setItem(STORAGE_KEY, JSON.stringify(stored));
  } catch {
    // sessionStorage indisponível (modo privado etc.) — segue sem UTM
  }
}

/** Monta a URL final do checkout com os UTMs preservados. */
export function getCheckoutUrl(): string {
  if (typeof window === "undefined") return site.checkoutUrl;
  try {
    const stored: Record<string, string> = JSON.parse(
      sessionStorage.getItem(STORAGE_KEY) || "{}"
    );
    const url = new URL(site.checkoutUrl);
    for (const [key, value] of Object.entries(stored)) {
      url.searchParams.set(key, value);
    }
    return url.toString();
  } catch {
    return site.checkoutUrl;
  }
}

declare global {
  interface Window {
    fbq?: (...args: unknown[]) => void;
    gtag?: (...args: unknown[]) => void;
  }
}

/**
 * Dispara os eventos de intenção de compra no clique do CTA.
 * @param location identificador da posição do CTA na página (ex.: "hero")
 */
export function trackCheckoutClick(location: string): void {
  if (typeof window === "undefined") return;

  // Meta Pixel — InitiateCheckout
  window.fbq?.("track", "InitiateCheckout", {
    content_name: site.productFullName,
    content_category: "infoproduto",
    currency: site.price.currency,
    value: site.price.fullNumber,
  });

  // GA4 — begin_checkout + evento custom com a posição do CTA
  window.gtag?.("event", "begin_checkout", {
    currency: site.price.currency,
    value: site.price.fullNumber,
    items: [{ item_name: site.productFullName }],
  });
  window.gtag?.("event", "cta_click", { cta_location: location });
}
