"""Testes do gerador de letra caixa (SVG -> STL)."""

import math
import unittest
from unittest import mock

from morumbi3d.letras import GeometriaInvalida, carregar_faces, gerar_de_svg
from morumbi3d.letras import geom2d as g
from morumbi3d.letras.cortar import cortar, cortar_para_caber, sugerir_cortes
from morumbi3d.letras.geom2d import circulo, montar_faces, triangular
from morumbi3d.letras.solid import (
    costurar_juntas_t, escalar_para_altura, escrever_stl, gerar,
)
from morumbi3d.letras.svg import carregar_svg, ler_path, ler_transform
from morumbi3d.mesh import analisar_arquivo, analisar_triangulos

from .ajuda import config_temporaria

QUADRADO = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0), (0.0, 100.0)]
FURO = [(30.0, 30.0), (30.0, 70.0), (70.0, 70.0), (70.0, 30.0)]
LETRA_B = [
    [(0.0, 0.0), (60.0, 0.0), (60.0, 100.0), (0.0, 100.0)],
    [(12.0, 12.0), (12.0, 44.0), (48.0, 44.0), (48.0, 12.0)],
    [(12.0, 56.0), (12.0, 88.0), (48.0, 88.0), (48.0, 56.0)],
]


def area_dos_triangulos(triangulos) -> float:
    return sum(abs(g._cruz(a, b, c)) / 2.0 for a, b, c in triangulos)


class TesteGeometria2D(unittest.TestCase):
    def test_orientacao(self):
        self.assertTrue(g.anti_horario(QUADRADO))
        self.assertFalse(g.anti_horario(QUADRADO[::-1]))
        self.assertAlmostEqual(g.area_assinada(QUADRADO), 10000.0)

    def test_furo_vira_furo_e_externo_vira_externo(self):
        faces = montar_faces([QUADRADO, FURO])
        self.assertEqual(len(faces), 1)
        self.assertEqual(len(faces[0].furos), 1)
        self.assertAlmostEqual(faces[0].area(), 10000.0 - 1600.0)

    def test_letra_com_dois_furos(self):
        """O ponto de teste do contorno externo nao pode cair dentro de um furo."""

        faces = montar_faces(LETRA_B)
        self.assertEqual(len(faces), 1, "o 'B' e uma face so, com duas barrigas")
        self.assertEqual(len(faces[0].furos), 2)
        self.assertAlmostEqual(faces[0].area(), 6000.0 - 2 * 1152.0)

    def test_ilha_dentro_do_furo(self):
        faces = montar_faces([circulo((0, 0), 20, 48), circulo((0, 0), 14, 48), circulo((0, 0), 6, 48)])
        self.assertEqual(len(faces), 2, "a ilha central e material de novo")

    def test_erosao_encolhe_externo_e_engorda_furo(self):
        face = montar_faces([QUADRADO, FURO])[0]
        cavidade = g.erodir_face(face, 5.0)
        self.assertIsNotNone(cavidade)
        self.assertAlmostEqual(g.caixa(cavidade.externo)[0], 5.0)
        self.assertAlmostEqual(g.caixa(cavidade.furos[0])[0], 25.0)

    def test_erosao_recusa_parede_que_nao_cabe(self):
        face = montar_faces([QUADRADO, FURO])[0]  # traco de 30 mm
        self.assertIsNotNone(g.erodir_face(face, 14.0))
        self.assertIsNone(g.erodir_face(face, 16.0), "parede maior que meio traco")

    def test_triangulacao_conserva_area(self):
        casos = [
            ([QUADRADO], 10000.0),
            ([QUADRADO, FURO], 8400.0),
            (LETRA_B, 3696.0),
            ([circulo((0, 0), 20, 64), circulo((0, 0), 12, 64)], math.pi * (400 - 144)),
        ]
        for aneis, esperado in casos:
            with self.subTest(esperado=esperado):
                tris = [t for f in montar_faces(aneis) for t in triangular(f)]
                self.assertAlmostEqual(area_dos_triangulos(tris), esperado, delta=esperado * 0.01)

    def test_simplificar_reduz_pontos_mantendo_forma(self):
        anel = circulo((0, 0), 100, 512)
        reduzido = g.simplificar(anel, 0.05)
        self.assertLess(len(reduzido), len(anel))
        self.assertAlmostEqual(
            abs(g.area_assinada(reduzido)), abs(g.area_assinada(anel)),
            delta=abs(g.area_assinada(anel)) * 0.01,
        )


class TesteSVG(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()

    def escrever(self, conteudo: str):
        caminho = self.cfg.raiz / "teste.svg"
        caminho.write_text(conteudo, encoding="utf-8")
        return caminho

    def test_formas_basicas_e_furo_por_subcaminho(self):
        caminho = self.escrever(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
            '<rect x="0" y="0" width="80" height="80"/>'
            '<path d="M100,10 L180,10 L180,90 L100,90 Z M120,30 L160,30 L160,70 L120,70 Z"/>'
            "</svg>"
        )
        faces = montar_faces(carregar_svg(caminho, 0.05))
        self.assertEqual(len(faces), 2)
        areas = sorted(round(f.area()) for f in faces)
        self.assertEqual(areas, [4800, 6400])

    def test_eixo_y_e_invertido(self):
        caminho = self.escrever(
            '<svg xmlns="http://www.w3.org/2000/svg"><rect x="0" y="10" width="10" height="20"/></svg>'
        )
        anel = carregar_svg(caminho)[0]
        self.assertLess(max(p[1] for p in anel), 0, "SVG cresce para baixo, o solido para cima")

    def test_transformacoes(self):
        self.assertEqual(ler_transform(None), (1, 0, 0, 1, 0, 0))
        m = ler_transform("translate(10,20)")
        self.assertEqual(m[4:], (10.0, 20.0))
        caminho = self.escrever(
            '<svg xmlns="http://www.w3.org/2000/svg">'
            '<g transform="translate(100,0)"><rect x="0" y="0" width="10" height="10"/></g></svg>'
        )
        anel = carregar_svg(caminho)[0]
        self.assertAlmostEqual(min(p[0] for p in anel), 100.0)

    def test_curvas_e_arco(self):
        cubica = ler_path("M0,0 C 0,50 50,50 50,0 Z", 0.01)
        self.assertGreater(len(cubica[0]), 20, "curva precisa virar muitos segmentos")
        arco = ler_path("M0,0 A 25,25 0 1 1 50,0 Z", 0.01)
        self.assertAlmostEqual(abs(g.area_assinada(arco[0])), math.pi * 25**2 / 2, delta=5.0)

    def test_quadratica_e_atalhos(self):
        self.assertTrue(ler_path("M0,0 Q 25,50 50,0 Z", 0.05))
        self.assertTrue(ler_path("M0,0 C 0,30 20,30 20,0 S 40,-30 40,0 Z", 0.05))

    def test_svg_sem_contorno_reclama(self):
        caminho = self.escrever('<svg xmlns="http://www.w3.org/2000/svg"><text>abc</text></svg>')
        with self.assertRaises(GeometriaInvalida) as ctx:
            carregar_faces(caminho)
        self.assertIn("curvas", str(ctx.exception), "a mensagem tem que ensinar o conserto")

    def test_arquivo_invalido(self):
        caminho = self.escrever("nao e xml")
        with self.assertRaises(ValueError):
            carregar_svg(caminho)
        with self.assertRaises(FileNotFoundError):
            carregar_svg(self.cfg.raiz / "sumiu.svg")


class TesteSolido(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()

    def conferir(self, letra):
        relatorio = analisar_triangulos(letra.triangulos, self.cfg)
        self.assertTrue(relatorio.fechada, f"malha aberta: {relatorio.arestas_abertas} arestas")
        self.assertEqual(relatorio.arestas_nao_manifold, 0)
        return relatorio

    def test_macica_fechada_e_volume_certo(self):
        faces = montar_faces([QUADRADO])
        relatorio = self.conferir(gerar(faces, profundidade=10, macica=True))
        self.assertAlmostEqual(relatorio.volume_cm3, 100.0, places=2)  # 10x10x1 cm

    def test_caixa_e_mais_leve_que_macica(self):
        faces = montar_faces([QUADRADO])
        macica = analisar_triangulos(gerar(faces, profundidade=20, macica=True).triangulos, self.cfg)
        caixa = analisar_triangulos(
            gerar(faces, profundidade=20, parede=2, frente=2).triangulos, self.cfg
        )
        self.assertLess(caixa.volume_cm3, macica.volume_cm3 / 2)

    def test_todas_as_combinacoes_ficam_fechadas(self):
        casos = {
            "quadrado caixa": (montar_faces([QUADRADO]), {}),
            "quadrado chanfro": (montar_faces([QUADRADO]), {"chanfro": 1.5, "frente": 3}),
            "quadrado furos": (montar_faces([QUADRADO]), {"furos": [(30, 30), (70, 70)]}),
            "O caixa": (montar_faces([circulo((0, 0), 50, 64), circulo((0, 0), 35, 64)]), {}),
            "O chanfro": (
                montar_faces([circulo((0, 0), 50, 64), circulo((0, 0), 35, 64)]),
                {"chanfro": 1.0, "frente": 3},
            ),
            "B caixa": (montar_faces(LETRA_B), {}),
            "B furos+chanfro": (
                montar_faces(LETRA_B),
                {"furos": [(6, 50)], "chanfro": 1.0, "frente": 3},
            ),
            "macica furos": (montar_faces([QUADRADO]), {"macica": True, "furos": [(50, 50)]}),
        }
        for nome, (faces, extra) in casos.items():
            with self.subTest(caso=nome):
                opcoes = {"profundidade": 20, "parede": 2, "frente": 2, **extra}
                relatorio = self.conferir(gerar(faces, **opcoes))
                self.assertEqual(relatorio.partes_soltas, 1)

    def test_traco_fino_sai_macico_com_aviso(self):
        fino = montar_faces([[(0, 0), (100, 0), (100, 3), (0, 3)]])
        letra = gerar(fino, profundidade=15, parede=2)
        self.assertTrue(letra.macica)
        self.assertTrue(any("fino" in a for a in letra.avisos))
        self.conferir(letra)

    def test_chanfro_tira_material_da_frente(self):
        faces = montar_faces([QUADRADO])
        sem = analisar_triangulos(gerar(faces, profundidade=20, macica=True).triangulos, self.cfg)
        com = analisar_triangulos(
            gerar(faces, profundidade=20, macica=True, chanfro=2.0).triangulos, self.cfg
        )
        self.assertLess(com.volume_cm3, sem.volume_cm3)

    def test_furo_fora_da_area_e_recusado_com_aviso(self):
        letra = gerar(montar_faces([QUADRADO]), profundidade=20, furos=[(5000, 5000)])
        self.assertEqual(letra.furos, [])
        self.assertTrue(any("cai fora" in a for a in letra.avisos))

    def test_furos_automaticos_nao_geram_aviso(self):
        letra = gerar(
            montar_faces([QUADRADO]), profundidade=20, furos_auto=True, espacamento_furo=30
        )
        self.assertGreater(len(letra.furos), 1)
        self.assertEqual([a for a in letra.avisos if "furo" in a], [])

    def test_parametros_impossiveis(self):
        faces = montar_faces([QUADRADO])
        with self.assertRaises(GeometriaInvalida):
            gerar(faces, profundidade=0)
        with self.assertRaises(GeometriaInvalida):
            gerar(faces, profundidade=10, chanfro=15)
        with self.assertRaises(GeometriaInvalida):
            gerar([], profundidade=10)

    def test_costura_de_junta_t(self):
        # Um quadrado partido ao meio de um lado so: o vizinho tem a aresta inteira.
        triangulos = [
            ((0, 0, 0), (2, 0, 0), (1, 1, 0)),
            ((0, 0, 0), (1, 0, 0), (0, -1, 0)),
            ((1, 0, 0), (2, 0, 0), (0, -1, 0)),
        ]
        antes = analisar_triangulos(triangulos, self.cfg)
        costurados, divisoes = costurar_juntas_t(triangulos)
        self.assertEqual(divisoes, 1)
        depois = analisar_triangulos(costurados, self.cfg)
        self.assertLess(depois.arestas_abertas, antes.arestas_abertas)

    def test_escala_para_altura(self):
        faces = escalar_para_altura(montar_faces([QUADRADO]), 250.0)
        x0, y0, x1, y1 = g.caixa(faces[0].externo)
        self.assertAlmostEqual(y1 - y0, 250.0)
        self.assertAlmostEqual(x0, 0.0)
        self.assertAlmostEqual(y0, 0.0)

    def test_stl_gravado_volta_igual(self):
        letra = gerar(montar_faces([QUADRADO]), profundidade=10, macica=True)
        caminho = escrever_stl(letra.triangulos, self.cfg.raiz / "p.stl")
        relatorio = analisar_arquivo(caminho, self.cfg)
        self.assertTrue(relatorio.fechada)
        self.assertAlmostEqual(relatorio.volume_cm3, 100.0, places=1)


class TesteCorte(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()

    def test_sugestao_de_cortes(self):
        self.assertEqual(sugerir_cortes(200, 25, 253, 253), [])
        self.assertEqual(sugerir_cortes(400, 25, 253, 253), [200.0])
        self.assertEqual(len(sugerir_cortes(1000, 25, 253, 253)), 3)

    def _conferir_corte(self, faces, eixo, posicoes, **extra):
        letra = gerar(faces, profundidade=25, parede=3, frente=3, **extra)
        inteira = analisar_triangulos(letra.triangulos, self.cfg)
        pedacos, _ = cortar(letra.triangulos, eixo, posicoes)
        soma = 0.0
        for pedaco in pedacos:
            relatorio = analisar_triangulos(pedaco, self.cfg)
            self.assertTrue(relatorio.fechada, "pedaco saiu aberto")
            self.assertEqual(relatorio.arestas_nao_manifold, 0)
            soma += relatorio.volume_cm3
        self.assertAlmostEqual(soma, inteira.volume_cm3, delta=inteira.volume_cm3 * 0.001)
        return pedacos

    def test_corte_conserva_o_volume(self):
        self._conferir_corte(montar_faces([[(0, 0), (400, 0), (400, 150), (0, 150)]]), 0, [200.0])

    def test_corte_em_letra_com_contra_forma(self):
        letra_o = montar_faces([circulo((200, 200), 200, 96), circulo((200, 200), 140, 96)])
        self._conferir_corte(letra_o, 0, [133.0, 266.0])

    def test_corte_no_eixo_de_simetria(self):
        """Caso degenerado: o plano passa rasante aos vertices."""

        letra_o = montar_faces([circulo((200, 200), 200, 96), circulo((200, 200), 140, 96)])
        self._conferir_corte(letra_o, 0, [200.0])

    def test_corte_em_y(self):
        self._conferir_corte(montar_faces([[(0, 0), (150, 0), (150, 400), (0, 400)]]), 1, [200.0])

    def test_corte_atravessando_furo_de_fixacao(self):
        self._conferir_corte(
            montar_faces([[(0, 0), (400, 0), (400, 150), (0, 150)]]),
            0, [100.0], furos=[(100, 75)], diametro_furo=8,
        )

    def test_cortar_para_caber_resolve_os_dois_eixos(self):
        letra = gerar(
            montar_faces([[(0, 0), (600, 0), (600, 500), (0, 500)]]),
            profundidade=25, parede=3, frente=3,
        )
        pedacos, avisos = cortar_para_caber(letra.triangulos, 253.0, 253.0)
        self.assertGreaterEqual(len(pedacos), 6)
        for pedaco in pedacos:
            relatorio = analisar_triangulos(pedaco, self.cfg)
            self.assertTrue(relatorio.cabe_na_mesa, f"{relatorio.dimensoes_mm} nao cabe")
            self.assertTrue(relatorio.fechada)
        self.assertTrue(any("largura" in a for a in avisos))
        self.assertTrue(any("altura" in a for a in avisos))

    def test_sem_corte_devolve_a_peca_inteira(self):
        letra = gerar(montar_faces([QUADRADO]), profundidade=20)
        pedacos, avisos = cortar(letra.triangulos, 0, [])
        self.assertEqual(len(pedacos), 1)
        self.assertEqual(avisos, [])


class TesteFluxoCompleto(unittest.TestCase):
    def setUp(self):
        self.cfg = config_temporaria()
        self.svg = self.cfg.raiz / "logo.svg"
        self.svg.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100">'
            '<path d="M20,10 L80,10 L80,90 L20,90 Z M35,25 L65,25 L65,75 L35,75 Z"/>'
            '<circle cx="150" cy="50" r="40"/><circle cx="150" cy="50" r="24"/>'
            '<path d="M210,10 L280,10 L280,90 L210,90 Z"/></svg>',
            encoding="utf-8",
        )

    def test_gera_stl_conferido(self):
        resultado = gerar_de_svg(self.svg, self.cfg, altura=150, profundidade=25, chanfro=1.0)
        self.assertTrue(resultado.pedacos)
        self.assertTrue(resultado.tudo_fechado)
        self.assertAlmostEqual(resultado.altura_mm, 150.0, places=1)
        self.assertGreater(resultado.material_g, 0)
        self.assertGreater(resultado.preco_sugerido, resultado.custo)
        for pedaco in resultado.pedacos:
            self.assertTrue(pedaco.arquivo.is_file())
            self.assertGreater(pedaco.arquivo.stat().st_size, 84)
            self.assertTrue(pedaco.relatorio.cabe_na_mesa)

    def test_peca_grande_sai_cortada_e_cada_pedaco_cabe(self):
        resultado = gerar_de_svg(self.svg, self.cfg, altura=400, profundidade=30)
        self.assertGreater(len(resultado.pedacos), 1)
        self.assertTrue(resultado.tudo_fechado)
        for pedaco in resultado.pedacos:
            self.assertTrue(pedaco.relatorio.cabe_na_mesa)
        self.assertTrue(any("cabe" in a or "cortada" in a for a in resultado.avisos))

    def test_sem_cortar_deixa_a_peca_inteira(self):
        resultado = gerar_de_svg(
            self.svg, self.cfg, altura=400, profundidade=30, cortar_para_mesa=False
        )
        self.assertEqual(len(resultado.pedacos), 1)
        self.assertFalse(resultado.pedacos[0].relatorio.cabe_na_mesa)

    def test_furos_automaticos_no_fluxo(self):
        resultado = gerar_de_svg(
            self.svg, self.cfg, altura=200, furos_auto=True, espacamento_furo=50
        )
        self.assertGreater(len(resultado.furos), 0)
        self.assertTrue(resultado.tudo_fechado)

    def test_nome_e_pasta_de_saida(self):
        destino = self.cfg.raiz / "saida"
        resultado = gerar_de_svg(self.svg, self.cfg, altura=120, saida=destino, nome="letreiro")
        self.assertTrue(resultado.pedacos[0].arquivo.is_file())
        self.assertEqual(resultado.pedacos[0].arquivo.parent, destino)
        self.assertIn("letreiro", resultado.pedacos[0].arquivo.name)


if __name__ == "__main__":
    unittest.main()


class TestePonteTrimesh(unittest.TestCase):
    """A ponte opcional para o trimesh (ver morumbi3d/letras/malha.py)."""

    def setUp(self):
        from morumbi3d.letras import malha

        self.malha = malha
        disponivel, motivo = malha.disponivel()
        if not disponivel:
            self.skipTest(f"trimesh indisponivel: {motivo}")
        self.cfg = config_temporaria()

    def test_disponivel_testa_o_caminho_todo(self):
        """Nao basta importar: scipy/networkx/rtree faltam longe da causa."""

        ok, motivo = self.malha.disponivel()
        self.assertTrue(ok)
        self.assertIn("trimesh", motivo)

    def test_ida_e_volta_preserva_a_geometria(self):
        letra = gerar(montar_faces([QUADRADO]), profundidade=10, macica=True)
        malha = self.malha.para_trimesh(letra.triangulos)
        self.assertTrue(malha.is_watertight)
        voltou = self.malha.para_triangulos(malha)
        relatorio = analisar_triangulos(voltou, self.cfg)
        self.assertTrue(relatorio.fechada)
        self.assertAlmostEqual(relatorio.volume_cm3, 100.0, places=2)

    def test_corte_por_um_plano(self):
        letra = gerar(
            montar_faces([[(0, 0), (400, 0), (400, 150), (0, 150)]]),
            profundidade=25, parede=3, frente=3,
        )
        inteira = analisar_triangulos(letra.triangulos, self.cfg)
        partes = self.malha.cortar_um_plano(letra.triangulos, 0, 200.0)
        self.assertIsNotNone(partes)
        self.assertEqual(len(partes), 2)
        soma = 0.0
        for parte in partes:
            relatorio = analisar_triangulos(parte, self.cfg)
            self.assertTrue(relatorio.fechada)
            soma += relatorio.volume_cm3
        self.assertAlmostEqual(soma, inteira.volume_cm3, delta=inteira.volume_cm3 * 0.001)

    def test_plano_fora_do_material_devolve_uma_peca_so(self):
        """Plano no vazio entre duas letras nao e erro: nao corta nada."""

        letra = gerar(montar_faces([QUADRADO]), profundidade=20)
        partes = self.malha.cortar_um_plano(letra.triangulos, 0, 500.0)
        self.assertIsNotNone(partes)
        self.assertEqual(len(partes), 1)

    def test_pacote_funciona_sem_trimesh(self):
        """A ponte e opcional: sem ela o cortador proprio assume."""

        with mock.patch.object(self.malha, "_estado", {"ok": False, "motivo": "teste"}):
            self.assertIsNone(self.malha.cortar_um_plano([], 0, 0.0))
        letra = gerar(
            montar_faces([[(0, 0), (400, 0), (400, 150), (0, 150)]]),
            profundidade=25, parede=3, frente=3,
        )
        with mock.patch("morumbi3d.letras.cortar.cortar_um_plano", return_value=None):
            pedacos, _ = cortar(letra.triangulos, 0, [200.0])
        self.assertEqual(len(pedacos), 2)
        for pedaco in pedacos:
            self.assertTrue(analisar_triangulos(pedaco, self.cfg).fechada)
