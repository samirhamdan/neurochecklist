/**
 * ============================================================
 * BANNER DE BÔNUS POR TEMPO LIMITADO — DESATIVADO
 *
 * Ativar SOMENTE quando houver uma campanha real com prazo real
 * (escassez fictícia é vedada pela diretriz do projeto e fere a
 * confiança de um público técnico).
 *
 * Para ativar:
 * 1. Preencha CAMPAIGN abaixo com o bônus e a data-limite reais;
 * 2. Em app/page.tsx, descomente a linha <LimitedBonusBanner />.
 *
 * O banner some sozinho depois da data-limite.
 * ============================================================
 */
"use client";

import { useEffect, useState } from "react";

const CAMPAIGN: { bonus: string; deadline: string } | null = null;
// Exemplo (apenas com campanha real):
// const CAMPAIGN = {
//   bonus: "Aula ao vivo de discussão de casos com o Prof. Hamdan",
//   deadline: "2026-08-31T23:59:59-03:00",
// };

export default function LimitedBonusBanner() {
  const [expired, setExpired] = useState(true);

  useEffect(() => {
    if (CAMPAIGN) setExpired(Date.now() > new Date(CAMPAIGN.deadline).getTime());
  }, []);

  if (!CAMPAIGN || expired) return null;

  const formatted = new Date(CAMPAIGN.deadline).toLocaleDateString("pt-BR", {
    day: "2-digit",
    month: "long",
  });

  return (
    <div className="bg-accent-700 text-white">
      <div className="section-container py-3 text-center text-sm sm:text-base">
        <strong>Bônus desta turma:</strong> {CAMPAIGN.bonus} — para inscrições
        até {formatted}.
      </div>
    </div>
  );
}
