"""Camada de acesso a rede — educada por construcao.

Tudo o que sai para a internet passa por aqui, e aqui estao embutidas as
regras da secao 6 da especificacao:

* User-Agent que identifica o sistema e um contato;
* robots.txt conferido antes de cada URL (e respeitado);
* intervalo minimo entre requisicoes ao mesmo host (respeita Crawl-delay);
* cache em disco: cada URL e baixada uma unica vez dentro do TTL;
* limite de tamanho de download e recuo exponencial em 429/5xx.

Nao ha nenhum mecanismo aqui para contornar bloqueio, captcha ou limite de
taxa: se a fonte disser nao, o conector devolve lista vazia com o motivo.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from dataclasses import dataclass
from pathlib import Path

from .config import Config


class AcessoNegado(RuntimeError):
    """A fonte (ou o robots.txt dela) nao autoriza esta requisicao."""


class FalhaRede(RuntimeError):
    """Erro de rede depois de esgotadas as tentativas."""


@dataclass
class Resposta:
    url: str
    status: int
    corpo: bytes
    do_cache: bool = False
    tipo: str = ""

    def texto(self) -> str:
        return self.corpo.decode("utf-8", errors="replace")

    def json(self):
        return json.loads(self.texto() or "null")


class SessaoEducada:
    """Cliente HTTP com robots.txt, rate limit e cache em disco."""

    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        cfg.preparar_diretorios()
        self._ultimo_acesso: dict[str, float] = {}
        self._robots: dict[str, urllib.robotparser.RobotFileParser | None] = {}
        self._crawl_delay: dict[str, float] = {}

    # ------------------------------------------------------------- robots
    def _host(self, url: str) -> str:
        partes = urllib.parse.urlsplit(url)
        return f"{partes.scheme}://{partes.netloc}"

    def _carregar_robots(self, url: str):
        host = self._host(url)
        if host in self._robots:
            return self._robots[host]
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(f"{host}/robots.txt")
        try:
            req = urllib.request.Request(
                f"{host}/robots.txt", headers={"User-Agent": self.cfg.rede.user_agent}
            )
            with urllib.request.urlopen(req, timeout=self.cfg.rede.timeout_s) as resp:
                parser.parse(resp.read().decode("utf-8", errors="replace").splitlines())
        except Exception:
            # Sem robots.txt legivel: nao inventamos permissao nem bloqueio;
            # segue o intervalo padrao entre requisicoes.
            parser = None
        self._robots[host] = parser
        if parser is not None:
            try:
                atraso = parser.crawl_delay(self.cfg.rede.user_agent)
                if atraso:
                    self._crawl_delay[host] = float(atraso)
            except Exception:
                pass
        return parser

    def permitido(self, url: str) -> tuple[bool, str]:
        """(pode_acessar, motivo). Sem robots.txt, assume permitido."""

        if not self.cfg.rede.respeitar_robots:
            return True, "verificacao de robots.txt desligada na configuracao"
        parser = self._carregar_robots(url)
        if parser is None:
            return True, "robots.txt indisponivel"
        agente = self.cfg.rede.user_agent
        if parser.can_fetch(agente, url) or parser.can_fetch("*", url):
            return True, "permitido pelo robots.txt"
        return False, f"robots.txt de {self._host(url)} nao permite {url}"

    # -------------------------------------------------------- rate limit
    def _esperar_vez(self, url: str) -> None:
        host = self._host(url)
        intervalo = max(
            self.cfg.rede.intervalo_min_s, self._crawl_delay.get(host, 0.0)
        )
        ultimo = self._ultimo_acesso.get(host)
        if ultimo is not None:
            faltam = intervalo - (time.monotonic() - ultimo)
            if faltam > 0:
                time.sleep(faltam)
        self._ultimo_acesso[host] = time.monotonic()

    # -------------------------------------------------------------- cache
    def _caminho_cache(self, url: str, dados: bytes | None) -> Path:
        assinatura = hashlib.sha256(url.encode("utf-8") + (dados or b"")).hexdigest()
        return self.cfg.cache_http / f"{assinatura}.json.gz"

    def _ler_cache(self, caminho: Path) -> Resposta | None:
        if not caminho.is_file():
            return None
        idade = time.time() - caminho.stat().st_mtime
        if idade > self.cfg.rede.cache_ttl_s:
            return None
        try:
            with gzip.open(caminho, "rt", encoding="utf-8") as fh:
                dados = json.load(fh)
        except Exception:
            return None
        return Resposta(
            url=dados["url"],
            status=dados["status"],
            corpo=bytes.fromhex(dados["corpo"]),
            do_cache=True,
            tipo=dados.get("tipo", ""),
        )

    def _gravar_cache(self, caminho: Path, resposta: Resposta) -> None:
        try:
            with gzip.open(caminho, "wt", encoding="utf-8") as fh:
                json.dump(
                    {
                        "url": resposta.url,
                        "status": resposta.status,
                        "corpo": resposta.corpo.hex(),
                        "tipo": resposta.tipo,
                    },
                    fh,
                )
        except OSError:
            pass  # cache e otimizacao: falha nele nao derruba a busca

    # --------------------------------------------------------------- HTTP
    def obter(
        self,
        url: str,
        *,
        cabecalhos: dict[str, str] | None = None,
        dados: bytes | None = None,
        usar_cache: bool = True,
        ignorar_robots: bool = False,
    ) -> Resposta:
        """GET (ou POST, se ``dados``), com cache, robots e rate limit."""

        if not ignorar_robots:
            ok, motivo = self.permitido(url)
            if not ok:
                raise AcessoNegado(motivo)

        caminho = self._caminho_cache(url, dados)
        if usar_cache:
            em_cache = self._ler_cache(caminho)
            if em_cache is not None:
                return em_cache

        cabecalhos_finais = {
            "User-Agent": self.cfg.rede.user_agent,
            "Accept": "application/json, text/html;q=0.9, */*;q=0.5",
            "Accept-Language": "pt-BR,pt;q=0.9,en;q=0.8",
        }
        cabecalhos_finais.update(cabecalhos or {})

        limite = int(self.cfg.rede.tamanho_max_download_mb * 1024 * 1024)
        ultimo_erro: Exception | None = None

        for tentativa in range(1, max(1, self.cfg.rede.tentativas) + 1):
            self._esperar_vez(url)
            requisicao = urllib.request.Request(
                url, data=dados, headers=cabecalhos_finais,
                method="POST" if dados else "GET",
            )
            try:
                with urllib.request.urlopen(
                    requisicao, timeout=self.cfg.rede.timeout_s
                ) as resp:
                    corpo = resp.read(limite + 1)
                    if len(corpo) > limite:
                        raise FalhaRede(
                            f"resposta maior que o limite de "
                            f"{self.cfg.rede.tamanho_max_download_mb} MB: {url}"
                        )
                    resposta = Resposta(
                        url=url,
                        status=resp.status,
                        corpo=corpo,
                        tipo=resp.headers.get("Content-Type", ""),
                    )
            except urllib.error.HTTPError as exc:
                ultimo_erro = exc
                if exc.code in (429, 500, 502, 503, 504):
                    espera = float(exc.headers.get("Retry-After") or 0) or (
                        2.0 ** tentativa
                    )
                    if tentativa < self.cfg.rede.tentativas:
                        time.sleep(min(espera, 60.0))
                        continue
                if exc.code in (401, 403):
                    raise AcessoNegado(
                        f"{exc.code} em {url}: a fonte recusou o acesso "
                        "(chave ausente/invalida ou bloqueio do site)"
                    ) from exc
                raise FalhaRede(f"HTTP {exc.code} em {url}") from exc
            except urllib.error.URLError as exc:
                ultimo_erro = exc
                if tentativa < self.cfg.rede.tentativas:
                    time.sleep(2.0 ** tentativa)
                    continue
                raise FalhaRede(f"falha de rede em {url}: {exc.reason}") from exc
            else:
                if usar_cache:
                    self._gravar_cache(caminho, resposta)
                return resposta

        raise FalhaRede(f"nao foi possivel obter {url}: {ultimo_erro}")

    def baixar(self, url: str, destino: Path, *, sobrescrever: bool = False) -> Path:
        """Baixa um arquivo para o cache local (uma vez so)."""

        destino = Path(destino)
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.is_file() and destino.stat().st_size > 0 and not sobrescrever:
            return destino
        resposta = self.obter(url, usar_cache=False)
        destino.write_bytes(resposta.corpo)
        return destino

    def baixar_imagem(self, url: str, nome: str) -> Path | None:
        if not url:
            return None
        sufixo = Path(urllib.parse.urlsplit(url).path).suffix.lower()
        if sufixo not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            sufixo = ".jpg"
        destino = self.cfg.cache_imagens / f"{nome}{sufixo}"
        try:
            return self.baixar(url, destino)
        except (AcessoNegado, FalhaRede):
            return None
