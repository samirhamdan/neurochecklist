"use client";

import { useEffect } from "react";
import Script from "next/script";
import { captureUtmParams } from "@/lib/checkout";

/**
 * Rastreamento: Meta Pixel + Google Analytics 4.
 *
 * Os IDs vêm de variáveis de ambiente ([PREENCHER] no .env.local / Vercel):
 *   NEXT_PUBLIC_META_PIXEL_ID — Meta Pixel
 *   NEXT_PUBLIC_GA4_ID        — GA4 Measurement ID (G-XXXXXXXXXX)
 *
 * Sem os IDs, nada é carregado — a página funciona normalmente.
 *
 * Eventos disparados:
 *   Meta Pixel: PageView + ViewContent (carga) e InitiateCheckout (clique no CTA)
 *   GA4: page_view (automático), begin_checkout + cta_click (clique no CTA)
 */
const PIXEL_ID = process.env.NEXT_PUBLIC_META_PIXEL_ID;
const GA4_ID = process.env.NEXT_PUBLIC_GA4_ID;

export default function Analytics() {
  // Captura utm_* / src / sck da URL para repassar ao checkout Hotmart
  useEffect(() => {
    captureUtmParams();
  }, []);

  return (
    <>
      {PIXEL_ID && (
        <Script id="meta-pixel" strategy="afterInteractive">
          {`
            !function(f,b,e,v,n,t,s)
            {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
            n.callMethod.apply(n,arguments):n.queue.push(arguments)};
            if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
            n.queue=[];t=b.createElement(e);t.async=!0;
            t.src=v;s=b.getElementsByTagName(e)[0];
            s.parentNode.insertBefore(t,s)}(window, document,'script',
            'https://connect.facebook.net/en_US/fbevents.js');
            fbq('init', '${PIXEL_ID}');
            fbq('track', 'PageView');
            fbq('track', 'ViewContent', {
              content_name: 'NeuroChecklist — Landing Page',
              content_category: 'infoproduto'
            });
          `}
        </Script>
      )}

      {GA4_ID && (
        <>
          <Script
            src={`https://www.googletagmanager.com/gtag/js?id=${GA4_ID}`}
            strategy="afterInteractive"
          />
          <Script id="ga4" strategy="afterInteractive">
            {`
              window.dataLayer = window.dataLayer || [];
              function gtag(){dataLayer.push(arguments);}
              window.gtag = gtag;
              gtag('js', new Date());
              gtag('config', '${GA4_ID}');
            `}
          </Script>
        </>
      )}
    </>
  );
}
