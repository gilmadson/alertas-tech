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
# Desde 18/09/2026 a lógica mora fora do HTML, compartilhada pelas páginas. O
# que é marcação continua sendo cobrado no `index.html`; o que é comportamento
# é cobrado aqui, no arquivo que as duas páginas carregam.
LANDING_JS = RAIZ / "landing.js"
GRUPOS_JSON = RAIZ / "grupos.json"

# Espelho da lista de categorias do motor (`monitor/config.py`, mapa CANAIS do
# repo trading_c_agente, conferido em 10/09/2026). O motor publica nestas 19 e
# só nestas: se ele ganhar categoria nova, este teste é o lembrete de que a
# landing também precisa ganhar.
CATEGORIAS_DO_MOTOR = (
    "smartphone", "notebook", "smart-tv", "fone-audio", "smartwatch",
    "livros", "tablet", "armazenamento", "camera", "monitor",
    "eletrodomestico", "cozinha", "mesa-posta", "casa-moveis", "fitness",
    # `salao` (10/09/2026) é o primeiro nicho de PRESTADOR DE SERVIÇO: fala com
    # quem compra para atender cliente, não para si. Fica ao lado de `beleza`
    # na lista porque é o vizinho de assunto, mas é outro público.
    "beleza", "salao", "moda", "outros",
)

# `geral` e `imperdiveis` não são categoria do motor principal: `geral` é o
# grupo de SUPER DESCONTO (GRUPOS_SUPER_DESCONTO no .env do motor), que recebe
# qualquer produto de qualquer loja acima do piso — por número, não por
# assunto. `imperdiveis` é o motor separado (`monitor/imperdiveis.py`, chip e
# cadência próprios, ativo desde 01/09/2026) que reveza as 9 categorias de
# vitrine do Mercado Livre pelo maior desconto do dia. Os dois são o destino
# de quem não quer escolher categoria fixa.
GRUPOS_EXTRAS = ("geral", "imperdiveis")


@pytest.fixture(scope="module")
def html():
    return INDEX.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def js():
    return LANDING_JS.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def dados():
    return sinc.carregar_grupos(GRUPOS_JSON)


@pytest.fixture(scope="module")
def mapa(js):
    """O objeto GRUPOS do landing.js, já parseado."""
    return sinc.parse_bloco(sinc.ler_bloco(js))


# ── grupos.json ──────────────────────────────────────────────────────────────

def test_grupos_json_cobre_as_19_categorias_do_motor(dados):
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


def test_o_bloco_gerado_tem_as_marcas_que_o_script_procura(js):
    assert sinc.MARCA_INICIO in js
    assert sinc.MARCA_FIM in js


def test_o_bloco_gerado_saiu_do_html_de_vez(html):
    """Duas cópias do mapa de grupos = uma delas com convite morto. O
    sincronizador escreve num lugar só."""
    assert sinc.MARCA_INICIO not in html
    assert "const GRUPOS" not in html


# ── Supabase: a falha silenciosa não pode voltar ─────────────────────────────

def test_placeholder_da_chave_nao_voltou(js):
    assert "__SUPABASE_ANON_KEY__" not in js


def test_a_chave_embutida_e_anon_do_projeto_certo(js):
    chave = re.search(r"const SUPABASE_ANON\s*=\s*'([^']+)'", js).group(1)
    payload = chave.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    dados = json.loads(base64.urlsafe_b64decode(payload))
    assert dados["role"] == "anon", "chave que não é anon nunca vai para o HTML"
    assert dados["ref"] == "jfuqmjbxzhoceycauhys"


def test_nao_existe_guarda_que_pule_o_post(js):
    """Era isto que fingia sucesso: `if (SUPABASE_ANON !== '__...__')`."""
    assert not re.search(r"if\s*\(\s*SUPABASE_ANON\s*[!=]==", js)


def test_a_resposta_do_supabase_e_conferida(js):
    assert "res.ok" in js or "resposta.ok" in js


def test_a_plataforma_enviada_respeita_o_check_do_banco(html):
    """A coluna `plataforma` tem CHECK ('wpp','tg'): qualquer outro valor
    devolve HTTP 400 (23514) e o lead se perde."""
    plats = set(re.findall(r'data-plat="([^"]+)"', html))
    assert plats == {"wpp", "tg"}, plats


                                            # ── colunas da tabela `leads` ──
# Espelho do schema (migration `leads_consentimento_e_origem`, 09/09/2026;
# `conteudo` chegou depois, por `docs/conteudo.sql`, em 22/09/2026).
# `id` e `criado_em` são do banco. Mandar coluna que não existe devolve HTTP
# 400 e o lead se perde — por isso o espelho vive aqui, sem depender de rede.
COLUNAS_DE_LEADS = {
    "nome", "email", "telefone", "categoria", "plataforma", "lojas",
    "consentimento", "consentimento_em", "origem", "meio", "campanha",
    "conteudo",
}


def test_o_cadastro_so_manda_coluna_que_existe(js):
    corpo = re.search(r"await salvarLead\(\{(.*?)\n  \}\)", js, re.S)
    assert corpo, "não achei a chamada de salvarLead"
    # `[:,]` porque o JS aceita atalho: `email,` é a chave `email`.
    chaves = set(re.findall(r"^\s{4}(\w+)\s*[:,]", corpo.group(1), re.M))
    assert chaves == COLUNAS_DE_LEADS


def test_o_consentimento_nunca_vai_sem_data(js):
    """`consentimento: true` com `consentimento_em` vazio não prova nada."""
    assert "consentimento_em: consentimentoEm || new Date().toISOString()" in js


def test_o_instante_do_aceite_e_o_da_caixa_marcada(html, js):
    """Quem grava a data é o onchange da caixa, não a submissão."""
    assert 'onchange="marcarConsentimento()"' in html
    fn = re.search(r"function marcarConsentimento\(\)\s*\{(.*?)\n\}", js, re.S)
    assert fn and "toISOString" in fn.group(1)


def test_todo_utm_passa_pela_limpeza_antes_de_ir_ao_banco(js):
    """Valor de URL é texto do mundo: nada entra cru no banco."""
    for campo in ("utm_source", "utm_medium", "utm_campaign", "utm_content"):
        assert re.search(r"limparUtm\(params\.get\('%s'\)\)" % campo, js), campo
    guardada = re.search(r"function lerOrigemGuardada\(\)\s*\{(.*?)\n\}", js, re.S)
    assert guardada and guardada.group(1).count("limparUtm") >= 4, \
        "a sessão é do visitante: o que vem dela também precisa ser limpo"


def test_a_limpeza_de_utm_tem_teto_e_lista_do_que_aceita(js):
    assert re.search(r"const UTM_MAX = \d+;", js)
    assert re.search(r"const UTM_ACEITO = /\^\[[^/]+\]\+\$/;", js)


def test_envio_rapido_nao_pula_o_cadastro(js):
    """O ramo antibot antigo abria o grupo e fechava o modal SEM tentar gravar:
    sucesso perfeito para quem visita, zero linha no banco."""
    ramo = re.search(
        r"if \(Date\.now\(\) - modalAbertaEm < BOT_THRESHOLD_MS\) \{(.*?)\n  \}",
        js, re.S)
    assert ramo, "sumiu a trava antibot"
    assert "abrirJanela" not in ramo.group(1), "não pode entregar convite sem tentar gravar"
    assert "fecharModal" not in ramo.group(1), "não pode fingir sucesso fechando o modal"


def test_falha_do_post_aparece_para_o_visitante(html, js):
    """Regra 1 da casa: falha silenciosa é o inimigo."""
    assert 'id="form-aviso"' in html
    assert "mostrarFalhaDeCadastro" in js


def test_o_convite_e_entregue_mesmo_quando_o_cadastro_falha(js):
    """Não punir o visitante por um problema que é nosso."""
    corpo = js[js.index("async function submeterLead"):]
    assert "abrirJanela" in corpo
    assert "apontarJanela" in corpo


# ── LGPD ─────────────────────────────────────────────────────────────────────

def test_existe_caixa_de_consentimento_e_ela_nao_vem_marcada(html):
    caixa = re.search(r'<input[^>]*id="consent-check"[^>]*>', html)
    assert caixa, "sem caixa de consentimento"
    assert "checked" not in caixa.group(0), "consentimento não pode vir pré-marcado"


def test_o_consentimento_declara_a_finalidade(html):
    trecho = html[html.index('id="consent-check"'):][:900]
    assert "WhatsApp" in trecho
    assert "grupo" in trecho.lower()


def test_sem_consentimento_o_botao_nao_libera(js):
    checagem = re.search(r"function checarCampos\(\)\s*\{.*?\n\}", js, re.S).group(0)
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


def test_nao_sobrou_caminho_especial_para_o_ofertas_gerais(html, js):
    """A lista embutida escondia o #form-aviso ao ocultar o formulário."""
    for texto in (html, js):
        assert "mostrarListaGeral" not in texto
        assert "montarListaGeral" not in texto
        assert "lista-geral" not in texto


def test_o_aviso_de_falha_nao_mora_em_lugar_que_alguem_esconde(js):
    """#form-aviso é filho do formulário: ninguém pode dar display:none nele."""
    assert "getElementById('lead-form').style.display = 'none'" not in js


                                          # ── colunas da tabela `visitas` ──
# O denominador (22/09/2026). Havia contagem de cadastro e nenhuma de visita:
# sem denominador não existe taxa de conversão, e sem taxa nenhuma mudança na
# página pode ser provada. A tabela é criada por `docs/visitas.sql`, e é DELE
# que saem as colunas conferidas aqui — coluna que o banco não tem devolve HTTP
# 400 e a visita se perde, igual ao lead.
DOCS = RAIZ / "docs"
VISITAS_SQL = DOCS / "visitas.sql"
# `id` e `criado_em` são do banco, não do navegador.
COLUNAS_DO_BANCO = {"id", "criado_em"}


@pytest.fixture(scope="module")
def sql_visitas():
    return VISITAS_SQL.read_text(encoding="utf-8")


def sem_comentarios(sql):
    """Só o SQL que o banco executa: comentário explica, não roda."""
    return "\n".join(l for l in sql.splitlines() if not l.strip().startswith("--"))


def colunas_de(tabela):
    """A tabela como ela fica DEPOIS de todas as migrations de `docs/`: o
    `create table` mais cada `add column` que veio depois. Conferir só o
    primeiro arquivo seria mirar num schema que não existe mais — e coluna que
    o banco não tem devolve HTTP 400 igual ao lead."""
    colunas = set()
    for arquivo in sorted(DOCS.glob("*.sql")):
        sql = sem_comentarios(arquivo.read_text(encoding="utf-8"))
        criada = re.search(r"create table[^(]*\b%s\s*\(\s*\n(.*?)\n\);" % tabela,
                           sql, re.S | re.I)
        if criada:
            colunas |= set(re.findall(r"^\s+(\w+)\s+", criada.group(1), re.M))
        colunas |= set(re.findall(
            r"alter table\s+(?:public\.)?%s\s+add column(?:\s+if not exists)?\s+(\w+)"
            % tabela, sql, re.I))
    assert colunas, f"não achei o schema da tabela `{tabela}` em docs/"
    return colunas


def test_a_migration_da_tabela_de_visitas_esta_no_repositorio(sql_visitas):
    """Schema que só existe no painel do Supabase é schema que ninguém revisa
    e que não volta depois de um acidente."""
    assert colunas_de("visitas") >= COLUNAS_DO_BANCO | {"pagina"}


def test_a_contagem_de_visita_manda_exatamente_as_colunas_da_tabela(js):
    corpo = re.search(r"const visita = \{(.*?)\n  \};", js, re.S)
    assert corpo, "não achei o corpo do POST de visita"
    chaves = set(re.findall(r"^\s{4}(\w+)\s*[:,]", corpo.group(1), re.M))
    assert chaves == colunas_de("visitas") - COLUNAS_DO_BANCO


def test_a_tabela_de_visitas_liga_o_rls(sql_visitas):
    assert re.search(r"enable row level security", sql_visitas, re.I)


def test_a_visita_e_insert_only_pela_chave_anonima(sql_visitas):
    """Mesmo desenho da `leads`: a chave `anon` é pública por desenho (vai no
    HTML de qualquer jeito), então a policy deixa INSERIR e não deixa LER."""
    assert re.search(r"for insert", sql_visitas, re.I)
    assert re.search(r"to anon", sql_visitas, re.I)
    assert not re.search(r"for\s+(select|all|update|delete)", sql_visitas, re.I)


def test_a_tabela_de_visitas_nao_tem_coluna_de_dado_pessoal(sql_visitas):
    """Visita não é lead. Sem consentimento não se guarda pessoa — e aqui não
    há consentimento nenhum para pedir, porque não há pessoa para identificar."""
    colunas = colunas_de("visitas")
    for pessoal in ("nome", "email", "telefone", "ip", "user_agent", "cpf"):
        assert pessoal not in colunas, pessoal


                                     # ── coluna `conteudo` (qual post) ──
# 22/09/2026, logo depois do denominador: `origem`/`meio`/`campanha` dizem de
# qual campanha a pessoa veio, mas não de qual POST. Sem isso não dá para saber
# qual publicação traz gente e qual só faz volume. É só o dado bruto — quem
# decide o que é eficiente é ele, olhando os números.
CONTEUDO_SQL = DOCS / "conteudo.sql"


@pytest.fixture(scope="module")
def sql_conteudo():
    return CONTEUDO_SQL.read_text(encoding="utf-8")


def test_a_coluna_conteudo_entra_nas_duas_tabelas(sql_conteudo):
    """Nas duas ou em nenhuma: `visitas` sem `conteudo` é denominador que não
    quebra por post, e `leads` sem `conteudo` é numerador que não quebra —
    qualquer um dos dois sozinho não vira taxa."""
    alvos = set(re.findall(
        r"alter table\s+public\.(\w+)\s+add column\s+if not exists\s+conteudo\s+text",
        sem_comentarios(sql_conteudo), re.I))
    assert alvos == {"visitas", "leads"}
    assert "conteudo" in colunas_de("visitas")


def test_a_migration_do_conteudo_pode_rodar_duas_vezes(sql_conteudo):
    """Ele aplica à mão, no SQL Editor. Colar de novo por engano não pode dar
    erro no meio do arquivo e deixar metade aplicada."""
    sql = sem_comentarios(sql_conteudo)
    assert not re.search(r"add column(?!\s+if not exists)", sql, re.I)


def test_a_migration_do_conteudo_so_acrescenta(sql_conteudo):
    """Insert-only e policy já existem nas duas tabelas: esta migration não
    mexe em segurança nem apaga nada. O que está escrito aqui vai ser colado no
    banco de produção — uma linha destrutiva no meio não tem como ser desfeita."""
    sql = sem_comentarios(sql_conteudo)
    for proibido in ("drop", "delete", "truncate", "update", "policy", "insert"):
        assert not re.search(r"\b%s\b" % proibido, sql, re.I), proibido


def test_a_migration_do_conteudo_diz_como_aplicar(sql_conteudo):
    """Migration que ninguém sabe rodar é migration que fica parada — e o campo
    chega nulo para sempre sem ninguém entender por quê."""
    assert "jfuqmjbxzhoceycauhys" in sql_conteudo, "sem o projeto, qual banco?"
    assert re.search(r"SQL Editor", sql_conteudo, re.I)


def test_o_cadastro_e_a_visita_mandam_o_mesmo_conteudo(js):
    """O campo tem de sair dos DOIS POSTs pela mesma origem calculada: se um
    lado gravar e o outro não, a taxa por post fica torta e ninguém vê."""
    assert re.search(r"^\s{4}conteudo: origem\.conteudo,$", js, re.M)
    assert re.search(r"^\s{4}conteudo: daVisita\.conteudo,$", js, re.M)


def test_a_contagem_de_visita_nao_e_esperada_por_ninguem(js):
    """`await` aqui seria a página esperando o banco para existir — e, num
    erro, telemetria custando cadastro. Mesma regra do Pixel e da origem."""
    assert re.search(r"^registrarVisita\(\);", js, re.M), "sumiu a chamada"
    assert "await registrarVisita" not in js
