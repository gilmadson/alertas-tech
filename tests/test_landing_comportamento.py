"""O JS da landing rodando de verdade (node + dublê de DOM), sem browser.

Regex prova que o código está escrito; isto prova que ele FAZ. O bug de
09/09/2026 era exatamente um caso em que o código estava lá e não fazia:
o POST era pulado e a página seguia como se tivesse dado certo.

Sem `node` no PATH, os testes são pulados — a suíte não mente dizendo que
passou o que não rodou.
"""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
INDEX = RAIZ / "index.html"
DOM_FALSO = Path(__file__).parent / "js_dom_falso.mjs"
CENARIOS = Path(__file__).parent / "js_cenarios.mjs"

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node não está no PATH")


def js_da_landing():
    html = INDEX.read_text(encoding="utf-8")
    return re.search(r"<script>(.*)</script>", html, re.S).group(1)


def rodar(cenario, tmp_path, **mundo):
    arquivo = tmp_path / "cenario.mjs"
    arquivo.write_text("\n".join([DOM_FALSO.read_text(encoding="utf-8"),
                                  js_da_landing(),
                                  CENARIOS.read_text(encoding="utf-8")]),
                       encoding="utf-8")
    # O node no Windows precisa do ambiente inteiro (SystemRoot e companhia):
    # com um env recortado ele morre com fatal error antes de rodar linha.
    ambiente = dict(os.environ, CENARIO=cenario, **mundo)
    saida = subprocess.run(["node", str(arquivo)], capture_output=True, text=True,
                           encoding="utf-8", env=ambiente)
    assert saida.returncode == 0, saida.stderr
    return json.loads(saida.stdout.strip().splitlines()[-1])


@pytest.fixture(scope="module")
def sucesso(tmp_path_factory):
    return rodar("sucesso", tmp_path_factory.mktemp("ok"))


# ── caminho feliz ────────────────────────────────────────────────────────────

def test_o_lead_e_enviado_ao_supabase(sucesso):
    assert len(sucesso["fetches"]) == 1
    assert sucesso["fetches"][0]["url"].endswith("/rest/v1/leads")


def test_o_corpo_enviado_respeita_o_banco(sucesso):
    corpo = sucesso["fetches"][0]["corpo"]
    assert corpo["telefone"] == "81999998888"
    assert corpo["categoria"] == "smartphone"
    assert corpo["plataforma"] == "wpp"          # CHECK ('wpp','tg')
    assert corpo["lojas"] == "mercadolivre"
    assert set(corpo) == {"nome", "email", "telefone", "categoria", "plataforma",
                          "lojas", "consentimento", "consentimento_em", "origem",
                          "meio", "campanha"}, "coluna que o banco não tem = HTTP 400"


def test_o_grupo_certo_abre(sucesso):
    assert sucesso["abertas"] == [
        "https://chat.whatsapp.com/F2jZYz7jPjP9JFKTvl83F9"]


def test_sucesso_nao_mostra_aviso_e_fecha_o_modal(sucesso):
    assert sucesso["avisoVisivel"] is False
    assert sucesso["modalAtivo"] is False


# ── falha VISÍVEL ────────────────────────────────────────────────────────────

def test_erro_do_banco_aparece_para_o_visitante(tmp_path):
    r = rodar("falha_http", tmp_path)
    assert r["avisoVisivel"] is True
    assert "500" in r["aviso"]
    assert r["modalAtivo"] is True, "o modal fica aberto para a pessoa ler"


def test_rede_fora_tambem_aparece(tmp_path):
    r = rodar("falha_rede", tmp_path)
    assert r["avisoVisivel"] is True
    assert "sem conexão" in r["aviso"]


def test_mesmo_falhando_o_convite_e_entregue(tmp_path):
    r = rodar("falha_http", tmp_path)
    assert r["abertas"] == ["https://chat.whatsapp.com/F2jZYz7jPjP9JFKTvl83F9"]
    assert "chat.whatsapp.com" in r["aviso"], "link manual no aviso"


def test_aba_barrada_pelo_navegador_vira_link_visivel(tmp_path):
    r = rodar("popup_bloqueado", tmp_path)
    assert r["avisoVisivel"] is True
    assert "chat.whatsapp.com" in r["aviso"]


# ── consentimento ────────────────────────────────────────────────────────────

def test_sem_consentimento_o_botao_fica_travado(tmp_path):
    r = rodar("sem_consentimento", tmp_path)
    assert r["botaoLiberado"] is False


def test_com_consentimento_o_botao_libera(sucesso):
    assert sucesso["botaoLiberado"] is True


def test_sem_consentimento_nada_e_enviado_nem_aberto(tmp_path):
    r = rodar("sem_consentimento", tmp_path)
    assert r["fetches"] == []
    assert r["abertas"] == []
    assert "autoriza" in r["erro"].lower()


def test_o_consentimento_nomeia_a_categoria(sucesso):
    assert sucesso["consentTexto"] == "Smartphones"


def test_o_consentimento_nasce_desmarcado_a_cada_abertura(sucesso, tmp_path):
    """abrirModal zera a caixa: consentimento não se herda de outra visita."""
    assert sucesso["consentMarcado"] is True   # foi marcado pelo cenário
    r = rodar("sem_consentimento", tmp_path)
    assert r["consentMarcado"] is False


# ── ofertas gerais ───────────────────────────────────────────────────────────

def test_ofertas_gerais_grava_o_lead_como_geral(tmp_path):
    r = rodar("geral", tmp_path)
    assert r["fetches"][0]["corpo"]["categoria"] == "geral"


def test_ofertas_gerais_abre_o_grupo_de_super_desconto(tmp_path):
    r = rodar("geral", tmp_path)
    assert r["abertas"] == ["https://chat.whatsapp.com/JaSa6KFkq30Ea24cJWx2za"]


def test_ofertas_gerais_fecha_o_modal_como_qualquer_categoria(tmp_path):
    r = rodar("geral", tmp_path)
    assert r["modalAtivo"] is False
    assert r["formDisplay"] != "none", "esconder o formulário some com o aviso"


def test_falha_no_ofertas_gerais_tambem_aparece(tmp_path):
    """Era o buraco: no caminho do card em destaque o aviso existia e ficava
    escondido junto com o formulário."""
    r = rodar("geral_falha_http", tmp_path)
    assert r["avisoVisivel"] is True
    assert r["formDisplay"] != "none"
    assert r["modalAtivo"] is True


def test_ofertas_gerais_esconde_o_botao_do_telegram(tmp_path):
    """O grupo de super desconto só existe no WhatsApp: oferecer Telegram ali
    seria um botão que não leva a lugar nenhum."""
    r = rodar("geral", tmp_path)
    assert r["botaoTelegram"] == "none"


def test_categoria_com_canal_mantem_o_botao_do_telegram(sucesso):
    assert sucesso["botaoTelegram"] == ""


# ── envio rápido (antibot) ───────────────────────────────────────────────────

def test_envio_rapido_nao_finge_sucesso(tmp_path):
    """Antes: convite aberto, modal fechado e ZERO tentativa de gravar."""
    r = rodar("envio_rapido", tmp_path)
    assert r["fetchesTentados"] == 0, "o envio rápido continua sem gravar"
    assert r["abertas"] == [], "nem convite: não houve cadastro"
    assert r["modalAtivo"] is True, "o modal fica aberto"
    assert r["erro"] != "", "e a pessoa lê o motivo"


# ── prova do consentimento ───────────────────────────────────────────────────

UTM_COMPLETO = "?utm_source=instagram&utm_medium=cpc&utm_campaign=piloto"


@pytest.fixture(scope="module")
def cadastro_com_utm(tmp_path_factory):
    return rodar("cadastro", tmp_path_factory.mktemp("utm"), URL_BUSCA=UTM_COMPLETO)


def corpo(resultado):
    return resultado["fetches"][0]["corpo"]


def test_o_aceite_vai_gravado_como_verdadeiro(cadastro_com_utm):
    assert corpo(cadastro_com_utm)["consentimento"] is True


def test_o_aceite_guarda_o_instante_em_que_a_caixa_foi_marcada(cadastro_com_utm):
    """Não é a hora do envio: é a hora do aceite. É essa a prova que a LGPD
    pede — e a que sustenta o link de afiliado da Amazon, que só admite
    comunicação solicitada."""
    quando = corpo(cadastro_com_utm)["consentimento_em"]
    assert quando == cadastro_com_utm["instanteDoAceite"]
    assert quando != cadastro_com_utm["instanteDoEnvio"], "gravou a hora errada"


def test_o_instante_do_aceite_e_uma_data_iso_de_verdade(cadastro_com_utm):
    from datetime import datetime
    quando = corpo(cadastro_com_utm)["consentimento_em"]
    assert datetime.fromisoformat(quando.replace("Z", "+00:00"))


# ── origem da visita (UTM / referrer) ────────────────────────────────────────

def test_utm_da_url_vai_para_origem_meio_e_campanha(cadastro_com_utm):
    c = corpo(cadastro_com_utm)
    assert (c["origem"], c["meio"], c["campanha"]) == ("instagram", "cpc", "piloto")


def test_utm_gigante_e_cortado_em_120(tmp_path):
    r = rodar("cadastro", tmp_path, URL_BUSCA="?utm_source=" + "a" * 300)
    assert len(corpo(r)["origem"]) == 120


def test_utm_com_aspas_e_script_nao_passa(tmp_path):
    """Texto que vem da URL vem do mundo — e vai para o banco."""
    sujo = "?utm_source=%3Cscript%3Ealert(1)%3C/script%3E&utm_medium=%22%3B+DROP&utm_campaign=ok"
    c = corpo(rodar("cadastro", tmp_path, URL_BUSCA=sujo))
    assert c["origem"] == "direto", "utm_source sujo não pode virar origem"
    assert c["meio"] is None and c["campanha"] is None


def test_sem_utm_a_origem_e_o_dominio_de_quem_indicou(tmp_path):
    r = rodar("cadastro", tmp_path,
              REFERRER="https://www.instagram.com/p/algum-post/")
    c = corpo(r)
    assert (c["origem"], c["meio"], c["campanha"]) == ("instagram.com", "referrer", None)


def test_referrer_da_propria_landing_nao_conta_como_origem(tmp_path):
    r = rodar("cadastro", tmp_path,
              REFERRER="https://alertastech-landing.vercel.app/")
    assert corpo(r)["origem"] == "direto"


def test_referrer_que_nao_e_url_nao_derruba_nada(tmp_path):
    r = rodar("cadastro", tmp_path, REFERRER="isto não é uma URL")
    assert corpo(r)["origem"] == "direto"


def test_sem_utm_e_sem_referrer_a_origem_e_direto(tmp_path):
    c = corpo(rodar("cadastro", tmp_path))
    assert (c["origem"], c["meio"], c["campanha"]) == ("direto", None, None)


def test_a_origem_da_visita_fica_guardada_na_sessao(cadastro_com_utm):
    import json as _json
    guardada = _json.loads(cadastro_com_utm["origemGuardada"])
    assert guardada["origem"] == "instagram"


def test_recarregar_sem_utm_mantem_a_origem_da_primeira_visita(tmp_path):
    """Chegou por campanha e depois deu F5 na URL limpa: a origem real é a
    primeira."""
    guardado = '{"origem":"tiktok","meio":"cpc","campanha":"lancamento"}'
    c = corpo(rodar("cadastro", tmp_path, SESSION_GUARDADO=guardado))
    assert (c["origem"], c["meio"], c["campanha"]) == ("tiktok", "cpc", "lancamento")


def test_utm_novo_na_url_vence_o_que_estava_guardado(tmp_path):
    """Clique novo de campanha é origem explícita: não pode ser engolido pelo
    'direto' de uma visita anterior."""
    c = corpo(rodar("cadastro", tmp_path, URL_BUSCA=UTM_COMPLETO,
                    SESSION_GUARDADO='{"origem":"direto","meio":null,"campanha":null}'))
    assert c["origem"] == "instagram"


def test_origem_adulterada_na_sessao_nao_passa(tmp_path):
    """sessionStorage é do visitante: dá para editar à mão."""
    c = corpo(rodar("cadastro", tmp_path,
                    SESSION_GUARDADO='{"origem":"<script>x</script>","meio":"cpc","campanha":"a"}'))
    assert c["origem"] == "direto"


def test_sessao_sem_json_valido_nao_derruba_nada(tmp_path):
    c = corpo(rodar("cadastro", tmp_path, SESSION_GUARDADO="{lixo"))
    assert c["origem"] == "direto"


def test_telemetria_quebrada_nao_perde_o_lead(tmp_path):
    """Nem storage bloqueado (Safari privado), nem location inacessível podem
    custar um cadastro."""
    r = rodar("cadastro", tmp_path, SESSION_QUEBRADO="1", LOCATION_QUEBRADA="1",
              REFERRER="lixo")
    c = corpo(r)
    assert c["telefone"] == "81999998888"
    assert c["consentimento"] is True
    assert c["origem"] == "direto"
    assert r["modalAtivo"] is False, "o cadastro seguiu normal"


# ── Telegram das categorias novas ────────────────────────────────────────────

def test_categoria_sem_canal_proprio_avisa_no_modal(tmp_path):
    r = rodar("telegram_categoria_nova", tmp_path)
    assert "Outros Tech" in r["notaTelegram"]


def test_categoria_sem_canal_proprio_manda_para_o_canal_de_outros(tmp_path):
    r = rodar("telegram_categoria_nova", tmp_path)
    assert r["abertas"] == ["https://t.me/alertatechoutrosprodutos"]
