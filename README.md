# NeuroChecklist — Landing Page

Página de vendas estática do **Checklist de Triagem Neuropsicológica — Guia
Prático para Psicólogos** (Prof. Dr. Amer C. Hamdan). Next.js 14 (App Router) +
Tailwind CSS, pronta para deploy na Vercel.

## Rodar localmente

```bash
npm install
npm run dev
```

Abra http://localhost:3000. Para simular produção: `npm run build && npm start`.

## Configurar o .env

Copie `.env.example` para `.env.local` e preencha:

| Variável | O que é |
| --- | --- |
| `NEXT_PUBLIC_META_PIXEL_ID` | ID do Meta Pixel (Gerenciador de Eventos) |
| `NEXT_PUBLIC_GA4_ID` | Measurement ID do GA4 (`G-XXXXXXXXXX`) |
| `NEXT_PUBLIC_SITE_URL` | URL pública final (canonical/Open Graph) |

Sem os IDs, os scripts de rastreamento simplesmente não carregam — a página
funciona normalmente.

**Eventos configurados:** Meta Pixel dispara `PageView` + `ViewContent` na
carga e `InitiateCheckout` no clique de qualquer CTA; o GA4 dispara
`begin_checkout` e `cta_click` (com o parâmetro `cta_location` identificando a
posição do botão). Parâmetros `utm_*`, `src` e `sck` da URL são preservados e
repassados ao link do checkout Hotmart (atribuição de campanhas/afiliados).

## Deploy na Vercel

1. Suba o repositório para o GitHub (ou GitLab/Bitbucket);
2. Em [vercel.com/new](https://vercel.com/new), importe o repositório — a
   Vercel detecta Next.js automaticamente, sem configuração extra (não é
   necessário `vercel.json`);
3. Em **Settings → Environment Variables**, cadastre as três variáveis acima;
4. Deploy. Depois, aponte o domínio próprio em **Settings → Domains** e
   atualize `NEXT_PUBLIC_SITE_URL`.

Alternativa via CLI: `npx vercel` na raiz do projeto.

## Onde editar cada coisa

| O quê | Onde |
| --- | --- |
| **Preço (R$ 197, 12× de R$ 20,37), link do checkout, FAQ, itens do kit** | [`lib/site.ts`](lib/site.ts) — configuração central |
| Headline do hero (3 variações A/B) | [`components/Hero.tsx`](components/Hero.tsx) → `ACTIVE_HEADLINE` |
| Copy das seções | `components/*.tsx` (uma seção por arquivo) |
| Ordem das seções | [`app/page.tsx`](app/page.tsx) |
| SEO (title, description, OG) | [`lib/site.ts`](lib/site.ts) + [`app/layout.tsx`](app/layout.tsx) |
| Imagem de compartilhamento (og:image) | [`app/opengraph-image.tsx`](app/opengraph-image.tsx) (gerada no build) |
| Cores/tokens de design | [`tailwind.config.ts`](tailwind.config.ts) |

## Design

A paleta é baseada na capa do produto — azul escuro (`ink: #0F172B`) como base,
com acentos em âmbar (`amber: #C4792E`) para destaque. Tipografia:
**Instrument Serif** (títulos), **IBM Plex Sans** (corpo), **IBM Plex Mono**
(rótulos e microcopy).

As imagens do autor (`public/prof-hamdan.webp`) e da capa do produto
(`public/capa-neurochecklist.webp`) já estão no repositório.

## Pendências marcadas com `[PREENCHER]`

Busque por `PREENCHER` no código. Resumo:

- **IDs de rastreamento** — `.env.local` / variáveis na Vercel;
- **Política de Privacidade e Termos de Uso** — `app/politica-de-privacidade/`
  e `app/termos-de-uso/` (texto jurídico definitivo antes de tráfego pago).

## Componentes desativados (ativar só quando for real)

- **Depoimentos** — `components/Testimonials.tsx`: preencha apenas com
  depoimentos reais e autorizados (nome + CRP + foto), depois descomente
  `<Testimonials />` em `app/page.tsx`;
- **Bônus por tempo limitado** — `components/LimitedBonusBanner.tsx`: preencha
  `CAMPAIGN` com prazo real e descomente `<LimitedBonusBanner />` em
  `app/page.tsx`;
- **Ancoragem de preço riscado** ("De R$ 497") — comentada em
  `components/OfferSection.tsx`; exibir apenas se o preço anterior for real.

## Diretrizes de copy (não remover)

O produto é ferramenta de **triagem** e apoio ao raciocínio clínico — a página
não promete diagnóstico nem resultado garantido (normas de publicidade do CFP).
O aviso de escopo aparece na seção do método e no rodapé; mantenha-o em
qualquer revisão de copy.
