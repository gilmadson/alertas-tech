// Lógica de TODAS as páginas do AlertasTech (index.html e as exclusivas).
//
// Saiu de dentro do index.html em 18/09/2026, quando a segunda página nasceu:
// cópia de JS entre páginas é como elas ficam diferentes sem ninguém ver.
//
// Duas regras de quem incluir este arquivo:
//   1. a tag entra no FIM do <body> — a leitura de `document.body` aqui
//      embaixo acontece no carregamento, e no <head> ela seria `null`;
//   2. o caminho é RELATIVO (src="landing.js"). O GitHub Pages serve de
//      `/alertas-tech/`, e um `/landing.js` quebraria só lá, calado.

// ── CONFIG ──────────────────────────────────────────
const SUPABASE_URL  = 'https://jfuqmjbxzhoceycauhys.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImpmdXFtamJ4emhvY2V5Y2F1aHlzIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgxNzc5MDMsImV4cCI6MjA5Mzc1MzkwM30.JuBLqxfyfaRClDIvwSoiDGsDLSAVHSwTI4eAayMyLvU';

// As 8 categorias criadas em 25/08/2026 ainda não têm canal próprio no
// Telegram: o motor manda todas para o canal de "outros". A landing avisa isso
// em vez de fingir que cada uma tem o seu.
const TELEGRAM_FALLBACK = 'https://t.me/alertatechoutrosprodutos';

// Convite de WhatsApp muda quando alguém revoga, e a página não tem como
// saber. Este bloco é REESCRITO por `scripts/sincronizar_landing.py`, que
// pergunta o convite atual ao gateway do OpenWA — não edite à mão.
// GRUPOS:INICIO (gerado por scripts/sincronizar_landing.py)
const GRUPOS = {
  'geral':           { tg: null, wpp: 'https://chat.whatsapp.com/JaSa6KFkq30Ea24cJWx2za' },
  'imperdiveis':     { tg: null, wpp: 'https://chat.whatsapp.com/IqTCyshHhzkEkN7cNbG2mC' },
  'smartphone':      { tg: 'https://t.me/alertatech_smartphone', wpp: 'https://chat.whatsapp.com/F2jZYz7jPjP9JFKTvl83F9' },
  'notebook':        { tg: 'https://t.me/alertatechnotebook', wpp: 'https://chat.whatsapp.com/BDBWJS2sBvA2oGk7UfCt5L' },
  'smart-tv':        { tg: 'https://t.me/alertatechsmarttvs', wpp: 'https://chat.whatsapp.com/K1Ib4Mn00vZApwLvF6d7ST' },
  'fone-audio':      { tg: 'https://t.me/alertatechFoneseAudio', wpp: 'https://chat.whatsapp.com/EGUo43WqI4RFQFhfTVSQts' },
  'smartwatch':      { tg: 'https://t.me/alertarechsmartwatch', wpp: 'https://chat.whatsapp.com/L5aWqcj0j1RL7cQbdBNuig' },
  'tablet':          { tg: 'https://t.me/alertatechtablet', wpp: 'https://chat.whatsapp.com/LBP4X0ZvK327KDX8VyLwfs' },
  'monitor':         { tg: 'https://t.me/monitoreperiferico', wpp: 'https://chat.whatsapp.com/JRgncBgVN0CClDaQzGGYTN' },
  'armazenamento':   { tg: 'https://t.me/alertatecharmazenamento', wpp: 'https://chat.whatsapp.com/CXWxsm29bJW09IyVk68uKt' },
  'camera':          { tg: 'https://t.me/alertatechcameras', wpp: 'https://chat.whatsapp.com/CD09VogNTSx6Qcn0UTd1YU' },
  'livros':          { tg: 'https://t.me/alertatechoutrosprodutos', wpp: 'https://chat.whatsapp.com/FF2rXTfphxT93dBRBym5Bc' },
  'eletrodomestico': { tg: 'https://t.me/alertatechoutrosprodutos', wpp: 'https://chat.whatsapp.com/LoELGKzQf3JDuFiK42uphy' },
  'cozinha':         { tg: 'https://t.me/alertatechoutrosprodutos', wpp: 'https://chat.whatsapp.com/E4XruWOnsTo9y5WOz6DkBo' },
  'mesa-posta':      { tg: 'https://t.me/alertatechoutrosprodutos', wpp: 'https://chat.whatsapp.com/HPCyzUhV3mbDqznpcASIvQ' },
  'casa-moveis':     { tg: 'https://t.me/alertatechoutrosprodutos', wpp: 'https://chat.whatsapp.com/JesM9T2DaXm9n2qsZ605Tz' },
  'fitness':         { tg: 'https://t.me/alertatechoutrosprodutos', wpp: 'https://chat.whatsapp.com/HWhxKTbS5P681DplTaJWX3' },
  'beleza':          { tg: 'https://t.me/alertatechoutrosprodutos', wpp: 'https://chat.whatsapp.com/LHRp0BRxsDM5MgXmBI6VGR' },
  'salao':           { tg: null, wpp: 'https://chat.whatsapp.com/CfN9CT2HnWGGpK2qaQ2KFm' },
  'moda':            { tg: 'https://t.me/alertatechoutrosprodutos', wpp: 'https://chat.whatsapp.com/EOJprKSQGI930gRRclVan2' },
  'outros':          { tg: 'https://t.me/alertatechoutrosprodutos', wpp: 'https://chat.whatsapp.com/FFvyqzf0VflJYbR5tfPOAK' },
};
// GRUPOS:FIM

// ── ORIGEM DA VISITA ─────────────────────────────────
// Campanha sem medir origem não é campanha, é gasto. Todo lead sai daqui com
// origem preenchida: UTM da URL, senão o domínio de quem indicou, senão
// 'direto'. Lead sem origem é o que estraga relatório de campanha.
//
// `conteudo` (o `utm_content`, 22/09/2026) é o degrau seguinte: origem, meio e
// campanha dizem de qual CAMPANHA a pessoa veio, e nenhum deles diz de qual
// POST. Sem esse campo, dois criativos da mesma campanha viram um número só e
// não dá para ver qual traz gente. Aqui só o dado bruto é gravado — quem
// decide o que é eficiente é ele, olhando os números depois.
const UTM_MAX = 120;
// O valor vem da URL — ou seja, do mundo — e vai para o banco. Só passa o
// inocente; o resto é descartado, não "consertado".
const UTM_ACEITO = /^[A-Za-z0-9._+ -]+$/;
const CHAVE_ORIGEM = 'alertastech:origem';
const SEM_ORIGEM = { origem: 'direto', meio: null, campanha: null, conteudo: null };

function limparUtm(valor) {
  if (typeof valor !== 'string') return null;
  const cru = valor.trim();
  if (!cru || !UTM_ACEITO.test(cru)) return null;
  return cru.slice(0, UTM_MAX);
}

function origemDaUrl() {
  const params = new URLSearchParams(location.search || '');
  const origem = limparUtm(params.get('utm_source'));
  if (!origem) return null;   // sem source não há campanha para atribuir
  return {
    origem,
    meio: limparUtm(params.get('utm_medium')),
    campanha: limparUtm(params.get('utm_campaign')),
    conteudo: limparUtm(params.get('utm_content')),
  };
}

function origemDoReferrer() {
  try {
    const host = new URL(document.referrer).hostname.replace(/^www\./, '');
    if (!host || host === location.hostname) return null;   // navegação interna
    return { origem: host, meio: 'referrer', campanha: null, conteudo: null };
  } catch (_) {
    return null;
  }
}

function lerOrigemGuardada() {
  try {
    const bruto = JSON.parse(sessionStorage.getItem(CHAVE_ORIGEM) || 'null');
    // A sessão é do visitante: dá para editar à mão. Limpa de novo na leitura.
    const origem = bruto && limparUtm(bruto.origem);
    if (!origem) return null;
    return {
      origem,
      meio: limparUtm(bruto.meio),
      campanha: limparUtm(bruto.campanha),
      // Sessão aberta antes de 22/09/2026 não tem este campo: `undefined` sai
      // daqui como null, sem derrubar a origem que ela já guardava.
      conteudo: limparUtm(bruto.conteudo),
    };
  } catch (_) {
    return null;
  }
}

function guardarOrigem(origem) {
  try {
    sessionStorage.setItem(CHAVE_ORIGEM, JSON.stringify(origem));
  } catch (_) {}   // Safari privado bloqueia storage — e nem por isso perdemos o lead
  return origem;
}

function origemDaVisita() {
  const daUrl = origemDaUrl();
  if (daUrl) return guardarOrigem(daUrl);          // clique de campanha é explícito
  const guardada = lerOrigemGuardada();
  if (guardada) return guardada;                   // recarregou sem UTM: vale a 1ª visita
  return guardarOrigem(origemDoReferrer() || SEM_ORIGEM);
}

let origemMemo = null;
function origemParaEnviar() {
  if (!origemMemo) {
    try {
      origemMemo = origemDaVisita();
    } catch (_) {
      origemMemo = SEM_ORIGEM;   // telemetria nunca custa um cadastro
    }
  }
  return origemMemo;
}

// ── CONTAGEM DE VISITA ───────────────────────────────
// Até 22/09/2026 havia contagem de CADASTRO e nenhuma de visita: o numerador
// sem o denominador. Sem saber quanta gente entra não existe taxa de conversão
// visita→cadastro, e sem taxa nenhuma mudança na página pode ser provada boa —
// foi esse o motivo de um redesenho inteiro ser vetado.
//
// A contagem mora no MESMO Supabase dos leads, e não no Analytics do Vercel,
// porque a página é servida por duas hospedagens (Vercel e GitHub Pages) e as
// duas recebem gente: medida que vê metade da casa é medida que engana.
// Tabela e policy em `docs/visitas.sql` — insert-only, como a `leads`.
//
// Sem dado pessoal: qual página, de onde veio, em qual hospedagem. O instante
// é o `criado_em` do banco.
const CHAVE_VISITA = 'alertastech:visita:';

// Cada página DECLARA o próprio nome em `<body data-pagina="...">`, do mesmo
// jeito que a exclusiva declara a loja fixa. Deduzir do caminho não serve: o
// Vercel serve `/imperdiveis` e o GitHub Pages serve
// `/alertas-tech/imperdiveis.html` — o mesmo arquivo viraria duas linhas
// diferentes no relatório. Quem esquecer de declarar aparece como
// 'nao-declarada', que é o dado gritando em vez de somar no balde errado.
function paginaAtual() {
  return document.body.dataset.pagina || 'nao-declarada';
}

function hospedagemAtual() {
  try {
    return location.hostname || null;
  } catch (_) {
    return null;
  }
}

// F5 não é visita nova. A marca é por página: quem foi contado no index e
// depois abre o /imperdiveis é visita daquela página também.
function visitaJaContada(pagina) {
  try {
    return sessionStorage.getItem(CHAVE_VISITA + pagina) === '1';
  } catch (_) {
    return false;   // storage bloqueado conta de novo: perder o denominador é pior
  }
}

function marcarVisitaContada(pagina) {
  try {
    sessionStorage.setItem(CHAVE_VISITA + pagina, '1');
  } catch (_) {}
}

// Dispara e segue: ninguém espera por isto. Contagem de visita é telemetria,
// igual ao Pixel e à origem — não pode segurar a página nem custar um cadastro,
// então nada aqui escapa para fora.
async function registrarVisita() {
  const pagina = paginaAtual();
  if (visitaJaContada(pagina)) return false;
  const daVisita = origemParaEnviar();
  const visita = {
    pagina,
    hospedagem: hospedagemAtual(),
    origem: daVisita.origem,
    meio: daVisita.meio,
    campanha: daVisita.campanha,
    conteudo: daVisita.conteudo,
  };
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/visitas`, {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_ANON,
        'Authorization': `Bearer ${SUPABASE_ANON}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
      },
      body: JSON.stringify(visita),
    });
    // Não passou, não aconteceu: sem marca, o próximo carregamento tenta de
    // novo em vez de dar a contagem por feita. É o que roda enquanto a
    // migration de `docs/visitas.sql` não foi aplicada (404).
    if (!res.ok) return false;
    marcarVisitaContada(pagina);
    return true;
  } catch (_) {
    return false;
  }
}

// ── STATE ────────────────────────────────────────────
let categoriaAtual = '';
let plataformaEscolhida = '';
const BOT_THRESHOLD_MS = 1500;
let modalAbertaEm = 0;
let consentimentoEm = null;

// O instante do ACEITE, não o do envio: é essa a prova que a LGPD pede como
// base legal (art. 7º, I) e é ela que sustenta o link de afiliado — a política
// de Associados da Amazon só admite comunicação "desde que tais comunicações
// sejam solicitadas". Sem o aceite guardado, não há como mostrar que foi.
function marcarConsentimento() {
  consentimentoEm = document.getElementById('consent-check').checked
    ? new Date().toISOString()
    : null;
  checarCampos();
}

// ── VALIDAÇÃO ────────────────────────────────────────
const LOJA_IDS = ['loja-ml', 'loja-amz', 'loja-mag', 'loja-shp', 'loja-ali', 'loja-kbm'];

// A página geral deixa escolher as lojas; as exclusivas não, porque a origem
// delas é fixa — o grupo do Imperdíveis ML só recebe Mercado Livre, e oferecer
// caixa de Amazon ali seria promessa que o grupo não cumpre. A página DECLARA
// isso em `<body data-lojas="mercadolivre">`: ausência de caixa não vale como
// decisão, porque elemento que some é drift e não escolha.
const LOJAS_FIXAS = (document.body.dataset.lojas || '')
  .split(',').map(s => s.trim()).filter(Boolean);

// "Ofertas gerais" promete "qualquer loja, não quero escolher" — mas até
// 22/09/2026 pedia pra marcar as 6 caixas de loja uma por uma mesmo assim.
// Foi exatamente esse contraste que o Gilmadson gravou no próprio teste
// (22/09/2026): tocou "não quero escolher" e teve que escolher assim mesmo.
// Agora as duas categorias "sem escolha" não mostram a seção de lojas — a
// loja gravada é a verdadeira de cada grupo (todas pro Ofertas gerais, só
// Mercado Livre pro Imperdíveis ML), nunca uma lista genérica. E quem clica
// em "Ofertas gerais" é sorteado, sem ver a escolha, entre os dois grupos que
// já existem pra quem não quer escolher — pedido dele, pra não lotar sempre
// o mesmo.
const LOJAS_SEM_ESCOLHA = {
  geral:       ['mercadolivre', 'amazon', 'magalu', 'shopee', 'aliexpress', 'kabum'],
  imperdiveis: ['mercadolivre'],
};

function sortearCategoriaSemEscolha() {
  return Math.random() < 0.5 ? 'geral' : 'imperdiveis';
}

function getLojasEscolhidas() {
  if (LOJAS_FIXAS.length) return LOJAS_FIXAS;
  if (LOJAS_SEM_ESCOLHA[categoriaAtual]) return LOJAS_SEM_ESCOLHA[categoriaAtual];
  return LOJA_IDS
    .map(id => document.getElementById(id))
    .filter(el => el.checked)
    .map(el => el.value);
}

// A caixa "Não sou um robô" saiu em 23/09/2026 (pedido dele, pra reduzir
// toque): ela era decorativa — um clique não prova humanidade nenhuma. A
// proteção de verdade já roda escondida e continua aqui: o campo-isca
// (`hp-field`) e a trava de 1,5s (`BOT_THRESHOLD_MS`, em `submeterLead`).
function checarCampos() {
  const tel      = document.getElementById('lead-tel').value.replace(/\D/g, '');
  const consent  = document.getElementById('consent-check').checked;
  const lojas    = getLojasEscolhidas();
  const ok       = tel.length >= 8 && consent && lojas.length > 0;
  document.getElementById('btn-whatsapp').disabled = !ok;
  document.getElementById('btn-telegram').disabled = !ok;
}

// ── MODAL ────────────────────────────────────────────
function abrirModal(emoji, nome, slug) {
  // O sorteio acontece aqui, uma vez, e o resultado vira a categoria de
  // verdade pro resto da função — GRUPOS, loja gravada e destino do convite
  // são todos do grupo sorteado. `slug`/`nome` continuam sendo o que a
  // pessoa clicou (o card não muda de nome na tela: ela não vê o sorteio).
  categoriaAtual = slug === 'geral' ? sortearCategoriaSemEscolha() : slug;
  document.getElementById('modal-emoji').textContent = emoji;
  document.getElementById('modal-nome').textContent = nome;
  document.getElementById('form-erro').textContent = '';
  document.getElementById('lead-nome').value = '';
  document.getElementById('lead-email').value = '';
  document.getElementById('lead-tel').value = '';
  document.getElementById('hp-field').value = '';
  document.getElementById('consent-check').checked = false;
  consentimentoEm = null;
  document.getElementById('consent-cat').textContent =
    slug === 'geral' ? 'ofertas que eu escolher' : nome;
  limparAviso();
  // As categorias novas ainda não têm canal próprio no Telegram. Dizer isso é
  // melhor que a pessoa entrar num canal com outro nome e achar que errou.
  const links = GRUPOS[categoriaAtual] || {};
  document.getElementById('tg-nota').textContent =
    (links.tg === TELEGRAM_FALLBACK && categoriaAtual !== 'outros')
      ? 'No Telegram esta categoria sai no canal Outros Tech — o canal próprio ainda não existe.'
      : '';
  // Sem canal no Telegram (é o caso das ofertas gerais) o botão some: botão que
  // não leva a lugar nenhum é promessa quebrada.
  document.getElementById('btn-telegram').style.display = links.tg ? '' : 'none';
  // Página com loja fixa não tem essas caixas: procurar por elas ali seria
  // `null.checked` e o modal morria antes de abrir. Mesmo raciocínio vale pra
  // categoria sorteada: a seção some, e o texto conta o que é verdade agora.
  if (!LOJAS_FIXAS.length) {
    const semEscolha = !!LOJAS_SEM_ESCOLHA[categoriaAtual];
    document.getElementById('lojas-section').style.display = semEscolha ? 'none' : '';
    document.getElementById('modal-subtitle').textContent = semEscolha
      ? 'Deixa seu contato — a gente cuida do resto.'
      : 'Deixa seu contato e escolha de quais lojas quer receber alertas.';
    if (!semEscolha) {
      LOJA_IDS.forEach(id => document.getElementById(id).checked = id === 'loja-ml');
    }
  }
  document.getElementById('btn-whatsapp').disabled = true;
  document.getElementById('btn-telegram').disabled = true;
  modalAbertaEm = Date.now();
  document.getElementById('modal').classList.add('active');
  // Em página sem grade (`data-auto-abrir`) o formulário É a página, não um
  // popup: travar a rolagem e focar o telefone sozinho deixava a tela
  // "congelada, sem os campos" no Safari e no navegador do Telegram (ele,
  // 23/09/2026).
  if (document.body.dataset.autoAbrir) return;
  document.body.style.overflow = 'hidden';
  setTimeout(() => document.getElementById('lead-tel').focus(), 300);
}

function fecharModal(e) {
  if (e && e.target !== document.getElementById('modal')) return;
  // Sem popup não existe "tocar fora pra fechar": o toque na margem em volta
  // do formulário reabria tudo e apagava o que a pessoa já tinha digitado.
  if (e && autoAbrir) return;
  // Página sem grade (`data-auto-abrir`) não tem pra onde "voltar" — a
  // grade já está escondida por CSS. Fechar do jeito normal deixava a
  // pessoa numa tela vazia até dar F5 (achado do projeto-arquiteto,
  // 23/09/2026). Cancelar reabre o mesmo formulário limpo, igual ao clique
  // automático do carregamento.
  if (autoAbrir) {
    const card = document.querySelector(`.cat-card[data-slug="${autoAbrir}"]`);
    if (card) { card.click(); return; }
  }
  document.getElementById('modal').classList.remove('active');
  document.body.style.overflow = '';
}

// ── DESTINO E AVISOS ─────────────────────────────────
function destinoDaCategoria() {
  const links = GRUPOS[categoriaAtual] || {};
  if (plataformaEscolhida === 'tg' && links.tg) return links.tg;
  return links.wpp || null;
}

// iOS Safari só deixa `window.open` criar aba dentro do mesmo gesto síncrono
// do toque. Uma chamada depois de um `await` (o POST no Supabase, por
// exemplo) é barrada em silêncio, sem erro nenhum para capturar — foi
// exatamente o que aconteceu com o Gilmadson em 22/09/2026: tocou "Entrar
// pelo WhatsApp", o cadastro gravou (linha 16 da `leads`), e a aba do grupo
// nunca abriu. Por isso a abertura virou duas etapas: `abrirJanela` cria a
// aba em branco ainda dentro do toque (síncrono, nunca barrado), e
// `apontarJanela` só manda essa aba já existente para o destino depois que o
// cadastro terminar — apontar uma aba que já existe não é gesto novo, então
// o Safari deixa.
function abrirJanela(destino) {
  if (!destino) return null;
  return window.open('', '_blank');
}

function apontarJanela(janela, destino) {
  if (!janela || !destino) return false;
  janela.location = destino;
  return true;
}

function limparAviso() {
  const aviso = document.getElementById('form-aviso');
  aviso.innerHTML = '';
  aviso.classList.remove('ativo');
}

function mostrarAviso(html) {
  const aviso = document.getElementById('form-aviso');
  aviso.innerHTML = html;
  aviso.classList.add('ativo');
}

function linkManual(destino) {
  return destino
    ? ' <a href="' + destino + '" target="_blank" rel="noopener">Abrir o grupo aqui</a>.'
    : ' Não achei o link do grupo — fale com o administrador.';
}

// Antes desta função a página fingia sucesso: o cadastro falhava, ninguém
// via nada e nenhum lead era gravado. Falha silenciosa é o inimigo.
function mostrarFalhaDeCadastro(detalhe, destino) {
  mostrarAviso('⚠️ Não consegui salvar seu cadastro (' + detalhe + '). ' +
    'Seu convite para o grupo continua valendo, mas para receber os alertas ' +
    'no seu WhatsApp tente de novo daqui a pouco.' + linkManual(destino));
}

async function salvarLead(dados) {
  try {
    const res = await fetch(`${SUPABASE_URL}/rest/v1/leads`, {
      method: 'POST',
      headers: {
        'apikey': SUPABASE_ANON,
        'Authorization': `Bearer ${SUPABASE_ANON}`,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal',
      },
      body: JSON.stringify(dados),
    });
    return res.ok ? { ok: true } : { ok: false, detalhe: 'erro ' + res.status };
  } catch (err) {
    return { ok: false, detalhe: 'sem conexão' };
  }
}

// ── SUBMISSÃO ────────────────────────────────────────
async function submeterLead(e) {
  e.preventDefault();
  const btn = e.submitter;
  plataformaEscolhida = btn ? btn.dataset.plat : 'wpp';

  const nome  = document.getElementById('lead-nome').value.trim();
  const email = document.getElementById('lead-email').value.trim() || null;
  const tel   = document.getElementById('lead-tel').value.replace(/\D/g, '');
  const lojas = getLojasEscolhidas();
  const erro  = document.getElementById('form-erro');
  limparAviso();

  if (tel.length < 8) {
    erro.textContent = 'Digite um número de WhatsApp válido com DDD.';
    return;
  }

  if (lojas.length === 0) {
    erro.textContent = 'Selecione pelo menos uma loja.';
    return;
  }

  // Sem consentimento não sai nada: nem o POST, nem o convite.
  if (!document.getElementById('consent-check').checked) {
    erro.textContent = 'Marque a autorização para eu poder te mandar as ofertas.';
    return;
  }

  if (document.getElementById('hp-field').value) return;

  const destino = destinoDaCategoria();

  // Rápido demais para ser gente. Antes daqui saía convite aberto e modal
  // fechado SEM nem tentar gravar: sucesso perfeito e zero linha no banco.
  // Agora barra e diz o motivo — quem é gente toca de novo e passa.
  if (Date.now() - modalAbertaEm < BOT_THRESHOLD_MS) {
    erro.textContent = 'Isso foi rápido demais. Toque no botão de novo, por favor.';
    return;
  }

  btn && (btn.disabled = true, btn.textContent = 'Entrando...');

  const janela = abrirJanela(destino);   // síncrono: ainda dentro do toque

  const origem = origemParaEnviar();
  const resultado = await salvarLead({
    nome: nome || null,
    email,
    telefone: tel,
    categoria: categoriaAtual,
    plataforma: plataformaEscolhida,   // 'wpp' ou 'tg': o banco tem CHECK
    lojas: lojas.join(','),
    consentimento: true,               // só chega aqui com a caixa marcada
    consentimento_em: consentimentoEm || new Date().toISOString(),
    origem: origem.origem,
    meio: origem.meio,
    campanha: origem.campanha,
    conteudo: origem.conteudo,
  });

  const abriu = apontarJanela(janela, destino);

  if (!resultado.ok) {
    mostrarFalhaDeCadastro(resultado.detalhe, destino);
  } else {
    // Pixel é telemetria, nunca gate: cadastro já foi salvo antes desta linha,
    // e ad blocker (fbq indefinido) ou exceção aqui não pode voltar a fingir
    // falha nem segurar o convite — mesma regra de origemParaEnviar().
    try {
      if (typeof fbq === 'function') fbq('track', 'Lead', { content_category: categoriaAtual });
    } catch (_) {}
    if (!abriu) {
      mostrarAviso('Seu cadastro foi salvo. O navegador segurou a aba do grupo:' +
                   linkManual(destino));
    } else {
      fecharModal();
    }
  }

  if (btn) { btn.disabled = false; btn.textContent = plataformaEscolhida === 'tg' ? '✈️ Entrar pelo Telegram' : '💬 Entrar pelo WhatsApp'; }
}

// ── ABERTURA AUTOMÁTICA (páginas de propósito único) ─
// `data-auto-abrir="<slug>"` no <body> clica sozinho no card dessa categoria
// ao carregar. Corrigido 18/09/2026 à noite: tentei um botão sem formulário
// ("entrada direta"), mas ele PARA de capturar o lead — o Gilmadson quer o
// contrário: nome/e-mail/telefone visíveis (autopreenchidos pelo celular
// sempre que ele tiver salvo antes — os 3 campos já têm autocomplete
// correto), o botão habilita ao preencher. Volta a ser isto.
//
// Desde 23/09/2026 o `index.html` também usa este padrão (slug `geral`): a
// grade de 21 categorias saiu de lá depois de medir que 15 delas nunca
// tiveram um cadastro sequer. `fecharModal` (acima) reusa este mesmo
// `autoAbrir` pra saber quando "Cancelar" tem de reabrir o formulário em vez
// de fechar — nesta variável abaixo é onde ele nasce.
const autoAbrir = document.body.dataset.autoAbrir;
if (autoAbrir) {
  const card = document.querySelector(`.cat-card[data-slug="${autoAbrir}"]`);
  if (card) card.click();
}

// Guarda a origem já no carregamento: se a pessoa chegou por campanha e só se
// cadastrar depois de dar uma volta pela página, a origem real dela não se perde.
origemParaEnviar();

// E conta a visita — depois da origem, que é ela quem diz de onde a pessoa
// veio. Sem `await`: a página não espera telemetria.
registrarVisita();
