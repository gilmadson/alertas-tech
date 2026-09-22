"""As páginas publicadas e o que elas têm em comum.

Até 18/09/2026 havia uma página só (`index.html`), com CSS e JS dentro. Com a
landing exclusiva do Imperdíveis ML passaram a ser duas, e o que era "o
arquivo" virou "o arquivo compartilhado": `landing.css` e `landing.js`.

Duas páginas com cópias do mesmo código é como elas ficam diferentes sem
ninguém ver — a mesma dor que já custou a landing publicada em dois lugares
divergindo. Por isso, aqui:

- o que é compartilhado é INCLUÍDO, nunca copiado;
- toda página tem os elementos que o `landing.js` procura (elemento que falta
  vira `null.checked` e mata o cadastro inteiro, calado);
- o caminho é RELATIVO: o GitHub Pages serve de `/alertas-tech/`, e um
  `src="/landing.js"` quebraria só lá.
"""

import json
import re
from pathlib import Path

import pytest

import sincronizar_landing as sinc

RAIZ = Path(__file__).resolve().parents[1]
INDEX = RAIZ / "index.html"
IMPERDIVEIS = RAIZ / "imperdiveis.html"
SUPER_DESCONTO = RAIZ / "super-desconto.html"
LANDING_JS = RAIZ / "landing.js"
LANDING_CSS = RAIZ / "landing.css"
VERCEL = RAIZ / "vercel.json"
GRUPOS_JSON = RAIZ / "grupos.json"

# Toda página que capta lead entra nesta lista. Quem esquecer de acrescentar
# aqui a próxima página exclusiva perde todas as travas de uma vez.
PAGINAS = ("index.html", "imperdiveis.html", "super-desconto.html")


@pytest.fixture(scope="module")
def js():
    return LANDING_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def paginas():
    return {nome: (RAIZ / nome).read_text(encoding="utf-8") for nome in PAGINAS}


@pytest.fixture(scope="module")
def dados():
    return sinc.carregar_grupos(GRUPOS_JSON)


def entrada(dados, slug):
    return next(c for c in dados["categorias"] if c["slug"] == slug)


# ── o que é compartilhado não se copia ───────────────────────────────────────

def test_toda_pagina_inclui_o_js_compartilhado(paginas):
    for nome, texto in paginas.items():
        assert '<script src="landing.js"></script>' in texto, nome


def test_toda_pagina_inclui_o_css_compartilhado(paginas):
    for nome, texto in paginas.items():
        assert '<link rel="stylesheet" href="landing.css">' in texto, nome


def test_nenhuma_pagina_chama_o_compartilhado_por_caminho_absoluto(paginas):
    """O GitHub Pages serve de `/alertas-tech/`: `/landing.js` quebraria só
    lá, e caladinho — a página abriria sem JS nenhum."""
    for nome, texto in paginas.items():
        absoluto = re.findall(r'(?:src|href)="(/[^"]*landing\.(?:js|css))"', texto)
        assert not absoluto, f"{nome}: {absoluto}"


def test_o_js_entra_no_fim_do_corpo(paginas):
    """`landing.js` lê `document.body` ao carregar (é de lá que vem a loja
    fixa da página exclusiva). No `<head>` isso seria `null`."""
    for nome, texto in paginas.items():
        assert texto.index('<script src="landing.js">') > texto.index('id="modal"'), nome


def test_nenhuma_pagina_guarda_logica_inline(paginas):
    """Só o Pixel do Meta continua inline (ele precisa disparar antes de
    tudo). Qualquer outra lógica dentro do HTML é a cópia voltando."""
    for nome, texto in paginas.items():
        inline = re.findall(r"<script>(.*?)</script>", texto, re.S)
        assert len(inline) == 1, f"{nome}: {len(inline)} blocos inline"
        assert "fbq(" in inline[0], nome
        for proibido in ("const GRUPOS", "function abrirModal", "SUPABASE_ANON"):
            assert proibido not in inline[0], f"{nome}: {proibido} inline"


def test_nenhuma_pagina_guarda_o_tema_inline(paginas):
    """Duas cópias de 680 linhas de CSS é drift garantido."""
    for nome, texto in paginas.items():
        assert "<style>" not in texto, nome


def test_o_js_compartilhado_nao_tem_tag_de_html(js):
    """Recorte mal feito na extração = `<script>` sobrando dentro do .js."""
    assert "<script" not in js and "</script>" not in js


# ── elemento que falta mata o cadastro ───────────────────────────────────────

def ids_que_o_js_procura(js):
    return set(re.findall(r"getElementById\('([^']+)'\)", js))


def loja_ids(js):
    lista = re.search(r"const LOJA_IDS = \[([^\]]+)\]", js)
    assert lista, "sumiu o LOJA_IDS do landing.js"
    return set(re.findall(r"'([^']+)'", lista.group(1)))


# `lojas-section`/`modal-subtitle` (22/09/2026) só existem nas páginas que
# escolhem loja na hora — a exclusiva já resolve com HTML próprio (texto fixo,
# sem seção pra esconder, ver `imperdiveis.html`). Mesma exceção que o
# `LOJA_IDS` já tem logo abaixo, pelo mesmo motivo.
IDS_SO_SEM_LOJA_FIXA = {"lojas-section", "modal-subtitle"}


def test_toda_pagina_tem_os_elementos_que_o_js_procura(paginas, js):
    """`document.getElementById('x').checked` com `x` ausente é TypeError: o
    cadastro inteiro morre, e a pessoa só vê um botão que não faz nada."""
    exigidos = ids_que_o_js_procura(js)
    assert "consent-check" in exigidos, "o parser de ids não achou nada"
    for nome, texto in paginas.items():
        presentes = set(re.findall(r'id="([^"]+)"', texto))
        pede = exigidos - IDS_SO_SEM_LOJA_FIXA if re.search(r"<body[^>]*data-lojas=", texto) else exigidos
        faltando = pede - presentes
        assert not faltando, f"{nome} sem: {sorted(faltando)}"


def test_pagina_com_caixas_de_loja_tem_todas_as_do_js(paginas, js):
    """Quem NÃO declara loja fixa tem de ter as seis caixas — o `LOJA_IDS`
    percorre todas."""
    for nome, texto in paginas.items():
        if re.search(r"<body[^>]*data-lojas=", texto):
            continue
        faltando = loja_ids(js) - set(re.findall(r'id="([^"]+)"', texto))
        assert not faltando, f"{nome} sem: {sorted(faltando)}"


def test_toda_pagina_tem_o_aviso_de_falha_dentro_do_formulario(paginas):
    """Regra 1 da casa: falha silenciosa é o inimigo. O `#form-aviso` é o
    lugar onde o erro do Supabase aparece."""
    for nome, texto in paginas.items():
        assert 'id="form-aviso"' in texto, nome
        formulario = texto[texto.index('id="lead-form"'):texto.index("</form>")]
        assert 'id="form-aviso"' in formulario, f"{nome}: o aviso saiu do formulário"


def test_toda_pagina_pede_consentimento_desmarcado(paginas):
    for nome, texto in paginas.items():
        caixa = re.search(r'<input[^>]*id="consent-check"[^>]*>', texto)
        assert caixa, f"{nome} sem caixa de consentimento"
        assert "checked" not in caixa.group(0), f"{nome}: consentimento pré-marcado"


def test_toda_pagina_leva_a_uma_politica_que_existe(paginas):
    """A política é uma só (mora no `index.html`) — duas cópias do mesmo texto
    legal é como elas passam a dizer coisas diferentes. O que cada página
    precisa ter é o CAMINHO até ela, e ele tem de chegar a algum lugar."""
    for nome, texto in paginas.items():
        links = set(re.findall(r'href="([^"]*#privacidade)"', texto))
        assert links, f"{nome} sem link para a política"
        for link in links:
            alvo = link.split("#")[0] or nome    # href="#..." é a própria página
            assert alvo in paginas, f"{nome} aponta para {alvo}, que não está publicada"
            assert 'id="privacidade"' in paginas[alvo], \
                f"{nome} aponta para uma política que não existe em {alvo}"


def test_toda_pagina_declara_qual_pagina_ela_e(paginas):
    """A contagem de visita grava `pagina`, e a página DECLARA o próprio nome —
    como já faz com `data-lojas`. Deduzir do caminho não serve: o Vercel serve
    `/imperdiveis` e o GitHub Pages serve `/alertas-tech/imperdiveis.html`; o
    mesmo arquivo viraria duas linhas diferentes no relatório."""
    for nome, texto in paginas.items():
        assert re.search(r'<body[^>]*data-pagina="[a-z0-9-]+"', texto), nome


def test_cada_pagina_declara_um_nome_diferente(paginas):
    """Duas páginas no mesmo balde e a taxa de conversão de cada uma vira
    invenção."""
    nomes = [re.search(r'<body[^>]*data-pagina="([^"]+)"', texto).group(1)
             for texto in paginas.values()]
    assert len(set(nomes)) == len(PAGINAS), nomes


def test_toda_pagina_carrega_o_mesmo_pixel(paginas):
    """Página de campanha sem Pixel é gasto sem medida; Pixel diferente por
    página é relatório partido em dois."""
    ids = {nome: re.findall(r"fbq\('init', '(\d+)'\)", texto)
           for nome, texto in paginas.items()}
    assert all(len(v) == 1 for v in ids.values()), ids
    assert len({v[0] for v in ids.values()}) == 1, ids


# ── a página exclusiva do Imperdíveis ML ─────────────────────────────────────

@pytest.fixture(scope="module")
def imperdiveis():
    return IMPERDIVEIS.read_text(encoding="utf-8")


def test_a_pagina_abre_o_modal_com_o_slug_do_grupos_json(imperdiveis, dados):
    cat = entrada(dados, "imperdiveis")
    padrao = r"abrirModal\('%s',\s*'%s',\s*'imperdiveis'\)" % (
        re.escape(cat["emoji"]), re.escape(cat["nome"]))
    assert re.search(padrao, imperdiveis), "a chamada não bate com o grupos.json"


def test_a_pagina_nao_tem_grade_de_categoria(imperdiveis):
    """Ela existe para uma coisa só: quem chega já escolheu."""
    assert set(re.findall(r'data-slug="([^"]+)"', imperdiveis)) == {"imperdiveis"}


def test_a_pagina_nao_oferece_escolha_de_loja(imperdiveis):
    """O motor dos imperdíveis é 100% Mercado Livre: caixa de Amazon ali
    seria promessa que o grupo não cumpre."""
    assert "lojas-section" not in imperdiveis
    assert not re.findall(r'id="(loja-[^"]+)"', imperdiveis)


def test_a_pagina_declara_a_loja_fixa_no_corpo(imperdiveis):
    """Ausência de caixa não vale como decisão — sumiço de elemento é drift.
    A página DIZ qual é a loja."""
    assert re.search(r'<body[^>]*data-lojas="mercadolivre"', imperdiveis)


def test_a_loja_fixa_e_a_mesma_string_que_o_banco_ja_recebe(imperdiveis):
    """`lojas` é texto livre no banco: 'ml' aqui e 'mercadolivre' lá vira
    relatório que não soma."""
    declarada = re.search(r'<body[^>]*data-lojas="([^"]+)"', imperdiveis).group(1)
    do_index = re.search(r'id="loja-ml" value="([^"]+)"',
                         INDEX.read_text(encoding="utf-8")).group(1)
    assert declarada == do_index


# ── a página exclusiva do Super Desconto ─────────────────────────────────────

@pytest.fixture(scope="module")
def super_desconto():
    return SUPER_DESCONTO.read_text(encoding="utf-8")


def test_super_desconto_abre_o_modal_com_o_slug_do_grupos_json(super_desconto, dados):
    """Reaproveita o slug 'geral' (grupo Super Descontos #1, já testado) em
    vez de criar categoria nova — o motor já publica lá por tamanho de
    desconto, não por assunto."""
    cat = entrada(dados, "geral")
    padrao = r"abrirModal\('%s',\s*'%s',\s*'geral'\)" % (
        re.escape(cat["emoji"]), re.escape(cat["nome"]))
    assert re.search(padrao, super_desconto), "a chamada não bate com o grupos.json"


def test_super_desconto_nao_tem_grade_de_categoria(super_desconto):
    """Ela existe para uma coisa só: quem chega já escolheu."""
    assert set(re.findall(r'data-slug="([^"]+)"', super_desconto)) == {"geral"}


def test_super_desconto_nao_declara_loja_fixa(super_desconto):
    """Ao contrário do Imperdíveis (100% ML), o grupo 'geral' recebe de
    QUALQUER loja — travar numa loja só aqui seria a promessa errada. Por
    isso ela mantém a escolha (coberta pelas 6 caixas em
    test_pagina_com_caixas_de_loja_tem_todas_as_do_js)."""
    assert not re.search(r"<body[^>]*data-lojas=", super_desconto)


# ── publicação (Vercel) ──────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def vercel():
    return json.loads(VERCEL.read_text(encoding="utf-8"))


def fontes(vercel):
    return [r["source"] for r in vercel["rewrites"]]


CATCH_ALL = "/(.*)"


def test_o_catch_all_e_sempre_a_ultima_regra(vercel):
    """As regras valem em ordem: qualquer coisa depois do catch-all é código
    morto — e a página nova cairia no index.html sem ninguém perceber."""
    assert fontes(vercel)[-1] == CATCH_ALL
    assert fontes(vercel).count(CATCH_ALL) == 1


def test_o_imperdiveis_tem_rota_propria_antes_do_catch_all(vercel):
    assert "/imperdiveis" in fontes(vercel)
    assert fontes(vercel).index("/imperdiveis") < fontes(vercel).index(CATCH_ALL)


def test_o_super_desconto_tem_rota_propria_antes_do_catch_all(vercel):
    assert "/super-desconto" in fontes(vercel)
    assert fontes(vercel).index("/super-desconto") < fontes(vercel).index(CATCH_ALL)


def test_todo_destino_de_rewrite_e_um_arquivo_que_existe(vercel):
    for regra in vercel["rewrites"]:
        destino = regra["destination"].lstrip("/")
        assert (RAIZ / destino).exists(), f"{regra['source']} -> {destino}"


def test_o_compartilhado_vai_sem_cache(vercel):
    """O `landing.js` carrega os convites de grupo. Convite revogado + JS
    velho no cache = a pessoa cai num grupo morto e some sem reclamar — o
    `index.html` já se protege disso com as metatags de no-cache."""
    cabecalhos = {
        regra["source"]: {c["key"].lower(): c["value"] for c in regra["headers"]}
        for regra in vercel.get("headers", [])
    }
    for alvo in ("/landing.js", "/landing.css"):
        assert alvo in cabecalhos, f"{alvo} sem regra de cache"
        assert "no-cache" in cabecalhos[alvo]["cache-control"], alvo
