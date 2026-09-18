"""Testes do sincronizador — todos SEM REDE (o gateway entra por dublê).

A regra que estes testes protegem: se UMA categoria falhar, nada é escrito.
Link vazio é pior que link velho — quem cai num convite morto some, e ninguém
fica sabendo.
"""

import json
from pathlib import Path

import pytest

import sincronizar_landing as sinc

RAIZ = Path(__file__).resolve().parents[1]

CATS = [
    {"slug": "smartphone", "nome": "Smartphones", "emoji": "X",
     "exemplos": "a", "jid": "120363426129841177@g.us",
     "sessao": "70bee236-4d02-48d6-8b8f-f99bec706af7",
     "telegram": "https://t.me/alertatech_smartphone"},
    {"slug": "moda", "nome": "Moda", "emoji": "Y", "exemplos": "b",
     "jid": "120363412462127930@g.us",
     "sessao": "70bee236-4d02-48d6-8b8f-f99bec706af7",
     "telegram": None},
]

# Desde 18/09/2026 o alvo do script é o `landing.js` (o JS saiu do HTML e passou
# a ser compartilhado pelas páginas). O script só enxerga as marcas, mas o dublê
# tem de ter a cara do arquivo de verdade.
JS_BASE = (
    "// antes\n"
    + sinc.MARCA_INICIO + "\n"
    "const GRUPOS = {\n"
    "  'smartphone': { tg: 'https://t.me/alertatech_smartphone', wpp: 'https://chat.whatsapp.com/VELHOvelhovelho1' },\n"
    "  'moda':       { tg: null, wpp: 'https://chat.whatsapp.com/VELHOvelhovelho2' },\n"
    "};\n"
    + sinc.MARCA_FIM + "\n"
    "// depois\n"
)


def buscador_falso(mapa):
    """Devolve um buscador que responde pelo JID, como o gateway responderia."""
    def buscar(sessao, jid):
        if jid not in mapa:
            raise sinc.ErroSincronizacao(f"grupo {jid} não respondeu")
        valor = mapa[jid]
        if isinstance(valor, Exception):
            raise valor
        return valor
    return buscar


NOVOS = {
    "120363426129841177@g.us": "https://chat.whatsapp.com/F2jZYz7jPjP9JFKTvl83F9",
    "120363412462127930@g.us": "https://chat.whatsapp.com/NOVOnovonovonovo22",
}


@pytest.fixture
def landing(tmp_path):
    alvo = tmp_path / "landing.js"
    alvo.write_text(JS_BASE, encoding="utf-8")
    return alvo


@pytest.fixture
def grupos_json(tmp_path):
    alvo = tmp_path / "grupos.json"
    alvo.write_text(json.dumps(
        {"gateway": {"base_url": "http://gateway.invalido:1", "chave_env": "OPENWA_API_KEY"},
         "telegram_fallback": "https://t.me/alertatechoutrosprodutos",
         "categorias": CATS}, ensure_ascii=False), encoding="utf-8")
    return alvo


# ── leitura ──────────────────────────────────────────────────────────────────

def test_carregar_grupos_le_o_arquivo_de_verdade():
    dados = sinc.carregar_grupos(RAIZ / "grupos.json")
    assert len(dados["categorias"]) == 21   # 19 do motor + geral + imperdiveis


def test_carregar_grupos_recusa_arquivo_sem_categorias(tmp_path):
    ruim = tmp_path / "g.json"
    ruim.write_text('{"categorias": []}', encoding="utf-8")
    with pytest.raises(sinc.ErroSincronizacao):
        sinc.carregar_grupos(ruim)


def test_carregar_grupos_recusa_categoria_sem_jid(tmp_path):
    ruim = tmp_path / "g.json"
    ruim.write_text('{"categorias": [{"slug": "x", "sessao": "s"}]}', encoding="utf-8")
    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.carregar_grupos(ruim)
    assert "jid" in str(erro.value)


def test_carregar_grupos_recusa_arquivo_que_nao_existe(tmp_path):
    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.carregar_grupos(tmp_path / "nao_existe.json")
    assert "não existe" in str(erro.value)


def test_carregar_grupos_recusa_json_quebrado(tmp_path):
    ruim = tmp_path / "g.json"
    ruim.write_text("{isto não é json", encoding="utf-8")
    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.carregar_grupos(ruim)
    assert "JSON" in str(erro.value)


def test_ler_bloco_devolve_so_o_miolo():
    bloco = sinc.ler_bloco(JS_BASE)
    assert "const GRUPOS" in bloco
    assert "antes" not in bloco


def test_ler_bloco_sem_marca_falha():
    with pytest.raises(sinc.ErroSincronizacao):
        sinc.ler_bloco("<html>sem marcas</html>")


def test_parse_bloco_le_links_e_telegram_nulo():
    mapa = sinc.parse_bloco(sinc.ler_bloco(JS_BASE))
    assert mapa["smartphone"]["wpp"].endswith("VELHOvelhovelho1")
    assert mapa["smartphone"]["tg"] == "https://t.me/alertatech_smartphone"
    assert mapa["moda"]["tg"] is None


# ── coleta ───────────────────────────────────────────────────────────────────

def test_coleta_convite_de_todas_as_categorias():
    convites = sinc.coletar_convites(CATS, buscador_falso(NOVOS))
    assert convites == {"smartphone": NOVOS[CATS[0]["jid"]],
                        "moda": NOVOS[CATS[1]["jid"]]}


def test_uma_categoria_que_falha_derruba_a_coleta_inteira():
    quebrado = dict(NOVOS)
    quebrado[CATS[1]["jid"]] = sinc.ErroSincronizacao("HTTP 500")
    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.coletar_convites(CATS, buscador_falso(quebrado))
    assert "moda" in str(erro.value)


def test_link_vazio_conta_como_falha():
    quebrado = dict(NOVOS)
    quebrado[CATS[0]["jid"]] = ""
    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.coletar_convites(CATS, buscador_falso(quebrado))
    assert "smartphone" in str(erro.value)


def test_link_que_nao_e_convite_do_whatsapp_conta_como_falha():
    quebrado = dict(NOVOS)
    quebrado[CATS[0]["jid"]] = "http://exemplo.com/entrar"
    with pytest.raises(sinc.ErroSincronizacao):
        sinc.coletar_convites(CATS, buscador_falso(quebrado))


def test_coleta_pausa_entre_as_chamadas():
    """Medido em 09/09/2026: 18 pedidos seguidos derrubam o gateway em HTTP 500
    a partir do 12º (o WhatsApp limita a consulta de convite). Com pausa, passa."""
    dormidas = []
    sinc.coletar_convites(CATS, buscador_falso(NOVOS), pausa=2.0,
                          dormir=dormidas.append)
    assert dormidas and all(d >= 2.0 for d in dormidas)


def test_coleta_tenta_de_novo_quando_o_gateway_tropeca():
    tentativas = {"n": 0}

    def instavel(sessao, jid):
        if jid == CATS[1]["jid"]:
            tentativas["n"] += 1
            if tentativas["n"] < 2:
                raise sinc.ErroSincronizacao("gateway devolveu HTTP 500")
        return NOVOS[jid]

    convites = sinc.coletar_convites(CATS, instavel, tentativas=3, dormir=lambda _: None)
    assert convites["moda"] == NOVOS[CATS[1]["jid"]]


def test_coleta_desiste_depois_das_tentativas():
    def sempre_ruim(sessao, jid):
        raise sinc.ErroSincronizacao("gateway devolveu HTTP 500")

    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.coletar_convites(CATS, sempre_ruim, tentativas=2, dormir=lambda _: None)
    assert "smartphone" in str(erro.value) and "moda" in str(erro.value)


def test_mesmo_convite_em_duas_categorias_conta_como_falha():
    igual = {CATS[0]["jid"]: NOVOS[CATS[0]["jid"]],
             CATS[1]["jid"]: NOVOS[CATS[0]["jid"]]}
    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.coletar_convites(CATS, buscador_falso(igual))
    assert "repetido" in str(erro.value).lower()


# ── montagem e escrita ───────────────────────────────────────────────────────

def test_bloco_montado_volta_igual_no_parse():
    bloco = sinc.montar_bloco(CATS, {"smartphone": NOVOS[CATS[0]["jid"]],
                                     "moda": NOVOS[CATS[1]["jid"]]})
    mapa = sinc.parse_bloco(bloco)
    assert mapa["smartphone"]["wpp"] == NOVOS[CATS[0]["jid"]]
    assert mapa["moda"]["tg"] is None
    assert sinc.MARCA_INICIO not in bloco


def test_substituir_bloco_preserva_o_resto_do_arquivo():
    bloco = sinc.montar_bloco(CATS, {"smartphone": NOVOS[CATS[0]["jid"]],
                                     "moda": NOVOS[CATS[1]["jid"]]})
    novo = sinc.substituir_bloco(JS_BASE, bloco)
    assert "// antes" in novo and "// depois" in novo
    assert "VELHOvelhovelho1" not in novo
    assert sinc.parse_bloco(sinc.ler_bloco(novo))["smartphone"]["wpp"] == NOVOS[CATS[0]["jid"]]


def test_substituir_sem_marca_falha():
    with pytest.raises(sinc.ErroSincronizacao):
        sinc.substituir_bloco("<html>nada</html>", "x")


def test_resumo_separa_o_que_mudou_do_que_ficou_igual():
    antes = {"smartphone": {"wpp": "https://chat.whatsapp.com/AAA", "tg": None},
             "moda": {"wpp": "https://chat.whatsapp.com/BBB", "tg": None}}
    depois = {"smartphone": "https://chat.whatsapp.com/AAA",
              "moda": "https://chat.whatsapp.com/ZZZ"}
    linhas = sinc.resumir(antes, depois)
    texto = "\n".join(linhas)
    assert "moda" in texto and "ZZZ" in texto
    assert any("smartphone" in ln and "igual" in ln.lower() for ln in linhas)


def test_resumo_avisa_categoria_que_sumiu_do_json():
    linhas = sinc.resumir({"velha": {"wpp": "https://chat.whatsapp.com/AAA", "tg": None}}, {})
    assert any("saiu" in ln for ln in linhas)


def test_resumo_marca_categoria_nova():
    linhas = sinc.resumir({}, {"moda": "https://chat.whatsapp.com/ZZZ"})
    assert any("nova" in ln.lower() for ln in linhas)


# ── gateway (com dublê de HTTP) ──────────────────────────────────────────────

class RespostaFalsa:
    def __init__(self, status, corpo):
        self.status_code = status
        self._corpo = corpo
        self.text = json.dumps(corpo)

    def json(self):
        return self._corpo


class HttpFalso:
    def __init__(self, resposta):
        self.resposta = resposta
        self.chamadas = []

    def get(self, url, headers=None, timeout=None):
        self.chamadas.append({"url": url, "headers": headers, "timeout": timeout})
        return self.resposta


def test_buscar_convite_monta_rota_e_header():
    http = HttpFalso(RespostaFalsa(200, {"inviteCode": "abc",
                                         "inviteLink": "https://chat.whatsapp.com/abc"}))
    link = sinc.buscar_convite("sessao-1", "123@g.us",
                               base_url="http://gw:2785/", api_key="segredo", http=http)
    assert link == "https://chat.whatsapp.com/abc"
    chamada = http.chamadas[0]
    assert chamada["url"] == "http://gw:2785/api/sessions/sessao-1/groups/123@g.us/invite-code"
    assert chamada["headers"]["X-API-Key"] == "segredo"


def test_buscar_convite_monta_link_quando_so_vem_o_codigo():
    http = HttpFalso(RespostaFalsa(200, {"inviteCode": "abc"}))
    assert sinc.buscar_convite("s", "1@g.us", base_url="http://gw", api_key="k",
                               http=http) == "https://chat.whatsapp.com/abc"


def test_buscar_convite_falha_em_status_diferente_de_200():
    http = HttpFalso(RespostaFalsa(500, {"message": "Internal server error"}))
    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.buscar_convite("s", "1@g.us", base_url="http://gw", api_key="k", http=http)
    assert "500" in str(erro.value)


def test_buscar_convite_falha_quando_a_rede_cai():
    class HttpQuebrado:
        def get(self, *a, **k):
            raise ConnectionError("sem rota")

    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.buscar_convite("s", "1@g.us", base_url="http://gw", api_key="k",
                            http=HttpQuebrado())
    assert "ConnectionError" in str(erro.value)


def test_buscar_convite_falha_quando_a_resposta_nao_e_json():
    class RespostaCrua(RespostaFalsa):
        def json(self):
            raise ValueError("não é json")

    http = HttpFalso(RespostaCrua(200, {}))
    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.buscar_convite("s", "1@g.us", base_url="http://gw", api_key="k", http=http)
    assert "JSON" in str(erro.value)


def test_buscar_convite_falha_quando_vem_200_sem_convite():
    http = HttpFalso(RespostaFalsa(200, {"tudoBem": True}))
    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.buscar_convite("s", "1@g.us", base_url="http://gw", api_key="k", http=http)
    assert "sem convite" in str(erro.value)


def test_buscar_convite_recusa_json_que_nao_e_objeto():
    """`null` e listas são JSON válido — e não têm convite dentro."""
    for corpo in (None, [1, 2], "texto"):
        http = HttpFalso(RespostaFalsa(200, corpo))
        with pytest.raises(sinc.ErroSincronizacao) as erro:
            sinc.buscar_convite("s", "1@g.us", base_url="http://gw", api_key="k",
                                http=http)
        assert "objeto" in str(erro.value)


def test_buscar_convite_recusa_convite_que_nao_e_texto():
    for corpo in ({"inviteCode": 12345}, {"inviteLink": ["x"]},
                  {"inviteCode": None, "inviteLink": None}):
        http = HttpFalso(RespostaFalsa(200, corpo))
        with pytest.raises(sinc.ErroSincronizacao) as erro:
            sinc.buscar_convite("s", "1@g.us", base_url="http://gw", api_key="k",
                                http=http)
        assert "sem convite" in str(erro.value)


def test_buscar_convite_nao_vaza_a_chave_na_mensagem_de_erro():
    http = HttpFalso(RespostaFalsa(401, {"message": "unauthorized"}))
    with pytest.raises(sinc.ErroSincronizacao) as erro:
        sinc.buscar_convite("s", "1@g.us", base_url="http://gw",
                            api_key="chave-super-secreta", http=http)
    assert "chave-super-secreta" not in str(erro.value)


# ── gravação atômica ─────────────────────────────────────────────────────────

def test_gravacao_troca_o_arquivo_de_uma_vez(tmp_path):
    alvo = tmp_path / "index.html"
    alvo.write_text("velho", encoding="utf-8")
    sinc.gravar_atomico(alvo, "novo")
    assert alvo.read_text(encoding="utf-8") == "novo"
    assert list(tmp_path.iterdir()) == [alvo], "temporário ficou para trás"


def test_falha_no_meio_da_troca_nao_estraga_o_arquivo(tmp_path, monkeypatch):
    """Interrupção no meio não pode deixar o index.html pela metade."""
    alvo = tmp_path / "index.html"
    alvo.write_text("página inteira", encoding="utf-8")

    def replace_quebrado(*a, **k):
        raise OSError("disco cheio")

    monkeypatch.setattr(sinc.os, "replace", replace_quebrado)
    with pytest.raises(sinc.ErroSincronizacao):
        sinc.gravar_atomico(alvo, "conteúdo novo")
    assert alvo.read_text(encoding="utf-8") == "página inteira"
    assert list(tmp_path.iterdir()) == [alvo], "temporário ficou para trás"


def test_main_avisa_quando_nao_consegue_gravar(landing, grupos_json, monkeypatch, capsys):
    monkeypatch.setenv("OPENWA_API_KEY", "k")
    monkeypatch.setattr(sinc, "gravar_atomico",
                        lambda *a: (_ for _ in ()).throw(sinc.ErroSincronizacao("disco cheio")))
    codigo = sinc.main(argv(landing, grupos_json), buscador=buscador_falso(NOVOS))
    assert codigo == 1
    assert "disco cheio" in capsys.readouterr().err
    assert landing.read_text(encoding="utf-8") == JS_BASE


# ── main ─────────────────────────────────────────────────────────────────────

def argv(landing, grupos_json, *extra):
    # --pausa 0: a espera existe para o gateway de verdade, não para o dublê.
    return ["--alvo", str(landing), "--grupos", str(grupos_json),
            "--pausa", "0", *extra]


def test_o_alvo_padrao_e_o_landing_js():
    """O JS saiu do HTML em 18/09/2026. Se o padrão tivesse ficado no
    `index.html`, a próxima sincronização de convites escreveria no arquivo
    errado e as 21 categorias publicadas parariam de ser atualizadas — sem
    erro nenhum na tela."""
    assert sinc.ALVO_PADRAO.name == "landing.js"


def test_main_grava_os_convites_novos(landing, grupos_json, monkeypatch, capsys):
    monkeypatch.setenv("OPENWA_API_KEY", "k")
    codigo = sinc.main(argv(landing, grupos_json), buscador=buscador_falso(NOVOS))
    assert codigo == 0
    texto = landing.read_text(encoding="utf-8")
    assert "F2jZYz7jPjP9JFKTvl83F9" in texto
    assert "VELHOvelhovelho1" not in texto
    assert "moda" in capsys.readouterr().out


def test_main_e_idempotente(landing, grupos_json, monkeypatch):
    monkeypatch.setenv("OPENWA_API_KEY", "k")
    sinc.main(argv(landing, grupos_json), buscador=buscador_falso(NOVOS))
    primeira = landing.read_text(encoding="utf-8")
    sinc.main(argv(landing, grupos_json), buscador=buscador_falso(NOVOS))
    assert landing.read_text(encoding="utf-8") == primeira


def test_main_nao_escreve_nada_quando_uma_categoria_falha(landing, grupos_json, monkeypatch, capsys):
    monkeypatch.setenv("OPENWA_API_KEY", "k")
    quebrado = dict(NOVOS)
    quebrado[CATS[1]["jid"]] = sinc.ErroSincronizacao("HTTP 500")
    codigo = sinc.main(argv(landing, grupos_json), buscador=buscador_falso(quebrado))
    assert codigo == 1
    assert landing.read_text(encoding="utf-8") == JS_BASE
    assert "moda" in capsys.readouterr().err


def test_main_exige_a_chave_no_ambiente(landing, grupos_json, monkeypatch, capsys):
    monkeypatch.delenv("OPENWA_API_KEY", raising=False)
    codigo = sinc.main(argv(landing, grupos_json))
    assert codigo == 2
    assert "OPENWA_API_KEY" in capsys.readouterr().err
    assert landing.read_text(encoding="utf-8") == JS_BASE


def test_dry_run_mostra_mas_nao_grava(landing, grupos_json, monkeypatch, capsys):
    monkeypatch.setenv("OPENWA_API_KEY", "k")
    codigo = sinc.main(argv(landing, grupos_json, "--dry-run"),
                       buscador=buscador_falso(NOVOS))
    assert codigo == 0
    assert landing.read_text(encoding="utf-8") == JS_BASE
    assert "F2jZYz7jPjP9JFKTvl83F9" in capsys.readouterr().out


def test_main_avisa_quando_nada_mudou(landing, grupos_json, monkeypatch, capsys):
    monkeypatch.setenv("OPENWA_API_KEY", "k")
    sinc.main(argv(landing, grupos_json), buscador=buscador_falso(NOVOS))
    sinc.main(argv(landing, grupos_json), buscador=buscador_falso(NOVOS))
    assert "igual" in capsys.readouterr().out.lower()
