import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { site } from "@/lib/site";
import Analytics from "@/components/Analytics";
import "./globals.css";

/**
 * Fonte via next/font: self-hosted no build, com fallback e
 * font-display: swap — sem FOIT, sem request externo em runtime.
 */
const inter = Inter({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-inter",
});

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: site.metaTitle,
  description: site.metaDescription,
  alternates: {
    canonical: "/",
  },
  openGraph: {
    type: "website",
    locale: "pt_BR",
    url: site.url,
    siteName: site.productName,
    title: site.metaTitle,
    description: site.metaDescription,
    // og:image gerada automaticamente pelo Next em app/opengraph-image.tsx
  },
  twitter: {
    card: "summary_large_image",
    title: site.metaTitle,
    description: site.metaDescription,
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="pt-BR" className={inter.variable}>
      <body className="font-sans">
        {children}
        <Analytics />
      </body>
    </html>
  );
}
