# -*- coding: utf-8 -*-
"""O catalogo do que da para CRIAR -- uma tela so, com filtro.

Ate aqui cada gerador era um link solto no menu: "Gerar letreiro", "Gerar
logo". Dois cabem. Doze nao -- e o plano tem doze pela frente. Pior: o menu
escondia o que a casa realmente sabe fazer, porque um link chamado "Gerar
letreiro" nao conta que ali dentro moram seis modelos diferentes.

Entao o catalogo nao lista GERADORES, lista o que da para FAZER. Cada modelo
e uma linha aqui, e a tela filtra por ela.

Duas regras seguram a honestidade desta lista:

  * `rota` vazia significa que ainda nao da para gerar. A tela mostra como
    planejado e nao oferece botao -- botao que nao leva a lugar nenhum e pior
    do que ausencia de botao;
  * um modelo `NO_AR` tem teste que ABRE a rota dele. Cartao que promete e
    rota que responde nao podem viver separados.

Acrescentar um modelo e acrescentar uma linha em MODELOS. Nao ha template
para mexer: a tela e as opcoes de filtro saem daqui.
"""
from __future__ import annotations

from dataclasses import dataclass, field

NO_AR = "no ar"
EM_OBRA = "em construção"

FESTA = "Festa"
IDENTIDADE = "Identidade"
DECORACAO = "Decoração"


@dataclass(frozen=True)
class Modelo:
    """Uma coisa que da para criar. Nao e um gerador: e um produto dele."""

    slug: str
    nome: str
    categoria: str
    resumo: str
    gerador: str            # de qual ferramenta ele sai
    rota: str = ""          # vazio = ainda nao da para gerar
    # Quantas cores o modelo ACEITA -- nao quantas ele tem. A pergunta que o
    # filtro faz e "consigo fazer isso sem trocar filamento?", e cada troca
    # custa 6 g de purga mais o tempo de parar a maquina.
    cores: tuple[int, ...] = (1, 2)
    cores_rotulo: str = ""
    saida: str = "STL"
    nota: str = ""          # o que voce precisa saber ANTES de escolher
    busca: tuple[str, ...] = field(default_factory=tuple)

    @property
    def status(self) -> str:
        return NO_AR if self.rota else EM_OBRA

    @property
    def cor_rotulo(self) -> str:
        if self.cores_rotulo:
            return self.cores_rotulo
        return {(1,): "1 cor", (2,): "2 cores", (1, 2): "1 ou 2 cores"}.get(
            tuple(sorted(self.cores)), "a definir")

    @property
    def procuravel(self) -> str:
        return " ".join((self.nome, self.categoria, self.gerador, self.resumo)
                        + self.busca).lower()


def _letreiro(slug, nome, resumo, cores, nota="", busca=()):
    return Modelo(slug=f"letreiro-{slug}", nome=f"Letreiro {nome}", categoria=FESTA,
                  resumo=resumo, gerador="Gerador de letreiros",
                  rota=f"/letreiros/?modelo={slug}", cores=cores, nota=nota, busca=busca)


# Os seis modelos abaixo sao os que existem hoje no gerador de letreiros --
# conferidos contra a tabela PRODUTOS dele, e ha teste que compara as duas
# listas. Cartao para modelo que o gerador nao conhece leva a uma tela que
# ignora o clique em silencio.
MODELOS: tuple[Modelo, ...] = (
    _letreiro("classico", "Clássico",
              "Letra cheia com moldura. O único que sai em uma cor só.",
              cores=(1, 2), busca=("nome", "aniversário", "simples")),
    _letreiro("magia", "Magia",
              "Base colorida com a face por cima, em duas camadas.", cores=(2,),
              nota="A moldura precisa de espaço: em tamanho pequeno o gerador barra e "
                   "manda usar o Clássico.",
              busca=("princesa", "encantado", "unicórnio")),
    _letreiro("gamer", "Gamer", "Letra angular de duas cores.", cores=(2,),
              nota="Altura mínima de 42 mm por linha — não achata como os outros.",
              busca=("games", "videogame", "neon")),
    _letreiro("cinema", "Cinema", "Letra de marquise, duas cores.", cores=(2,),
              busca=("filme", "hollywood", "estrela")),
    _letreiro("futuro", "Futuro", "Letra geométrica, duas cores.", cores=(2,),
              busca=("espaço", "foguete", "astronauta", "robô")),
    _letreiro("terror", "Terror", "Letra irregular, duas cores.", cores=(2,),
              busca=("halloween", "monstro", "susto")),
    Modelo(slug="logo-3d", nome="Logo 3D", categoria=IDENTIDADE,
           resumo="Transforma uma imagem de logo em peça impressa, separada por cor.",
           gerador="Gerador de logo 3D", rota="/logo/", cores=(1, 2),
           cores_rotulo="depende da arte", saida="pacote STL",
           nota="Logo de terceiro com marca registrada ativa não entra no catálogo "
                "comercial — só peça encomendada pelo dono da marca.",
           busca=("marca", "empresa", "placa", "fachada", "brinde")),
    Modelo(slug="chaveiro", nome="Chaveiro de nome", categoria=FESTA,
           resumo="O nome em letras ligadas, com argola. Peça de bolso.",
           gerador="Gerador de chaveiro", rota="/criar/chaveiro/", cores=(1,),
           saida="STL",
           nota="Escolhido para o C4 por ser o único dos dez do plano com demanda "
                "dentro do próprio sistema: está nos pedidos, no custo e nas licenças. "
                "Os templates nascem EM TESTE, como manda o §6.",
           busca=("chaveiro", "argola", "lembrancinha", "bolso", "nome")),
    Modelo(slug="topo-de-bolo", nome="Topo de bolo", categoria=FESTA,
           resumo="Nome, idade e tema em cima do bolo, a partir de um template.",
           gerador="Gerador de topo de bolo", rota="/criar/topo/", cores=(1,), saida="STL",
           nota="Os seis templates estão EM TESTE: o desenho sai, mas nenhum foi "
                "impresso e aprovado ainda. O §6 do documento manda testar na mesa "
                "antes de vender.",
           busca=("bolo", "aniversário", "festa", "idade", "topo")),
    Modelo(slug="display", nome="Display de mesa", categoria=DECORACAO,
           resumo="Peça em pé para a mesa do bolo: número, tema ou silhueta.",
           gerador="Gerador de displays", cores=(1, 2), saida="STL",
           busca=("display", "centro de mesa", "mesa do bolo", "numero",
                  "silhueta", "enfeite", "decoração")),
    Modelo(slug="bandeja", nome="Bandeja decorativa", categoria=DECORACAO,
           resumo="Bandeja para doces e salgados com borda personalizada.",
           gerador="Gerador de bandejas", cores=(1, 2), saida="STL",
           busca=("bandeja", "doces", "salgados", "porta doces",
                  "mesa de doces", "travessa")),
    Modelo(slug="personagem", nome="Personagem temático", categoria=FESTA,
           resumo="Boneco ou silhueta de personagem para decoração de mesa.",
           gerador="Gerador de personagens", cores=(1, 2), saida="STL",
           nota="Personagem de franquia (Disney, Marvel etc.) só sob encomenda "
                "do dono da marca — não entra no catálogo.",
           busca=("personagem", "boneco", "mascote", "silhueta",
                  "figura", "tema", "herói")),
    Modelo(slug="lembrancinha", nome="Lembrancinha personalizada", categoria=FESTA,
           resumo="Peça pequena para dar aos convidados: porta-foto, caixinha ou enfeite.",
           gerador="Gerador de lembrancinhas", cores=(1,), saida="STL",
           busca=("lembrancinha", "brinde", "convidado", "recordação",
                  "porta foto", "caixinha", "mimo")),
    Modelo(slug="kit-de-mesa", nome="Kit de mesa completo", categoria=DECORACAO,
           resumo="Conjunto coordenado: display, bandeja e lembrancinhas no mesmo tema.",
           gerador="Gerador de kits de mesa", cores=(1, 2),
           cores_rotulo="depende do kit", saida="pacote STL",
           nota="Combina os outros geradores num pacote só. "
                "É o objetivo final da linha de personalização.",
           busca=("kit", "conjunto", "pacote", "mesa completa",
                  "decoração completa", "festa completa")),
)


def categorias() -> list[str]:
    """As categorias que EXISTEM. Filtro para gaveta vazia nao ajuda ninguem."""
    vistas = []
    for m in MODELOS:
        if m.categoria not in vistas:
            vistas.append(m.categoria)
    return vistas


def cores_possiveis() -> list[int]:
    return sorted({n for m in MODELOS for n in m.cores})


def contagem() -> dict[str, int]:
    no_ar = sum(1 for m in MODELOS if m.status == NO_AR)
    return {"total": len(MODELOS), "no_ar": no_ar, "em_obra": len(MODELOS) - no_ar}
