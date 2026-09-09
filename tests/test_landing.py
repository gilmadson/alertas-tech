"""Trava contra dessincronia: a landing tem de bater com o `grupos.json`.

Estes testes rodam SEM REDE. Eles existem por causa de um estrago medido em
09/09/2026: a página publicada carregava a chave do Supabase como
`__SUPABASE_ANON_KEY__`, pulava o POST e redirecionava como se tivesse dado
certo (zero lead gravado desde sempre), e nenhum dos links de grupo apontava
para um grupo onde o motor publica hoje.

Se alguém mexer na landing e ela desencontrar do `grupos.json`, é aqui que a
casa cai — antes do deploy, não depois.
"""

import base64
import json
import re
from pathlib import Path

import pytest

import sincronizar_landing as sinc

RAIZ = Path(__file__).resolve().parents[1]
INDEX = RAIZ / "index.html"
GRUPOS_JSON = RAIZ / "grupos.json"

# Espelho da lista de categorias do motor (`monitor/config.py`, mapa CANAIS do
# repo trading_c_agente, conferido em 09/09/2026). O motor publica nestas 18 e
# só nestas: se ele ganhar categoria nova, este teste é o lembrete de que a
# landing também precisa ganhar.
CATEGORIAS_DO_MOTOR = (
    "smartphone", "notebook", "smart-tv", "fone-audio", "smartwatch",
    "livros", "tablet", "armazenamento", "camera", "monitor",
    "eletrodomestico", "cozinha", "mesa-posta", "casa-moveis", "fitness",
    "beleza", "moda", "outros",
)

# `geral` não é categoria do motor: é o grupo de SUPER DESCONTO
# (GRUPOS_SUPER_DESCONTO no .env do motor), que recebe qualquer produto de
# qualquer loja acima do piso — por número, não por assunto. É o destino de
# quem não quer escolher categoria.
GRUPOS_EXTRAS = ("geral",)


@pytest.fixture(scope="module")
def html():
    return INDEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dados():
    return sinc.carregar_grupos(GRUPOS_JSON)


@pytest.fixture(scope="module")
def mapa(html):
    """O objeto GRUPOS do index.html, já parseado."""
    return sinc.parse_bloco(sinc.ler_bloco(html))


# ── grupos.json ──────────────────────────────────────────────────────────────

def test_grupos_json_cobre_as_18_categorias_do_motor(dados):
    slugs = {c["slug"] for c in dados["categorias"]}
    faltando = set(CATEGORIAS_DO_MOTOR) - slugs
    assert not faltando, f"categorias do motor fora da landing: {sorted(faltando)}"


def test_grupos_json_nao_tem_grupo_inventado(dados):
    slugs = {c["slug"] for c in dados["categorias"]}
    assert slugs - set(CATEGORIAS_DO_MOTOR) == set(GRUPOS_EXTRAS)


def test_cada_categoria_tem_jid_e_sessao(dados):
    for cat in dados["categorias"]:
        assert cat["jid"].endswith("@g.us"), cat["slug"]
        assert re.fullmatch(r"\d{15,}@g\.us", cat["jid"]), cat["slug"]
        assert re.fullmatch(
            r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
            cat["sessao"],
        ), cat["slug"]


def test_nenhum_jid_repetido(dados):
    jids = [c["jid"] for c in dados["categorias"]]
    assert len(set(jids)) == len(jids)


def test_grupos_json_nao_guarda_a_chave_do_gateway():
    """A X-API-Key vive em variável de ambiente, nunca no repositório."""
    bruto = GRUPOS_JSON.read_text(encoding="utf-8")
    assert "OPENWA_API_KEY" in bruto  # o NOME pode; o valor não
    assert not re.search(r"\b[0-9a-f]{64}\b", bruto)


# ── landing x grupos.json ────────────────────────────────────────────────────

def test_toda_categoria_do_json_tem_card_no_grid(html, dados):
    slugs_no_html = set(re.findall(r'class="cat-card[^"]*"\s+data-slug="([^"]+)"', html))
    faltando = {c["slug"] for c in dados["categorias"]} - slugs_no_html
    assert not faltando, f"categorias sem card: {sorted(faltando)}"


def test_todo_card_abre_o_modal_com_o_proprio_slug(html, dados):
    for cat in dados["categorias"]:
        padrao = (r'data-slug="%s"[^>]*onclick="abrirModal\(&#39;[^&]+&#39;,\s*'
                  r'&#39;[^&]+&#39;,\s*&#39;%s&#39;\)"') % (cat["slug"], cat["slug"])
        alternativo = r"data-slug=\"%s\"[^>]*abrirModal\('[^']+',\s*'[^']+',\s*'%s'\)" % (
            cat["slug"], cat["slug"])
        assert re.search(padrao, html) or re.search(alternativo, html), cat["slug"]


def test_toda_categoria_do_json_tem_link_no_mapa_grupos(mapa, dados):
    faltando = {c["slug"] for c in dados["categorias"]} - set(mapa)
    assert not faltando, f"categorias fora do mapa GRUPOS: {sorted(faltando)}"


def test_o_mapa_nao_tem_categoria_a_mais(mapa, dados):
    sobrando = set(mapa) - {c["slug"] for c in dados["categorias"]}
    assert not sobrando, f"categorias no HTML que não existem no grupos.json: {sorted(sobrando)}"


def test_todo_link_de_whatsapp_e_um_convite_de_verdade(mapa):
    for slug, links in mapa.items():
        assert re.fullmatch(r"https://chat\.whatsapp\.com/[A-Za-z0-9]{15,}",
                            links["wpp"]), f"{slug}: {links['wpp']}"


def test_nenhum_link_de_whatsapp_repetido_entre_categorias(mapa):
    """O bug de 09/09: 12 categorias caindo no mesmo WPP_GERAL."""
    vistos = {}
    for slug, links in mapa.items():
        vistos.setdefault(links["wpp"], []).append(slug)
    repetidos = {k: v for k, v in vistos.items() if len(v) > 1}
    assert not repetidos, f"mesmo convite em categorias diferentes: {repetidos}"


def test_telegram_so_repete_no_canal_de_fallback(mapa, dados):
    """As 8 categorias novas não têm canal próprio no Telegram — o motor manda
    todas para o canal de `outros`. Repetir ALI é a verdade da produção;
    repetir em qualquer outro canal é dessincronia."""
    fallback = dados["telegram_fallback"]
    vistos = {}
    for slug, links in mapa.items():
        if links["tg"]:
            vistos.setdefault(links["tg"], []).append(slug)
    repetidos = {k: v for k, v in vistos.items() if len(v) > 1 and k != fallback}
    assert not repetidos, f"canal de Telegram repetido fora do fallback: {repetidos}"


def test_o_bloco_gerado_tem_as_marcas_que_o_script_procura(html):
    assert sinc.MARCA_INICIO in html
    assert sinc.MARCA_FIM in html


# ── Supabase: a falha silenciosa não pode voltar ─────────────────────────────

def test_placeholder_da_chave_nao_voltou(html):
    assert "__SUPABASE_ANON_KEY__" not in html


def test_a_chave_embutida_e_anon_do_projeto_certo(html):
    chave = re.search(r"const SUPABASE_ANON\s*=\s*'([^']+)'", html).group(1)
    payload = chave.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    dados = json.loads(base64.urlsafe_b64decode(payload))
    assert dados["role"] == "anon", "chave que não é anon nunca vai para o HTML"
    assert dados["ref"] == "jfuqmjbxzhoceycauhys"


def test_nao_existe_guarda_que_pule_o_post(html):
    """Era isto que fingia sucesso: `if (SUPABASE_ANON !== '__...__')`."""
    assert not re.search(r"if\s*\(\s*SUPABASE_ANON\s*[!=]==", html)


def test_a_resposta_do_supabase_e_conferida(html):
    assert "res.ok" in html or "resposta.ok" in html


def test_a_plataforma_enviada_respeita_o_check_do_banco(html):
    """A coluna `plataforma` tem CHECK ('wpp','tg'): qualquer outro valor
    devolve HTTP 400 (23514) e o lead se perde."""
    plats = set(re.findall(r'data-plat="([^"]+)"', html))
    assert plats == {"wpp", "tg"}, plats


def test_envio_rapido_nao_pula_o_cadastro(html):
    """O ramo antibot antigo abria o grupo e fechava o modal SEM tentar gravar:
    sucesso perfeito para quem visita, zero linha no banco."""
    ramo = re.search(
        r"if \(Date\.now\(\) - modalAbertaEm < BOT_THRESHOLD_MS\) \{(.*?)\n  \}",
        html, re.S)
    assert ramo, "sumiu a trava antibot"
    assert "abrirDestino" not in ramo.group(1), "não pode entregar convite sem tentar gravar"
    assert "fecharModal" not in ramo.group(1), "não pode fingir sucesso fechando o modal"


def test_falha_do_post_aparece_para_o_visitante(html):
    """Regra 1 da casa: falha silenciosa é o inimigo."""
    assert 'id="form-aviso"' in html
    assert "mostrarFalhaDeCadastro" in html


def test_o_convite_e_entregue_mesmo_quando_o_cadastro_falha(html):
    """Não punir o visitante por um problema que é nosso."""
    corpo = html[html.index("async function submeterLead"):]
    assert "abrirDestino" in corpo


# ── LGPD ─────────────────────────────────────────────────────────────────────

def test_existe_caixa_de_consentimento_e_ela_nao_vem_marcada(html):
    caixa = re.search(r'<input[^>]*id="consent-check"[^>]*>', html)
    assert caixa, "sem caixa de consentimento"
    assert "checked" not in caixa.group(0), "consentimento não pode vir pré-marcado"


def test_o_consentimento_declara_a_finalidade(html):
    trecho = html[html.index('id="consent-check"'):][:900]
    assert "WhatsApp" in trecho
    assert "grupo" in trecho.lower()


def test_sem_consentimento_o_botao_nao_libera(html):
    checagem = re.search(r"function checarCampos\(\)\s*\{.*?\n\}", html, re.S).group(0)
    assert "consent-check" in checagem


def test_existe_secao_de_politica_de_privacidade(html):
    assert 'id="privacidade"' in html
    secao = html[html.index('id="privacidade"'):]
    secao = secao[:secao.index("</section>")]
    for exigido in ["Respons", "coleta", "exclus"]:
        assert exigido.lower() in secao.lower(), exigido


def test_a_politica_e_alcancavel_a_partir_do_formulario(html):
    assert html.count('href="#privacidade"') >= 2


# ── ofertas gerais ───────────────────────────────────────────────────────────

def test_existe_a_opcao_de_ofertas_gerais(html):
    """Ele pediu literalmente: quem não quer escolher categoria tem que ver
    a opção, e ela ocupa a linha inteira do grid para não se esconder."""
    card = re.search(r'<div class="cat-card([^"]*)" data-slug="geral"[^>]*>(.*?)</div>\s*</div>',
                     html, re.S)
    assert card, "sem card de ofertas gerais"
    assert "full" in card.group(1), "a opção geral não pode virar mais um card no meio"
    assert "Ofertas gerais" in card.group(2)


def test_ofertas_gerais_e_uma_categoria_como_as_outras(mapa):
    """Era um caminho especial — e o caminho especial escondia o aviso de erro.
    Agora `geral` tem grupo real (o de super desconto) e passa pelo mesmo
    fluxo das outras."""
    assert "geral" in mapa
    assert mapa["geral"]["wpp"].startswith("https://chat.whatsapp.com/")


def test_nao_sobrou_caminho_especial_para_o_ofertas_gerais(html):
    """A lista embutida escondia o #form-aviso ao ocultar o formulário."""
    assert "mostrarListaGeral" not in html
    assert "montarListaGeral" not in html
    assert "lista-geral" not in html


def test_o_aviso_de_falha_nao_mora_em_lugar_que_alguem_esconde(html):
    """#form-aviso é filho do formulário: ninguém pode dar display:none nele."""
    assert "getElementById('lead-form').style.display = 'none'" not in html
