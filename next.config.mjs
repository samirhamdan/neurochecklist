/** @type {import('next').NextConfig} */
const nextConfig = {
  // Página 100% estática — o Next gera tudo em build time.
  // Na Vercel o deploy é automático, sem configuração extra.
  reactStrictMode: true,
};

export default nextConfig;
