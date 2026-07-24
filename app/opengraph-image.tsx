import { ImageResponse } from "next/og";

/**
 * og:image gerada em build time pelo Next (1200x630).
 * Para usar uma arte própria, delete este arquivo e adicione
 * /app/opengraph-image.png (1200x630).
 */
// Runtime edge: necessário para o @vercel/og (o runtime Node falha no build em Windows)
export const runtime = "edge";

export const alt =
  "NeuroChecklist — Protocolo de Triagem Neuropsicológica para Psicólogos";
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OgImage() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "80px",
          background: "linear-gradient(135deg, #0a2740 0%, #0e3a5d 60%, #1f5270 100%)",
          color: "#ffffff",
          fontFamily: "sans-serif",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "16px",
            fontSize: 28,
            color: "#8dbcd6",
            textTransform: "uppercase",
            letterSpacing: "4px",
          }}
        >
          NeuroChecklist
        </div>
        <div
          style={{
            marginTop: 28,
            fontSize: 58,
            fontWeight: 700,
            lineHeight: 1.15,
            maxWidth: 980,
          }}
        >
          Da suspeita à conduta em 2 sessões: triagem neuropsicológica
          estruturada
        </div>
        <div style={{ marginTop: 32, fontSize: 30, color: "#bcd8e8" }}>
          Por Prof. Dr. Amer C. Hamdan · UFPR
        </div>
        <div
          style={{
            marginTop: 48,
            display: "flex",
            alignItems: "center",
            gap: "12px",
            fontSize: 26,
            color: "#0f766e",
            background: "#f0fdf9",
            padding: "14px 28px",
            borderRadius: 999,
            width: "fit-content",
            fontWeight: 600,
          }}
        >
          Guia prático para psicólogos que atendem idosos
        </div>
      </div>
    ),
    { ...size }
  );
}
