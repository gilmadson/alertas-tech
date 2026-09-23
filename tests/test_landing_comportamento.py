"""O JS da landing rodando de verdade (node + dublê de DOM), sem browser.

Regex prova que o código está escrito; isto prova que ele FAZ. O bug de
09/09/2026 era exatamente um caso em que o código estava lá e não fazia:
o POST era pulado e a página seguia como se tivesse dado certo.

Sem `node` no PATH, os testes são pulados — a suíte não mente dizendo que
passou o que não rodou.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
# Até 18/09/2026 este arquivo recortava o último `<script>` do index.html. O JS
# agora mora fora do HTML (`landing.js`), compartilhado pelas páginas — ler o
# arquivo direto é ler exatamente o que vai para o ar, sem recorte nenhum.
LANDING_JS = RAIZ / "landing.js"
DOM_FALSO = Path(__file__).parent / "js_dom_falso.mjs"
CENARIOS = Path(__file__).parent / "js_cenarios.mjs"

pytestmark = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node não está no PATH")


def js_da_landing():
    return LANDING_JS.read_text(encoding="utf-8")


def _executar(cenario, tmp_path, **mundo):
    arquivo = tmp_path / "cenario.mjs"
    arquivo.write_text("\n".join([DOM_FALSO.read_text(encoding="utf-8"),
                                  js_da_landing(),
                                  CENARIOS.read_text(encoding="utf-8")]),
                       encoding="utf-8")
    # O node no Windows precisa do ambiente inteiro (SystemRoot e companhia):
    # com um env recortado ele morre com fatal error antes de rodar linha.
    ambiente = dict(os.environ, CENARIO=cenario, **mundo)
    return subprocess.run(["node", str(arquivo)], capture_output=True, text=True,
                          encoding="utf-8", env=ambiente)


def rodar(cenario, tmp_path, **mundo):
    saida = _executar(cenario, tmp_path, **mundo)
    assert saida.returncode == 0, saida.stderr
    return json.loads(saida.stdout.strip().splitlines()[-1])


def rodar_esperando_erro(cenario, tmp_path, **mundo):
    """Para provar que o dublê estrito realmente morde."""
    saida = _executar(cenario, tmp_path, **mundo)
    assert saida.returncode != 0, "esperava o cenário quebrar e ele passou"
    return saida.stderr


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
                          "meio", "campanha", "conteudo"}, \
        "coluna que o banco não tem = HTTP 400"


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


def test_a_janela_abre_antes_do_post_para_nao_ser_barrada_pelo_safari(sucesso):
    """Achado de 22/09/2026: o Gilmadson tocou "Entrar pelo WhatsApp", o
    cadastro gravou (linha 16 da `leads`, testado e confirmado no banco), e o
    Safari do iPhone dele nunca abriu o grupo — sem erro nenhum na tela.

    Causa: `window.open` só é permitido pelo Safari dentro do mesmo gesto
    síncrono do toque. Chamar depois de um `await` (o POST no Supabase) é
    barrado em silêncio. A prova certa não é "abriu ou não abriu" — isso o
    `popup_bloqueado` já cobria — é a ORDEM: a janela tem de abrir ANTES do
    POST começar, não depois dele terminar."""
    ordem = sucesso["ordemDeChamadas"]
    assert "abrir-janela" in ordem, "a janela nunca abriu"
    assert "fetch:leads" in ordem, "o POST do cadastro nunca aconteceu"
    assert ordem.index("abrir-janela") < ordem.index("fetch:leads"), \
        "abriu a janela DEPOIS do POST — é exatamente o que o Safari barra"


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


# ── sorteio de quem não quer escolher (achado de 22/09/2026) ────────────────
# "Ofertas gerais" promete "qualquer loja, não quero escolher" — mas pedia pra
# marcar as 6 caixas de loja uma por uma mesmo assim. O Gilmadson pediu pra
# tirar essa escolha e sortear, sem o usuário ver, entre os dois grupos que já
# existem pra quem não quer escolher: Ofertas gerais (geral) e Imperdíveis ML.

def test_categoria_comum_continua_mostrando_a_secao_de_lojas(sucesso):
    """Só as categorias "sem escolha" mudam — o resto do grid (Smartphones
    aqui) continua pedindo loja como sempre."""
    assert sucesso["secaoLojas"] != "none"
    assert sucesso["subtituloModal"] == \
        "Deixa seu contato e escolha de quais lojas quer receber alertas."


def test_ofertas_gerais_esconde_a_secao_de_lojas(tmp_path):
    r = rodar("geral", tmp_path)
    assert r["secaoLojas"] == "none"
    assert r["subtituloModal"] == "Deixa seu contato — a gente cuida do resto."


def test_ofertas_gerais_grava_todas_as_lojas_quando_o_sorteio_fica_nele(tmp_path):
    """Sem forçar o sorteio, o dublê cai sempre no mesmo lado (< 0,5): é o
    "geral" de sempre, com a promessa de "qualquer loja" batendo de verdade."""
    r = rodar("geral", tmp_path)
    assert corpo(r)["lojas"] == "mercadolivre,amazon,magalu,shopee,aliexpress,kabum"


def test_sorteio_pode_cair_no_imperdiveis_sem_o_usuario_escolher(tmp_path):
    """Mesmo clique de sempre em "Ofertas gerais" — o card não muda de nome,
    só o destino de verdade muda, e a pessoa nunca vê essa escolha."""
    r = rodar("geral_sorteado_imperdiveis", tmp_path, SORTEIO_FORCA_IMPERDIVEIS="1")
    c = corpo(r)
    assert c["categoria"] == "imperdiveis"
    assert c["lojas"] == "mercadolivre", "a loja gravada tem de ser a verdadeira do grupo sorteado"
    assert r["abertas"] == ["https://chat.whatsapp.com/IqTCyshHhzkEkN7cNbG2mC"]
    assert r["secaoLojas"] == "none"


def test_imperdiveis_clicado_direto_no_grid_tambem_fica_sem_escolha_de_loja(tmp_path):
    """"Imperdíveis ML" é card comum do grid nesta página (não a exclusiva) —
    antes pedia loja como qualquer outro, mas o grupo só manda Mercado Livre
    aqui também. Clicar direto tem de valer a mesma regra do sorteio."""
    r = rodar("imperdiveis_direto_no_grid", tmp_path)
    c = corpo(r)
    assert c["categoria"] == "imperdiveis"
    assert c["lojas"] == "mercadolivre"
    assert r["secaoLojas"] == "none"
    assert r["abertas"] == ["https://chat.whatsapp.com/IqTCyshHhzkEkN7cNbG2mC"]


def test_salao_esconde_o_telegram_e_entrega_o_grupo_certo(tmp_path):
    """`salao` (10/09/2026) é a segunda entrada com `tg: null` — e a primeira
    num card COMUM do grid, não no card em destaque do `geral`.

    Vale rodar de verdade porque isto lê o bloco GRUPOS do `index.html`
    publicado: prova que o convite do salão está lá e que o botão do Telegram
    some, em vez de prometer um canal que não existe. Se alguém "consertar" o
    `tg: null` para o canal de fallback, é aqui que aparece.
    """
    r = rodar("salao", tmp_path)
    assert r["botaoTelegram"] == "none"
    assert r["abertas"] == ["https://chat.whatsapp.com/CfN9CT2HnWGGpK2qaQ2KFm"]
    assert r["fetches"][0]["corpo"]["categoria"] == "salao"


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


# ── página exclusiva do Imperdíveis ML ───────────────────────────────────────
# A página não tem seção de lojas (o motor dos imperdíveis é 100% Mercado
# Livre): ela declara a loja fixa em `<body data-lojas="...">`. Aqui o dublê de
# DOM roda ESTRITO — se o JS encostar numa caixa `loja-*` que a página não tem,
# o cenário morre. É o que aconteceria no navegador de verdade.

MUNDO_IMPERDIVEIS = {"BODY_LOJAS": "mercadolivre", "DOM_SEM_LOJAS": "1"}


@pytest.fixture(scope="module")
def imperdiveis(tmp_path_factory):
    return rodar("imperdiveis", tmp_path_factory.mktemp("imp"), **MUNDO_IMPERDIVEIS)


def test_imperdiveis_grava_o_lead_na_categoria_certa(imperdiveis):
    assert corpo(imperdiveis)["categoria"] == "imperdiveis"


def test_imperdiveis_grava_a_loja_fixa_sem_caixa_nenhuma(imperdiveis):
    """O grupo só recebe Mercado Livre: o lead tem de sair dizendo isso."""
    assert corpo(imperdiveis)["lojas"] == "mercadolivre"


def test_imperdiveis_abre_o_grupo_do_motor_de_imperdiveis(imperdiveis):
    assert imperdiveis["abertas"] == [
        "https://chat.whatsapp.com/IqTCyshHhzkEkN7cNbG2mC"]


def test_imperdiveis_libera_o_botao_mesmo_sem_secao_de_lojas(imperdiveis):
    """`checarCampos` exige pelo menos uma loja: sem a loja fixa o botão
    ficaria travado para sempre e a página nova não captaria ninguém."""
    assert imperdiveis["botaoLiberado"] is True
    assert imperdiveis["modalAtivo"] is False


def test_imperdiveis_esconde_o_botao_do_telegram(imperdiveis):
    assert imperdiveis["botaoTelegram"] == "none"


def test_falha_de_cadastro_no_imperdiveis_tambem_aparece(tmp_path):
    """Página nova não pode trazer de volta o sucesso fingido."""
    r = rodar("imperdiveis_falha_http", tmp_path, **MUNDO_IMPERDIVEIS)
    assert r["avisoVisivel"] is True
    assert r["modalAtivo"] is True
    assert r["abertas"] == ["https://chat.whatsapp.com/IqTCyshHhzkEkN7cNbG2mC"]


def test_categoria_sem_fallback_proprio_ainda_quebra_sem_a_loja_declarada(tmp_path):
    """Prova que o dublê estrito morde — senão os testes acima não provariam
    nada. Só Imperdíveis ML (e Ofertas gerais) têm um segundo dono da verdade
    sobre a loja (`LOJAS_SEM_ESCOLHA`, 22/09/2026); qualquer categoria
    exclusiva FUTURA que esquecer o `data-lojas` ainda cai aqui, não no ar —
    'smartphone' aqui representa essa categoria futura."""
    erro = rodar_esperando_erro("sucesso", tmp_path, DOM_SEM_LOJAS="1")
    assert "loja-" in erro


def test_imperdiveis_tem_fallback_proprio_mesmo_sem_data_lojas(tmp_path):
    """Achado de 22/09/2026: Imperdíveis ML ganhou um segundo dono da verdade
    sobre a própria loja fixa (`LOJAS_SEM_ESCOLHA['imperdiveis']`), porque o
    sorteio de "Ofertas gerais" pode cair nele em páginas que não têm — nem
    podem ter — `data-lojas` fixo (index.html e super-desconto.html servem
    várias categorias). Redundância proposital: mesmo que a declaração da
    página exclusiva suma, o valor gravado continua correto."""
    r = rodar("imperdiveis", tmp_path, DOM_SEM_LOJAS="1")
    c = corpo(r)
    assert c["categoria"] == "imperdiveis"
    assert c["lojas"] == "mercadolivre"


# ── página sem grade: abertura automática e o botão "Cancelar" ──────────────
# Achado do projeto-arquiteto (23/09/2026): o mecanismo de `data-auto-abrir`
# nunca tinha teste próprio — os cenários de página exclusiva acima chamam
# `abrirModal` direto, sem provar que o clique automático em si funciona. E
# "Cancelar" numa página sem grade (a `.categorias` já está escondida por
# CSS) deixava a pessoa numa tela vazia: sem card pra clicar de novo, só o F5
# trazia o formulário de volta. Fica mais grave agora que o index.html também
# usa esse padrão — antes era só um canto pouco visitado das exclusivas.

def test_pagina_sem_grade_abre_o_formulario_sozinha(tmp_path):
    r = rodar("abertura_automatica", tmp_path, BODY_AUTOABRIR="geral")
    assert r["modalAtivoSozinho"] is True


def test_cancelar_em_pagina_sem_grade_reabre_em_vez_de_sumir(tmp_path):
    r = rodar("cancelar_em_pagina_sem_grade", tmp_path, BODY_AUTOABRIR="geral")
    assert r["modalAtivo"] is True, "cancelar não pode deixar tela vazia"
    assert r["nomePreenchido"] == "", "tem de reabrir limpo, não com dado velho"


def test_cancelar_em_pagina_com_grade_continua_fechando(tmp_path):
    """Sem `data-auto-abrir`: comportamento de sempre — cancelar fecha o
    modal, a grade por baixo resolve. Nenhuma página pública usa mais este
    caminho hoje, mas o código ainda o suporta — este teste é a garantia."""
    r = rodar("cancelar_em_pagina_com_grade", tmp_path)
    assert r["modalAtivo"] is False


# ── Telegram das categorias novas ────────────────────────────────────────────

def test_categoria_sem_canal_proprio_avisa_no_modal(tmp_path):
    r = rodar("telegram_categoria_nova", tmp_path)
    assert "Outros Tech" in r["notaTelegram"]


def test_categoria_sem_canal_proprio_manda_para_o_canal_de_outros(tmp_path):
    r = rodar("telegram_categoria_nova", tmp_path)
    assert r["abertas"] == ["https://t.me/alertatechoutrosprodutos"]


# ── contagem de visita (o denominador) ───────────────────────────────────────
# Até 22/09/2026 o projeto contava CADASTRO e não contava VISITA. Sem saber
# quanta gente entrou na página não existe taxa de conversão — e sem taxa,
# nenhuma mudança na landing pode ser provada boa ou ruim. Foi por isso que o
# redesenho foi vetado: não havia como mostrar que melhoraria algo.
#
# Aqui a contagem roda de verdade: sai sozinha no carregamento, sai sem dado
# pessoal, e não encosta no caminho do lead.

MUNDO_INDEX = {"BODY_PAGINA": "index"}


@pytest.fixture(scope="module")
def visita_do_index(tmp_path_factory):
    return rodar("visita", tmp_path_factory.mktemp("visita"), **MUNDO_INDEX)


def visita(resultado):
    assert resultado["visitas"], "nenhuma visita foi contada"
    return resultado["visitas"][0]["corpo"]


def test_a_visita_e_contada_sozinha_no_carregamento(visita_do_index):
    """Ninguém clicou em nada no cenário: quem abre a página já conta."""
    assert len(visita_do_index["visitas"]) == 1
    assert visita_do_index["visitas"][0]["url"].endswith("/rest/v1/visitas")


def test_a_visita_vai_com_a_chave_anonima(visita_do_index):
    assert visita_do_index["visitas"][0]["apikey"] == "eyJhbGciOiJI"


def test_a_visita_diz_qual_pagina_foi(visita_do_index):
    assert visita(visita_do_index)["pagina"] == "index"


def test_cada_pagina_conta_no_proprio_nome(tmp_path):
    r = rodar("visita", tmp_path, BODY_PAGINA="imperdiveis")
    assert visita(r)["pagina"] == "imperdiveis"


def test_pagina_que_esquecer_de_se_declarar_grita_no_relatorio(tmp_path):
    """Ausência de declaração não vale como decisão. Se alguém publicar uma
    página nova sem `data-pagina`, o dado diz isso em vez de somar no balde
    errado — e `tests/test_paginas.py` pega antes de ir para o ar."""
    r = rodar("visita", tmp_path)
    assert visita(r)["pagina"] == "nao-declarada"


def test_a_visita_nao_carrega_dado_pessoal(visita_do_index):
    """Visita não é lead: nada de telefone, e-mail, nome ou IP. Só instante
    (do banco), qual página, de onde veio, por qual post e em qual hospedagem."""
    c = visita(visita_do_index)
    assert set(c) == {"pagina", "hospedagem", "origem", "meio", "campanha",
                      "conteudo"}


def test_a_visita_carrega_a_mesma_origem_que_o_lead_carregaria(tmp_path):
    """O denominador tem de ser quebrável por campanha, senão só dá para medir
    o site inteiro — e campanha nenhuma consegue se defender."""
    r = rodar("visita", tmp_path, URL_BUSCA=UTM_COMPLETO, **MUNDO_INDEX)
    c = visita(r)
    assert (c["origem"], c["meio"], c["campanha"]) == ("instagram", "cpc", "piloto")


def test_visita_sem_utm_e_sem_referrer_e_direto(visita_do_index):
    c = visita(visita_do_index)
    assert (c["origem"], c["meio"], c["campanha"]) == ("direto", None, None)


def test_a_visita_diz_de_qual_hospedagem_ela_veio(visita_do_index):
    assert visita(visita_do_index)["hospedagem"] == "alertastech-landing.vercel.app"


def test_o_espelho_do_github_pages_tambem_e_contado(tmp_path):
    """A página vive em DUAS hospedagens, e as duas recebem gente. Foi este o
    motivo de a contagem ficar no Supabase e não no Analytics do Vercel: medida
    que só vê metade da casa é a medida que engana."""
    r = rodar("visita", tmp_path, HOSTNAME="gilmadson.github.io", **MUNDO_INDEX)
    assert visita(r)["hospedagem"] == "gilmadson.github.io"


def test_recarregar_na_mesma_sessao_nao_conta_visita_de_novo(tmp_path):
    """F5 não é visita nova. Denominador inflado por recarregamento faz a taxa
    de conversão parecer pior do que é."""
    r = rodar("visita_recarregada", tmp_path, **MUNDO_INDEX)
    assert len(r["visitas"]) == 1


def test_quem_ja_foi_contado_na_sessao_nao_conta_outra_vez(tmp_path):
    r = rodar("visita", tmp_path, VISITA_CONTADA_EM="index", **MUNDO_INDEX)
    assert r["visitas"] == []


def test_outra_pagina_na_mesma_sessao_conta_a_propria_visita(tmp_path):
    """A marca é por página: quem foi contado no index e depois abre o
    /imperdiveis é visita daquela página também."""
    r = rodar("visita", tmp_path, VISITA_CONTADA_EM="index",
              BODY_PAGINA="imperdiveis")
    assert visita(r)["pagina"] == "imperdiveis"


def test_tabela_fora_do_ar_nao_marca_a_visita_como_contada(tmp_path):
    """Se o POST não passou, a visita não existe para o banco: o próximo
    carregamento tenta de novo em vez de dar a contagem por feita. É também o
    que acontece enquanto a migration de `docs/visitas.sql` não foi aplicada."""
    r = rodar("visita_recarregada", tmp_path, RESPOSTA_STATUS="404",
              **MUNDO_INDEX)
    assert len(r["visitas"]) == 2


def test_storage_bloqueado_nao_apaga_a_contagem(tmp_path):
    """Safari privado bloqueia sessionStorage. Contar um F5 duas vezes é ruim;
    perder o denominador inteiro é pior — então sem storage, conta. E com o
    `location` bloqueado a hospedagem vira nula em vez de derrubar a contagem."""
    r = rodar("visita", tmp_path, SESSION_QUEBRADO="1", LOCATION_QUEBRADA="1",
              **MUNDO_INDEX)
    assert len(r["visitas"]) == 1
    c = visita(r)
    assert c["origem"] == "direto"
    assert c["hospedagem"] is None
    assert c["pagina"] == "index", "a página não depende do location"


# ── a contagem de visita não pode custar um cadastro ─────────────────────────

def test_a_contagem_de_visita_nao_entra_no_caminho_do_lead(sucesso):
    """O cadastro continua sendo UM POST em /leads. Telemetria misturada ao
    caminho do lead é telemetria que pode custar um cadastro."""
    assert len(sucesso["fetches"]) == 1
    assert sucesso["fetches"][0]["url"].endswith("/rest/v1/leads")
    assert len(sucesso["visitas"]) == 1


def test_contagem_de_visita_no_chao_nao_derruba_o_cadastro(tmp_path):
    """Rede fora derruba os dois POSTs. Mesmo assim o cadastro é tentado, a
    falha aparece na tela e o convite é entregue — como antes desta fatia."""
    r = rodar("falha_rede", tmp_path, **MUNDO_INDEX)
    assert r["visitas"] != [], "a visita foi tentada"
    assert len(r["fetches"]) == 1, "e o cadastro seguiu o caminho normal"
    assert r["avisoVisivel"] is True
    assert r["abertas"] == ["https://chat.whatsapp.com/F2jZYz7jPjP9JFKTvl83F9"]


# ── qual POST trouxe (utm_content → `conteudo`) ──────────────────────────────
# `origem`/`meio`/`campanha` dizem de qual CAMPANHA a pessoa veio; nenhum deles
# diz de qual POST. Dois criativos da mesma campanha viram um número só, e não
# há como ver qual traz gente e qual só faz volume. Aqui só o dado bruto entra:
# `utm_content` da URL, pela MESMA limpeza dos outros UTM, nos dois lados da
# conta (visita e cadastro). Nada de cálculo de eficiência — isso é leitura
# dele nos números, não do código.

UTM_COM_CONTEUDO = UTM_COMPLETO + "&utm_content=post-carrossel-01"


def test_o_utm_content_da_url_vira_conteudo_no_lead(tmp_path):
    c = corpo(rodar("cadastro", tmp_path, URL_BUSCA=UTM_COM_CONTEUDO))
    assert c["conteudo"] == "post-carrossel-01"
    assert (c["origem"], c["meio"], c["campanha"]) == ("instagram", "cpc", "piloto")


def test_a_visita_carrega_o_mesmo_conteudo_do_lead(tmp_path):
    """Numerador e denominador têm de quebrar pelo mesmo campo: `conteudo` só
    na `leads` daria cadastro por post sem saber quanta gente aquele post
    trouxe — de novo o numerador sem o denominador."""
    r = rodar("visita", tmp_path, URL_BUSCA=UTM_COM_CONTEUDO, **MUNDO_INDEX)
    assert visita(r)["conteudo"] == "post-carrossel-01"


def test_sem_utm_content_o_conteudo_vai_nulo_e_nada_mais_muda(cadastro_com_utm):
    """Quem chega sem `utm_content` na URL segue exatamente como antes."""
    c = corpo(cadastro_com_utm)
    assert c["conteudo"] is None
    assert (c["origem"], c["meio"], c["campanha"]) == ("instagram", "cpc", "piloto")


def test_visita_sem_utm_content_tambem_vai_nula(visita_do_index):
    assert visita(visita_do_index)["conteudo"] is None


def test_conteudo_sujo_nao_passa_e_nao_leva_a_campanha_junto(tmp_path):
    """Texto de URL vem do mundo e vai para o banco: mesma limpeza dos outros."""
    sujo = UTM_COMPLETO + "&utm_content=%3Cscript%3Ealert(1)%3C/script%3E"
    c = corpo(rodar("cadastro", tmp_path, URL_BUSCA=sujo))
    assert c["conteudo"] is None
    assert c["campanha"] == "piloto", "conteúdo sujo não pode derrubar a campanha"


def test_conteudo_gigante_e_cortado_em_120(tmp_path):
    c = corpo(rodar("cadastro", tmp_path,
                    URL_BUSCA=UTM_COMPLETO + "&utm_content=" + "b" * 300))
    assert len(c["conteudo"]) == 120


def test_o_conteudo_fica_guardado_na_sessao(tmp_path):
    import json as _json
    r = rodar("cadastro", tmp_path, URL_BUSCA=UTM_COM_CONTEUDO)
    assert _json.loads(r["origemGuardada"])["conteudo"] == "post-carrossel-01"


def test_recarregar_sem_utm_mantem_o_conteudo_da_primeira_visita(tmp_path):
    guardado = ('{"origem":"instagram","meio":"cpc","campanha":"piloto",'
                '"conteudo":"reel-03"}')
    c = corpo(rodar("cadastro", tmp_path, SESSION_GUARDADO=guardado))
    assert c["conteudo"] == "reel-03"


def test_conteudo_adulterado_na_sessao_nao_passa(tmp_path):
    """sessionStorage é do visitante: dá para editar à mão."""
    guardado = ('{"origem":"instagram","meio":"cpc","campanha":"piloto",'
                '"conteudo":"<script>x</script>"}')
    c = corpo(rodar("cadastro", tmp_path, SESSION_GUARDADO=guardado))
    assert c["conteudo"] is None
    assert c["origem"] == "instagram", "o resto da origem continua valendo"


def test_sessao_antiga_sem_o_campo_novo_nao_quebra(tmp_path):
    """Quem já estava com a página aberta quando isto subir tem na sessão um
    JSON sem `conteudo`. Não pode quebrar o cadastro: grava nulo e segue."""
    guardado = '{"origem":"tiktok","meio":"cpc","campanha":"lancamento"}'
    c = corpo(rodar("cadastro", tmp_path, SESSION_GUARDADO=guardado))
    assert c["conteudo"] is None
    assert (c["origem"], c["meio"], c["campanha"]) == ("tiktok", "cpc", "lancamento")


def test_utm_content_sem_utm_source_nao_inventa_campanha(tmp_path):
    """Sem `utm_source` não há campanha para atribuir — regra que já existia. O
    post sozinho na URL não muda isso: origem 'direto' e conteúdo nulo."""
    c = corpo(rodar("cadastro", tmp_path, URL_BUSCA="?utm_content=post-solto"))
    assert (c["origem"], c["conteudo"]) == ("direto", None)


def test_telemetria_quebrada_manda_conteudo_nulo_sem_perder_o_cadastro(tmp_path):
    r = rodar("cadastro", tmp_path, SESSION_QUEBRADO="1", LOCATION_QUEBRADA="1")
    assert corpo(r)["conteudo"] is None
    assert r["modalAtivo"] is False, "o cadastro seguiu normal"


# ── página sem grade não pode travar a tela (23/09/2026) ─────────────────────

@pytest.mark.parametrize("slug", ["geral", "smartphone", "moda", "imperdiveis"])
def test_pagina_sem_grade_nao_trava_a_rolagem_nem_rola_sozinha(tmp_path, slug):
    """Ele abriu /smartphone no Safari e no navegador do Telegram e a tela
    ficou "congelada, sem os campos": o formulário mora embaixo do topo, e o
    abrirModal travava a rolagem do body (herança do modal por cima da
    grade) e ainda agendava o foco automático no telefone."""
    r = rodar("pagina_sem_grade_nao_trava_a_tela", tmp_path, BODY_AUTOABRIR=slug)
    assert r["modalAtivo"] is True, "o formulário tem de estar aberto"
    assert r["overflowDoBody"] != "hidden"
    assert r["timersAgendados"] == 0, "nada de foco automático rolando a tela"


def test_modal_por_cima_da_grade_continua_travando_o_fundo(tmp_path):
    """Sem `data-auto-abrir` o modal é um popup de verdade: aí sim o fundo
    trava, e o foco no telefone ajuda."""
    r = rodar("modal_por_cima_da_grade_ainda_trava", tmp_path)
    assert r["overflowDoBody"] == "hidden"
    assert r["timersAgendados"] == 1


def test_toque_na_margem_da_pagina_sem_grade_nao_apaga_o_que_foi_digitado(tmp_path):
    r = rodar("toque_na_margem_da_pagina_sem_grade", tmp_path, BODY_AUTOABRIR="smartphone")
    assert r["modalAtivo"] is True
    assert r["telDepois"] == "81999998888"
