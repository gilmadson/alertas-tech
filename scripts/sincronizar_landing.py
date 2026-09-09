#!/usr/bin/env python3
"""Reescreve os links de grupo da landing com o convite ATUAL de cada grupo.

Por que existe
--------------
Em 09/09/2026 nenhum dos links publicados apontava para um grupo onde o motor
publica hoje (0 de 7 conferidos). Convite de WhatsApp muda quando alguém
revoga, e a landing não tinha como saber — o desencontro só apareceria em quem
clicasse e caísse num convite morto, calado.

Este script vai ao gateway do OpenWA, pega o convite de cada grupo listado no
`grupos.json` e reescreve o bloco `GRUPOS` do `index.html`.

A regra dura: **se qualquer categoria falhar, nada é escrito**. Link vazio é
pior que link velho.

Uso
---
    OPENWA_API_KEY=... python scripts/sincronizar_landing.py [--dry-run]

A chave do gateway NUNCA entra no repositório: vem do ambiente
(`OPENWA_API_KEY`). O endereço do gateway pode ser trocado por
`OPENWA_BASE_URL`.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
INDEX_PADRAO = RAIZ / "index.html"
GRUPOS_PADRAO = RAIZ / "grupos.json"

# O bloco entre as marcas é território do script. Editar à mão ali é o mesmo
# que voltar ao problema que ele resolve.
MARCA_INICIO = "// GRUPOS:INICIO (gerado por scripts/sincronizar_landing.py)"
MARCA_FIM = "// GRUPOS:FIM"

CHAVE_ENV = "OPENWA_API_KEY"
BASE_URL_ENV = "OPENWA_BASE_URL"

CONVITE_VALIDO = re.compile(r"^https://chat\.whatsapp\.com/[A-Za-z0-9]{15,}$")
TIMEOUT_S = 30


class ErroSincronizacao(Exception):
    """Qualquer motivo para NÃO escrever no index.html."""


# ── grupos.json ──────────────────────────────────────────────────────────────

def carregar_grupos(caminho: Path | str = GRUPOS_PADRAO) -> dict:
    caminho = Path(caminho)
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ErroSincronizacao(f"{caminho} não existe") from e
    except json.JSONDecodeError as e:
        raise ErroSincronizacao(f"{caminho} não é JSON válido: {e}") from e

    categorias = dados.get("categorias") or []
    if not categorias:
        raise ErroSincronizacao(f"{caminho} não tem categoria nenhuma")
    for cat in categorias:
        for campo in ("slug", "jid", "sessao"):
            if not cat.get(campo):
                raise ErroSincronizacao(
                    f"categoria {cat.get('slug', '?')} sem campo '{campo}'")
    return dados


# ── bloco GRUPOS dentro do index.html ────────────────────────────────────────

def ler_bloco(html: str) -> str:
    inicio = html.find(MARCA_INICIO)
    fim = html.find(MARCA_FIM)
    if inicio < 0 or fim < 0 or fim < inicio:
        raise ErroSincronizacao(
            "index.html sem as marcas do bloco GRUPOS "
            f"({MARCA_INICIO!r} .. {MARCA_FIM!r})")
    return html[inicio + len(MARCA_INICIO):fim]


_ENTRADA = re.compile(
    r"'(?P<slug>[a-z0-9-]+)':\s*\{\s*"
    r"tg:\s*(?:'(?P<tg>[^']*)'|(?P<nulo>null))\s*,\s*"
    r"wpp:\s*'(?P<wpp>[^']*)'\s*\}")


def parse_bloco(bloco: str) -> dict[str, dict]:
    return {
        m.group("slug"): {"tg": None if m.group("nulo") else m.group("tg"),
                          "wpp": m.group("wpp")}
        for m in _ENTRADA.finditer(bloco)
    }


def montar_bloco(categorias: list[dict], convites: dict[str, str]) -> str:
    largura = max(len(c["slug"]) for c in categorias) + 3
    linhas = ["", "const GRUPOS = {"]
    for cat in categorias:
        slug = cat["slug"]
        tg = f"'{cat['telegram']}'" if cat.get("telegram") else "null"
        rotulo = f"'{slug}':".ljust(largura)
        linhas.append(f"  {rotulo} {{ tg: {tg}, wpp: '{convites[slug]}' }},")
    linhas += ["};", ""]
    return "\n".join(linhas)


def substituir_bloco(html: str, bloco: str) -> str:
    ler_bloco(html)  # valida as marcas antes de mexer
    inicio = html.find(MARCA_INICIO) + len(MARCA_INICIO)
    fim = html.find(MARCA_FIM)
    return html[:inicio] + bloco + html[fim:]


# ── gateway ──────────────────────────────────────────────────────────────────

def buscar_convite(sessao: str, jid: str, *, base_url: str, api_key: str,
                   http=None) -> str:
    """Convite atual de um grupo. Levanta ErroSincronizacao em qualquer tropeço."""
    if http is None:  # pragma: no cover - caminho com rede de verdade
        import requests
        http = requests
    url = f"{base_url.rstrip('/')}/api/sessions/{sessao}/groups/{jid}/invite-code"
    try:
        resp = http.get(url, headers={"X-API-Key": api_key}, timeout=TIMEOUT_S)
    except Exception as e:  # rede fora, DNS, timeout...
        raise ErroSincronizacao(f"gateway não respondeu ({type(e).__name__})") from e
    if resp.status_code != 200:
        raise ErroSincronizacao(f"gateway devolveu HTTP {resp.status_code}")
    try:
        corpo = resp.json()
    except Exception as e:
        raise ErroSincronizacao("gateway devolveu resposta que não é JSON") from e
    # `null` e lista também são JSON válido: sem esta guarda o .get() estoura
    # traceback cru no lugar da mensagem de erro.
    if not isinstance(corpo, dict):
        raise ErroSincronizacao(
            f"gateway devolveu JSON que não é objeto ({type(corpo).__name__})")
    link = corpo.get("inviteLink")
    if not isinstance(link, str) or not link:
        codigo = corpo.get("inviteCode")
        link = (f"https://chat.whatsapp.com/{codigo}"
                if isinstance(codigo, str) and codigo else None)
    if not link:
        raise ErroSincronizacao("gateway respondeu sem convite")
    return link


def _com_teimosia(buscar, cat, tentativas, pausa, dormir):
    """Tenta de novo antes de desistir de uma categoria."""
    ultimo = None
    for tentativa in range(1, tentativas + 1):
        if pausa:
            dormir(pausa * tentativa)
        try:
            return buscar(cat["sessao"], cat["jid"])
        except ErroSincronizacao as e:
            ultimo = e
    raise ultimo


def coletar_convites(categorias: list[dict], buscar, *, pausa: float = 0.0,
                     tentativas: int = 1, dormir=time.sleep) -> dict[str, str]:
    """Convite de TODAS as categorias, ou exceção. Nunca meio conjunto.

    `pausa` existe porque o WhatsApp limita a consulta de convite: medido em
    09/09/2026, 18 pedidos em sequência começam a voltar HTTP 500 a partir do
    12º, e os mesmos grupos respondem 200 quando consultados devagar.
    """
    convites: dict[str, str] = {}
    falhas: list[str] = []
    for cat in categorias:
        slug = cat["slug"]
        try:
            link = _com_teimosia(buscar, cat, tentativas, pausa, dormir)
        except ErroSincronizacao as e:
            falhas.append(f"{slug}: {e}")
            continue
        if not link:
            falhas.append(f"{slug}: convite vazio")
        elif not CONVITE_VALIDO.match(link):
            falhas.append(f"{slug}: convite com cara errada ({link})")
        else:
            convites[slug] = link

    repetidos = {}
    for slug, link in convites.items():
        repetidos.setdefault(link, []).append(slug)
    for link, slugs in repetidos.items():
        if len(slugs) > 1:
            falhas.append(f"convite repetido em {sorted(slugs)} — JID errado no grupos.json?")

    if falhas:
        raise ErroSincronizacao(
            "nada foi escrito; %d problema(s):\n  - %s" % (len(falhas), "\n  - ".join(falhas)))
    return convites


# ── escrita ──────────────────────────────────────────────────────────────────

def gravar_atomico(caminho: Path, texto: str) -> None:
    """Grava num temporário do mesmo diretório e troca de uma vez.

    Escrever direto no index.html significa que uma interrupção no meio (Ctrl+C,
    disco cheio, sessão encerrada) deixa a landing truncada no ar. `os.replace`
    é atômico dentro do mesmo volume: ou a página velha, ou a nova.
    """
    temporario = caminho.with_name(caminho.name + ".novo")
    try:
        temporario.write_text(texto, encoding="utf-8")
        os.replace(temporario, caminho)
    except OSError as e:
        raise ErroSincronizacao(f"não consegui gravar {caminho}: {e}") from e
    finally:
        if temporario.exists():
            temporario.unlink()


# ── relatório ────────────────────────────────────────────────────────────────

def resumir(antes: dict[str, dict], depois: dict[str, str]) -> list[str]:
    linhas = []
    for slug, link in depois.items():
        anterior = (antes.get(slug) or {}).get("wpp")
        if anterior is None:
            linhas.append(f"  + {slug}: NOVA -> {link}")
        elif anterior != link:
            linhas.append(f"  ~ {slug}: {anterior} -> {link}")
        else:
            linhas.append(f"  = {slug}: igual")
    for slug in antes:
        if slug not in depois:
            linhas.append(f"  - {slug}: saiu do grupos.json")
    return linhas


# ── linha de comando ─────────────────────────────────────────────────────────

def main(argv=None, buscador=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", default=str(INDEX_PADRAO))
    parser.add_argument("--grupos", default=str(GRUPOS_PADRAO))
    parser.add_argument("--dry-run", action="store_true",
                        help="mostra o que mudaria e não grava")
    parser.add_argument("--pausa", type=float, default=2.0,
                        help="segundos entre consultas (o WhatsApp limita)")
    parser.add_argument("--tentativas", type=int, default=3,
                        help="quantas vezes insistir em cada grupo")
    args = parser.parse_args(argv)

    api_key = os.environ.get(CHAVE_ENV, "").strip()
    if buscador is None and not api_key:
        print(f"ERRO: falta a variável de ambiente {CHAVE_ENV} "
              "(a chave do gateway OpenWA não mora no repositório).",
              file=sys.stderr)
        return 2

    try:
        dados = carregar_grupos(args.grupos)
        categorias = dados["categorias"]
        index = Path(args.index)
        html = index.read_text(encoding="utf-8")
        antes = parse_bloco(ler_bloco(html))

        if buscador is None:  # pragma: no cover - caminho com rede de verdade
            base_url = os.environ.get(BASE_URL_ENV) or dados["gateway"]["base_url"]

            def buscador(sessao, jid):
                return buscar_convite(sessao, jid, base_url=base_url, api_key=api_key)

        convites = coletar_convites(categorias, buscador, pausa=args.pausa,
                                    tentativas=args.tentativas)
        novo_html = substituir_bloco(html, montar_bloco(categorias, convites))
    except ErroSincronizacao as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1

    print(f"{len(convites)} categorias consultadas no gateway:")
    print("\n".join(resumir(antes, convites)))

    if args.dry_run:
        print("\n--dry-run: index.html NÃO foi tocado.")
        return 0
    if novo_html == html:
        print("\nNada a fazer: a landing já estava sincronizada.")
        return 0
    try:
        gravar_atomico(index, novo_html)
    except ErroSincronizacao as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 1
    print(f"\n{index} atualizado.")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
